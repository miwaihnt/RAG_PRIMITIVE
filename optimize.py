from rag_primitive.storage.lancedb_client import LanceDBClient
from rag_primitive.core.logging import setup_logging

def main():
    setup_logging()
    client = LanceDBClient()
    # 一旦インデックスを消して、Flat 検索（全件スキャン）に戻すわよ！
    # client.drop_index()
    client.create_index(index_type="HNSW")


if __name__ == "__main__":
    main()