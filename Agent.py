import os
os.environ["HF_TOKEN"] = "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"
import os
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# 1. Dán API Key của bạn vào đây
os.environ["GOOGLE_API_KEY"] = "AQ.Ab8RN6Kf32iFopL5JZctllBGjGggmf3pVRfxjvaZFnF8jrwa9Q"


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


def ask_agent(question):
    embeddings_model = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

    vector_db = Chroma(
        persist_directory="./my_vector_db",
        embedding_function=embeddings_model
    )
    retriever = vector_db.as_retriever(search_kwargs={"k": 3})

    # CẬP NHẬT: Sử dụng đúng mô hình Gemini 3.6 Flash như trong ảnh của bạn!
    llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0)

    system_prompt = (
        "Bạn là một chuyên gia phân tích chứng khoán Việt Nam.\n"
        "Hãy trả lời câu hỏi dựa trên các đoạn tin tức (Context) được cung cấp bên dưới.\n\n"
        "QUY TẮC BẮT BUỘC:\n"
        "- Mọi thông tin bạn nói ra PHẢI lấy từ Context.\n"
        "- BẮT BUỘC phải trích dẫn nguồn bằng cách liệt kê [Link URL của bài báo] ở cuối câu trả lời.\n"
        "- Nếu Context không có thông tin, hãy nói thẳng: 'Dữ liệu hiện tại không đề cập đến vấn đề này'.\n\n"
        "Ngữ cảnh (Context):\n{context}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])

    rag_chain = (
            {"context": retriever | format_docs, "input": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
    )

    print(f"\n[AI đang suy nghĩ...]")
    response = rag_chain.invoke(question)

    print("\n✨ GEMINI TRẢ LỜI:")
    print("-" * 50)
    print(response)
    print("-" * 50)


# TÍNH NĂNG CHAT LIÊN TỤC TỪ BÀN PHÍM
if __name__ == "__main__":
    print("=" * 50)
    print("🤖 CHÀO MỪNG ĐẾN VỚI TRỢ LÝ CHỨNG KHOÁN AI (GEMINI 3.6)")
    print("Gõ câu hỏi của bạn. Gõ 'q' hoặc 'thoat' để dừng chương trình.")
    print("=" * 50)

    while True:
        # Lấy đầu vào từ bàn phím
        cau_hoi = input("\nBạn hỏi 👤: ")

        # Kiểm tra nếu người dùng muốn thoát
        if cau_hoi.lower() in ['q', 'thoat', 'exit', 'quit']:
            print("👋 Tạm biệt! Hẹn gặp lại.")
            break

        # Kiểm tra nếu người dùng gõ rỗng
        if not cau_hoi.strip():
            continue

        ask_agent(cau_hoi)