import streamlit as st
import FinanceDataReader as fdr
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import json
import os
from datetime import datetime, timedelta

st.set_page_config(page_title="주식 대시보드", page_icon="📈", layout="wide")
st.title("📈 한국/미국 주식 대시보드")

# ───────────────────────────────────────────
# 영구 저장 함수
# Streamlit Cloud는 'data.json' 파일을 앱이 재시작해도 유지해요
# ───────────────────────────────────────────
SAVE_FILE = "data.json"

def load_data():
    """저장된 종목 목록을 파일에서 불러옵니다."""
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    # 파일이 없으면 기본 종목 반환
    return {
        "KR": {"삼성전자": "005930", "SK하이닉스": "000660", "NAVER": "035420", "카카오": "035720", "현대차": "005380"},
        "US": {"Apple": "AAPL", "Microsoft": "MSFT", "NVIDIA": "NVDA", "Tesla": "TSLA", "Google": "GOOGL"}
    }

def save_data(data):
    """종목 목록을 파일에 저장합니다."""
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ───────────────────────────────────────────
# 앱 시작 시 저장된 데이터 불러오기
# ───────────────────────────────────────────
if "tickers" not in st.session_state:
    st.session_state.tickers = load_data()

# ───────────────────────────────────────────
# 기간 설정
# 분/시간 단위는 yfinance, 일 이상은 FinanceDataReader 사용
# ───────────────────────────────────────────
PERIOD_OPTIONS = {
    "1분": {"yf_period": "1d", "yf_interval": "1m", "type": "minute"},
    "3분": {"yf_period": "1d", "yf_interval": "3m", "type": "minute"},
    "5분": {"yf_period": "1d", "yf_interval": "5m", "type": "minute"},
    "15분": {"yf_period": "5d", "yf_interval": "15m", "type": "minute"},
    "30분": {"yf_period": "5d", "yf_interval": "30m", "type": "minute"},
    "60분": {"yf_period": "1mo", "yf_interval": "60m", "type": "minute"},
    "4시간": {"yf_period": "1mo", "yf_interval": "4h", "type": "minute"},
    "일": {"days": 180, "type": "daily"},
    "주": {"days": 365, "type": "daily"},
    "월": {"days": 365*3, "type": "daily"},
    "년": {"days": 365*5, "type": "daily"},
}

# ───────────────────────────────────────────
# 사이드바
# ───────────────────────────────────────────
st.sidebar.title("⚙️ 설정")
market = st.sidebar.selectbox("시장 선택", ["🇺🇸 미국", "🇰🇷 한국"])
market_key = "KR" if market == "🇰🇷 한국" else "US"
ticker_dict = st.session_state.tickers[market_key]

selected = st.sidebar.selectbox("종목 선택", list(ticker_dict.keys()))
ticker = ticker_dict[selected]
period_label = st.sidebar.selectbox("기간", list(PERIOD_OPTIONS.keys()), index=7)
period_info = PERIOD_OPTIONS[period_label]

# ───────────────────────────────────────────
# 종목 추가
# ───────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("### ➕ 종목 추가")

if market == "🇰🇷 한국":
    new_name = st.sidebar.text_input("종목명", placeholder="예: LG전자")
    new_ticker = st.sidebar.text_input("종목코드 (6자리)", placeholder="예: 066570")
else:
    new_name = st.sidebar.text_input("종목명", placeholder="예: Amazon")
    new_ticker = st.sidebar.text_input("티커", placeholder="예: AMZN")

if st.sidebar.button("➕ 추가"):
    if new_name and new_ticker:
        # 메모리에 추가
        st.session_state.tickers[market_key][new_name] = new_ticker.strip()
        # 파일에 저장 (영구 저장)
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
    del st.session_state.tickers[market_key][delete_target]
    save_data(st.session_state.tickers)
    st.sidebar.success(f"🗑️ {delete_target} 삭제됨!")
    st.rerun()

# ───────────────────────────────────────────
# 데이터 불러오기
# 분/시간 단위 → yfinance
# 일/주/월/년 단위 → FinanceDataReader
# ───────────────────────────────────────────
with st.spinner("데이터 불러오는 중..."):
    try:
        if period_info["type"] == "minute":
            # 분/시간봉: yfinance 사용
            yf_ticker = f"{ticker}.KS" if market_key == "KR" else ticker
            stock = yf.Ticker(yf_ticker)
            df = stock.history(
                period=period_info["yf_period"],
                interval=period_info["yf_interval"]
            )
            # 시간대 정보 제거
            if not df.empty:
                df.index = df.index.tz_localize(None)
        else:
            # 일봉 이상: FinanceDataReader 사용
            end = datetime.today()
            start = end - timedelta(days=period_info["days"])
            df = fdr.DataReader(ticker, start, end)
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
    price = df['Close'].iloc[-1]
    prev = df['Close'].iloc[-2] if len(df) > 1 else price
    change_pct = (price - prev) / prev * 100 if prev else 0

    col1.metric("현재가", f"{price:,.2f}", f"{change_pct:+.2f}%")
    col2.metric("기간 최고가", f"{df['High'].max():,.2f}")
    col3.metric("기간 최저가", f"{df['Low'].min():,.2f}")

    # 캔들 차트
    fig = go.Figure(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close']
    ))
    fig.update_layout(
        title=f"{selected} — {period_label}봉 차트",
        xaxis_rangeslider_visible=False,
        template="plotly_dark"
    )
    st.plotly_chart(fig, use_container_width=True)

    # 거래량 차트
    fig2 = go.Figure(go.Bar(
        x=df.index,
        y=df['Volume'],
        marker_color='lightblue'
    ))
    fig2.update_layout(title="거래량", template="plotly_dark")
    st.plotly_chart(fig2, use_container_width=True)

    # 최근 데이터 테이블
    st.subheader("📋 최근 데이터")
    st.dataframe(df.tail(20), use_container_width=True)
