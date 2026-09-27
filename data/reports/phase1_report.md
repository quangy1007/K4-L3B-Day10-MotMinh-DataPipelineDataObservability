# Báo Cáo Pha 1: Baseline Data Pipeline & Observability

> **Ngày thực hiện:** 2026-09-26 22:18:32 UTC  
> **Nguồn dữ liệu:** Crossref REST API  
> **Bộ mã hóa:** `sentence-transformers/all-MiniLM-L6-v2`  
> **Vector Database:** ChromaDB (Collection: `papers-baseline`)

---

## 1. Tóm Tắt Dữ Liệu Nguồn & Tiền Xử Lý (Ingestion & Cleaning)

| Chỉ số | Giá trị |
| :--- | :--- |
| **Số bài báo tải về (Raw):** | 24 |
| **Số bài báo sau làm sạch (Clean):** | 24 |
| **Tỷ lệ bảo toàn dữ liệu:** | 100% |
| **Cấu trúc trường `text_for_embedding`:** | Đạt chuẩn 5 phần: Title, Authors, Categories, Published, Summary |

---

## 2. Kết Quả Kiểm Định Chất Lượng Dữ Liệu (Data Observability)

### A. Great Expectations 1.x Quality Gate
- **Trạng thái tổng thể:** **`PASSED (100%)`**
- **Số Expectations kiểm tra:** 5
  1. `ExpectTableRowCountToBeBetween` (1 <= N <= 1000): **Hợp lệ**
  2. `ExpectColumnValuesToNotBeNull` (`paper_id` & `title`): **Hợp lệ**
  3. `ExpectColumnValuesToBeUnique` (`paper_id`): **Hợp lệ (Không trùng lặp)**
  4. `ExpectColumnValueLengthsToBeBetween` (`summary` từ 10 - 5000 ký tự): **Hợp lệ**

### B. Freshness SLA Monitoring
- **Tổng số bài báo:** 24
- **Ngưỡng SLA quy định:** <= 180 ngày
- **Số bài quá hạn (`age_days > 180`):** 1
- **Tỷ lệ bài cũ (Stale Ratio):** 4.2%
- **Đánh giá Freshness:** **`PASSED (SLA đạt chuẩn)`** (Ngưỡng cảnh báo: > 25%)

---

## 3. Hiệu Năng RAG Agent Trên Dữ Liệu Sạch (Baseline Benchmarks)

Đánh giá trên bộ kiểm thử chuẩn hóa gồm 10 câu hỏi đa dạng qua 4 nhóm nghiệp vụ (`summary`, `authors`, `date`, `categories`):

| Thước đo hiệu năng | Điểm số đạt được | Tiêu chuẩn đánh giá |
| :--- | :---: | :--- |
| **Retrieval Hit Rate:** | **100.0%** | Khả năng truy xuất đúng tài liệu cơ sở |
| **Mean Token F1 Score:** | **0.8000** | Độ chính xác từng từ của câu trả lời |
| **Judge Accuracy:** | **80.0%** | Đánh giá tính chính xác ngữ nghĩa |
| **Mean Judge Score (1-5):** | **4.20 / 5.0** | Điểm số trung bình từ chuyên gia chấm |

> **Kết luận Pha 1:** Dữ liệu đầu vào hoàn toàn sạch, vượt qua mọi chốt kiểm dịch Data Quality Gate GX 1.x và Freshness SLA, đảm bảo RAG Agent đạt độ tin cậy tối đa.
