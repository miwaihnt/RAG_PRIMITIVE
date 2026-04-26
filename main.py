import os
import asyncio
import logging
import time
from pathlib import Path
from typing import Optional, List, Generator
import pyarrow as pa
import pyarrow.parquet as pq
import numpy as np
from concurrent.futures import ProcessPoolExecutor

from rag_primitive.core.config import settings, setup_directories
from rag_primitive.core.logging import setup_logging
from rag_primitive.core.utils import batch_iterator
from rag_primitive.acquisition.api_client import NDLAPIClient
from rag_primitive.processing.chunker import SpeechChunker
from rag_primitive.embedding.model import SpeechEmbedder
from rag_primitive.storage.lancedb_client import LanceDBClient
from rag_primitive.schemas.speech import MeetingResponse
from rag_primitive.schemas.chunk import Chunk

logger = logging.getLogger("rag_primitive.main")

# --- 同期的な力仕事（別プロセス/スレッドで動かす関数たち） ---

def exec_chunk(file: Path) -> Path:
    """CPU仕事：チャンキングしてファイルに書き出す"""
    pid = os.getpid()
    chunker = SpeechChunker()
    issue_id = file.stem
    output_path = settings.PROCESSED_DATA_DIR / f"{issue_id}.chunks.jsonl"

    if not output_path.exists():
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
        logger.info(f"[Process {pid}] Finished: {file.name} (Chunks: {chunk_count})")
    return output_path

def exec_embedding_sync(file_path: Path, embedder: SpeechEmbedder, lancedb_client: LanceDBClient) -> Path:
    """I/O & GPU仕事：ベクトル化してParquetに書き出す（同期版）"""
    issue_id = file_path.name.replace(".chunks.jsonl", "")
    output_path = settings.PROCESSED_DATA_DIR / f"{issue_id}.embedded.parquet"
    schema = lancedb_client._get_schema(vector_dim=embedder.dimension)

    if not output_path.exists():
        def chunk_loader(fp: Path) -> Generator[Chunk, None, None]:
            with open(fp, "r", encoding="utf-8") as f:
                for line in f:
                    yield Chunk.model_validate_json(line)

        logger.info(f"🔮 Embedding starting: {issue_id}")
        with pq.ParquetWriter(output_path, schema) as writer:
            for batch in batch_iterator(chunk_loader(file_path), settings.BATCH_SIZE):
                texts = [c.content for c in batch]
                embeddings_tensor = embedder.encode(texts)
                embeddings_np = embeddings_tensor.cpu().numpy()

                vector_array = pa.FixedSizeListArray.from_arrays(
                    pa.array(embeddings_np.flatten(), type=pa.float32()),
                    embedder.dimension
                )

                table = pa.Table.from_pydict({
                    "chunk_id": [c.chunk_id for c in batch],
                    "speech_id": [c.speech_id for c in batch],
                    "content": [c.content for c in batch],
                    "speaker": [c.speaker for c in batch],
                    "date": [c.date for c in batch],
                    "meeting_name": [c.meeting_name for c in batch],
                    "vector": vector_array
                }, schema=schema)

                writer.write_table(table)
        logger.info(f"✨ Embedding finished: {issue_id}")
    
    return output_path

def exec_storage_sync(file_path: Path, client: LanceDBClient) -> int:
    """I/O仕事：Parquetを読み込んでLanceDBに格納する"""
    table = pq.read_table(file_path)
    client.upsert_data(table)
    return len(table)


# --- 非同期ワーカー（イベントループで並行に動く役者たち） ---

async def acquisition_worker(out_q: asyncio.Queue) -> None:
    client = NDLAPIClient()
    logger.info(f"🚀 Acquisition Worker started: {settings.from_date} to {settings.to_date}")

    async for record in client.stream_meetings(from_date=settings.from_date, to_date=settings.to_date, max_records_per_request=10):
        response_obj = MeetingResponse(
            number_of_records=1,
            meeting_records=[record]
        )
        output_path = settings.RAW_DATA_DIR / f"{record.issue_id}.jsonl"
        
        if not output_path.exists():
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(response_obj.model_dump_json(by_alias=True))
            logger.info(f"💾 Saved raw: {record.issue_id}")
 
        await out_q.put(output_path)

    await out_q.put(None)
    logger.info("🏁 Acquisition Worker finished")

async def chunk_worker(in_q: asyncio.Queue, out_q: asyncio.Queue) -> None:
    loop = asyncio.get_running_loop()
    with ProcessPoolExecutor(max_workers=2) as executor:
        logger.info("🚀 Chunking Worker started")
        while True:
            file_path = await in_q.get()
            if file_path is None:
                await out_q.put(None)
                in_q.task_done()
                break
            
            chunk_file_path = await loop.run_in_executor(executor, exec_chunk, file_path)
            await out_q.put(chunk_file_path)
            in_q.task_done()
    logger.info("🏁 Chunking Worker finished")

async def embedding_worker(in_q: asyncio.Queue, out_q: asyncio.Queue) -> None:
    embedder = SpeechEmbedder()
    client = LanceDBClient()
    loop = asyncio.get_running_loop()
    logger.info("🚀 Embedding Worker started")

    while True:
        chunk_file = await in_q.get()
        if chunk_file is None:
            await out_q.put(None)
            in_q.task_done()
            break
        
        # スレッドプール（None）を使って重い処理を逃がすわよ！
        embedded_file = await loop.run_in_executor(None, exec_embedding_sync, chunk_file, embedder, client)
        await out_q.put(embedded_file)
        in_q.task_done()
    logger.info("🏁 Embedding Worker finished")

async def storage_worker(in_q: asyncio.Queue) -> None:
    client = LanceDBClient()
    loop = asyncio.get_running_loop()
    logger.info("🚀 Storage Worker started")

    while True:
        embedded_file = await in_q.get()
        if embedded_file is None:
            in_q.task_done()
            break
        
        # ストレージ格納もスレッドに逃がす！
        count = await loop.run_in_executor(None, exec_storage_sync, embedded_file, client)
        logger.info(f"📦 Storage: Upserted {count} chunks from {embedded_file.name}")
        in_q.task_done()
    logger.info("🏁 Storage Worker finished")


# --- メインエントリーポイント ---

async def main():
    setup_logging()
    setup_directories()
    
    logger.info("[bold magenta]Starting RAG Primitive Streaming Pipeline[/bold magenta]")
    total_start = time.time()

    # キューの作成 (maxsize で背圧をかける！)
    raw_q = asyncio.Queue(maxsize=10)
    chunk_q = asyncio.Queue(maxsize=10)
    vector_q = asyncio.Queue(maxsize=10)

    # ワーカーを並行起動！
    await asyncio.gather(
        acquisition_worker(raw_q),
        chunk_worker(raw_q, chunk_q),
        embedding_worker(chunk_q, vector_q),
        storage_worker(vector_q)
    )

    total_elapsed = time.time() - total_start
    logger.info(f"[bold cyan]Streaming Pipeline finished in {total_elapsed:.2f}s[/bold cyan]")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user.")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
