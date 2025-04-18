# spellcheck_web.py
import streamlit as st
import os
from openai import OpenAI
from io import BytesIO
import base64
import fitz  # PyMuPDF
import textwrap
from docx import Document
from difflib import ndiff

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
.changed {
    background-color: #ffffcc;
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
1. Tải lên tệp văn bản tiếng Việt cần kiểm tra lỗi chính tả (hỗ trợ định dạng `.txt`, `.docx`, `.pdf`).
2. Hệ thống sẽ kiểm tra và hiển thị kết quả đã chỉnh sửa ngay bên dưới.
3. Có thể tải kết quả về dưới dạng `.txt` hoặc `.docx` để lưu trữ.
4. So sánh đoạn văn gốc và đoạn đã sửa để thấy rõ thay đổi.
5. Có thể lựa chọn mô hình GPT-3.5 để tiết kiệm chi phí.
---
""")

model = st.radio("🔍 Chọn mô hình AI để kiểm tra:", ["gpt-3.5-turbo", "gpt-4o"], index=1)

uploaded_file = st.file_uploader("📄 Tải lên tệp cần kiểm tra chính tả:", type=["txt", "docx", "pdf"])

if uploaded_file:
    with st.spinner("📑 Đang xử lý tệp..."):
        file_text = ""
        paragraphs = []
        doc = None

        if uploaded_file.type == "text/plain":
            file_text = uploaded_file.read().decode("utf-8", errors="ignore")
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = Document(uploaded_file)
            for para in doc.paragraphs:
                text = para.text.strip()
                if text:
                    paragraphs.append((para, text))
                    file_text += text + "\n"
        elif uploaded_file.type == "application/pdf":
            pdf_doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            for page in pdf_doc:
                file_text += page.get_text()

        if not file_text.strip():
            st.warning("📭 Không thể đọc được nội dung từ tệp đã tải lên.")
            st.stop()

        def chunk_text(text, max_length=3000):
            paragraphs = textwrap.wrap(text, width=max_length, break_long_words=False, replace_whitespace=False)
            return paragraphs

        corrected_all = ""
        original_all = ""
        total_tokens = 0

        def highlight_diff(original, corrected):
            diff = ndiff(original.split(), corrected.split())
            highlighted = []
            for word in diff:
                if word.startswith('+'):
                    highlighted.append(f"<span class='changed'>{word[2:]}</span>")
                elif word.startswith('-'):
                    continue
                elif word.startswith(' '):
                    highlighted.append(word[2:])
            return ' '.join(highlighted)

        if doc and paragraphs:
            highlighted_output = []
            for para, text in paragraphs:
                res = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "Bạn là một chuyên gia ngôn ngữ tiếng Việt. Hãy sửa lỗi chính tả trong đoạn văn sau."},
                        {"role": "user", "content": text}
                    ],
                    temperature=0.3,
                    max_tokens=1024
                )
                corrected = res.choices[0].message.content.strip()
                para.text = corrected
                corrected_all += corrected + "\n"
                original_all += text + "\n"
                if hasattr(res, "usage"):
                    total_tokens += res.usage.total_tokens
                highlighted_output.append(highlight_diff(text, corrected))
        else:
            chunks = chunk_text(file_text)
            highlighted_output = []
            for chunk in chunks:
                res = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "Bạn là một chuyên gia ngôn ngữ tiếng Việt. Hãy sửa lỗi chính tả trong đoạn văn sau."},
                        {"role": "user", "content": chunk}
                    ],
                    temperature=0.3,
                    max_tokens=1024
                )
                corrected = res.choices[0].message.content.strip()
                corrected_all += corrected + "\n"
                original_all += chunk + "\n"
                if hasattr(res, "usage"):
                    total_tokens += res.usage.total_tokens
                highlighted_output.append(highlight_diff(chunk, corrected))

        st.subheader("📝 So sánh văn bản trước và sau khi sửa lỗi")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**📄 Văn bản gốc:**")
            st.text_area("", original_all[:5000], height=300)
        with col2:
            st.markdown("**✅ Đã sửa lỗi (bôi vàng chỗ thay đổi):**")
            st.markdown(f"<div class='result-box'>{'<br>'.join(highlighted_output)}</div>", unsafe_allow_html=True)

        if total_tokens > 0:
            st.info(f"🔢 Token đã sử dụng: {total_tokens} (ước tính chi phí ~{total_tokens / 1000 * (0.01 if model == 'gpt-3.5-turbo' else 0.03):.4f} USD)")

        if doc:
            output = BytesIO()
            doc.save(output)
            b64_docx = base64.b64encode(output.getvalue()).decode()
            st.markdown(f'<a class="download-btn" href="data:application/octet-stream;base64,{b64_docx}" download="ket_qua_da_sua.docx">📥 Tải file Word đã sửa</a>', unsafe_allow_html=True)
        else:
            b64 = base64.b64encode(corrected_all.encode()).decode()
            href = f'<a class="download-btn" href="data:file/txt;base64,{b64}" download="ket_qua_da_sua.txt">📥 Tải kết quả về</a>'
            st.markdown(href, unsafe_allow_html=True)

        st.markdown("---")
        if st.button("🔄 Bắt đầu phiên kiểm tra mới"):
            st.experimental_rerun()
