import streamlit as st
import random
import dashboard # Đây là file dashboard.py của bạn

# =========================
# PAGE CONFIG (Chỉ gọi 1 lần ở file chính)
# =========================
st.set_page_config(
    page_title="Software License Sales Report & QA",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================
# NGÂN HÀNG CÂU HỎI
# =========================
QUESTION_BANK = [
    "1. Quốc gia nào dẫn đầu về tổng doanh thu trong mục Country Performance?",
    "2. Số lượng 'Days Left EOQ' hiện tại trên dashboard là bao nhiêu?",
    "3. Có bao nhiêu giao dịch (QTD Transactions) được ghi nhận trong quý hiện tại?",
    "4. Số lượng 'Admins' và 'Designers' hiện tại là bao nhiêu?",
    "5. Khách hàng nào đứng đầu trong danh sách 'Last 5 Orders'?",
    "6. Biểu đồ Quarterly Metrics cho thấy quý nào trong năm 2016 có số lượng Servers cao nhất?",
    "7. Số lượng 'Active Clients' QTD hiện tại là bao nhiêu?",
    "8. Khi lọc theo 'Product 1', chỉ số QTD Sales thay đổi như thế nào?",
    "9. Đường Running Total của quý hiện tại (Current) đang nằm trên hay dưới quý trước (Previous)?",
    "10. Nếu chỉ chọn giấy phép 'Invoice', số lượng QTD SAMS là bao nhiêu?"
]

# =========================
# HÀM TẠO PDF
# =========================

# =========================
# GIAO DIỆN CHÍNH
# =========================
def main():
    st.sidebar.title("📌 Điều hướng")
    page = st.sidebar.radio("Chọn trang:", ["Trang Câu hỏi", "Trang Dashboard"])

    if page == "Trang Câu hỏi":
        st.title("Danh sách câu hỏi")
        # Sử dụng session_state để lưu 5 câu hỏi ngẫu nhiên, tránh việc reload lại mỗi lần người dùng click
        if "random_questions" not in st.session_state:
            st.session_state.random_questions = random.sample(QUESTION_BANK, 5)

        # Hiển thị câu hỏi
        st.markdown("### 5 Câu hỏi bất kì:")
        for q in st.session_state.random_questions:
            st.info(q)

        st.write("---")
        
        # Nút tạo mới câu hỏi và xuất PDF
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Tạo bộ 5 câu hỏi mới", use_container_width=True):
                st.session_state.random_questions = random.sample(QUESTION_BANK, 5)
                st.rerun()

    elif page == "Trang Dashboard":
        # Gọi hàm hiển thị dashboard từ file dashboard.py
        dashboard.show_dashboard()

if __name__ == "__main__":
    main()