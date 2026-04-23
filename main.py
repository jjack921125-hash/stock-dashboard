import streamlit as st
import FinanceDataReader as fdr
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import json
import os
from datetime import datetime, timedelta

st.set_page_config(page_title="주식/코인 대시보드", page_icon="📈", layout="wide")
st.title("📈 주식/코인 대시보드")

# ───────────────────────────────────────────
# 영구 저장 함수
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
# 기본 종목
# ───────────────────────────────────────────
DEFAULT_TICKERS = {
    "S&P500": {
        "JPMorgan": "JPM", "Berkshire": "BRK-B", "Eli Lilly": "LLY", "Visa": "V",
        "ExxonMobil": "XOM", "UnitedHealth": "UNH", "Johnson&Johnson": "JNJ",
        "Mastercard": "MA", "Procter&Gamble": "PG", "Home Depot": "HD",
    },
    "나스닥": {
        "Apple": "AAPL", "Microsoft": "MSFT", "NVIDIA": "NVDA", "Amazon": "AMZN",
        "Alphabet": "GOOGL", "Meta": "META", "Broadcom": "AVGO", "Tesla": "TSLA",
        "Costco": "COST", "Netflix": "NFLX",
    },
    "코스피": {
        "삼성전자": "005930", "SK하이닉스": "000660", "삼성바이오로직스": "207940",
        "LG에너지솔루션": "373220", "현대차": "005380", "셀트리온": "068270",
        "기아": "000270", "KB금융": "105560", "신한지주": "055550", "삼성물산": "028260",
    },
    "코스닥": {
        "에코프로비엠": "247540", "HLB": "028300", "에코프로": "086520",
        "알테오젠": "196170", "셀트리온제약": "068760", "리가켐바이오": "141080",
        "클래시스": "214150", "휴젤": "145020", "HPSP": "403870", "삼천당제약": "000250",
    },
    "코인": {
        "Bitcoin": "BTC", "Ethereum": "ETH", "BNB": "BNB", "Solana": "SOL",
        "XRP": "XRP", "Dogecoin": "DOGE", "Cardano": "ADA", "Avalanche": "AVAX",
        "Chainlink": "LINK", "Dot": "DOT",
    },
}

MARKET_CONFIG = {
    "S&P500": {"currency": "USD", "data_type": "US"},
    "나스닥":  {"currency": "USD", "data_type": "US"},
    "코스피":  {"currency": "KRW", "data_type": "KR"},
    "코스닥":  {"currency": "KRW", "data_type": "KR"},
    "코인":    {"currency": "KRW", "data_type": "COIN"},
}

CANDLE_OPTIONS = {"1일": "D", "1주": "W", "1달": "ME", "1년": "YE"}

if "tickers" not in st.session_state:
    st.session_state.tickers = load_data()

def fmt(price, currency):
    if currency == "KRW":
        return f"₩{price:,.0f}"
    return f"${price:,.2f}"

# ───────────────────────────────────────────
# 데이터 수집 핵심 함수 (수정됨)
# ───────────────────────────────────────────
@st.cache_data(ttl=300)
def get_stable_coin_data(coin_ticker):
    """안정적인 USD 티커로 가져온 뒤 환율을 적용하여 KRW 데이터 생성"""
    try:
        # 1. 코인 달러 가격 가져오기
        coin_df = yf.download(f"{coin_ticker}-USD", start="2018-01-01", progress=False)
        # 2. 환율 데이터 가져오기
        fx_df = yf.download("USDKRW=X", start="2018-01-01", progress=False)
        
        if isinstance(coin_df.columns, pd.MultiIndex): coin_df.columns = coin_df.columns.get_level_values(0)
        if isinstance(fx_df.columns, pd.MultiIndex): fx_df.columns = fx_df.columns.get_level_values(0)

        if coin_df.empty or fx_df.empty: return pd.DataFrame()

        # 데이터 결합 및 원화 환산
        df = coin_df.copy()
        df['ExchangeRate'] = fx_df['Close'].reindex(df.index).ffill()
        
        # 모든 OHLC 가격에 환율 적용
        for col in ['Open', 'High', 'Low', 'Close']:
            df[col] = df[col] * df['ExchangeRate']
            
        return df
    except:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_kimchi_premium_stable(coin_ticker):
    """국내(Upbit 예상치) vs 해외 프리미엄 계산"""
    try:
        # 업비트 등의 API를 직접 쓰지 않는 이상, fdr의 KRW 티커가 작동해야 함
        # 만약 fdr이 계속 안되면 이 부분은 '해외 가격' 추이 위주로 보게 됨
        df_krw = fdr.DataReader(f"{coin_ticker}/KRW", datetime(2023, 1, 1))
        df_usd_stable = get_stable_coin_data(coin_ticker) # 이게 위에서 만든 원화환산가

        if df_krw.empty or df_usd_stable.empty: return pd.DataFrame(), None

        common_index = df_krw.index.intersection(df_usd_stable.index)
        df = pd.DataFrame(index=common_index)
        df['KRW가격'] = df_krw['Close']
        df['해외환산가'] = df_usd_stable['Close']
        df['김치프리미엄(%)'] = (df['KRW가격'] / df['해외환산가'] - 1) * 100
        
        return df, df['김치프리미엄(%)'].iloc[-1]
    except:
        return pd.DataFrame(), None

# ───────────────────────────────────────────
# 메인 로직
# ───────────────────────────────────────────
st.sidebar.title("⚙️ 설정")
market = st.sidebar.selectbox("시장 선택", list(MARKET_CONFIG.keys()))
config = MARKET_CONFIG[market]
ticker_dict = st.session_state.tickers[market]
selected = st.sidebar.selectbox("종목 선택", list(ticker_dict.keys()))
ticker = ticker_dict[selected]
candle_label = st.sidebar.selectbox("캔들 단위", list(CANDLE_OPTIONS.keys()))

with st.spinner("데이터 로딩 중..."):
    if config["data_type"] == "COIN":
        df = get_stable_coin_data(ticker)
    else:
        df = fdr.DataReader(ticker, "2020-01-01")

if df.empty:
    st.error("⚠️ 데이터를 가져오지 못했습니다. 잠시 후 다시 시도하거나 티커를 확인하세요.")
else:
    # 차트 및 지표 표시
    c1, c2, c3 = st.columns(3)
    curr_p = df['Close'].iloc[-1]
    diff = ((curr_p - df['Close'].iloc[-2]) / df['Close'].iloc[-2] * 100) if len(df) > 1 else 0
    c1.metric("현재가 (원화 환산)", fmt(curr_p, "KRW"), f"{diff:.2f}%")
    c2.metric("기간 최고가", fmt(df['High'].max(), "KRW"))
    c3.metric("기간 최저가", fmt(df['Low'].min(), "KRW"))

    fig = go.Figure(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']))
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, title=f"{selected} 차트")
    st.plotly_chart(fig, use_container_width=True)

# 하락률 테이블 (생략 없이 유지)
st.markdown("---")
st.subheader(f"📉 {market} 하락률 현황")
# (하락률 계산 로직...)
