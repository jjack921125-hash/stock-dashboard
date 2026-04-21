import streamlit as st
import FinanceDataReader as fdr
import yfinance as yf
import ccxt
import plotly.graph_objects as go
import pandas as pd
import json
import os
from datetime import datetime, timedelta

st.set_page_config(page_title="주식 대시보드", page_icon="📈", layout="wide")
st.title("📈 주식/코인 대시보드")

# ───────────────────────────────────────────
# 바이낸스 객체 생성
# API 키 없이도 시세 조회는 무료로 가능해요
# ───────────────────────────────────────────
binance = ccxt.binance()

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
# 시장별 기본 종목 (시총 상위 10위, 2025년 4월 기준)
# 코인 티커는 CCXT 바이낸스 형식: "BTC/USDT"
# ───────────────────────────────────────────
DEFAULT_TICKERS = {
    "S&P500": {
        "Apple":            "AAPL",
        "Microsoft":        "MSFT",
        "NVIDIA":           "NVDA",
        "Amazon":           "AMZN",
        "Alphabet(Google)": "GOOGL",
        "Meta":             "META",
        "Berkshire":        "BRK-B",
        "Broadcom":         "AVGO",
        "Tesla":            "TSLA",
        "JPMorgan":         "JPM",
    },
    "나스닥": {
        "Apple":            "AAPL",
        "Microsoft":        "MSFT",
        "NVIDIA":           "NVDA",
        "Amazon":           "AMZN",
        "Alphabet(Google)": "GOOGL",
        "Meta":             "META",
        "Broadcom":         "AVGO",
        "Tesla":            "TSLA",
        "Costco":           "COST",
        "Netflix":          "NFLX",
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
        "HLB":              "028300",
        "에코프로":         "086520",
        "알테오젠":         "196170",
        "셀트리온제약":     "068760",
        "리가켐바이오":     "141080",
        "클래시스":         "214150",
        "휴젤":             "145020",
        "HPSP":             "403870",
        "삼천당제약":       "000250",
    },
    "코인": {
        "Bitcoin":   "BTC/USDT",
        "Ethereum":  "ETH/USDT",
        "BNB":       "BNB/USDT",
        "Solana":    "SOL/USDT",
        "XRP":       "XRP/USDT",
        "Dogecoin":  "DOGE/USDT",
        "Cardano":   "ADA/USDT",
        "Avalanche": "AVAX/USDT",
        "Chainlink": "LINK/USDT",
        "Polkadot":  "DOT/USDT",
    },
}

# ───────────────────────────────────────────
# 시장별 설정
# ───────────────────────────────────────────
MARKET_CONFIG = {
    "S&P500": {"currency": "USD", "data_type": "US"},
    "나스닥":  {"currency": "USD", "data_type": "US"},
    "코스피":  {"currency": "KRW", "data_type": "KR"},
    "코스닥":  {"currency": "KRW", "data_type": "KR"},
    "코인":    {"currency": "USD", "data_type": "COIN"},
}

# ───────────────────────────────────────────
# 캔들 단위 설정
# ───────────────────────────────────────────
CANDLE_OPTIONS = {
    "1분":   {"type": "minute", "yf_interval": "1m",  "yf_period": "7d",  "ccxt_interval": "1m"},
    "3분":   {"type": "minute", "yf_interval": "3m",  "yf_period": "7d",  "ccxt_interval": "3m"},
    "5분":   {"type": "minute", "yf_interval": "5m",  "yf_period": "7d",  "ccxt_interval": "5m"},
    "15분":  {"type": "minute", "yf_interval": "15m", "yf_period": "60d", "ccxt_interval": "15m"},
    "30분":  {"type": "minute", "yf_interval": "30m", "yf_period": "60d", "ccxt_interval": "30m"},
    "60분":  {"type": "minute", "yf_interval": "60m", "yf_period": "60d", "ccxt_interval": "1h"},
    "4시간": {"type": "minute", "yf_interval": "4h",  "yf_period": "60d", "ccxt_interval": "4h"},
    "1일":   {"type": "daily",  "ccxt_interval": "1d"},
    "1주":   {"type": "weekly", "ccxt_interval": "1w"},
    "1달":   {"type": "monthly","ccxt_interval": "1M"},
    "1년":   {"type": "yearly", "ccxt_interval": "1M"},
}

RESAMPLE_MAP = {
    "1일":  None,
    "1주":  "W",
    "1달":  "ME",
    "1년":  "YE",
}

# ───────────────────────────────────────────
# 앱 시작 시 저장된 데이터 불러오기
# ───────────────────────────────────────────
if "tickers" not in st.session_state:
    st.session_state.tickers = load_data()

for market_key in DEFAULT_TICKERS:
    if market_key not in st.session_state.tickers:
        st.session_state.tickers[market_key] = DEFAULT_TICKERS[market_key].copy()

# ───────────────────────────────────────────
# 가격 포맷 함수
# ───────────────────────────────────────────
def fmt(price, currency):
    if currency == "KRW":
        return f"₩{price:,.0f}"
    else:
        return f"${price:,.4f}" if price < 1 else f"${price:,.2f}"

# ───────────────────────────────────────────
# CCXT로 코인 OHLCV 데이터 가져오기
# OHLCV = Open(시가) High(고가) Low(저가) Close(종가) Volume(거래량)
# ───────────────────────────────────────────
@st.cache_data(ttl=60)  # 60초 캐시 (매번 API 호출 방지)
def get_coin_data(symbol, ccxt_interval, limit=500):
    """
    바이낸스에서 코인 캔들 데이터를 가져옵니다.
    
    symbol: "BTC/USDT" 형식
    ccxt_interval: "1m", "1h", "1d" 등
    limit: 가져올 캔들 개수 (최대 1000)
    """
    try:
        # fetch_ohlcv: 캔들 데이터 요청
        ohlcv = binance.fetch_ohlcv(symbol, timeframe=ccxt_interval, limit=limit)
        
        # 받아온 데이터를 DataFrame으로 변환
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        
        # timestamp(밀리초)를 날짜 형식으로 변환
        # unit='ms': 밀리초 단위
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
    except Exception as e:
        st.error(f"코인 데이터 오류: {e}")
        return pd.DataFrame()

# ───────────────────────────────────────────
# 사이드바
# ───────────────────────────────────────────
st.sidebar.title("⚙️ 설정")

market = st.sidebar.selectbox("시장 선택", list(MARKET_CONFIG.keys()))
config    = MARKET_CONFIG[market]
currency  = config["currency"]
data_type = config["data_type"]
ticker_dict = st.session_state.tickers[market]

selected     = st.sidebar.selectbox("종목 선택", list(ticker_dict.keys()))
ticker       = ticker_dict[selected]
candle_label = st.sidebar.selectbox("캔들 단위", list(CANDLE_OPTIONS.keys()), index=7)
candle_info  = CANDLE_OPTIONS[candle_label]

# ───────────────────────────────────────────
# 종목 추가
# ───────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("### ➕ 종목 추가")

if data_type == "KR":
    new_name   = st.sidebar.text_input("종목명", placeholder="예: LG전자")
    new_ticker = st.sidebar.text_input("종목코드 (6자리)", placeholder="예: 066570")
elif data_type == "COIN":
    new_name   = st.sidebar.text_input("코인명", placeholder="예: Shiba Inu")
    new_ticker = st.sidebar.text_input("티커 (바이낸스 형식)", placeholder="예: SHIB/USDT")
else:
    new_name   = st.sidebar.text_input("종목명", placeholder="예: AMD")
    new_ticker = st.sidebar.text_input("티커", placeholder="예: AMD")

if st.sidebar.button("➕ 추가"):
    if new_name and new_ticker:
        st.session_state.tickers[market][new_name] = new_ticker.strip()
        save_data(st.session_state.tickers)
        st.sidebar.success(f"✅ {new_name} 추가 및 저장됨!")
        st.rerun()
    else:
        st.sidebar.error("종목명과 코드를 모두 입력해주세요!")

# ───────────────────────────────────────────
# 종목 삭제
# ───────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("### 🗑️ 종목 삭제")
delete_target = st.sidebar.selectbox("삭제할 종목", list(ticker_dict.keys()), key="delete")

if st.sidebar.button("🗑️ 삭제"):
    del st.session_state.tickers[market][delete_target]
    save_data(st.session_state.tickers)
    st.sidebar.success(f"🗑️ {delete_target} 삭제됨!")
    st.rerun()

# ───────────────────────────────────────────
# 데이터 불러오기
# ───────────────────────────────────────────
with st.spinner("데이터 불러오는 중..."):
    try:
        if data_type == "COIN":
            # ── 코인: CCXT 바이낸스 ──
            ccxt_interval = candle_info["ccxt_interval"]

            # 1년봉은 월봉 데이터를 연단위로 리샘플링
            if candle_label == "1년":
                df = get_coin_data(ticker, "1M", limit=120)
                if not df.empty:
                    df = df.resample("YE").agg({
                        'Open': 'first', 'High': 'max',
                        'Low': 'min', 'Close': 'last', 'Volume': 'sum'
                    }).dropna()
            else:
                # limit: 캔들 개수
                # 분봉은 500개, 일봉 이상은 1000개
                limit = 500 if candle_info["type"] == "minute" else 1000
                df = get_coin_data(ticker, ccxt_interval, limit=limit)

        elif candle_info["type"] == "minute":
            # ── 주식 분봉/시간봉: yfinance ──
            yf_ticker = f"{ticker}.KS" if data_type == "KR" else ticker
            stock = yf.Ticker(yf_ticker)
            df = stock.history(
                period=candle_info["yf_period"],
                interval=candle_info["yf_interval"]
            )
            if not df.empty:
                df.index = df.index.tz_localize(None)

        else:
            # ── 주식 일봉 이상: 상장일부터 전체 데이터 ──
            yf_ticker = f"{ticker}.KS" if data_type == "KR" else ticker
            stock = yf.Ticker(yf_ticker)
            info  = stock.info

            # 상장일 가져오기
            first_trade = info.get("firstTradeDateEpochUtc")
            start = datetime.fromtimestamp(first_trade) if first_trade else datetime(2000, 1, 1)
            end   = datetime.today()

            df = fdr.DataReader(ticker, start, end)

            # 주/월/년봉 리샘플링
            resample_rule = RESAMPLE_MAP.get(candle_label)
            if resample_rule:
                df = df.resample(resample_rule).agg({
                    'Open': 'first', 'High': 'max',
                    'Low': 'min', 'Close': 'last', 'Volume': 'sum'
                }).dropna()

    except Exception as e:
        st.error(f"데이터 오류: {e}")
        df = pd.DataFrame()

# ───────────────────────────────────────────
# 차트 표시
# ───────────────────────────────────────────
if df.empty:
    st.error("데이터를 불러올 수 없습니다. 종목코드를 확인해주세요.")
else:
    # 현재가 지표
    col1, col2, col3 = st.columns(3)
    price      = df['Close'].iloc[-1]
    prev       = df['Close'].iloc[-2] if len(df) > 1 else price
    change_pct = (price - prev) / prev * 100 if prev else 0

    col1.metric("현재가",     fmt(price, currency), f"{change_pct:+.2f}%")
    col2.metric("기간 최고가", fmt(df['High'].max(), currency))
    col3.metric("기간 최저가", fmt(df['Low'].min(),  currency))

    # 캔들 차트 (상승: 빨간색, 하락: 파란색)
    fig = go.Figure(go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'],
        low=df['Low'],   close=df['Close'],
        increasing=dict(line=dict(color='red'),  fillcolor='red'),
        decreasing=dict(line=dict(color='blue'), fillcolor='blue'),
    ))
    fig.update_layout(
        title=f"{selected} — {candle_label}봉 차트",
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        yaxis=dict(
            tickprefix="₩" if currency == "KRW" else "$",
            tickformat=",.0f" if currency == "KRW" else ",.2f",
        )
    )
    st.plotly_chart(fig, use_container_width=True)

    # 거래량 차트 (상승일: 빨간색, 하락일: 파란색)
    colors = ['red' if c >= o else 'blue'
              for c, o in zip(df['Close'], df['Open'])]
    fig2 = go.Figure(go.Bar(
        x=df.index, y=df['Volume'], marker_color=colors
    ))
    fig2.update_layout(title="거래량", template="plotly_dark")
    st.plotly_chart(fig2, use_container_width=True)

    # 최근 데이터 테이블
    st.subheader("📋 최근 데이터")
    display_df = df.tail(20).copy()
    for col in ['Open', 'High', 'Low', 'Close']:
        display_df[col] = display_df[col].apply(lambda x: fmt(x, currency))
    display_df['Volume'] = display_df['Volume'].apply(lambda x: f"{x:,.0f}")
    st.dataframe(display_df, use_container_width=True)
