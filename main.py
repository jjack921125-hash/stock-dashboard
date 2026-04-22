import streamlit as st
import FinanceDataReader as fdr
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import json
import os
import ccxt
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(page_title="통합 금융 대시보드", page_icon="📈", layout="wide")

# ───────────────────────────────────────────
# 1. 초기 설정 및 데이터 로드
# ───────────────────────────────────────────
SAVE_FILE = "data.json"
binance = ccxt.binance()

DEFAULT_TICKERS = {
    "S&P500": {"JPMorgan": "JPM", "Visa": "V", "ExxonMobil": "XOM"},
    "나스닥": {"Apple": "AAPL", "Microsoft": "MSFT", "NVIDIA": "NVDA", "Tesla": "TSLA"},
    "코스피": {"삼성전자": "005930", "SK하이닉스": "000660", "현대차": "005380"},
    "코스닥": {"에코프로비엠": "247540", "알테오젠": "196170", "HLB": "028300"},
    "코인(Binance)": {"Bitcoin": "BTC/USDT", "Ethereum": "ETH/USDT", "Solana": "SOL/USDT", "XRP": "XRP/USDT"},
}

def load_data():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return DEFAULT_TICKERS.copy()
    return DEFAULT_TICKERS.copy()

def save_data(data):
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if "tickers" not in st.session_state:
    st.session_state.tickers = load_data()

# ───────────────────────────────────────────
# 2. 데이터 수집 함수 (Caching 적용)
# ───────────────────────────────────────────

@st.cache_data(ttl=60) # 코인 실시간성을 위해 1분 캐시
def get_crypto_data(symbol, interval='1d'):
    """바이낸스 API를 통한 코인 데이터 수집"""
    # Streamlit 단위와 바이낸스 단위 매칭
    tf_map = {"1분":"1m","5분":"5m","15분":"15m","1시간":"1h","4시간":"4h","1일":"1d","1주":"1w"}
    tf = tf_map.get(interval, "1d")
    try:
        ohlcv = binance.fetch_ohlcv(symbol, timeframe=tf, limit=200)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms') + timedelta(hours=9) # KST 보정
        df.set_index('timestamp', inplace=True)
        return df
    except Exception as e:
        st.error(f"Binance API 오류: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_stock_data(ticker, interval_label, market_type):
    """주식 데이터 수집 (FDR & yfinance)"""
    try:
        if "분" in interval_label or "시간" in interval_label:
            # 분봉/시간봉은 yfinance
            yf_ticker = f"{ticker}.KS" if market_type == "코스피" else f"{ticker}.KQ" if market_type == "코스닥" else ticker
            period_map = {"1분":"1d", "5분":"5d", "15분":"5d", "1시간":"1mo"}
            int_map = {"1분":"1m", "5분":"5m", "15분":"15m", "1시간":"1h"}
            df = yf.download(yf_ticker, period=period_map.get(interval_label, "5d"), 
                             interval=int_map.get(interval_label, "5m"), progress=False)
            df.index = df.index + timedelta(hours=9) # KST 보정
        else:
            # 일봉 이상은 FinanceDataReader
            df = fdr.DataReader(ticker, '2023-01-01')
        return df
    except Exception as e:
        st.error(f"주식 데이터 오류: {e}")
        return pd.DataFrame()

# ───────────────────────────────────────────
# 3. 사이드바 UI
# ───────────────────────────────────────────
st.sidebar.title("⚙️ DashBoard Setting")
market = st.sidebar.selectbox("시장 선택", list(st.session_state.tickers.keys()))
ticker_dict = st.session_state.tickers[market]

selected_name = st.sidebar.selectbox("종목 선택", list(ticker_dict.keys()))
selected_ticker = ticker_dict[selected_name]

candle_op = ["1분", "5분", "15분", "1시간", "1일", "1주"]
interval = st.sidebar.selectbox("캔들 단위", candle_op, index=4)

# 종목 추가/삭제 로직 (기존 코드 유지)
st.sidebar.markdown("---")
with st.sidebar.expander("➕ 종목 관리"):
    new_n = st.text_input("이름")
    new_t = st.text_input("티커/ID")
    if st.button("추가"):
        st.session_state.tickers[market][new_n] = new_t
        save_data(st.session_state.tickers)
        st.rerun()
    
    del_target = st.selectbox("삭제", list(ticker_dict.keys()))
    if st.button("삭제"):
        del st.session_state.tickers[market][del_target]
        save_data(st.session_state.tickers)
        st.rerun()

# ───────────────────────────────────────────
# 4. 메인 화면 출력
# ───────────────────────────────────────────
st.title(f"📈 {selected_name} ({selected_ticker})")

if "코인" in market:
    df = get_crypto_data(selected_ticker, interval)
    currency = "USDT"
else:
    df = get_stock_data(selected_ticker, interval, market)
    currency = "KRW" if "코" in market else "USD"

if not df.empty:
    # 상단 지표
    c1, c2, c3, c4 = st.columns(4)
    curr_price = df['Close'].iloc[-1]
    prev_price = df['Close'].iloc[-2]
    change = curr_price - prev_price
    change_pct = (change / prev_price) * 100
    
    price_fmt = f"₩{curr_price:,.0f}" if currency == "KRW" else f"${curr_price:,.2f}"
    
    c1.metric("현재가", price_fmt, f"{change_pct:+.2f}%")
    c2.metric("고가(Period)", f"{df['High'].max():,.2f}")
    c3.metric("저가(Period)", f"{df['Low'].min():,.2f}")
    c4.metric("거래량", f"{df['Volume'].iloc[-1]:,.0f}")

    # 차트 그리기
    fig = go.Figure(data=[go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        increasing_line_color='#FF4B4B', decreasing_line_color='#007BFF', # 한국형 색상
        increasing_fillcolor='#FF4B4B', decreasing_fillcolor='#007BFF'
    )])
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=600)
    st.plotly_chart(fig, use_container_width=True)
    
    # 거래량 바 차트
    v_colors = ['#FF4B4B' if c >= o else '#007BFF' for c, o in zip(df['Close'], df['Open'])]
    fig_v = go.Figure(data=[go.Bar(x=df.index, y=df['Volume'], marker_color=v_colors)])
    fig_v.update_layout(template="plotly_dark", height=200, title="거래량")
    st.plotly_chart(fig_v, use_container_width=True)
else:
    st.warning("데이터를 불러올 수 없습니다. 티커를 확인해주세요.")

# 하락률 테이블 (MDD 체크용)
st.markdown("---")
st.subheader("📉 전고점 대비 하락률 (Drawdown)")
all_high = df['High'].max()
drawdown = (curr_price - all_high) / all_high * 100
st.write(f"현재 선택 기간 최고가({all_high:,.2f}) 대비 **{drawdown:.2f}%** 하락 중입니다.")
