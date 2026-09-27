# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K4 - L3B                  |
| Tên nhóm         | MotMinh                   |
| Repository         | `https://github.com/quangy1007/K4-L3B-Day10-MotMinh-DataPipelineDataObservability` |
| Ngày hoàn thành | 2026-09-27               |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Đậu Quang Ý | 2A202602661 | Trưởng nhóm / Pipeline Integrator | `core/config.py`, `pipelines/phase1.py`, `pipelines/corruption_flow.py` |
| 2 | Trần Thị B | 20260002 | Data Foundation & Recovery | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, raw data snapshot |
| 3 | Lê Hoàng C | 20260003 | RAG & Vector Index | `src/retrieval/index.py`, `src/retrieval/embeddings.py`, ChromaDB |
| 4 | Phạm Minh D | 20260004 | Observability & Evaluation | `src/observability/quality.py` (GX 1.x), `src/evaluation/testset.py`, reporting |

---

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành trọn vẹn toàn bộ 7 Checkpoints (CP0 đến CP6) của bài lab:
1. **Baseline Pipeline:** Thu thập 24 bản ghi từ Crossref API (hỗ trợ offline fallback an toàn), làm sạch văn bản, tính toán `age_days`, tạo trường `text_for_embedding` cấu trúc 5 phần và lập chỉ mục vào ChromaDB (`papers-baseline`). Bộ test 10 câu hỏi đạt **Retrieval Hit Rate 100.0%** và **Mean Token F1 0.8000**.
2. **Data Observability:** Thiết lập thành công chốt kiểm dịch Great Expectations 1.x (chế độ Ephemeral) với 4 nhóm kỳ vọng thiết yếu và cơ chế giám sát Freshness SLA (ngưỡng 180 ngày).
3. **Data Corruption:** Tiêm 6 kịch bản lỗi (drop 20% bản ghi mới, blank summary, inject noise, truncate title, stale date, duplicate rows). Khi đó, RAG gặp hiện tượng **Silent Failure** nghiêm trọng: Retrieval Hit Rate tụt từ 100% xuống **70.0%**, Mean Token F1 tụt xuống **0.6000**, đồng thời Quality Gate báo động **FAILED** và Freshness SLA báo động **VIOLATED**.
4. **Idempotent Repair:** Phục hồi toàn vẹn dữ liệu từ snapshot nguồn thô đáng tin cậy (`crossref_records.json`), tái tạo vector store (`papers-repaired`), xóa sạch ghost vectors và phục hồi hoàn toàn các chỉ số về mức ban đầu (**100.0% Hit Rate**, **0.8000 Token F1**).

---

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref Metadata API (hoặc Local Snapshot data/raw/)
    ↓
Raw Response / Records Artifacts (Bảo toàn Data Lineage)
    ↓
Cleaning & Pre-embed Modeling (Lọc JATS XML, tính age_days, text_for_embedding 5 phần)
    ↓
Embedding (all-MiniLM-L6-v2) + ChromaDB Index (papers-baseline)
    ↓
Benchmark Evaluation (10 câu qua 4 nhóm nghiệp vụ) → baseline_metrics.json
    ↓
Data Quality Gate (Great Expectations 1.x) + Freshness SLA Check
    ↓
Synthetic Data Corruption Suite (6 kịch bản lỗi dữ liệu)
    ↓
Re-index (papers-corrupted) + Re-evaluate → Đo lường Silent Failure
    ↓
Idempotent Repair từ Raw Snapshot → papers-repaired
    ↓
Đối chiếu 3 trạng thái (Baseline vs Corrupted vs Repaired) → corruption_report.md
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| :--- | :--- | :--- | :--- | :--- |
| **Ingestion** | Crossref API / Raw Snapshot | Fetch với retry, fallback offline, parse JSON | `data/raw/crossref_response.json`, `crossref_records.json` | Trần Thị B |
| **Cleaning** | `PaperRecord` raw list | Lọc thẻ XML, deduplicate theo `paper_id`, tính `age_days`, ghép `text_for_embedding` 5 phần | `data/clean/papers_clean.csv`, `papers_clean.json` | Trần Thị B |
| **Embedding/Index** | Cleaned DataFrame | Mã hóa `all-MiniLM-L6-v2`, nạp ChromaDB persistent | `data/chroma/`, `data/embeddings/papers_embeddings.json` | Lê Hoàng C |
| **Evaluation** | Clean DataFrame, Query Index | Sinh 10 câu testset, truy xuất top-k, tính Hit Rate, Token F1, Judge Score | `data/eval/test_set.json`, `data/results/*_metrics.json` | Phạm Minh D |
| **Observability** | DataFrame (mỗi trạng thái) | GX 1.x Ephemeral Context (4 expectations), kiểm tra tỷ lệ quá hạn > 25% | `data/quality/*_quality_report.json`, `freshness_report.json` | Phạm Minh D |
| **Corruption/Repair** | Clean DataFrame, Raw Snapshot | Tiêm 6 kịch bản lỗi; đọc lại raw snapshot để tái tạo dữ liệu sạch | `data/results/corruption_log.json`, `papers_clean_corrupted.*`, `papers_clean_repaired.*` | Nguyễn Văn A & Trần Thị B |
| **Orchestration** | Toàn bộ các module | Điều phối luồng Phase 1 và Corruption Flow | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` | Nguyễn Văn A |

---

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| :--- | :--- |
| `LLM_PROVIDER` | `mock` (hoặc `gemini` khi cấu hình key) |
| `LLM_MODEL` | `gemini-2.5-flash` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 ngày |
| Python Environment | Python 3.11.15 quản lý bởi `uv` |

### Lệnh cài đặt

```bash
uv venv --python 3.11
.\.venv\Scripts\activate
uv pip install -e .
```

### Lệnh chạy

**1. Baseline Pipeline (Pha 1):**
```bash
python script/run_phase1.py
```

**2. Corruption & Repair Flow:**
```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy | Bằng chứng |
| :--- | :--- | :--- | :--- |
| `python script/run_phase1.py` | Thành công (Exit code 0) | 2026-09-27 05:18 | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| `python script/run_corruption_flow.py` | Thành công (Exit code 0) | 2026-09-27 05:19 | `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`, `data/reports/corruption_report.md` |

---

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| :--- | :--- |
| Source | Crossref REST API (`https://api.crossref.org/works`) |
| Query/filter | `query=agentic retrieval augmented generation...`, `filter=has-abstract:true` |
| Số record nhận được | 24 bài báo khoa học |
| Cơ chế fallback | Tự động đọc snapshot offline `data/raw/crossref_response.json` khi mạng gián đoạn |

### Clean Schema & Data Modeling

Mỗi bài báo được chuẩn hóa với các trường chính:
* `paper_id`: Chuỗi DOI duy nhất của bài báo (Primary Key).
* `title`: Tiêu đề đã chuẩn hóa khoảng trắng thừa.
* `summary`: Tóm tắt đã loại bỏ sạch các thẻ JATS XML (`<jats:p>`, `<jats:italic>`, v.v.).
* `authors_joined`: Danh sách các tác giả nối nhau bằng dấu phẩy.
* `categories_joined`: Các danh mục phân loại bài báo.
* `published`: Ngày xuất bản chuẩn `YYYY-MM-DD`.
* `age_days`: Số ngày tính từ ngày xuất bản đến thời điểm chạy (`(run_date - published).days`).
* `text_for_embedding`: Chuỗi văn bản cấu trúc 5 phần chuẩn cho model nhúng:
  ```text
  Title: {title}
  Authors: {authors_joined}
  Categories: {categories_joined}
  Published: {published}
  Summary: {summary}
  ```

---

## 6. Evaluation Setup

| Thành phần | Cấu hình thực tế |
| :--- | :--- |
| Số câu hỏi benchmark | 10 câu hỏi |
| Các `question_type` | `summary` (3 câu), `authors` (3 câu), `date` (2 câu), `categories` (2 câu) |
| Ground-truth document ID | Trỏ chính xác đến `paper_id` của bài báo mục tiêu |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector Store | ChromaDB (3 collections riêng biệt: `papers-baseline`, `papers-corrupted`, `papers-repaired`) |
| Retrieval `top_k` | 4 |
| Tính nhất quán của Test Set | Bộ câu hỏi trong `data/eval/test_set.json` được **giữ nguyên không đổi** cho cả 3 trạng thái để đảm bảo tính khách quan và khoa học khi so sánh hiệu năng. |

---

## 7. Kết quả Baseline

### Artifact Checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| :--- | :--- | :---: | :--- |
| Raw response/records | `data/raw/` | Có | `crossref_response.json`, `crossref_records.json` |
| Cleaned dataset | `data/clean/` | Có | `papers_clean.csv`, `papers_clean.json` |
| Embedding manifest/index | `data/embeddings/` | Có | `papers_embeddings.json` (ChromaDB) |
| Evaluation set | `data/eval/` | Có | `test_set.json` (10 câu hỏi) |
| Baseline metrics | `data/results/baseline_metrics.json` | Có | Hit Rate 100%, F1 0.8000 |
| Quality/freshness | `data/quality/` | Có | `baseline_quality_report.json`, `freshness_report.json` |
| Baseline report | `data/reports/phase1_report.md` | Có | Markdown báo cáo chi tiết pha 1 |

### Baseline Metrics

| Metric | Giá trị | Diễn giải |
| :--- | :---: | :--- |
| `retrieval_hit_rate` | **100.0%** | Toàn bộ 10/10 câu hỏi đều truy xuất chính xác tài liệu nguồn trong top-k. |
| `mean_token_f1` | **0.8000** | Độ trùng khớp token giữa câu trả lời và ground-truth đạt mức rất cao. |
| `judge_accuracy` | **80.0%** | Đánh giá ngữ nghĩa câu trả lời đạt chuẩn nghiệp vụ. |
| `mean_judge_score` | **4.20 / 5.0** | Điểm số chất lượng câu trả lời từ giám khảo tự động. |

---

## 8. Data Quality và Freshness

### Great Expectations 1.x Quality Checks

| Check / Expectation | Quality Dimension | Ngưỡng / Kỳ vọng | Kết quả Baseline | Bằng chứng |
| :--- | :--- | :--- | :---: | :--- |
| `ExpectTableRowCountToBeBetween` | Completeness | 1 <= rows <= 1000 | PASSED (24 dòng) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` (`paper_id`) | Validity | 0% null | PASSED (0 null) | `baseline_quality_report.json` |
| `ExpectColumnValuesToBeUnique` (`paper_id`) | Uniqueness | 100% unique | PASSED (0 duplicate) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` (`title`) | Completeness | 0% null | PASSED (0 null) | `baseline_quality_report.json` |
| `ExpectColumnValueLengthsToBeBetween` (`summary`) | Conformity | 10 <= len <= 5000 | PASSED (Tất cả hợp lệ) | `baseline_quality_report.json` |

### Freshness SLA

| Thuộc tính | Giá trị |
| :--- | :--- |
| Nơi đo lường | `data/clean/papers_clean.json` |
| Ngưỡng Freshness SLA | `<= 180` ngày |
| Số dòng quá hạn (`age_days > 180`) | 0 / 24 dòng (0.0%) |
| Trạng thái Baseline | **FRESH ✅ (Đạt chuẩn SLA, không có cảnh báo)** |

---

## 9. Corruption Scenarios và Repair

| STT | Loại Corruption | Cách tạo | Record bị tác động | Quality Signal kỳ vọng | Tác động thực tế lên RAG |
| :---: | :--- | :--- | :---: | :--- | :--- |
| 1 | **Drop latest** | Xóa 20% bản ghi mới nhất | 5 bản ghi | Row count giảm | Hit Rate tụt do mất tài liệu nguồn |
| 2 | **Blank summary** | Gán `summary = ""` | 2 bản ghi | Vi phạm độ dài summary tối thiểu | Không có context để tóm tắt |
| 3 | **Inject noise** | Chèn ký tự rác vào abstract | 2 bản ghi | Embedding drift | Token F1 giảm mạnh |
| 4 | **Truncate title** | Cắt ngắn title `< 8` ký tự | 2 bản ghi | Mất semantic title | Lookup theo tiêu đề bị sai lệch |
| 5 | **Stale date** | Lùi ngày xuất bản về 1990 | 7 bản ghi (35%) | Tỷ lệ quá hạn > 25% | Kích hoạt cảnh báo Freshness SLA |
| 6 | **Duplicate rows** | Nhân bản 2 dòng dữ liệu | 2 bản ghi | Vi phạm Uniqueness `paper_id` | Gây nhiễu thứ hạng top-k trong ChromaDB |

### Cơ Chế Idempotent Repair

* **Nguyên lý:** Phục hồi từ bản sao lưu thô ban đầu `data/raw/crossref_records.json` (nguồn Single Source of Truth).
* **Tính Idempotent:** Quy trình làm sạch và nạp vector store được thiết kế sao cho dù thực thi 1 lần hay 100 lần, kết quả đầu ra luôn đồng nhất. ChromaDB collection `papers-repaired` được purge hoàn toàn trước khi nạp mới, loại bỏ 100% hiện tượng **Ghost Vectors**.

---

## 10. So Sánh 3 Trạng Thái: Baseline vs Corrupted vs Repaired

| Metric / Signal | Baseline | Corrupted | Repaired | Biến thiên do Corruption | Mức phục hồi |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Retrieval Hit Rate** | **100.0%** | **70.0%** | **100.0%** | **-30.0%** | **100% phục hồi** |
| **Mean Token F1** | **0.8000** | **0.6000** | **0.8000** | **-0.2000** | **100% phục hồi** |
| **Judge Accuracy** | **80.0%** | **60.0%** | **80.0%** | **-20.0%** | **100% phục hồi** |
| **Judge Score (1-5)** | **4.20** | **3.40** | **4.20** | **-0.80** | **100% phục hồi** |
| **GX 1.x Quality Gate** | **PASSED ✅** | **FAILED ❌** | **PASSED ✅** | Bắt lỗi Uniqueness & Length | Hoàn toàn sạch |
| **Freshness SLA** | **FRESH ✅** | **VIOLATED ⚠️** | **FRESH ✅** | Cảnh báo quá hạn 35% | Trở lại chuẩn SLA |

### Hai Kết Luận Nhân Quả Cốt Lõi:
1. **Dữ liệu lỗi gây Silent Failure cho AI:** Khi tiêm lỗi, code hệ thống vẫn chạy bình thường không crash, nhưng Retrieval Hit Rate giảm tới 30% và Token F1 giảm 25%. Nếu không có Great Expectations 1.x, hệ thống serving sẽ âm thầm trả về thông tin sai lệch cho người dùng cuối.
2. **Idempotent Repair phục hồi trọn vẹn phong độ RAG:** Nhờ việc bảo toàn Data Lineage trong `data/raw/`, pipeline đã tự động tái lập sạch sẽ và đưa toàn bộ chỉ số đánh giá của AI trở lại mức tối ưu 100.0% Hit Rate mà không để lại vector rác.

---

## 11. Vấn Đề Tích Hợp Đã Xử Lý

* **Triệu chứng:** Khi chạy lệnh in tiếng Việt trên console Windows, xảy ra lỗi `UnicodeEncodeError: 'charmap' codec can't encode characters`.
* **Nguyên nhân:** PowerShell trên Windows mặc định sử dụng code page CP1252 không tương thích UTF-8 khi pipe ký tự tiếng Việt.
* **Cách xử lý:** Thiết lập biến môi trường `$env:PYTHONIOENCODING="utf-8"` và cấu hình mã hóa UTF-8 chuẩn hóa trên toàn bộ các file I/O (`encoding="utf-8"`).
* **Xác minh:** Tất cả các lệnh kiểm thử CP0-CP6 đều chạy thành công với Exit Code 0 và in tiếng Việt sắc nét.

---

## 12. Checklist Trước Khi Nộp Bài

- [x] Đã hoàn thành 100% các checkpoint từ CP0 đến CP6.
- [x] Lệnh `python script/run_phase1.py` chạy exit code 0.
- [x] Lệnh `python script/run_corruption_flow.py` chạy exit code 0.
- [x] Có đầy đủ các file metrics: `baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`.
- [x] Báo cáo đối chiếu 3 trạng thái đầy đủ tại `data/reports/corruption_report.md`.
- [x] Bộ test benchmark dùng chung 10 câu hỏi nhất quán cho 3 trạng thái.
- [x] Cấu hình Great Expectations 1.x theo chuẩn mới Ephemeral Context.
- [x] Tuyệt đối không commit API Key / Secret vào Git (đã dùng `.env.example`).
