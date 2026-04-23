pip install -U yfinance finance-datareader pandas

import streamlit as st
import FinanceDataReader as fdr
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import json
import os
from datetime import datetime, timedelta

st.set_page_config(page_title="주식/코인 대시보드", page_icon="📈", layout="wide")
st.title("📈 돈 버는 정보")

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
        "JPMorgan":        "JPM",
        "Berkshire":       "BRK-B",
        "Eli Lilly":       "LLY",
        "Visa":            "V",
        "ExxonMobil":      "XOM",
        "UnitedHealth":    "UNH",
        "Johnson&Johnson": "JNJ",
        "Mastercard":      "MA",
        "Procter&Gamble":  "PG",
        "Home Depot":      "HD",
    },
    "나스닥": {
        "Apple":           "AAPL",
        "Microsoft":       "MSFT",
        "NVIDIA":          "NVDA",
        "Amazon":          "AMZN",
        "Alphabet":        "GOOGL",
        "Meta":            "META",
        "Broadcom":        "AVGO",
        "Tesla":           "TSLA",
        "Costco":          "COST",
        "Netflix":         "NFLX",
    },
    "코스피": {
        "삼성전자":         "005930",
        "SK하이닉스":       "000660",
        "삼성바이오로직스": "207940",
        "LG에너지솔루션":   "373220",
        "현대차":           "005380",
        "셀트리온":         "068270",
        "기아":             "000270",
        "KB금융":           "105560",
        "신한지주":         "055550",
        "삼성물산":         "028260",
    },
    "코스닥": {
        "에코프로비엠":     "247540",
        "HLB":             "028300",
        "에코프로":         "086520",
        "알테오젠":         "196170",
        "셀트리온제약":     "068760",
        "리가켐바이오":     "141080",
        "클래시스":         "214150",
        "휴젤":             "145020",
        "HPSP":            "403870",
        "삼천당제약":       "000250",
    },
    "코인": {
        "Bitcoin":   "BTC",
        "Ethereum":  "ETH",
        "BNB":       "BNB",
        "Solana":    "SOL",
        "XRP":       "XRP",
        "Dogecoin":  "DOGE",
        "Cardano":   "ADA",
        "Avalanche": "AVAX",
        "Chainlink": "LINK",
        "Polkadot":  "DOT",
    },
}

MARKET_CONFIG = {
    "S&P500": {"currency": "USD", "data_type": "US"},
    "나스닥":  {"currency": "USD", "data_type": "US"},
    "코스피":  {"currency": "KRW", "data_type": "KR"},
    "코스닥":  {"currency": "KRW", "data_type": "KR"},
    "코인":    {"currency": "KRW", "data_type": "COIN"},
}

CANDLE_OPTIONS = {
    "1일":  {"type": "daily"},
    "1주":  {"type": "weekly"},
    "1달":  {"type": "monthly"},
    "1년":  {"type": "yearly"},
}

RESAMPLE_MAP = {
    "1주": "W",
    "1달": "ME",
    "1년": "YE",
}

if "tickers" not in st.session_state:
    st.session_state.tickers = load_data()

for k in DEFAULT_TICKERS:
    if k not in st.session_state.tickers:
        st.session_state.tickers[k] = DEFAULT_TICKERS[k].copy()

def fmt(price, currency):
    if currency == "KRW":
        return f"₩{price:,.0f}"
    return f"${price:,.4f}" if price < 1 else f"${price:,.2f}"

# ───────────────────────────────────────────
# 코인 데이터 가져오기 (안정성 강화 버전)
# ───────────────────────────────────────────
@st.cache_data(ttl=300)
def get_coin_data(coin: str, currency: str = "KRW"):
    try:
        # 1. 티커 변환 (yf는 BTC-USD, BTC-KRW 형태를 선호)
        symbol = f"{coin}-{currency}"
        
        # 2. 데이터 다운로드 (최근 데이터가 안 나올 경우 대비하여 기간 설정)
        ticker_obj = yf.Ticker(symbol)
        df = ticker_obj.history(start="2018-01-01")
        
        if df.empty:
            # 보조 수단: download 함수 사용
            df = yf.download(symbol, start="2018-01-01", progress=False)
            
        if df.empty:
            return pd.DataFrame()
            
        # yfinance MultiIndex 컬럼 평탄화
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_usd_krw():
    try:
        df = fdr.DataReader('USD/KRW', datetime(2024, 1, 1), datetime.today())
        if df.empty:
            return None
        return df['Close'].iloc[-1]
    except:
        return None

@st.cache_data(ttl=300)
def get_kimchi_premium(coin: str):
    try:
        df_krw = get_coin_data(coin, "KRW")
        df_usd = get_coin_data(coin, "USD")
        # 환율은 yfinance에서 직접 가져오는게 더 빠를 수 있음
        df_fx = yf.download("USDKRW=X", start="2018-01-01", progress=False)
        
        if isinstance(df_fx.columns, pd.MultiIndex):
            df_fx.columns = df_fx.columns.get_level_values(0)

        if df_krw.empty or df_usd.empty or df_fx.empty:
            return pd.DataFrame(), None

        df = pd.DataFrame({
            'KRW가격':  df_krw['Close'],
            'USD가격':  df_usd['Close'],
        }).dropna()
        
        df['환율'] = df_fx['Close'].reindex(df.index).ffill()
        df['달러환산원화'] = df['USD가격'] * df['환율']
        df['김치프리미엄(%)'] = (df['KRW가격'] / df['달러환산원화'] - 1) * 100

        current_premium = df['김치프리미엄(%)'].iloc[-1]
        return df, current_premium
    except:
        return pd.DataFrame(), None

@st.cache_data(ttl=3600)
def get_drawdown_table(ticker_dict: dict, data_type: str, currency: str):
    rows = []
    for name, ticker in ticker_dict.items():
        try:
            if data_type == "COIN":
                df = get_coin_data(ticker, "KRW")
            else:
                start = datetime(2000, 1, 1)
                df = fdr.DataReader(ticker, start, datetime.today())

            if df.empty:
                continue

            current       = df['Close'].iloc[-1]
            all_time_high = df['High'].max()
            drawdown      = (current - all_time_high) / all_time_high * 100

            rows.append({
                "종목":               name,
                "현재가":             fmt(current, currency),
                "역대 최고가":        fmt(all_time_high, currency),
                "최고점 대비 하락률": f"{drawdown:.2f}%",
                "_drawdown":          drawdown,
            })
        except:
            continue

    if not rows:
        return pd.DataFrame()

    df_result = pd.DataFrame(rows)
    df_result = df_result.sort_values("_drawdown").drop(columns=["_drawdown"])
    df_result.reset_index(drop=True, inplace=True)
    return df_result

# ───────────────────────────────────────────
# UI 및 출력 부분 (이전과 동일)
# ───────────────────────────────────────────
st.sidebar.title("⚙️ 설정")
market    = st.sidebar.selectbox("시장 선택", list(MARKET_CONFIG.keys()))
config    = MARKET_CONFIG[market]
currency  = config["currency"]
data_type = config["data_type"]
ticker_dict = st.session_state.tickers[market]

selected     = st.sidebar.selectbox("종목 선택", list(ticker_dict.keys()))
ticker       = ticker_dict[selected]
candle_label = st.sidebar.selectbox("캔들 단위", list(CANDLE_OPTIONS.keys()), index=0)

st.sidebar.markdown("---")
st.sidebar.markdown("### ➕ 종목 추가")
if data_type == "KR":
    new_name   = st.sidebar.text_input("종목명", placeholder="예: LG전자")
    new_ticker = st.sidebar.text_input("종목코드 (6자리)", placeholder="예: 066570")
elif data_type == "COIN":
    new_name   = st.sidebar.text_input("코인명", placeholder="예: Shiba Inu")
    new_ticker = st.sidebar.text_input("티커", placeholder="예: SHIB")
else:
    new_name   = st.sidebar.text_input("종목명", placeholder="예: AMD")
    new_ticker = st.sidebar.text_input("티커", placeholder="예: AMD")

if st.sidebar.button("➕ 추가"):
    if new_name and new_ticker:
        st.session_state.tickers[market][new_name] = new_ticker.strip().upper()
        save_data(st.session_state.tickers)
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 🗑️ 종목 삭제")
delete_target = st.sidebar.selectbox("삭제할 종목", list(ticker_dict.keys()), key="delete")
if st.sidebar.button("🗑️ 삭제"):
    del st.session_state.tickers[market][delete_target]
    save_data(st.session_state.tickers)
    st.rerun()

with st.spinner("데이터 불러오는 중..."):
    df = pd.DataFrame()
    try:
        if data_type == "COIN":
            df = get_coin_data(ticker, "KRW")
        else:
            start = datetime(2000, 1, 1)
            df = fdr.DataReader(ticker, start, datetime.today())

        resample_rule = RESAMPLE_MAP.get(candle_label)
        if resample_rule and not df.empty:
            df = df.resample(resample_rule).agg({
                'Open': 'first', 'High': 'max',
                'Low': 'min', 'Close': 'last', 'Volume': 'sum'
            }).dropna()
    except Exception as e:
        st.error(f"데이터 오류: {e}")

if df.empty:
    st.error("데이터를 불러올 수 없습니다. 티커를 확인하거나 잠시 후 다시 시도해주세요.")
else:
    col1, col2, col3 = st.columns(3)
    price      = df['Close'].iloc[-1]
    prev       = df['Close'].iloc[-2] if len(df) > 1 else price
    change_pct = (price - prev) / prev * 100 if prev else 0

    col1.metric("현재가",      fmt(price, currency), f"{change_pct:+.2f}%")
    col2.metric("기간 최고가", fmt(df['High'].max(), currency))
    col3.metric("기간 최저가", fmt(df['Low'].min(),  currency))

    fig = go.Figure(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        increasing=dict(line=dict(color='red'), fillcolor='red'),
        decreasing=dict(line=dict(color='blue'), fillcolor='blue'),
    ))
    fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

if data_type == "COIN":
    st.markdown("---")
    st.subheader(f"🌶️ {selected} 김치프리미엄")
    with st.spinner("김치프리미엄 계산 중..."):
        kp_df, current_kp = get_kimchi_premium(ticker)
    if kp_df.empty or current_kp is None:
        st.warning("김치프리미엄 데이터를 불러올 수 없습니다.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("현재 프리미엄", f"{current_kp:+.2f}%")
        c2.metric("국내 가격", fmt(kp_df['KRW가격'].iloc[-1], "KRW"))
        c3.metric("해외(원화환산)", fmt(kp_df['달러환산원화'].iloc[-1], "KRW"))
        c4.metric("기준 환율", f"₩{kp_df['환율'].iloc[-1]:,.0f}")
        
        fig_kp = go.Figure(go.Scatter(x=kp_df.index, y=kp_df['김치프리미엄(%)'], line=dict(color='orange')))
        fig_kp.add_hline(y=0, line_dash="dash", line_color="white")
        fig_kp.update_layout(template="plotly_dark", yaxis=dict(ticksuffix="%"))
        st.plotly_chart(fig_kp, use_container_width=True)

st.markdown("---")
st.subheader(f"📉 {market} — 하락률 테이블")
with st.spinner("하락률 계산 중..."):
    dd_df = get_drawdown_table(dict(ticker_dict), data_type, currency)
if not dd_df.empty:
    st.dataframe(dd_df, use_container_width=True, hide_index=True)
