# spellcheck_web.py
import streamlit as st
import os
from openai import OpenAI
from io import BytesIO
import base64
import fitz  # PyMuPDF
from docx import Document
from difflib import ndiff, SequenceMatcher
import re
import time

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
3. Có thể tải kết quả về dưới dạng `.txt`, `.docx` hoặc `.pdf` để lưu trữ.
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
        pdf_data = None
        filename = uploaded_file.name.rsplit('.', 1)[0]

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
            pdf_data = uploaded_file.read()
            pdf_doc = fitz.open(stream=pdf_data, filetype="pdf")
            for page in pdf_doc:
                lines = page.get_text("text").split("\n")
                for line in lines:
                    if line.strip() and len(line.strip()) > 10:
                        file_text += line.strip() + "\n"

        if not file_text.strip():
            st.warning("📭 Không thể đọc được nội dung từ tệp đã tải lên.")
            st.stop()

        def chunk_sentences(text, max_len=500):
            sentences = re.split(r'(?<=[.!?])\s+', text)
            chunks = []
            chunk = ""
            for s in sentences:
                if len(chunk) + len(s) < max_len:
                    chunk += s + " "
                else:
                    chunks.append(chunk.strip())
                    chunk = s + " "
            if chunk:
                chunks.append(chunk.strip())
            return chunks

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

        def count_corrections(orig, corrected):
            sm = SequenceMatcher(None, orig.split(), corrected.split())
            return sum(1 for tag, _, _, _, _ in sm.get_opcodes() if tag != 'equal')

        corrected_all = ""
        original_all = ""
        highlighted_output = []
        total_tokens = 0
        total_corrections = 0
        start_time = time.time()

        if doc and paragraphs:
            for para, text in paragraphs:
                try:
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
                    total_corrections += count_corrections(text, corrected)
                    if hasattr(res, "usage"):
                        total_tokens += res.usage.total_tokens
                    highlighted_output.append(highlight_diff(text, corrected))
                except Exception as e:
                    highlighted_output.append(f"<span style='color:red;'>Lỗi xử lý đoạn: {text[:50]}... ➜ {str(e)}</span>")
        else:
            chunks = chunk_sentences(file_text)
            for chunk in chunks:
                try:
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
                    total_corrections += count_corrections(chunk, corrected)
                    if hasattr(res, "usage"):
                        total_tokens += res.usage.total_tokens
                    highlighted_output.append(highlight_diff(chunk, corrected))
                except Exception as e:
                    highlighted_output.append(f"<span style='color:red;'>Lỗi xử lý đoạn: {chunk[:50]}... ➜ {str(e)}</span>")

        duration = time.time() - start_time

        st.subheader("📝 So sánh văn bản trước và sau khi sửa lỗi")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**📄 Văn bản gốc:**")
            st.text_area("", original_all[:5000], height=300)
        with col2:
            st.markdown("**✅ Đã sửa lỗi (bôi vàng chỗ thay đổi):**")
            st.markdown(f"<div class='result-box'>{'<br>'.join(highlighted_output)}</div>", unsafe_allow_html=True)

        st.info(f"🔢 Token đã sử dụng: {total_tokens} (ước tính chi phí ~{total_tokens / 1000 * (0.01 if model == 'gpt-3.5-turbo' else 0.03):.4f} USD)")
        st.info(f"✏️ Tổng số lỗi đã sửa: {total_corrections}")
        st.info(f"⏱️ Thời gian xử lý: {duration:.2f} giây")

        if doc:
            output = BytesIO()
            doc.save(output)
            b64_docx = base64.b64encode(output.getvalue()).decode()
            st.markdown(f'<a class="download-btn" href="data:application/octet-stream;base64,{b64_docx}" download="{filename}_da_sua.docx">📥 Tải file Word đã sửa</a>', unsafe_allow_html=True)
        elif pdf_data:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            from PyPDF2 import PdfWriter, PdfReader
            import tempfile

            # Tạo PDF mới từ nội dung đã sửa
            temp_pdf = BytesIO()
            c = canvas.Canvas(temp_pdf, pagesize=letter)
            textobject = c.beginText(40, 750)
            for line in corrected_all.split("
"):
                textobject.textLine(line)
            c.drawText(textobject)
            c.save()

            # Tạo file kết hợp nếu muốn ghép lại nền cũ + sửa mới (tuỳ chỉnh nâng cao)
            # Còn không thì chỉ cần xuất file sửa
            temp_pdf.seek(0)
            b64_pdf_corrected = base64.b64encode(temp_pdf.read()).decode()
            st.markdown(f'<a class="download-btn" href="data:application/pdf;base64,{b64_pdf_corrected}" download="{filename}_da_sua.pdf">📥 Tải file PDF đã sửa</a>', unsafe_allow_html=True)">📥 Tải lại file PDF gốc</a>', unsafe_allow_html=True)
        else:
            b64 = base64.b64encode(corrected_all.encode()).decode()
            href = f'<a class="download-btn" href="data:file/txt;base64,{b64}" download="{filename}_da_sua.txt">📥 Tải kết quả về</a>'
            st.markdown(href, unsafe_allow_html=True)

        st.markdown("---")
        if st.button("🔄 Bắt đầu phiên kiểm tra mới"):
            preserved_model = st.session_state.get("model", "gpt-4o")
            keys_to_clear = list(st.session_state.keys())
            for key in keys_to_clear:
                del st.session_state[key]
            st.session_state["model"] = preserved_model
            st.experimental_rerun()
