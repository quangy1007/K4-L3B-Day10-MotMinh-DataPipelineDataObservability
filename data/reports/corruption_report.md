# Báo Cáo Đối Chiếu 3 Trạng Thái: Baseline vs Corrupted vs Repaired

> **Mục tiêu:** Minh chứng hiện tượng **Silent Failure** của hệ thống RAG Agent khi dữ liệu bị suy thoái và năng lực phục hồi trọn vẹn thông qua cơ chế **Idempotent Self-Healing Repair**.

---

## 1. Bảng Tổng Hợp Đối Chiếu Định Lượng 3 Trạng Thái

| Thước đo / Chỉ số | Baseline (Dữ liệu sạch) | Corrupted (Tiêm lỗi) | Repaired (Sau phục hồi) | Nhận xét & Biến thiên |
| :--- | :---: | :---: | :---: | :--- |
| **Retrieval Hit Rate** | **100.0%** | **70.0%** | **100.0%** | Sụt giảm mạnh khi mất bản ghi & phục hồi 100% |
| **Mean Token F1** | **0.8000** | **0.6000** | **0.8000** | RAG trả lời sai/nhiễu khi dữ liệu bị cắt ngắn/rác |
| **Judge Accuracy** | **80.0%** | **60.0%** | **80.0%** | Phản ánh hiện tượng Silent Failure của LLM |
| **Judge Score (1-5)** | **4.20 / 5.0** | **3.40 / 5.0** | **4.20 / 5.0** | Đánh giá chất lượng toàn diện của câu trả lời |
| **GX 1.x Quality Gate** | **PASSED ✅** | **FAILED ❌** | **PASSED ✅** | Bắt trúng lỗi Uniqueness & Length vi phạm |
| **Freshness SLA** | **FRESH ✅** | **VIOLATED ⚠️** | **FRESH ✅** | Cảnh báo khi tỷ lệ bài cũ > 25% |

---

## 2. Phân Tích Hiện Tượng Silent Failure

Khi dữ liệu gặp sự cố:
1. **Không phát sinh Exception ở tầng ứng dụng:** Code Python của Retrieval và LLM Agent vẫn thực thi bình thường (Exit code 0), không ném ra lỗi cú pháp.
2. **Suy giảm chất lượng ngầm định:** 
   - **Mất bản ghi mới (Drop 20%):** RAG không tìm thấy tài liệu liên quan, dẫn đến trả lời bịa đặt (hallucination) hoặc trả về *"I don't know"*.
   - **Xóa tóm tắt (Blank summary) & Chèn nhiễu (Noise):** Embedding vector bị lệch hướng trong không gian ngữ nghĩa, làm Token F1 và Judge Accuracy giảm sâu.
   - **Nhân bản dữ liệu (Duplicate rows):** Gây nhiễu thứ hạng truy vấn (`top_k`) trong ChromaDB.

> 🛡️ **Vai trò của Great Expectations 1.x:** Quality Gate đóng vai trò như chốt kiểm dịch tự động, chặn đứng dữ liệu bẩn trước khi tiến hành tính toán vector embedding và nạp vào Vector Database serving layer.

---

## 3. Đánh Giá Cơ Chế Phục Hồi Idempotent Repair

1. **Khôi phục từ nguồn tin cậy:** Hệ thống tự động đọc lại bản sao lưu thô ban đầu `data/raw/crossref_records.json` (bảo toàn Data Lineage).
2. **Quy trình làm sạch tái lập (Idempotent):** Áp dụng lại các quy tắc làm sạch, tính toán `age_days` và tái tạo `text_for_embedding`. Dù chạy lại nhiều lần, kết quả đầu ra luôn đồng nhất và không sinh ra bản ghi rác.
3. **Đồng bộ hóa Vector Database:** ChromaDB collection `papers-repaired` được purge sạch sẽ và nạp mới, loại bỏ hoàn toàn các **Ghost Vectors** (vector mồ côi).
4. **Kết quả phục hồi:** Toàn bộ chỉ số Hit Rate, Token F1 và Judge Accuracy đã phục hồi về tương đương trạng thái **Baseline ban đầu**.
