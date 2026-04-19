# RAG Project Status

このドキュメントは、プロジェクトの全体進捗とタスクを管理するためのものである。
「1億件のスケール」に耐えうるアーキテクチャを実現するためのマイルストーンを定義する。

## 🎯 プロジェクトゴール
- **短期目標**: 特定の会議を Unit of Work として End-to-End で処理し、LanceDB へ格納する。
- **長期目標**: 1,000万〜1億件のチャンクを $O(1)$ の空間計算量で処理し、インデックス構築のトレードオフを定量化する。

---

## 📈 全体進捗 (Milestones)

- [x] **Phase 0: Architecture & Environment**
    - [x] アーキテクチャ設計 (v1.1 in `ARCH_DESIGN.md`)
    - [x] `uv` によるモダンな開発環境の構築 (`pyproject.toml`, `.venv`)
- [x] **Phase 1: Acquisition (Data Lake Construction)**
    - [x] 国会会議録 API クローラーの実装 (Rate Limit / Retry 考慮)
    - [x] 非同期ジェネレータによるストリーミング取得の実装
    - [x] 「1会議1ファイル」形式による粒度の細かいべき等性の担保
- [x] **Phase 2: Processing (Streaming Pipeline)**
    - [x] 再帰的チャンキング (Recursive Character Text Splitter) の実装
    - [x] ローカルモデル (multilingual-e5-small) による Embedding
    - [x] ディレクトリベースの複数ファイル一括処理の実装
    - [x] PULL 型バックプレッシャー制御 (Generator による遅延評価)
- [x] **Phase 3: Storage (LanceDB Integration)**
    - [x] LanceDB テーブルの作成とスキーマ定義 (item 規格の完全一致)
    - [x] ディレクトリ内の全 Parquet からのインポート (Zero-copy Join)
    - [x] Content-based Addressing によるべき等性の担保 (Upsert 実装)
- [x] **Phase 4: Optimization & Benchmarking**
    - [x] 期間指定による実データのバルクロード（3.5万件規模）の成功
    - [x] Flat vs HNSW vs IVF-PQ のベンチマーク計測 (3.5万件でインデックスが優位に)
    - [x] 空間/時間計算量の実測報告作成 (`BENCHMARK_REPORT.md`)
- [x] **Phase 5: Search & Verification (Bonus)**
    - [x] ベクトル検索インターフェース (`search.py`) の実装
    - [x] 検索疎通確認 (実際のクエリに対する top-k 結果の取得成功)
- [ ] **Phase 6: Scalability & Parallelization**
    - [ ] `ProcessPoolExecutor` による Chunker の CPU 並列化
    - [ ] **Embedding の並列化・高速化 (最大のボトルネック: 97.4% の時間を消費)**
    - [ ] タスクキュー (Worker モデル) による分散パイプラインの構築
    - [ ] ベクトル書き出しのストリーミング化 (`Incremental Append`)

---

## 🛠️ 現在の作業 (Current Task)
**Phase 6: Scalability & Parallelization**
- 3.5万件の検証により、Embedding 処理が全体の 97% 以上を占める圧倒的なボトルネックであることが判明。
- **Next Step**: 1億件達成（推定 31日間）を現実的な時間（数日以内）に短縮するため、Embedding のバッチサイズ最適化および並列化戦略を立案・実装する。

---

## 📝 決定事項 & ログ
- **2026-04-01**: プロジェクト開始。`uv` を採用。
- **2026-04-13**: Phase 5 完了。`search.py` によるベクトル検索の成功を確認。
- 2026-04-16: **Architecture v1.1 到達。** ストリーミング・パイプライン実装。
- 2026-04-16: **Phase 4 完了。** 3.5万件規模でのインデックス特性を実測。Flat 検索（0.027s）に対し、IVF_HNSW_PQ（0.012s）の優位性を実証。Embedding が 902s かかる最大ボトルネックであることを数値で特定。

