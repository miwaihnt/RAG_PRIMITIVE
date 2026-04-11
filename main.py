import asyncio
import logging
import json
from pathlib import Path
from typing import Optional, List, Generator
import pyarrow as pa
import pyarrow.parquet as pq

from rag_primitive.core.config import settings
from rag_primitive.core.logging import setup_logging
from rag_primitive.core.utils import batch_iterator
from rag_primitive.acquisition.crawler import NDLCrawler
from rag_primitive.processing.chunker import SpeechChunker
from rag_primitive.embedding.model import SpeechEmbedder
from rag_primitive.schemas.speech import MeetingResponse
from rag_primitive.schemas.chunk import Chunk

# ロガーの取得
logger = logging.getLogger("rag_primitive.main")


async def run_phase_1(crawler: NDLCrawler, target_id: str) -> Optional[Path]:
    """Phase 1: Acquisition (API -> Raw JSONL)"""
    logger.info(f"[bold blue]--- Phase 1: Acquisition ---[/bold blue]")
    path = await crawler.save_meeting_to_jsonl(target_id)
    return path


async def run_phase_2_chunking(raw_path: Path) -> Optional[Path]:
    """Phase 2 (Part 1): Chunking (Raw JSONL -> Chunked JSONL)"""
    logger.info(f"[bold blue]--- Phase 2: Processing (Chunking) ---[/bold blue]")
    
    issue_id = raw_path.stem
    output_path = settings.PROCESSED_DATA_DIR / f"{issue_id}.chunks.jsonl"
    
    if output_path.exists():
        logger.info(f"Chunked data already exists: [yellow]{output_path}[/yellow]. Skipping.")
        return output_path

    chunker = SpeechChunker()
    chunk_count = 0

    with open(raw_path, "r", encoding="utf-8") as f_in, \
         open(output_path, "w", encoding="utf-8") as f_out:
        
        for line in f_in:
            if not line.strip(): continue
            response = MeetingResponse.model_validate_json(line)
            for meeting in response.meeting_records:
                for chunk in chunker.generate_chunks(meeting):
                    f_out.write(chunk.model_dump_json() + "\n")
                    chunk_count += 1
    
    logger.info(f"Successfully generated [bold green]{chunk_count}[/bold green] chunks.")
    return output_path


async def run_phase_2_embedding(chunk_path: Path) -> Optional[Path]:
    """Phase 2 (Part 2): Embedding (Chunked JSONL -> Embedded Parquet)"""
    logger.info(f"[bold blue]--- Phase 2: Processing (Embedding) ---[/bold blue]")
    
    issue_id = chunk_path.stem.split('.')[0]
    output_path = settings.PROCESSED_DATA_DIR / f"{issue_id}.embedded.parquet"
    
    if output_path.exists():
        logger.info(f"Embedded data already exists: [yellow]{output_path}[/yellow]. Skipping.")
        return output_path

    # モデルのロード
    embedder = SpeechEmbedder()
    
    chunks: List[Chunk] = []
    vectors_list = []

    # 1. チャンクを読み込むジェネレータ
    def chunk_loader() -> Generator[Chunk, None, None]:
        with open(chunk_path, "r", encoding="utf-8") as f:
            for line in f:
                yield Chunk.model_validate_json(line)

    # 2. バッチ処理でベクトル化 (O(1) メモリ)
    # チャンクを読み込み、バッチサイズごとにエンベッダーへ流す
    for batch in batch_iterator(chunk_loader(), settings.BATCH_SIZE):
        texts = [c.content for c in batch]
        # 推論実行 (Torch Tensor が返ってくる)
        embeddings_tensor = embedder.encode(texts)
        # Arrow 変換のために CPU NumPy に変換 (ここだけはコピーが必要よ)
        embeddings_np = embeddings_tensor.cpu().numpy()
        
        # 保存用にデータを溜める (1会議分ならメモリに載るわ)
        chunks.extend(batch)
        vectors_list.append(embeddings_np)

    import numpy as np
    all_vectors = np.vstack(vectors_list)

    # 3. PyArrow を使った格納 (Zero-copy への布石)
    # 各フィールドを Arrow 形式に変換
    table_data = {
        "chunk_id": [c.chunk_id for c in chunks],
        "speech_id": [c.speech_id for c in chunks],
        "content": [c.content for c in chunks],
        "speaker": [c.speaker for c in chunks],
        "date": [c.date for c in chunks],
        "meeting_name": [c.meeting_name for c in chunks],
        "vector": [list(v) for v in all_vectors], # LanceDB 用の形式
    }
    
    table = pa.Table.from_pydict(table_data)
    pq.write_table(table, output_path)
    
    logger.info(f"Successfully embedded [bold green]{len(chunks)}[/bold green] chunks.")
    logger.info(f"Saved to: [bold green]{output_path}[/bold green]")
    return output_path


async def main():
    setup_logging()
    logger.info("[bold magenta]Starting RAG Primitive End-to-End Pipeline[/bold magenta]")

    crawler = NDLCrawler()
    target_id = settings.TARGET_ISSUE_ID

    # Step 1: Acquisition
    raw_path = await run_phase_1(crawler, target_id)
    if not raw_path: return

    # Step 2-1: Chunking
    chunk_path = await run_phase_2_chunking(raw_path)
    if not chunk_path: return

    # Step 2-2: Embedding
    embedded_path = await run_phase_2_embedding(chunk_path)
    
    if embedded_path:
        logger.info("[bold cyan]Phase 2 Complete: Text turned into Numbers![/bold cyan]")
    else:
        logger.error("Phase 2 Embedding failed.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user.")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
