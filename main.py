import asyncio
import logging
import time
from pathlib import Path
from typing import Optional, List, Generator
import pyarrow as pa
import pyarrow.parquet as pq
import numpy as np

from rag_primitive.core.config import settings, setup_directories
from rag_primitive.core.logging import setup_logging
from rag_primitive.core.utils import batch_iterator
from rag_primitive.acquisition.crawler import NDLCrawler
from rag_primitive.processing.chunker import SpeechChunker
from rag_primitive.embedding.model import SpeechEmbedder
from rag_primitive.storage.lancedb_client import LanceDBClient
from rag_primitive.schemas.speech import MeetingResponse
from rag_primitive.schemas.chunk import Chunk

logger = logging.getLogger("rag_primitive.main")

async def run_phase_1(crawler: NDLCrawler) -> Path:
    """Phase 1: Acquisition (ID or Range)"""
    start = time.time()
    logger.info(f"[bold blue]--- Phase 1: Acquisition ---[/bold blue]")
    if settings.TARGET_ISSUE_ID and settings.TARGET_ISSUE_ID != "YOUR_TARGET_ISSUE_ID":
         await crawler.save_meeting_to_jsonl(settings.TARGET_ISSUE_ID)
    else:
         await crawler.crawl_range(settings.from_date, settings.to_date)
    
    elapsed = time.time() - start
    logger.info(f"Phase 1 finished in {elapsed:.2f}s")
    return settings.RAW_DATA_DIR

async def run_phase_2_chunking(raw_dir: Path):
    """Phase 2 (Part 1): Chunking (Raw JSONL -> Chunked JSONL)"""
    start = time.time()
    logger.info(f"[bold blue]--- Phase 2-1: Chunking ---[/bold blue]")

    chunker = SpeechChunker()
    total_chunks = 0
    for file in raw_dir.glob("*.jsonl"):
        issue_id = file.stem
        output_path = settings.PROCESSED_DATA_DIR / f"{issue_id}.chunks.jsonl"

        if output_path.exists():
            continue

        chunk_count = 0
        with open(file, "r", encoding="utf-8") as f_in, \
             open(output_path, "w", encoding="utf-8") as f_out:
            for line in f_in:
                if not line.strip(): continue
                try:
                    response = MeetingResponse.model_validate_json(line)
                    for meeting in response.meeting_records:
                        for chunk in chunker.generate_chunks(meeting):
                            f_out.write(chunk.model_dump_json() + "\n")
                            chunk_count += 1
                except Exception as e:
                    logger.error(f"Error processing line in {file}: {e}")
        
        total_chunks += chunk_count
    
    elapsed = time.time() - start
    logger.info(f"Phase 2-1 finished in {elapsed:.2f}s (Total chunks generated: {total_chunks})")

async def run_phase_2_embedding(chunk_dir: Path):
    """Phase 2 (Part 2): Embedding (Chunked JSONL -> Embedded Parquet)"""
    start = time.time()
    logger.info(f"[bold blue]--- Phase 2-2: Embedding ---[/bold blue]")

    embedder = SpeechEmbedder()
    client = LanceDBClient()
    schema = client._get_schema(vector_dim=embedder.dimension)

    total_embedded = 0
    for path in chunk_dir.glob("*.chunks.jsonl"):
        issue_id = path.name.replace(".chunks.jsonl", "")
        output_path = settings.PROCESSED_DATA_DIR / f"{issue_id}.embedded.parquet"
    
        if output_path.exists():
            continue

        def chunk_loader(file_path: Path) -> Generator[Chunk, None, None]:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    yield Chunk.model_validate_json(line)

        chunks: List[Chunk] = []
        vectors_list = []

        for batch in batch_iterator(chunk_loader(path), settings.BATCH_SIZE):
            texts = [c.content for c in batch]
            embeddings_tensor = embedder.encode(texts)
            embeddings_np = embeddings_tensor.cpu().numpy()
            
            chunks.extend(batch)
            vectors_list.append(embeddings_np)

        if not vectors_list:
            continue
        
        all_vectors = np.vstack(vectors_list)
        vector_array = pa.FixedSizeListArray.from_arrays(
            pa.array(all_vectors.flatten(), type=pa.float32()), 
            embedder.dimension
        )

        table = pa.Table.from_pydict({
            "chunk_id": [c.chunk_id for c in chunks],
            "speech_id": [c.speech_id for c in chunks],
            "content": [c.content for c in chunks],
            "speaker": [c.speaker for c in chunks],
            "date": [c.date for c in chunks],
            "meeting_name": [c.meeting_name for c in chunks],
            "vector": vector_array,
        }, schema=schema)
        
        pq.write_table(table, output_path)
        total_embedded += len(chunks)

    elapsed = time.time() - start
    logger.info(f"Phase 2-2 finished in {elapsed:.2f}s (Total chunks embedded: {total_embedded})")

async def run_phase_3(embedded_dir: Path):
    """Phase 3: Storage (Embedded Parquet -> LanceDB)"""
    start = time.time()
    logger.info(f"[bold blue]--- Phase 3: Storage ---[/bold blue]")
    
    client = LanceDBClient()
    total_upserted = 0
    for file in embedded_dir.glob("*.embedded.parquet"):
        table = pq.read_table(file)
        client.upsert_data(table)
        total_upserted += len(table)

    elapsed = time.time() - start
    logger.info(f"Phase 3 finished in {elapsed:.2f}s (Total rows upserted: {total_upserted})")

async def main():
    setup_logging()
    setup_directories()
    
    logger.info("[bold magenta]Starting RAG Primitive End-to-End Pipeline[/bold magenta]")

    total_start = time.time()

    crawler = NDLCrawler()
    # Phase 1: クロール
    raw_dir = await run_phase_1(crawler)

    # Phase 2: チャンク化 & ベクトル化
    await run_phase_2_chunking(raw_dir)
    await run_phase_2_embedding(settings.PROCESSED_DATA_DIR)

    # Phase 3: 格納
    await run_phase_3(settings.PROCESSED_DATA_DIR)

    total_elapsed = time.time() - total_start
    logger.info(f"[bold cyan]Pipeline finished successfully! Total time: {total_elapsed:.2f}s[/bold cyan]")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user.")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
