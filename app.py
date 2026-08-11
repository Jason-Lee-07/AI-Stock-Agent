import streamlit as st
import sys
import os
import re
import os
from apscheduler.schedulers.background import BackgroundScheduler
import vector_db

# 1. Tự động cào tin ngay khi server khởi động nếu phát hiện kho dữ liệu bị mất
if not os.path.exists("./my_vector_db"):
    print("Khởi tạo kho dữ liệu lần đầu trên Cloud...")
    vector_db.update_vector_db()

# 2. Lập lịch cào tin tự động 07:00 sáng mỗi ngày
def start_scheduler():
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(vector_db.update_vector_db, 'cron', hour=7, minute=0)
    scheduler.start()

if "scheduler_started" not in st.session_state:
    start_scheduler()
    st.session_state.scheduler_started = True

# Ép Python luôn tìm thấy file analytics.py trong cùng thư mục dự án
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Cấu hình mã hóa UTF-8 chống lỗi Unicode
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
os.environ["PYTHONIOENCODING"] = "utf-8"

import streamlit as st
import analytics  # Thư viện tính toán FA/TA/Quant
import screener
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# Cấu hình trang Web
st.set_page_config(page_title="AI Stock Agent", page_icon="📈", layout="centered")
# ==========================================
# CÔNG CỤ QUÉT TOÀN THỊ TRƯỜNG (SIDEBAR)
# ==========================================
with st.sidebar:
    st.header("⚙️ Phân Tích Định Lượng")
    st.write("Thuật toán kết hợp CANSLIM & Top-Down")

    if st.button("🔍 Quét Thị Trường 4 Bước", use_container_width=True):
        st.session_state.trigger_scan = True

# Khởi tạo state để bắt sự kiện click nút
if 'trigger_scan' not in st.session_state:
    st.session_state.trigger_scan = False
# API Keys (Lưu ý: Thay API Key Gemini thật của bạn vào đây)
os.environ["GOOGLE_API_KEY"] = "AQ.Ab8RN6Kf32iFopL5JZctllBGjGggmf3pVRfxjvaZFnF8jrwa9Q"
os.environ["HF_TOKEN"] = "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"

st.title("📈 Trợ Lý Phân Tích Chứng Khoán AI")
st.caption("Hệ thống RAG tự động cập nhật tin tức & trích dẫn nguồn chuẩn xác từ báo chí")


@st.cache_resource
def init_rag_chain():
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    vector_db = Chroma(
        persist_directory="./my_vector_db",
        embedding_function=embeddings
    )
    retriever = vector_db.as_retriever(search_kwargs={"k": 3})
    llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0)

    system_prompt = (
        "Bạn là Giám đốc Quản lý Quỹ đầu tư chứng khoán Việt Nam.\n"
        "Hãy kết hợp linh hoạt 2 nguồn thông tin được cung cấp:\n"
        "1. Dữ liệu Tin tức Báo chí trong Context (BẮT BUỘC trích dẫn [Link URL] ở cuối câu nếu dùng thông tin này).\n"
        "2. Dữ liệu Số liệu Định lượng (Giá, MA50, ROE, RS Score) do Python cung cấp trong Input.\n\n"
        "QUY TẮC PHÂN TÍCH:\n"
        "- Với Bước 1 (Vĩ mô): Dùng tin tức báo chí để đánh giá sóng ngành. Nếu mã nào không có tin tức báo chí, hãy đánh giá sức mạnh ngành dựa vào RS Score và Tăng trưởng lợi nhuận từ số liệu Python.\n"
        "- Với Bước 4 (Kịch bản): Dùng Giá đóng cửa và MA50 để tự tính toán Điểm mua Breakout (Giá đỉnh +2%) và Điểm Cắt lỗ (Vùng MA50 hoặc -5% từ giá mua).\n\n"
        "Context Tin Tức:\n{context}"
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])

    def format_docs(docs):
        return "\n\n".join(
            f"{doc.page_content}\nNguồn link: {doc.metadata.get('link', '')}"
            for doc in docs
        )

    return (
            {"context": retriever | format_docs, "input": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
    )


rag_chain = init_rag_chain()

# Bộ nhớ cuộc trò chuyện
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Xin chào! Tôi có thể giúp gì cho bạn về tin tức chứng khoán hôm nay?"}
    ]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])
# Xử lý sự kiện bấm nút Quét thị trường
if st.session_state.trigger_scan:
    # Reset nút
    st.session_state.trigger_scan = False

    # Tạo câu prompt tự động hiển thị trên giao diện
    scan_request = "Hệ thống: Kích hoạt thuật toán quét thị trường 4 bước..."
    st.session_state.messages.append({"role": "user", "content": scan_request})
    st.chat_message("user").write(scan_request)

    with st.chat_message("assistant"):
        with st.spinner("Đang chạy bộ lọc định lượng hàng ngàn mã..."):
            # 1. Gọi Bước 2 & 3: Python quét và chấm điểm
            top_stocks_data = screener.run_market_screener()

            # 2. Gọi Bước 1 & 4: Giao cho AI tư duy Vĩ mô và tìm Điểm nổ
            ai_prompt = (
                f"Dữ liệu định lượng vừa lọc được các mã dẫn dắt sau:\n{top_stocks_data}\n\n"
                "Nhiệm vụ của bạn (Áp dụng Tư duy Top-Down và Tìm Điểm Nổ):\n"
                "1. Bước 1 (Vĩ mô): Đánh giá nhanh bối cảnh dòng tiền hiện tại đang ủng hộ các ngành nào trong danh sách trên.\n"
                "2. Bước 4 (Ra quyết định): Chọn ra 2 mã có tiềm năng nhất từ danh sách. Đưa ra Kịch bản giao dịch cụ thể (Điểm mua Breakout khi nào, Cắt lỗ ở đâu) và nêu Chất xúc tác (Catalyst) của doanh nghiệp đó."
            )

        with st.spinner("AI đang phân tích vĩ mô và thiết lập kịch bản giao dịch..."):
            # Gửi yêu cầu qua RAG Chain
            response = rag_chain.invoke(ai_prompt)
            st.write(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
# Ô NHẬP LIỆU DUY NHẤT
if user_query := st.chat_input("Nhập câu hỏi hoặc yêu cầu phân tích mã (VD: HPG)..."):
    st.session_state.messages.append({"role": "user", "content": user_query})
    st.chat_message("user").write(user_query)

    stock_context = ""

    # Dùng Regex tự động tìm mã chứng khoán 3 chữ cái IN HOA trong câu văn
    match = re.search(r'\b[A-Z]{3}\b', user_query)
    if match:
        ticker = match.group(0)
        with st.spinner(f"Đang phân tích dữ liệu FA/TA/Quant cho mã {ticker}..."):
            data = analytics.analyze_stock(ticker)
            stock_context = f"\n\n[DỮ LIỆU TÀI CHÍNH & KỸ THUẬT MỚI NHẤT CỦA {ticker}]:\n{data}"

    with st.chat_message("assistant"):
        with st.spinner("Đang tổng hợp phân tích..."):
            full_prompt = user_query + stock_context
            response = rag_chain.invoke(full_prompt)
            st.write(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
