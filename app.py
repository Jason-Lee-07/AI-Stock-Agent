import streamlit as st
import sys
import os
import re
from apscheduler.schedulers.background import BackgroundScheduler

# Cấu hình trang Web (BẮT BUỘC đặt ở đầu file)
st.set_page_config(page_title="AI Stock Agent", page_icon="📈", layout="centered")

# Ép Python tìm thấy file trong cùng thư mục & chống lỗi UTF-8
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
os.environ["PYTHONIOENCODING"] = "utf-8"

# Đồng bộ API Key từ Streamlit Secrets vào Environment Variables
if "GOOGLE_API_KEY" in st.secrets:
    os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]

import vector_db
import analytics  # Thư viện tính toán FA/TA/Quant
import screener
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

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

# ==========================================
# CÔNG CỤ QUÉT TOÀN THỊ TRƯỜNG (SIDEBAR)
# ==========================================
with st.sidebar:
    st.header("⚙️ Phân Tích Định Lượng")
    st.write("Thuật toán kết hợp CANSLIM & Top-Down")

    if st.button("🔍 Quét Thị Trường 4 Bước", use_container_width=True):
        st.session_state.trigger_scan = True

if 'trigger_scan' not in st.session_state:
    st.session_state.trigger_scan = False

st.title("📈 Trợ Lý Phân Tích Chứng Khoán AI")
st.caption("Hệ thống RAG tự động cập nhật tin tức & trích dẫn nguồn chuẩn xác từ báo chí")

@st.cache_resource
def init_rag_chain():
    # Sử dụng HuggingFace Embeddings chạy nội bộ
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )

    vector_store = Chroma(
        persist_directory="./my_vector_db",
        embedding_function=embeddings
    )
    retriever = vector_store.as_retriever(search_kwargs={"k": 3})

    # Kết nối mô hình Gemini
    llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash", temperature=0)

    # BƯỚC C: NÂNG CẤP PROMPT ĐÁNH GIÁ TÂM LÝ THỊ TRƯỜNG (MARKET SENTIMENT)
    system_prompt = (
        "Bạn là Giám đốc Quản lý Quỹ kiêm Chuyên gia Phân tích Tâm lý Thị trường Chứng khoán Việt Nam.\n"
        "Nhiệm vụ của bạn là kết hợp Dữ liệu Tin tức Báo chí (Context) và Dữ liệu Định lượng (Input) để đưa ra góc nhìn sắc bén.\n\n"
        "BẮT BUỘC CẤU TRÚC BÀI PHÂN TÍCH THEO CÁC BƯỚC:\n"
        "1. 🧠 **ĐÁNH GIÁ TÂM LÝ THỊ TRƯỜNG (MARKET SENTIMENT)**:\n"
        "   - Phân loại sắc thái tin tức vĩ mô/ngành hiện tại: [TÍCH CỰC (Bullish) / TIÊU CỰC (Bearish) / TRUNG LẬP (Neutral)].\n"
        "   - Tóm tắt 1-2 ý chính từ tin tức làm cơ sở phân loại (BẮT BUỘC trích dẫn [Link URL] từ Context ở cuối câu).\n"
        "   - Đánh giá tâm lý nhà đầu tư cá nhân (Đang hưng phấn, lo sợ hay quan sát?).\n\n"
        "2. 📊 **PHÂN TÍCH ĐỊNH LƯỢNG & DÒNG TIỀN (FA/TA/VOLUME)**:\n"
        "   - Đánh giá sức khỏe tài chính (P/E, ROE) và kỹ thuật (Xu hướng MA50, RSI).\n"
        "   - Đặc biệt chú ý dòng 'Dấu chân Dòng tiền (Volume)' do Python cung cấp để nhận diện cá mập gom/xả.\n\n"
        "3. 🎯 **KỊCH BẢN GIAO DỊCH & HÀNH ĐỘNG**:\n"
        "   - Kết luận: CÓ NÊN MUA HAY KHÔNG?\n"
        "   - Đưa ra vùng Giá mua Breakout (+2% từ đỉnh ngắn hạn) và Điểm Cắt lỗ cụ thể (-5% hoặc vi phạm MA50).\n\n"
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

    chain = (
            {"context": retriever | format_docs, "input": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
    )
    return chain

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
    st.session_state.trigger_scan = False

    scan_request = "Hệ thống: Kích hoạt thuật toán quét thị trường 4 bước..."
    st.session_state.messages.append({"role": "user", "content": scan_request})
    st.chat_message("user").write(scan_request)

    with st.chat_message("assistant"):
        with st.spinner("Đang chạy bộ lọc định lượng hàng ngàn mã..."):
            top_stocks_data = screener.run_market_screener()

            ai_prompt = (
                f"Dữ liệu định lượng vừa lọc được các mã dẫn dắt sau:\n{top_stocks_data}\n\n"
                "Nhiệm vụ của bạn (Áp dụng Tư duy Top-Down và Tìm Điểm Nổ):\n"
                "1. Bước 1 (Vĩ mô): Đánh giá nhanh bối cảnh dòng tiền hiện tại đang ủng hộ các ngành nào trong danh sách trên.\n"
                "2. Bước 4 (Ra quyết định): Chọn ra 2 mã có tiềm năng nhất từ danh sách. Đưa ra Kịch bản giao dịch cụ thể (Điểm mua Breakout khi nào, Cắt lỗ ở đâu) và nêu Chất xúc tác (Catalyst) của doanh nghiệp đó."
            )

        with st.spinner("AI đang phân tích vĩ mô và thiết lập kịch bản giao dịch..."):
            response = rag_chain.invoke(ai_prompt)
            st.write(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

# ==========================================
# Ô NHẬP LIỆU DUY NHẤT & BỘ QUÉT MÃ CỔ PHIẾU TỐI ƯU
# ==========================================
if user_query := st.chat_input("Nhập câu hỏi hoặc yêu cầu phân tích mã (VD: HPG, fpt, so sánh SSI và VND)..."):
    st.session_state.messages.append({"role": "user", "content": user_query})
    st.chat_message("user").write(user_query)

    stock_context = ""

    # 1. BỘ QUÉT THÔNG MINH: Tìm tất cả từ 3 chữ cái (bắt cả chữ hoa lẫn chữ thường)
    raw_matches = re.findall(r'\b[a-zA-Z]{3}\b', user_query)

    # 2. BỘ LỌC TỪ GÂY NHIỄU: Loại bỏ chỉ báo kỹ thuật & từ tiếng Việt 3 chữ cái
    ignore_words = {
        "RSI", "MAC", "GDP", "FDI", "PE", "EPS", "ROE", "BOT",
        "MUA", "BAN", "GIA", "CHO", "NEN", "TOP", "HAY", "LAI",
        "LUC", "MAI", "NAY", "ROI", "SAO", "THE", "TIN", "TOT", "XAU", "YEU"
    }

    found_tickers = []
    for word in raw_matches:
        ticker = word.upper()
        if ticker not in ignore_words and ticker not in found_tickers:
            found_tickers.append(ticker)

    # 3. KÉO DỮ LIỆU ĐA MÃ CÙNG LÚC
    if found_tickers:
        with st.spinner(f"Đang phân tích dữ liệu FA/TA/Quant cho: {', '.join(found_tickers)}..."):
            for ticker in found_tickers:
                data = analytics.analyze_stock(ticker)
                stock_context += f"\n\n[DỮ LIỆU TÀI CHÍNH & KỸ THUẬT MỚI NHẤT CỦA {ticker}]:\n{data}"

    with st.chat_message("assistant"):
        with st.spinner("Đang tổng hợp phân tích..."):
            full_prompt = user_query + stock_context
            response = rag_chain.invoke(full_prompt)
            st.write(response)
            st.session_state.messages.append({"role": "assistant", "content": response})