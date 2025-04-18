# spellcheck_web.py
import streamlit as st
import os
from openai import OpenAI
from io import StringIO
import base64

openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    st.error("🚫 Hệ thống chưa cấu hình API Key. Vui lòng liên hệ quản trị viên để thiết lập biến môi trường OPENAI_API_KEY.")
    st.stop()

client = OpenAI(api_key=openai_api_key)

st.set_page_config(
    page_title="Trợ lý Sửa lỗi Chính tả | ECOVIS AFA VIETNAM",
    page_icon="📝",
    layout="wide",
)

password = st.text_input("🔐 Nhập mật khẩu để truy cập:", type="password")
if password != "ecovis2025":
    st.warning("Vui lòng nhập đúng mật khẩu.")
    st.stop()

st.markdown("""
<style>
.result-box {
    padding: 1rem;
    border: 1px solid #ccc;
    border-radius: 10px;
    background-color: #f9f9f9;
    white-space: pre-wrap;
    font-family: monospace;
}
.download-btn {
    margin-top: 1rem;
}
</style>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 10])
with col1:
    st.image("LOGO ECOVIS AFA VIETNAM.jpg", width=80)
with col2:
    st.title("📘 Trợ lý Sửa lỗi Chính tả | ECOVIS AFA VIETNAM")

st.markdown("---")

st.markdown("""
#### 📂 Hướng dẫn sử dụng:
1. Tải lên tệp văn bản tiếng Việt cần kiểm tra lỗi chính tả (chỉ hỗ trợ định dạng `.txt`, `.docx`, `.pdf`).
2. Hệ thống sẽ kiểm tra và hiển thị kết quả đã chỉnh sửa ngay bên dưới.
3. Có thể tải kết quả về dưới dạng `.txt` để lưu trữ.

---
""")

uploaded_file = st.file_uploader("📄 Tải lên tệp cần kiểm tra chính tả:", type=["txt"])

if uploaded_file:
    with st.spinner("📑 Đang xử lý tệp..."):
        file_text = uploaded_file.read().decode("utf-8", errors="ignore")

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Bạn là một chuyên gia ngôn ngữ tiếng Việt. Hãy giúp tôi kiểm tra và sửa lỗi chính tả, lỗi đánh máy và lỗi ngữ pháp trong đoạn văn sau."},
                {"role": "user", "content": file_text[:3000]}  # Giới hạn token đầu vào để tiết kiệm
            ],
            temperature=0.3,
            max_tokens=1024
        )

        corrected = response.choices[0].message.content

        st.subheader("📝 Kết quả kiểm tra chính tả")
        st.markdown(f"<div class='result-box'>{corrected}</div>", unsafe_allow_html=True)

        # Chuẩn bị file tải về
        b64 = base64.b64encode(corrected.encode()).decode()
        href = f'<a class="download-btn" href="data:file/txt;base64,{b64}" download="ket_qua_da_sua.txt">📥 Tải kết quả về</a>'
        st.markdown(href, unsafe_allow_html=True)
