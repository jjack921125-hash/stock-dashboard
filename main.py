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
# 코인 데이터 가져오기 (yfinance로 수정)
# ───────────────────────────────────────────
@st.cache_data(ttl=300)
def get_coin_data(coin: str, currency: str = "KRW"):
    try:
        # yfinance 티커: BTC-KRW, BTC-USD 형식
        symbol = f"{coin}-{currency}"
        df = yf.download(symbol, start="2018-01-01", progress=False)
        
        if df.empty:
            return pd.DataFrame()
            
        # yfinance 최신 버전의 MultiIndex 컬럼 방지
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        return df
    except Exception as e:
        return pd.DataFrame()

# ───────────────────────────────────────────
# 환율 데이터 가져오기
# ───────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_usd_krw():
    try:
        df = fdr.DataReader('USD/KRW', datetime(2024, 1, 1), datetime.today())
        if df.empty:
            return None
        return df['Close'].iloc[-1]
    except:
        return None

# ───────────────────────────────────────────
# 김치프리미엄 계산 함수 (보간 처리 추가)
# ───────────────────────────────────────────
@st.cache_data(ttl=300)
def get_kimchi_premium(coin: str):
    try:
        df_krw = get_coin_data(coin, "KRW")
        df_usd = get_coin_data(coin, "USD")
        df_fx  = fdr.DataReader('USD/KRW', datetime(2018, 1, 1), datetime.today())

        if df_krw.empty or df_usd.empty or df_fx.empty:
            return pd.DataFrame(), None

        # 날짜 기준으로 합치기
        df = pd.DataFrame({
            'KRW가격':  df_krw['Close'],
            'USD가격':  df_usd['Close'],
        }).dropna()
        
        # 환율 데이터 매칭 및 주말 공백 채우기
        df['환율'] = df_fx['Close'].reindex(df.index).ffill()
        df['달러환산원화'] = df['USD가격'] * df['환율']
        df['김치프리미엄(%)'] = (df['KRW가격'] / df['달러환산원화'] - 1) * 100

        current_premium = df['김치프리미엄(%)'].iloc[-1]
        return df, current_premium

    except Exception as e:
        return pd.DataFrame(), None

# ───────────────────────────────────────────
# 최고점 대비 하락률 계산
# ───────────────────────────────────────────
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

# ───────────────────────────────────────────
# 차트 표시
# ───────────────────────────────────────────
if df.empty:
    st.error("데이터를 불러올 수 없습니다.")
else:
    col1, col2, col3 = st.columns(3)
    price      = df['Close'].iloc[-1]
    prev       = df['Close'].iloc[-2] if len(df) > 1 else price
    change_pct = (price - prev) / prev * 100 if prev else 0

    col1.metric("현재가",      fmt(price, currency), f"{change_pct:+.2f}%")
    col2.metric("기간 최고가", fmt(df['High'].max(), currency))
    col3.metric("기간 최저가", fmt(df['Low'].min(),  currency))

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

    colors = ['red' if c >= o else 'blue'
              for c, o in zip(df['Close'], df['Open'])]
    fig2 = go.Figure(go.Bar(
        x=df.index, y=df['Volume'], marker_color=colors
    ))
    fig2.update_layout(title="거래량", template="plotly_dark")
    st.plotly_chart(fig2, use_container_width=True)

# ───────────────────────────────────────────
# 코인 전용: 김치프리미엄
# ───────────────────────────────────────────
if data_type == "COIN":
    st.markdown("---")
    st.subheader(f"🌶️ {selected} 김치프리미엄")
    st.caption("일봉 기준 | KRW가격 vs USD가격×환율 비교")

    with st.spinner("김치프리미엄 계산 중..."):
        kp_df, current_kp = get_kimchi_premium(ticker)

    if kp_df.empty or current_kp is None:
        st.warning("김치프리미엄 데이터를 불러올 수 없습니다.")
    else:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(
            "현재 김치프리미엄",
            f"{current_kp:+.2f}%",
            delta_color="normal" if current_kp > 0 else "inverse"
        )
        col2.metric(
            "국내(KRW) 가격",
            fmt(kp_df['KRW가격'].iloc[-1], "KRW")
        )
        col3.metric(
            "해외(USD→KRW 환산)",
            fmt(kp_df['달러환산원화'].iloc[-1], "KRW")
        )
        col4.metric(
            "현재 환율",
            f"₩{kp_df['환율'].iloc[-1]:,.0f}"
        )

        fig_kp = go.Figure()
        fig_kp.add_trace(go.Scatter(
            x=kp_df.index,
            y=kp_df['김치프리미엄(%)'],
            mode='lines',
            name='김치프리미엄(%)',
            line=dict(color='orange', width=2),
        ))

        fig_kp.add_hline(
            y=0,
            line_dash="dash",
            line_color="white",
            annotation_text="0% 기준선",
            annotation_position="bottom right"
        )

        fig_kp.update_layout(
            title=f"{selected} 김치프리미엄 추이",
            template="plotly_dark",
            yaxis=dict(ticksuffix="%"),
            hovermode="x unified",
        )
        st.plotly_chart(fig_kp, use_container_width=True)

        st.subheader("📋 최근 30일 김치프리미엄")
        recent = kp_df.tail(30).copy()
        recent['KRW가격']       = recent['KRW가격'].apply(lambda x: fmt(x, "KRW"))
        recent['달러환산원화']   = recent['달러환산원화'].apply(lambda x: fmt(x, "KRW"))
        recent['환율']           = recent['환율'].apply(lambda x: f"₩{x:,.0f}")
        recent['김치프리미엄(%)'] = recent['김치프리미엄(%)'].apply(lambda x: f"{x:+.2f}%")
        recent = recent.drop(columns=['USD가격'])
        st.dataframe(recent.sort_index(ascending=False), use_container_width=True)

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
