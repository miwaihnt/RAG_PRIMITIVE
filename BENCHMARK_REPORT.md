# RAG Primitive Benchmark Report

このドキュメントは、異なるインデックス設定における検索性能（Latency）と精度（Recall）を定量的に評価し、1億件スケールに向けた最適解を導き出すためのものである。

## 1. 実行環境 (Hardware & Environment)
- **OS**: macOS (darwin)
- **CPU**: Apple M4 (MacBook Pro)
- **RAM**: [YOUR_RAM_SIZE] GB
- **DB**: LanceDB (v0.x.x)
- **Embedding Model**: `intfloat/multilingual-e5-small` (384 dim)

## 2. データセット (Dataset)
- **ソース**: 国会会議録 API (2024-01-01 〜 2024-03-31 程度)
- **総チャンク数**: **35,152 チャンク**

---

## 3. ベンチマーク結果 (Benchmark Results)

| Case | Index Type | Build Time (s) | Search Latency (avg s) | Precision/Recall | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Case 1** | **No Index (Flat)** | - | 0.080 s (Cold) / 0.027 s (Warm) | 最高 (Exact) | M4 チップにより全件スキャンも高速 |
| **Case 2** | **IVF_HNSW_PQ** | **18.81 s** | **0.012 s** | 高 | **最速を記録。順位変動（Maehara #1）が発生** |
| **Case 3** | **IVF_PQ** | **17.76 s** | **0.012 s** | 中 | 僅かに遅いが、構築コストは HNSW より低い |

### 3.1. 検索クエリ「少子化」における Top 3 比較 (3.5万件規模)
| Rank | **No Index (Flat)** | **IVF_PQ** | **IVF_HNSW_PQ** |
| :--- | :--- | :--- | :--- |
| **#1** | 佐藤主光 (Dist: 0.2670) | 佐藤主光 (Dist: 0.2628) | **前原誠司** (Dist: 0.2535) |
| **#2** | 前原誠司 (Dist: 0.2670) | 勝目康 (Dist: 0.2647) | 佐藤主光 (Dist: 0.2671) |
| **#3** | 勝目康 (Dist: 0.2678) | 越智隆雄 (Dist: 0.2663) | 末冨芳 (Dist: 0.2698) |

---

## 4. 分析と考察 (Analysis & Insights)

### 4.1. パイプライン全体のボトルネック (Bottleneck Analysis)
(中略 - Embedding 902s)

### 4.2. インデックス構築コストの比較
- `IVF_HNSW_PQ` は `IVF_PQ` に比べ、グラフ構築の分だけ時間が約 6% 増加（17.76s -> 18.81s）。
- 1億件スケールでは、この数パーセントの差が数時間の差に繋がるため、メモリ容量と相談して選択する必要がある。

### 4.3. 検索レイテンシと精度のトレードオフ
- **速度**: HNSW と PQ はほぼ同等の 0.012s を記録し、Flat 検索に対して **2.2倍の高速化** を達成した。
- **精度（順位の逆転）**: 興味深いことに、HNSW では Flat 検索で 2位だった前原委員が 1位に浮上した。これは ANN アルゴリズム固有の近似計算が、特定のデータ点において Flat 検索とは異なる挙動を示すことを示唆している。
- **結論**: 中規模（数万件）においては、インデックスの種類による「速度の差」よりも「精度の差（順位の入れ替わり）」の方が顕著に現れる。

---

## 6. バッチサイズ最適化実験 (Batch Size Optimization)

1億件スケールに向けた Embedding 処理の高速化を目的とし、バッチサイズによるスループットの変化を測定する。

### 6.1. 実験結果ログ

| Date | Total Chunks | BATCH_SIZE | Embedding Time (s) | Throughput (chunks/sec) | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 2026-04-21 | 35,056 | **64** | **955.51 s** | **36.69** | ベースライン（M4 MPS使用） |

---

## 7. 分析と考察 (Analysis & Insights)
