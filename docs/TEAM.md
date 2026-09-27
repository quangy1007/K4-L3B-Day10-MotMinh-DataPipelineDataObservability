# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `MotMinh`
- **Mã Nhóm / Lớp:** `K4-L3B-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3B-Day10-MotMinh-DataPipelineDataObservability`

---

## 1. Danh Sách Thành Viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | **Đậu Quang Ý** | **2A202602661** | `2a202602661@vinuni.edu.vn` | Trưởng nhóm / Pipeline Integrator (`core/`, `phase1.py`, `corruption_flow.py`) | [`report/2A202602661_DauQuangY.md`](../report/2A202602661_DauQuangY.md) |
| 2 | Trần Thị B | 2A202602662 | `tranb@vinuni.edu.vn` | Data Foundation & Recovery (`crossref.py`, `cleaning.py`, raw data) | `report/2A202602662_TranThiB.md` |
| 3 | Lê Hoàng C | 2A202602663 | `lec@vinuni.edu.vn` | RAG & Vector Index (`retrieval/index.py`, `embeddings.py`, ChromaDB) | `report/2A202602663_LeHoangC.md` |
| 4 | Phạm Minh D | 2A202602664 | `phamd@vinuni.edu.vn` | Observability & Evaluation (`quality.py` GX 1.x, `testset.py`, reporting) | `report/2A202602664_PhamMinhD.md` |

---

## 2. Báo Cáo Tự Khai Đóng Góp Cá Nhân

### Đậu Quang Ý - 2A202602661
- **Vai trò:** Trưởng nhóm & Điều phối Toàn trình Pipeline (Pipeline Integrator).
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập cấu hình hệ thống `core/config.py` và các tiện ích quản lý artifacts `core/utils.py`.
  - Kết nối luồng thực thi end-to-end trong `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py`.
  - Xây dựng bộ test tự động Pytest CI trong `tests/test_pipeline.py` (đạt 6/6 test pass).
  - Khắc phục lỗi mã hóa ký tự UTF-8 trên Windows console và điều phối kiểm tra chất lượng artifacts báo cáo 3 trạng thái.
  - Theo dõi Contributor tracking và kiểm soát chất lượng code trên GitHub nhánh `main`.
- **Điều học được / Đóng góp chính:**
  - Nắm vững kiến trúc Idempotent Data Pipeline cho hệ thống RAG Agent, ngăn chặn tình trạng Ghost Vectors và cô lập các không gian vector serving.

### Thành Viên 2 (Trần Thị B)
- **Vai trò:** Phụ trách Ingestion, Làm sạch & Phục hồi dữ liệu.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng module thu thập Crossref API với cơ chế Fallback offline trong `src/ingestion/crossref.py`.
  - Chuẩn hóa schema, tính toán trường `age_days` và cấu trúc `text_for_embedding` 5 phần trong `src/ingestion/cleaning.py`.
  - Thực thi cơ chế Idempotent Repair phục hồi dữ liệu từ raw snapshot `data/raw/crossref_records.json`.
- **Điều học được / Đóng góp chính:**
  - Kỹ thuật truy vết nguồn gốc dữ liệu (Data Lineage) và bảo toàn raw snapshot trước khi biến đổi.

### Thành Viên 3 (Lê Hoàng C)
- **Vai trò:** Phụ trách RAG, Vector Database & Embedding.
- **Công việc chi tiết đã hoàn thành:**
  - Quản lý mô hình embedding `sentence-transformers/all-MiniLM-L6-v2`.
  - Nạp và quản lý 3 collection riêng biệt trong ChromaDB (`papers-baseline`, `papers-corrupted`, `papers-repaired`).
  - Xây dựng QA Agent truy vấn ngữ cảnh chính xác theo tài liệu.
- **Điều học được / Đóng góp chính:**
  - Cách cô lập các không gian vector để so sánh khách quan giữa dữ liệu sạch và dữ liệu bị lỗi.

### Thành Viên 4 (Phạm Minh D)
- **Vai trò:** Phụ trách Data Observability & Benchmark Evaluation.
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập Quality Gate theo chuẩn mới **Great Expectations 1.x** và giám sát Freshness SLA trong `src/observability/quality.py`.
  - Xây dựng bộ câu hỏi đánh giá chuẩn trong `src/evaluation/testset.py`.
  - Đo lường và xuất bảng đối chiếu 3 trạng thái vào `data/reports/corruption_report.md`.
- **Điều học được / Đóng góp chính:**
  - Cách thiết lập hệ thống cảnh báo sớm chặn đứng hiện tượng Silent Failure trước khi dữ liệu vào serving layer.
