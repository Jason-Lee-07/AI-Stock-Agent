import pandas as pd
import pandas_ta as ta
import requests
from datetime import datetime, timedelta

# ==========================================
# BƯỚC D: HỆ QUY CHIẾU NGÀNH (Dữ liệu tham khảo)
# ==========================================
INDUSTRY_PE = {
    "Ngân hàng": 10.5,
    "Chứng khoán": 18.0,
    "Thép": 15.0,
    "Công nghệ": 22.5,
    "Bất động sản": 20.0,
    "Bán lẻ": 25.0,
    "Khác": 15.0  # Mức trung bình của VN-Index
}

TICKER_SECTOR = {
    'VCB': 'Ngân hàng', 'TCB': 'Ngân hàng', 'MBB': 'Ngân hàng', 'VPB': 'Ngân hàng', 'STB': 'Ngân hàng',
    'SSI': 'Chứng khoán', 'VND': 'Chứng khoán', 'VCI': 'Chứng khoán',
    'HPG': 'Thép', 'HSG': 'Thép', 'NKG': 'Thép',
    'FPT': 'Công nghệ', 'CMG': 'Công nghệ',
    'VHM': 'Bất động sản', 'DIG': 'Bất động sản', 'KBC': 'Bất động sản', 'NVL': 'Bất động sản',
    'MWG': 'Bán lẻ', 'FRT': 'Bán lẻ', 'PNJ': 'Bán lẻ'
}


# ==========================================
# CÁC HÀM LẤY DỮ LIỆU
# ==========================================
def get_price_history(ticker: str):
    """Lấy lịch sử giá đa nguồn (VCI -> TCBS -> REST API)."""
    start_str = (datetime.now() - timedelta(days=200)).strftime('%Y-%m-%d')
    today_str = datetime.now().strftime('%Y-%m-%d')

    # Cách 1: Thử qua thư viện vnstock
    try:
        import vnstock
        # Dành cho vnstock3 / phiên bản mới
        if hasattr(vnstock, 'Vnstock'):
            for src in ['VCI', 'TCBS', 'MSN']:
                try:
                    df = vnstock.Vnstock().stock(symbol=ticker, source=src).quote.history(start=start_str,
                                                                                          end=today_str)
                    if isinstance(df, pd.DataFrame) and not df.empty and len(df) > 10:
                        return df
                except:
                    continue
        # Dành cho vnstock phiên bản cũ
        elif hasattr(vnstock, 'stock_historical_data'):
            df = vnstock.stock_historical_data(symbol=ticker, start_date=start_str, end_date=today_str, source='TCBS')
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
    except Exception as e:
        print(f"[Lỗi vnstock]: {e}")

    # Cách 2: Dự phòng gọi API trực tiếp TCBS
    try:
        end_ts = int(datetime.now().timestamp())
        start_ts = int((datetime.now() - timedelta(days=200)).timestamp())
        url = f"https://apipubks.tcbs.com.vn/stock-insight/v1/stock/bars-long-term?ticker={ticker}&type=stock&resolution=D&from={start_ts}&to={end_ts}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json().get('data', [])
            if data:
                df = pd.DataFrame(data)
                return df
    except Exception as e:
        print(f"[Lỗi API Trực tiếp]: {e}")

    return None


def get_financial_ratios(ticker: str):
    """Lấy chỉ số tài chính đa nguồn."""
    try:
        import vnstock
        if hasattr(vnstock, 'Vnstock'):
            for src in ['VCI', 'TCBS']:
                try:
                    ratios = vnstock.Vnstock().stock(symbol=ticker, source=src).finance.ratio(period='quarter',
                                                                                              lang='vi')
                    if isinstance(ratios, pd.DataFrame) and not ratios.empty:
                        return ratios
                except:
                    continue
        elif hasattr(vnstock, 'financial_ratio'):
            ratios = vnstock.financial_ratio(symbol=ticker, report_range='quarterly')
            if isinstance(ratios, pd.DataFrame) and not ratios.empty:
                return ratios
    except:
        pass

    # Dự phòng gọi API rating/financials từ TCBS
    try:
        url = f"https://apipubks.tcbs.com.vn/stock-insight/v1/financial/rating?ticker={ticker}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data:
                return pd.DataFrame([data])
    except:
        pass

    return None


# ==========================================
# HÀM PHÂN TÍCH CHÍNH (Đã gộp Bước B và Bước D)
# ==========================================
def analyze_stock(ticker: str):
    """Phân tích tổng hợp FA, TA, Quant (Đã có Dòng tiền và Định giá tương đối)."""
    ticker = ticker.upper().strip()
    fa_data, ta_data, quant_data = {}, {}, {}

    # 1. PHÂN TÍCH KỸ THUẬT & DÒNG TIỀN (BƯỚC B)
    df = get_price_history(ticker)
    if isinstance(df, pd.DataFrame) and not df.empty and len(df) > 20:
        df.columns = [c.lower() for c in df.columns]

        if 'close' in df.columns:
            df['rsi'] = ta.rsi(df['close'], length=14)
            df['sma_50'] = ta.sma(df['close'], length=50) if len(df) >= 50 else df['close']

            # Xử lý Volume
            vol_spike_status = "Không có dữ liệu Volume"
            if 'volume' in df.columns:
                df['vol_sma_20'] = ta.sma(df['volume'], length=20)

            latest = df.iloc[-1]

            if 'volume' in df.columns and pd.notnull(latest.get('vol_sma_20')) and latest['vol_sma_20'] > 0:
                vol_ratio = latest['volume'] / latest['vol_sma_20']
                if vol_ratio >= 2.0:
                    vol_spike_status = f"🔥 BÙNG NỔ (Gấp {round(vol_ratio, 1)} lần TB 20 phiên) - Dấu hiệu Dòng tiền lớn/Cá mập tham gia"
                elif vol_ratio >= 1.3:
                    vol_spike_status = f"Tích cực (Gấp {round(vol_ratio, 1)} lần TB 20 phiên) - Cầu đang vào"
                elif vol_ratio <= 0.5:
                    vol_spike_status = "Cạn cung / Thanh khoản thấp (Chỉ bằng 1/2 mức trung bình)"
                else:
                    vol_spike_status = "Bình thường (Biến động trung bình)"

            ta_data = {
                "Giá đóng cửa (VND)": latest['close'],
                "RSI (14)": round(latest['rsi'], 2) if pd.notnull(latest['rsi']) else "N/A",
                "Kháng cự (30 phiên)": df['high'].tail(30).max() if 'high' in df.columns else "N/A",
                "Hỗ trợ (30 phiên)": df['low'].tail(30).min() if 'low' in df.columns else "N/A",
                "Xu hướng (SMA50)": "Tăng" if latest['close'] >= latest['sma_50'] else "Giảm",
                "Dấu chân Dòng tiền (Volume)": vol_spike_status
            }

            if len(df) >= 20:
                ret_1m = (df['close'].iloc[-1] / df['close'].iloc[-20] - 1) * 100
                volatility = df['close'].pct_change().tail(20).std() * (252 ** 0.5) * 100
                quant_data = {
                    "Momentum (1 Tháng)": f"{round(ret_1m, 2)}%",
                    "Biến động năm": f"{round(volatility, 2)}%"
                }
    else:
        ta_data = {"Thông báo": "Chưa lấy được lịch sử giá"}
        quant_data = {"Thông báo": "Thiếu dữ liệu Quant"}

    # 2. PHÂN TÍCH CƠ BẢN & ĐỊNH GIÁ TƯƠNG ĐỐI (BƯỚC D)
    ratios = get_financial_ratios(ticker)
    if isinstance(ratios, pd.DataFrame) and not ratios.empty:
        latest_r = ratios.iloc[0]

        pe_raw = latest_r.get('P/E', latest_r.get('priceToEarning', latest_r.get('pe', 'N/A')))
        pb = latest_r.get('P/B', latest_r.get('priceToBook', latest_r.get('pb', 'N/A')))
        roe = latest_r.get('ROE (%)', latest_r.get('roe', 'N/A'))
        eps = latest_r.get('EPS (VND)', latest_r.get('eps', 'N/A'))

        # Xử lý Định giá tương đối
        sector = TICKER_SECTOR.get(ticker, "Khác")
        ind_pe = INDUSTRY_PE.get(sector, 15.0)

        valuation_status = "Chưa thể đánh giá"
        pe_val = "N/A"

        try:
            pe_val = float(pe_raw)
            if pe_val < ind_pe:
                valuation_status = f"✅ Rẻ hơn ngành (P/E mã: {round(pe_val, 1)} < P/E {sector}: {ind_pe})"
            else:
                valuation_status = f"⚠️ Đắt hơn ngành (P/E mã: {round(pe_val, 1)} > P/E {sector}: {ind_pe})"
        except (ValueError, TypeError):
            pass

        fa_data = {
            "Nhóm ngành": sector,
            "P/E": pe_val,
            "Định giá tương đối": valuation_status,
            "P/B": pb,
            "ROE (%)": roe,
            "EPS": eps
        }
    else:
        fa_data = {"Thông báo": "Chưa lấy được chỉ số tài chính"}

    return {"FA": fa_data, "TA": ta_data, "Quant": quant_data}