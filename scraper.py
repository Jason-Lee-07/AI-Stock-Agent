import feedparser
import requests


def get_latest_news():
    print("Đang kết nối đến tòa soạn báo...")
    rss_url = "https://vnexpress.net/rss/kinh-doanh.rss"

    # 1. Gắn thẻ căn cước (User-Agent) giả làm người dùng thật đang xài MacBook
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        # 2. Dùng thư viện requests để gõ cửa trang web một cách lịch sự
        response = requests.get(rss_url, headers=headers)

        # 3. Đưa nội dung thô cho feedparser đọc hiểu
        feed = feedparser.parse(response.content)

        news_data = []
        for entry in feed.entries[:5]:  # Vẫn lấy 5 bài đầu tiên
            news_item = {
                "title": entry.title,
                "link": entry.link,
                "published_at": entry.published if 'published' in entry else "Vừa xong",
                "source": "VNExpress"
            }
            summary = entry.summary if 'summary' in entry else ""
            news_item["content"] = summary

            news_data.append(news_item)

        print(f"Đã vượt tường lửa và lấy thành công {len(news_data)} bài báo!")
        return news_data

    except Exception as e:
        print(f"Có lỗi xảy ra: {e}")
        return []


if __name__ == "__main__":
    tin_tuc = get_latest_news()
    print("-" * 50)
    for tin in tin_tuc:
        print(f"⏰ {tin['published_at']}")
        print(f"📰 {tin['title']}")
        print(f"🔗 {tin['link']}")
        print("-" * 50)