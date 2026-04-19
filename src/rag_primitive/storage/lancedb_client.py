import logging
import lancedb
import pyarrow as pa
import time
import numpy as np
from pathlib import Path
from typing import Union

from rag_primitive.core.config import settings

logger = logging.getLogger(__name__)


class LanceDBClient:
    """
    LanceDB への接続とデータ操作を担当する。
    「Phase 3: Storage」の責任を負う。
    """

    def __init__(self, uri: str = None):
        self.uri = uri or settings.LANCEDB_URI
        # 接続 (ディレクトリがなければ自動生成される)
        self.db = lancedb.connect(self.uri)
        self.table_name = settings.TABLE_NAME

    def _get_schema(self, vector_dim: int) -> pa.Schema:
        """
        テーブルの Arrow スキーマを定義する。
        """
        return pa.schema([
            pa.field("chunk_id", pa.string(), nullable=False),
            pa.field("speech_id", pa.string(), nullable=False),
            pa.field("content", pa.string(), nullable=False),
            pa.field("speaker", pa.string(), nullable=False),
            pa.field("date", pa.string(), nullable=False),
            pa.field("meeting_name", pa.string(), nullable=False),
            # ベクトルカラム (固定次元数)
            pa.field("vector", pa.list_(pa.float32(), vector_dim), nullable=False),
        ])

    def get_or_create_table(self, vector_dim: int = 384):
        """
        テーブルを取得、存在しない場合は新規作成する。
        """
        if self.table_name in self.db.table_names():
            logger.info(f"Opening existing table: [bold cyan]{self.table_name}[/bold cyan]")
            return self.db.open_table(self.table_name)
        
        logger.info(f"Creating new table: [bold cyan]{self.table_name}[/bold cyan]")
        schema = self._get_schema(vector_dim)
        # スキーマを指定して空のテーブルを作成
        return self.db.create_table(self.table_name, schema=schema)

    def upsert_data(self, data: Union[pa.Table, pa.RecordBatchReader]):
        """
        データを Upsert (Update or Insert) する。
        chunk_id を一意識別子として使用する。
        """
        table = self.get_or_create_table()
        
        logger.info(f"Upserting data into [bold cyan]{self.table_name}[/bold cyan]...")
        
        (
            table.merge_insert("chunk_id")
            .when_matched_update_all()
            .when_not_matched_insert_all()
            .execute(data)
        )
        
        logger.info(f"Upsert complete. Total rows: [bold green]{len(table)}[/bold green]")

    def create_index(self, index_type: str = "HNSW"):
        """
        指定されたタイプのインデックスをベクトルカラムに構築する。
        """
        table = self.get_or_create_table()
        start_time = time.time()

        logger.info(f"Creating index: [bold cyan]{index_type}[/bold cyan] on [bold cyan]{self.table_name}[/bold cyan]...")

        try:
            # 同期APIでは、index_type に有効な文字列を指定する必要があるわ。
            # "HNSW" 単体ではなく "IVF_HNSW_PQ" などが正解よ！
            idx_type = index_type.upper().replace("-", "_")

            if idx_type in ["HNSW", "IVF_HNSW_PQ"]:
                # 精度重視の HNSW コンボよ！
                table.create_index(
                    metric="cosine",
                    index_type="IVF_HNSW_PQ",
                    num_partitions=256,
                    num_sub_vectors=96,
                    m=16,
                    ef_construction=100,
                    replace=True
                )
            elif idx_type == "IVF_PQ":
                # 標準的な IVF-PQ よ
                table.create_index(
                    metric="cosine",
                    index_type="IVF_PQ",
                    num_partitions=256,
                    num_sub_vectors=96,
                    replace=True
                )
            else:
                logger.error(f"Unknown index type: [bold red]{index_type}[/bold red]")
                return

            elapsed_time = time.time() - start_time
            logger.info(f"Finished creating [bold green]{index_type}[/bold green] index. Time: [bold yellow]{elapsed_time:.2f}[/bold yellow] seconds")
        except Exception as e:
            logger.error(f"Failed to create index: {e}")

    def drop_index(self, name: str = None):
        """
        既存のベクトルインデックスを削除する。
        """
        table = self.get_or_create_table()
        
        try:
            indices = table.list_indices()
            if not indices:
                logger.warning("No indices found to drop.")
                return

            if name:
                logger.info(f"Dropping index: [bold cyan]{name}[/bold cyan]...")
                table.drop_index(name)
            else:
                for idx in indices:
                    # IndexConfig オブジェクトから名前を抽出するのよ！
                    # バージョンによって index_name だったり name だったりするから、安全に取るわ。
                    target_name = getattr(idx, "index_name", getattr(idx, "name", None))
                    if target_name:
                        logger.info(f"Dropping index: [bold cyan]{target_name}[/bold cyan]...")
                        table.drop_index(target_name)
            
            # ディスクのゴミも掃除してあげるのがシニアの嗜みよ！
            table.optimize()
            logger.info("Index(es) dropped and table optimized. Falling back to Flat search.")
        except Exception as e:
            logger.error(f"Failed to drop index: {e}")

    def search(self, query_vector: Union[list, np.ndarray], limit: int = 5):
        """
        ベクトル検索を実行し、類似度の高いチャンクを返す。
        """
        table = self.get_or_create_table()

        start = time.time()
        
        # LanceDB の検索クエリ発行
        results = (
            table.search(query_vector)
            .limit(limit)
            .select(["content", "speaker", "date", "meeting_name", "chunk_id"])
            .to_list()
        )

        elapsed_time = time.time() - start
        logger.info(f"search finished: time:{elapsed_time}")
        
        return results
