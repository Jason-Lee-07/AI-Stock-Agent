import pandas as pd


def fetch_mock_data():
    """
    Giả lập dữ liệu toàn thị trường.
    (Thực tế: Bạn sẽ dùng thư viện vnstock để tải dữ liệu thật của 1600 mã)
    """
    data = {
        'Ticker': ['FPT', 'HPG', 'SSI', 'VND', 'MWG', 'VJC', 'VIC', 'VCB'],
        'Sector': ['Công nghệ', 'Thép', 'Chứng khoán', 'Chứng khoán', 'Bán lẻ', 'Hàng không', 'Bất động sản',
                   'Ngân hàng'],
        'Price': [130, 30, 35, 17, 50, 100, 45, 90],
        'MA50': [120, 28, 33, 18, 45, 105, 48, 88],
        'Volume_Avg': [2000000, 15000000, 8000000, 10000000, 5000000, 400000, 1000000, 1500000],
        'ROE': [25, 18, 16, 10, 15.5, 5, 8, 20],
        'Profit_Growth': [20, 30, 25, 5, 18, -10, -5, 16],
        'Debt_Equity': [0.5, 0.4, 0.8, 1.2, 0.6, 2.0, 1.5, 0.9],
        'RS_Score': [95, 88, 85, 40, 90, 30, 20, 75]  # Điểm Sức mạnh giá (Relative Strength)
    }
    return pd.DataFrame(data)


def run_market_screener():
    """
    Thực thi Bước 2 & 3: Lọc Tự động và Chấm điểm Xếp hạng
    """
    df = fetch_mock_data()

    # BƯỚC 2: BỘ LỌC TỰ ĐỘNG (Stock Screener)
    # 1. Lọc FA (Loại bỏ rác tài chính)
    # Tiêu chí: ROE >= 15%, Tăng trưởng LN >= 15%, Nợ/Vốn chủ < 1
    cond_fa = (df['ROE'] >= 15) & (df['Profit_Growth'] >= 15) & (df['Debt_Equity'] < 1.0)

    # 2. Lọc TA (Thanh khoản & Xu hướng)
    # Tiêu chí: Volume trung bình > 500k, Giá đang nằm trên MA50 (Đang trong Uptrend)
    cond_ta = (df['Volume_Avg'] >= 500000) & (df['Price'] > df['MA50'])

    # Kết hợp 2 bộ lọc
    filtered_df = df[cond_fa & cond_ta].copy()

    # BƯỚC 3: CHẤM ĐIỂM & XẾP HẠNG (Scoring & Ranking)
    # Sắp xếp theo Sức mạnh giá (RS_Score) để tìm ra "Con đầu đàn"
    ranked_df = filtered_df.sort_values(by='RS_Score', ascending=False)

    # Lấy Top 5 mã mạnh nhất thị trường
    leaders = ranked_df.head(5)

    # Trình bày kết quả thành chuỗi văn bản để đưa cho AI đọc
    result_text = "Danh sách Top Cổ Phiếu Dẫn Dắt (Đã qua bộ lọc FA & TA khắt khe):\n"
    for index, row in leaders.iterrows():
        result_text += f"- Mã: {row['Ticker']} | Ngành: {row['Sector']} | Giá: {row['Price']} | RS Score: {row['RS_Score']}/100 | Tăng trưởng: {row['Profit_Growth']}%\n"

    return result_text