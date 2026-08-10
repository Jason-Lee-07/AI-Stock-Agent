import os
import urllib3

# Tắt cảnh báo SSL không an toàn trên máy Mac
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Thiết lập USER_AGENT lên đầu để triệt tiêu cảnh báo của LangChain
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
os.environ["USER_AGENT"] = USER_AGENT

import requests
import feedparser
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma


def get_daily_news_urls():
    """Dùng requests kéo trực tiếp XML từ RSS để vượt qua tường lửa/lỗi SSL Mac."""
    print("Đang quét các bài báo mới nhất từ các nguồn RSS...")
    urls = []

    # Nguồn RSS chuẩn đã được tối ưu
    rss_feeds = [
        "https://vnexpress.net/rss/kinh-doanh.rss",
        "https://tuoitre.vn/rss/kinh-doanh.rss"
    ]

    headers = {'User-Agent': USER_AGENT}

    for feed_url in rss_feeds:
        try:
            # Kéo nội dung XML bằng requests (bỏ qua verify SSL nếu môi trường Python Mac bị thiếu chứng chỉ)
            response = requests.get(feed_url, headers=headers, timeout=10, verify=False)
            if response.status_code == 200:
                feed = feedparser.parse(response.content)
                for entry in feed.entries[:10]:
                    if hasattr(entry, 'link'):
                        urls.append(entry.link)
            else:
                print(f"Không thể truy cập {feed_url} - Mã lỗi: {response.status_code}")
        except Exception as e:
            print(f"Lỗi khi đọc luồng {feed_url}: {e}")

    urls = list(set(urls))
    print(f"Đã tìm thấy {len(urls)} bài báo mới hôm nay!")
    return urls


def update_vector_db():
    dynamic_urls = get_daily_news_urls()

    if not dynamic_urls:
        print("Không tìm thấy link nào để nạp. Vui lòng kiểm tra lại kết nối mạng.")
        return

    print("1. Đang tải nội dung chi tiết từ các đường link...")
    loader = WebBaseLoader(dynamic_urls)
    docs = loader.load()

    print("2. Đang phân tách văn bản thành các đoạn nhỏ...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    splits = text_splitter.split_documents(docs)

    for doc in splits:
        if "source" in doc.metadata:
            doc.metadata["link"] = doc.metadata["source"]

    print("3. Đang mã hóa và nạp vào kho tri thức AI (Chroma DB)...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )

    vector_db = Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        persist_directory="./my_vector_db"
    )
    print("✅ Thành công! Kho dữ liệu AI đã được cập nhật tin tức mới nhất.")


if __name__ == "__main__":
    update_vector_db()