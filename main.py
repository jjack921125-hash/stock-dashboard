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
# S&P500: 나스닥 중복 제외 시총 상위 10위
# 코인: yfinance 형식 "BTC" → "BTC-USD"로 자동 변환
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
    # 코인 티커: "BTC", "ETH" 등
    # 내부적으로 "BTC-USD" 형식으로 변환해서 yfinance로 가져와요
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

# ───────────────────────────────────────────
# 시장별 설정
# ───────────────────────────────────────────
MARKET_CONFIG = {
    "S&P500": {"currency": "USD", "data_type": "US"},
    "나스닥":  {"currency": "USD", "data_type": "US"},
    "코스피":  {"currency": "KRW", "data_type": "KR"},
    "코스닥":  {"currency": "KRW", "data_type": "KR"},
    "코인":    {"currency": "KRW", "data_type": "COIN"},
}

# ───────────────────────────────────────────
# 캔들 단위
# ───────────────────────────────────────────
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
# 환율 가져오기 (USD/KRW)
# ───────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_usd_krw():
    """
    yfinance로 현재 달러/원 환율을 가져옵니다.
    코인 가격을 원화로 환산할 때 사용해요.
    """
    try:
        fx = yf.download("USDKRW=X", period="5d", progress=False)
        if isinstance(fx.columns, pd.MultiIndex):
            fx.columns = fx.columns.get_level_values(0)
        if not fx.empty:
            return float(fx['Close'].iloc[-1])
    except:
        pass
    return 1380.0  # API 실패 시 기본값

# ───────────────────────────────────────────
# 코인 데이터 가져오기
# yfinance로 USD 가격을 받아와서 환율 곱해 원화로 변환
# ───────────────────────────────────────────
@st.cache_data(ttl=300)
def get_coin_data(symbol: str):
    """
    yfinance로 코인 데이터를 가져와서 원화로 변환합니다.
    symbol: "BTC" → yfinance에서 "BTC-USD"로 요청
    """
    try:
        target = f"{symbol}-USD"
        # period="max": 상장일부터 전체 데이터
        df = yf.download(target, period="max", progress=False)

        if df.empty:
            return pd.DataFrame()

        # MultiIndex 컬럼 → 단일 컬럼으로 변환
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 환율 적용해서 원화로 변환
        rate = get_usd_krw()
        result = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        result[['Open', 'High', 'Low', 'Close']] *= rate
        return result

    except Exception as e:
        return pd.DataFrame()

# ───────────────────────────────────────────
# 주식 데이터 가져오기 (FinanceDataReader)
# ───────────────────────────────────────────
@st.cache_data(ttl=300)
def get_stock_data(symbol: str, data_type: str):
    """
    FinanceDataReader로 주식 데이터를 가져옵니다.
    2000년부터 현재까지 전체 데이터를 가져와요.
    """
    try:
        start = datetime(2000, 1, 1)
        df = fdr.DataReader(symbol, start, datetime.today())
        return df
    except Exception as e:
        return pd.DataFrame()

# ───────────────────────────────────────────
# 김치프리미엄 계산
# ───────────────────────────────────────────
@st.cache_data(ttl=300)
def get_kimchi_premium(symbol: str):
    """
    코인의 김치프리미엄을 계산합니다.
    KRW가격(업비트 대용: yfinance KRW 가격) vs USD×환율 비교
    
    FinanceDataReader로 BTC/KRW, BTC/USD를 비교해서 계산해요.
    """
    try:
        # USD 가격 (yfinance)
        target = f"{symbol}-USD"
        df_usd = yf.download(target, period="max", progress=False)
        if isinstance(df_usd.columns, pd.MultiIndex):
            df_usd.columns = df_usd.columns.get_level_values(0)

        # 환율
        fx = yf.download("USDKRW=X", period="max", progress=False)
        if isinstance(fx.columns, pd.MultiIndex):
            fx.columns = fx.columns.get_level_values(0)

        if df_usd.empty or fx.empty:
            return pd.DataFrame(), None

        # 날짜 맞춰서 합치기
        df = pd.DataFrame({
            'USD가격': df_usd['Close'],
            '환율':    fx['Close'],
        }).dropna()

        # 달러 환산 원화가격
        df['달러환산원화'] = df['USD가격'] * df['환율']

        # FinanceDataReader로 실제 KRW 가격 시도
        try:
            df_krw_raw = fdr.DataReader(
                f"{symbol}/KRW",
                datetime(2018, 1, 1),
                datetime.today()
            )
            if not df_krw_raw.empty:
                df['KRW가격'] = df_krw_raw['Close']
                df = df.dropna()
                df['김치프리미엄(%)'] = (
                    df['KRW가격'] / df['달러환산원화'] - 1
                ) * 100
            else:
                raise Exception("KRW 데이터 없음")
        except:
            # KRW 직접 데이터 없으면 환산가격으로 대체
            # (이 경우 김치프리미엄은 의미 없으므로 None 반환)
            return pd.DataFrame(), None

        current_kp = df['김치프리미엄(%)'].iloc[-1]
        return df, current_kp

    except Exception as e:
        return pd.DataFrame(), None

# ───────────────────────────────────────────
# 최고점 대비 하락률 계산
# ───────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_drawdown_table(ticker_dict: dict, data_type: str, currency: str):
    """
    목록의 모든 종목에 대해
    역대 최고가 대비 현재가 하락률을 계산합니다.
    """
    rows = []
    for name, ticker in ticker_dict.items():
        try:
            if data_type == "COIN":
                df = get_coin_data(ticker)
            else:
                df = get_stock_data(ticker, data_type)

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
            df = get_coin_data(ticker)
        else:
            df = get_stock_data(ticker, data_type)

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
    col1.metric("현재가",      fmt(price, currency), f"{change_pct:+.2f}%")
    col2.metric("기간 최고가", fmt(float(df['High'].max()), currency))
    col3.metric("기간 최저가", fmt(float(df['Low'].min()),  currency))

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

# ───────────────────────────────────────────
# 코인 전용: 김치프리미엄
# ───────────────────────────────────────────
if data_type == "COIN":
    st.markdown("---")
    st.subheader(f"🌶️ {selected} 김치프리미엄")
    st.caption("일봉 기준 | KRW가격 vs USD×환율 비교")

    with st.spinner("김치프리미엄 계산 중..."):
        kp_df, current_kp = get_kimchi_premium(ticker)

    if kp_df.empty or current_kp is None:
        st.info("💡 김치프리미엄은 KRW 직접 시세 데이터가 필요해요. 현재는 데이터를 불러올 수 없습니다.")
    else:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("현재 김치프리미엄", f"{current_kp:+.2f}%")
        col2.metric("국내(KRW) 가격",    fmt(float(kp_df['KRW가격'].iloc[-1]),     "KRW"))
        col3.metric("해외(USD→KRW환산)", fmt(float(kp_df['달러환산원화'].iloc[-1]), "KRW"))
        col4.metric("현재 환율",          f"₩{float(kp_df['환율'].iloc[-1]):,.0f}")

        fig_kp = go.Figure()
        fig_kp.add_trace(go.Scatter(
            x=kp_df.index,
            y=kp_df['김치프리미엄(%)'],
            mode='lines',
            name='김치프리미엄(%)',
            line=dict(color='orange', width=2),
        ))
        fig_kp.add_hline(y=0, line_dash="dash", line_color="white",
                         annotation_text="0% 기준선",
                         annotation_position="bottom right")
        fig_kp.update_layout(
            title=f"{selected} 김치프리미엄 추이",
            template="plotly_dark",
            yaxis=dict(ticksuffix="%"),
            hovermode="x unified",
        )
        st.plotly_chart(fig_kp, use_container_width=True)

        # 최근 30일 테이블
        st.subheader("📋 최근 30일 김치프리미엄")
        recent = kp_df.tail(30).copy()
        recent['KRW가격']        = recent['KRW가격'].apply(lambda x: fmt(x, "KRW"))
        recent['달러환산원화']    = recent['달러환산원화'].apply(lambda x: fmt(x, "KRW"))
        recent['환율']            = recent['환율'].apply(lambda x: f"₩{x:,.0f}")
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
