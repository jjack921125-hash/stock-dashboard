import streamlit as st
import FinanceDataReader as fdr
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import json
import os
from datetime import datetime

st.set_page_config(page_title="주식/코인 대시보드", page_icon="📈", layout="wide")
st.title("📈 주식/코인 대시보드")

# ───────────────────────────────────────────
# 데이터 저장 및 로드 함수
# ───────────────────────────────────────────
SAVE_FILE = "data.json"

def load_data():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_TICKERS.copy()

def save_data(data):
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ───────────────────────────────────────────
# 기본 종목 설정
# ───────────────────────────────────────────
DEFAULT_TICKERS = {
    "S&P500": {
        "JPMorgan": "JPM", "Berkshire": "BRK-B", "Eli Lilly": "LLY", "Visa": "V",
        "ExxonMobil": "XOM", "UnitedHealth": "UNH", "Johnson&Johnson": "JNJ",
        "Mastercard": "MA", "Procter&Gamble": "PG", "Home Depot": "HD"
    },
    "나스닥": {
        "Apple": "AAPL", "Microsoft": "MSFT", "NVIDIA": "NVDA", "Amazon": "AMZN",
        "Alphabet": "GOOGL", "Meta": "META", "Broadcom": "AVGO", "Tesla": "TSLA",
        "Costco": "COST", "Netflix": "NFLX"
    },
    "코스피": {
        "삼성전자": "005930", "SK하이닉스": "000660", "삼성바이오로직스": "207940",
        "LG에너지솔루션": "373220", "현대차": "005380", "셀트리온": "068270",
        "기아": "000270", "KB금융": "105560", "신한지주": "055550", "삼성물산": "028260"
    },
    "코스닥": {
        "에코프로비엠": "247540", "HLB": "028300", "에코프로": "086520",
        "알테오젠": "196170", "셀트리온제약": "068760", "리가켐바이오": "141080",
        "클래시스": "214150", "휴젤": "145020", "HPSP": "403870", "삼천당제약": "000250"
    },
    "코인": {
        "Bitcoin": "BTC", "Ethereum": "ETH", "BNB": "BNB", "Solana": "SOL",
        "XRP": "XRP", "Dogecoin": "DOGE", "Cardano": "ADA", "Avalanche": "AVAX"
    },
}

MARKET_CONFIG = {
    "S&P500": {"currency": "USD", "data_type": "US"},
    "나스닥":  {"currency": "USD", "data_type": "US"},
    "코스피":  {"currency": "KRW", "data_type": "KR"},
    "코스닥":  {"currency": "KRW", "data_type": "KR"},
    "코인":    {"currency": "KRW", "data_type": "COIN"},
}

if "tickers" not in st.session_state:
    st.session_state.tickers = load_data()

# ───────────────────────────────────────────
# [핵심] 안정적인 데이터 수집 로직 (결합 버전)
# ───────────────────────────────────────────
@st.cache_data(ttl=300)
def get_safe_data(symbol, market_type):
    try:
        if market_type == "COIN":
            # 코인은 USD 티커로 가져오기
            target = f"{symbol}-USD"
            df = yf.download(target, period="1y", progress=False)
            if df.empty: return pd.DataFrame()
            
            # Multi-index 평탄화
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # 환율 적용 (야후 파이낸스 환율 데이터 사용)
            fx = yf.download("USDKRW=X", period="1d", progress=False)
            if isinstance(fx.columns, pd.MultiIndex):
                fx.columns = fx.columns.get_level_values(0)
            rate = float(fx['Close'].iloc[-1]) if not fx.empty else 1380.0
            
            res = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
            for col in ['Open', 'High', 'Low', 'Close']:
                res[col] = res[col] * rate
            return res
        else:
            # 주식은 fdr 사용
            df = fdr.DataReader(symbol, "2023-01-01")
            return df
    except:
        return pd.DataFrame()

def fmt(price, currency):
    if currency == "KRW":
        return f"₩{price:,.0f}"
    return f"${price:,.2f}"

# ───────────────────────────────────────────
# 사이드바
# ───────────────────────────────────────────
st.sidebar.title("⚙️ 설정")
market = st.sidebar.selectbox("시장 선택", list(MARKET_CONFIG.keys()))
config = MARKET_CONFIG[market]
ticker_dict = st.session_state.tickers[market]

selected_name = st.sidebar.selectbox("종목 선택", list(ticker_dict.keys()))
ticker = ticker_dict[selected_name]

# 종목 추가/삭제 (기능 유지)
st.sidebar.markdown("---")
st.sidebar.markdown("### ➕ 종목 추가")
new_n = st.sidebar.text_input("종목/코인명")
new_t = st.sidebar.text_input("티커/코드")
if st.sidebar.button("추가"):
    if new_n and new_t:
        st.session_state.tickers[market][new_n] = new_t.strip().upper()
        save_data(st.session_state.tickers)
        st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("🗑️ 현재 종목 삭제"):
    del st.session_state.tickers[market][selected_name]
    save_data(st.session_state.tickers)
    st.rerun()

# ───────────────────────────────────────────
# 메인 차트 및 지표
# ───────────────────────────────────────────
with st.spinner("데이터 로딩 중..."):
    df = get_safe_data(ticker, config["data_type"])

if df.empty:
    st.error(f"❌ '{selected_name}' 데이터를 불러오지 못했습니다.")
else:
    # 1. 지표
    c1, c2, c3 = st.columns(3)
    curr = float(df['Close'].iloc[-1])
    prev = float(df['Close'].iloc[-2])
    high = float(df['High'].max())
    change = ((curr - prev) / prev) * 100
    
    c1.metric("현재가", fmt(curr, config["currency"]), f"{change:+.2f}%")
    c2.metric("기간 최고가", fmt(high, config["currency"]))
    c3.metric("최고점 대비", f"{((curr/high)-1)*100:.2f}%")

    # 2. 캔들 차트
    fig = go.Figure(data=[go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        increasing_line_color='red', decreasing_line_color='blue'
    )])
    fig.
