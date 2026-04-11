# RAG Project Status

このドキュメントは、プロジェクトの全体進捗とタスクを管理するためのものである。
「1億件のスケール」に耐えうるアーキテクチャを実現するためのマイルストーンを定義する。

## 🎯 プロジェクトゴール
- **短期目標**: 特定の会議（`minId=122104339X00320260312`）を Unit of Work として End-to-End で処理し、LanceDB へ格納する。
- **長期目標**: 1,000万〜1億件のチャンクを $O(1)$ の空間計算量で処理し、インデックス構築のトレードオフを定量化する。

---

## 📈 全体進捗 (Milestones)

- [x] **Phase 0: Architecture & Environment**
    - [x] アーキテクチャ設計 (v1.0 in `ARCH_DESIGN.md`)
    - [x] `uv` によるモダンな開発環境の構築 (`pyproject.toml`, `.venv`)
- [x] **Phase 1: Acquisition (Data Lake Construction)**
    - [x] 国会会議録 API クローラーの実装 (Rate Limit / Retry 考慮)
    - [x] チェックポイント機能（べき等性）の実装 (ファイル存在チェック)
    - [x] Raw Data (JSONL) への永続化 (1会議1行形式)
- [x] **Phase 2: Processing (Streaming Pipeline)**
    - [x] 再帰的チャンキング (Recursive Character Text Splitter) の実装
    - [x] ローカルモデル (multilingual-e5-small) による Embedding
    - [x] PULL 型バックプレッシャー制御 (Generator による遅延評価)
    - [x] Silver Data (Parquet) へのベクトル永続化
- [ ] **Phase 3: Storage (LanceDB Integration)**
    - [ ] LanceDB テーブルの作成とスキーマ定義
    - [ ] Parquet からのインポート (Zero-copy Join)
    - [ ] Content-based Addressing によるべき等性の担保 (Upsert)
- [ ] **Phase 4: Optimization & Benchmarking**
    - [ ] IVFFlat vs HNSW のベンチマーク計測
    - [ ] 空間/時間計算量の実測報告

---

## 🛠️ 現在の作業 (Current Task)
**Phase 3: Storage (LanceDB)**
- 埋め込み済みの Parquet データから LanceDB へデータをロードする。
- 1億件スケールに耐えうるテーブル設計と、再実行可能な Upsert ロジックの実装。
- **Next Step**: `src/rag_primitive/storage/lancedb_client.py` の実装。

---

## 📝 決定事項 & ログ
- **2026-04-01**: プロジェクト開始。`uv` を採用し、`lancedb`, `pyarrow`, `sentence-transformers` 等を主要スタックに選定。
- **2026-04-01**: 「まずは1つの会議を完遂させる」という垂直立ち上げ戦略に決定。
- **2026-04-01**: Phase 1 (Acquisition) 完了。特定の会議ID (`122104339X00320260312`) の JSONL 永続化に成功。
- **2026-04-01**: Phase 2 (Processing) 完了。Recursive チャンキングと MPS (GPU) によるベクトル化に成功。
