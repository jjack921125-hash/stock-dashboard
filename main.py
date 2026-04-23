import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import plotly.graph_objects as go
import pandas as pd
import json
import os
from datetime import datetime

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

# ───────────────────────────────────────────
# 앱 시작 시 저장된 데이터 불러오기
# ───────────────────────────────────────────
if "tickers" not in st.session_state:
    st.session_state.tickers = load_data()

for k in DEFAULT_TICKERS:
    if k not in st.session_state.tickers:
        st.session_state.tickers[k] = DEFAULT_TICKERS[k].copy()

# ───────────────────────────────────────────
# 가격 포맷 함수
# ───────────────────────────────────────────
def fmt(price, currency):
    if currency == "KRW":
        return f"₩{price:,.0f}"
    return f"${price:,.4f}" if price < 1 else f"${price:,.2f}"

# ───────────────────────────────────────────
# 됐던 코드 그대로: 핵심 데이터 수집 함수
# ───────────────────────────────────────────
@st.cache_data(ttl=300)
def get_any_data(symbol, market_type):
    try:
        if market_type == "COIN":
            # 됐던 코드 그대로: period="1y"
            target = f"{symbol}-USD"
            df = yf.download(target, period="1y", progress=False)

            if df.empty:
                return pd.DataFrame()

            # MultiIndex 제거 (됐던 코드 그대로)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # 환율 (됐던 코드 그대로)
            fx = yf.download("USDKRW=X", period="1d", progress=False)
            if isinstance(fx.columns, pd.MultiIndex):
                fx.columns = fx.columns.get_level_values(0)

            rate = float(fx['Close'].iloc[-1]) if not fx.empty else 1380.0

            final_df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
            final_df[['Open', 'High', 'Low', 'Close']] = \
                final_df[['Open', 'High', 'Low', 'Close']] * rate
            return final_df

        elif market_type in ["US"]:
            # 미국 주식: yfinance
            df = yf.download(symbol, period="max", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if df.empty:
                return pd.DataFrame()
            return df[['Open', 'High', 'Low', 'Close', 'Volume']]

        else:
            # 한국 주식: FinanceDataReader
            return fdr.DataReader(symbol, datetime(2000, 1, 1), datetime.today())

    except Exception as e:
        return pd.DataFrame()

# ───────────────────────────────────────────
# 최고점 대비 하락률 계산
# ───────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_drawdown_table(ticker_dict: dict, data_type: str, currency: str):
    rows = []
    for name, ticker in ticker_dict.items():
        try:
            df = get_any_data(ticker, data_type)
            if df.empty:
                continue

            current       = float(df['Close'].iloc[-1])
            all_time_high = float(df['High'].max())
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
# 사이드바
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
    new_ticker = st.sidebar.text_input("티커", placeholder="예: SHIB")
else:
    new_name   = st.sidebar.text_input("종목명", placeholder="예: AMD")
    new_ticker = st.sidebar.text_input("티커", placeholder="예: AMD")

if st.sidebar.button("➕ 추가"):
    if new_name and new_ticker:
        st.session_state.tickers[market][new_name] = new_ticker.strip().upper()
        save_data(st.session_state.tickers)
        st.sidebar.success(f"✅ {new_name} 추가됨!")
        st.rerun()
    else:
        st.sidebar.error("종목명과 코드를 모두 입력해주세요!")

# ───────────────────────────────────────────
# 종목 삭제
# ───────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("### 🗑️ 종목 삭제")
delete_target = st.sidebar.selectbox(
    "삭제할 종목", list(ticker_dict.keys()), key="delete"
)
if st.sidebar.button("🗑️ 삭제"):
    del st.session_state.tickers[market][delete_target]
    save_data(st.session_state.tickers)
    st.sidebar.success(f"🗑️ {delete_target} 삭제됨!")
    st.rerun()

# ───────────────────────────────────────────
# 데이터 불러오기
# ───────────────────────────────────────────
with st.spinner("데이터 불러오는 중..."):
    df = pd.DataFrame()
    try:
        df = get_any_data(ticker, data_type)

        # 주/월/년봉 리샘플링
        resample_rule = RESAMPLE_MAP.get(candle_label)
        if resample_rule and not df.empty:
            df = df.resample(resample_rule).agg({
                'Open': 'first', 'High': 'max',
                'Low': 'min', 'Close': 'last', 'Volume': 'sum'
            }).dropna()

    except Exception as e:
        st.error(f"데이터 오류: {e}")

# ───────────────────────────────────────────
# 차트 표시
# ───────────────────────────────────────────
if df.empty:
    st.error("데이터를 불러올 수 없습니다.")
else:
    price      = float(df['Close'].iloc[-1])
    prev       = float(df['Close'].iloc[-2]) if len(df) > 1 else price
    change_pct = (price - prev) / prev * 100 if prev else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("현재가",      fmt(price, currency),                    f"{change_pct:+.2f}%")
    col2.metric("기간 최고가", fmt(float(df['High'].max()), currency))
    col3.metric("기간 최저가", fmt(float(df['Low'].min()),  currency))

    # 캔들 차트
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

    # 거래량 차트
    colors = ['red' if c >= o else 'blue'
              for c, o in zip(df['Close'], df['Open'])]
    fig2 = go.Figure(go.Bar(
        x=df.index, y=df['Volume'], marker_color=colors
    ))
    fig2.update_layout(title="거래량", template="plotly_dark")
    st.plotly_chart(fig2, use_container_width=True)

# ───────────────────────────────────────────
# 최고점 대비 하락률 테이블
# ───────────────────────────────────────────
st.markdown("---")
st.subheader(f"📉 {market} — 최고점 대비 현재 하락률")
st.caption("일봉 기준 | 역대 최고가 대비 현재가 하락률 | 하락률 높은 순")

with st.spinner("하락률 계산 중..."):
    dd_df = get_drawdown_table(dict(ticker_dict), data_type, currency)

if dd_df.empty:
    st.warning("하락률 데이터를 불러올 수 없습니다.")
else:
    def color_drawdown(val):
        try:
            v = float(val.replace('%', ''))
            if v < -50:
                return 'color: #0040ff; font-weight: bold'
            elif v < -30:
                return 'color: #4488ff'
            elif v < -10:
                return 'color: #88aaff'
            else:
                return 'color: #aaaaaa'
        except:
            return ''

    styled = dd_df.style.map(color_drawdown, subset=["최고점 대비 하락률"])
    st.dataframe(styled, use_container_width=True, hide_index=True)
