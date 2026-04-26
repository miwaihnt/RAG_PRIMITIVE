# RAG Project Status

このドキュメントは、プロジェクトの全体進捗とタスクを管理するためのものである。
「1億件のスケール」に耐えうるアーキテクチャを実現するためのマイルストーンを定義する。

## 🎯 プロジェクトゴール
- **短期目標**: 特定の会議を Unit of Work として End-to-End で処理し、LanceDB へ格納する。
- **長期目標**: 1,000万〜1億件のチャンクを $O(1)$ の空間計算量で処理し、インデックス構築のトレードオフを定量化する。
- **Advanced Goal**: ハイブリッド検索（ベクトル + BM25）とリランキングによる、商用レベルの検索精度とスケーラビリティの両立。

---

## 📈 全体進捗 (Milestones)

- [x] **Phase 0-6: Foundations & Streaming Pipeline (STEP 1)**
    - [x] アーキテクチャ設計とモダンな開発環境 (`uv`) の構築
    - [x] ストリーミング・クローラーの実装
    - [x] 空間計算量 $O(B)$ を維持した増分書き出し (`Incremental Append`)
    - [x] `asyncio.Queue` による並行ワーカーモデル（Acquisition/Chunk/Embed/Store）の構築
    - [x] 3.5万件規模でのインデックス特性（IVF-PQ vs HNSW）の検証

- [ ] **Phase 7: Hybrid Search & Reranking (STEP 2)**
    - [ ] **BM25 (Full Text Search) の実装**: 特定キーワードへの再現率（Recall）向上
    - [ ] **RRF (Reciprocal Rank Fusion) の統合**: ベクトルスコアと単語スコアの公平な融合
    - [ ] **Cohere Rerank の導入**: 二段階検索（Retrieve & Re-rank）による精度極大化
    - [ ] **性能・レイテンシ評価**: ハイブリッド化による精度の向上幅と計算コストの定量化

---

## 🛠️ 現在의 作業 (Current Task)
**Phase 7: Hybrid Search & Reranking**
- **Goal**: ベクトル検索の弱点である「固有名詞・特定キーワード」への弱さを、BM25 全文検索の統合により克服する。
- **Current Task**: `rank_bm25` ライブラリの導入と、LanceDB または Parquet からの BM25 インデックス構築戦略の立案。
- **Next Step**: RRF スコアリングロジックの自作による、ハイブリッド検索エンジンのプロトタイプ作成。

---

## 📝 決定事項 & ログ
- **2026-04-01**: プロジェクト開始。`uv` を採用。
- 2026-04-23: **Phase 6 完了。** ワーカーモデルへの移行により、E2E ストリーミング処理を達成。
- 2026-04-23: **STEP 2 (Phase 7) 開始。** マネージド SaaS の内部ロジックを理解するため、ハイブリッド検索の自作フェーズへ移行。
