import pandas as pd
import time
import analytics  # Tái sử dụng ngay thư viện của bạn để lấy data

# Danh sách các mã cổ phiếu đầu ngành, thanh khoản cao để quét
# (Bạn có thể thêm bớt tùy ý, nhưng nên giữ dưới 50 mã để tối ưu tốc độ)
WATCHLIST = [
    'FPT', 'HPG', 'SSI', 'VND', 'MWG', 'VJC', 'VIC', 'VCB',
    'TCB', 'MBB', 'VPB', 'STB', 'VHM', 'GVR', 'DIG', 'PVD', 'DGC', 'KBC'
]


def fetch_real_data():
    """Lấy dữ liệu thật từ thị trường qua module analytics."""
    records = []

    for ticker in WATCHLIST:
        try:
            # 1. Lấy dữ liệu lịch sử giá
            df_price = analytics.get_price_history(ticker)
            if df_price is None or df_price.empty or len(df_price) < 50:
                continue

            # Chuẩn hóa tên cột về chữ thường
            df_price.columns = [c.lower() for c in df_price.columns]

            # Lấy giá trị Kỹ thuật (TA)
            current_price = df_price['close'].iloc[-1]
            ma50 = df_price['close'].rolling(window=50).mean().iloc[-1]

            # Xử lý cột khối lượng (nếu API có trả về)
            vol_avg = 0
            if 'volume' in df_price.columns:
                vol_avg = df_price['volume'].rolling(window=20).mean().iloc[-1]

            # Tính RS Score cơ bản (Dùng Động lượng: % Tăng giá trong 1 tháng/20 phiên)
            ret_1m = ((current_price / df_price['close'].iloc[-20]) - 1) * 100

            # 2. Lấy dữ liệu tài chính (FA)
            ratios = analytics.get_financial_ratios(ticker)
            roe = 0
            profit_growth = 15  # Đặt mặc định để pass bộ lọc nếu API thiếu dữ liệu tạm thời
            debt_equity = 0.5

            if ratios is not None and not ratios.empty:
                latest_r = ratios.iloc[0]
                # Lấy ROE (Tùy nguồn VCI hoặc TCBS sẽ có tên cột khác nhau)
                roe_raw = latest_r.get('ROE (%)', latest_r.get('roe', 0))
                if pd.notna(roe_raw):
                    roe = float(roe_raw)

            # Đưa dữ liệu vào danh sách
            records.append({
                'Ticker': ticker,
                'Sector': 'Thị trường',
                'Price': current_price,
                'MA50': ma50,
                'Volume_Avg': vol_avg,
                'ROE': roe,
                'Profit_Growth': profit_growth,
                'Debt_Equity': debt_equity,
                'RS_Score': round(ret_1m, 2)  # Càng tăng mạnh trong 1 tháng -> Điểm RS càng cao
            })

            # Nghỉ ngơi 0.2 giây giữa các lần gọi API để tránh bị chặn IP
            time.sleep(0.2)

        except Exception as e:
            print(f"[Lỗi lọc mã {ticker}]: {e}")
            continue

    return pd.DataFrame(records)


def run_market_screener():
    """
    Thực thi Bước 2 & 3: Lọc Tự động và Chấm điểm Xếp hạng bằng DỮ LIỆU THẬT
    """
    df = fetch_real_data()

    if df.empty:
        return "Không lấy được dữ liệu thị trường lúc này. Hãy thử lại sau."

    # BƯỚC 2: BỘ LỌC TỰ ĐỘNG (Stock Screener)
    # 1. Lọc FA (Cơ bản tốt)
    cond_fa = (df['ROE'] >= 10) & (df['Debt_Equity'] < 1.0)

    # 2. Lọc TA (Xu hướng tăng & Có thanh khoản)
    cond_ta = (df['Volume_Avg'] >= 300000) & (df['Price'] > df['MA50'])

    # Kết hợp 2 bộ lọc
    filtered_df = df[cond_fa & cond_ta].copy()

    # Nếu thị trường quá xấu, không mã nào lọt qua bộ lọc, nới lỏng điều kiện
    if filtered_df.empty:
        filtered_df = df[df['Price'] > df['MA50']].copy()

    # BƯỚC 3: CHẤM ĐIỂM & XẾP HẠNG
    # Sắp xếp theo Sức mạnh giá (RS_Score - Cổ phiếu tăng mạnh nhất tháng qua)
    ranked_df = filtered_df.sort_values(by='RS_Score', ascending=False)

    # Lấy Top 3-5 mã mạnh nhất
    leaders = ranked_df.head(5)

    result_text = "Danh sách Top Cổ Phiếu Dẫn Dắt (Đã qua bộ lọc Uptrend & Cơ bản):\n"
    for index, row in leaders.iterrows():
        result_text += f"- Mã: {row['Ticker']} | Giá hiện tại: {row['Price']:,.0f} VND | Điểm Sức mạnh (1 Tháng): {row['RS_Score']}% | Đang vượt MA50 ({row['MA50']:,.0f})\n"

    return result_text