import streamlit as st
import FinanceDataReader as fdr
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="주식 대시보드", page_icon="📈", layout="wide")
st.title("📈 한국/미국 주식 대시보드")

# ───────────────────────────────────────────
# 기본 종목 목록 (앱 처음 실행 시 보여줄 종목들)
# ───────────────────────────────────────────
DEFAULT_KR = {"삼성전자": "005930", "SK하이닉스": "000660", "NAVER": "035420", "카카오": "035720", "현대차": "005380"}
DEFAULT_US = {"Apple": "AAPL", "Microsoft": "MSFT", "NVIDIA": "NVDA", "Tesla": "TSLA", "Google": "GOOGL"}

# ───────────────────────────────────────────
# session_state = 앱이 켜져 있는 동안 데이터를 기억하는 공간
# 처음 실행 시 기본 종목으로 초기화
# ───────────────────────────────────────────
if "kr_tickers" not in st.session_state:
    st.session_state.kr_tickers = DEFAULT_KR.copy()
if "us_tickers" not in st.session_state:
    st.session_state.us_tickers = DEFAULT_US.copy()

# ───────────────────────────────────────────
# 사이드바
# ───────────────────────────────────────────
st.sidebar.title("⚙️ 설정")
market = st.sidebar.selectbox("시장 선택", ["🇺🇸 미국", "🇰🇷 한국"])

# 시장에 따라 종목 목록 선택
if market == "🇰🇷 한국":
    ticker_dict = st.session_state.kr_tickers
else:
    ticker_dict = st.session_state.us_tickers

# 종목 선택
selected = st.sidebar.selectbox("종목 선택", list(ticker_dict.keys()))
ticker = ticker_dict[selected]

# 기간 선택
period = st.sidebar.selectbox("기간", ["1개월", "3개월", "6개월", "1년", "3년"], index=1)
period_map = {"1개월": 30, "3개월": 90, "6개월": 180, "1년": 365, "3년": 1095}
days = period_map[period]

# ───────────────────────────────────────────
# 종목 추가 기능
# ───────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("### ➕ 종목 추가")

# 한국 주식: 6자리 숫자 코드 입력
# 미국 주식: 알파벳 티커 입력 (예: AAPL)
if market == "🇰🇷 한국":
    new_name = st.sidebar.text_input("종목명", placeholder="예: LG전자")
    new_ticker = st.sidebar.text_input("종목코드 (6자리)", placeholder="예: 066570")
else:
    new_name = st.sidebar.text_input("종목명", placeholder="예: Amazon")
    new_ticker = st.sidebar.text_input("티커", placeholder="예: AMZN")

if st.sidebar.button("➕ 추가"):
    if new_name and new_ticker:
        if market == "🇰🇷 한국":
            st.session_state.kr_tickers[new_name] = new_ticker
        else:
            st.session_state.us_tickers[new_name] = new_ticker.upper()
        st.sidebar.success(f"✅ {new_name} 추가됨!")
        st.rerun()  # 앱 새로고침해서 목록 업데이트
    else:
        st.sidebar.error("종목명과 코드를 모두 입력해주세요!")

# ───────────────────────────────────────────
# 종목 삭제 기능
# ───────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("### 🗑️ 종목 삭제")
delete_target = st.sidebar.selectbox("삭제할 종목", list(ticker_dict.keys()), key="delete")

if st.sidebar.button("🗑️ 삭제"):
    if market == "🇰🇷 한국":
        del st.session_state.kr_tickers[delete_target]
    else:
        del st.session_state.us_tickers[delete_target]
    st.sidebar.success(f"🗑️ {delete_target} 삭제됨!")
    st.rerun()

# ───────────────────────────────────────────
# 메인 차트 영역
# ───────────────────────────────────────────
end = datetime.today()
start = end - timedelta(days=days)

with st.spinner("데이터 불러오는 중..."):
    df = fdr.DataReader(ticker, start, end)

if df.empty:
    st.error("데이터를 불러올 수 없습니다. 종목코드를 확인해주세요.")
else:
    # 현재가 지표
    col1, col2, col3 = st.columns(3)
    price = df['Close'].iloc[-1]
    prev = df['Close'].iloc[-2]
    change_pct = (price - prev) / prev * 100
    col1.metric("현재가", f"{price:,.0f}", f"{change_pct:+.2f}%")
    col2.metric("기간 최고가", f"{df['High'].max():,.0f}")
    col3.metric("기간 최저가", f"{df['Low'].min():,.0f}")

    # 캔들 차트
    fig = go.Figure(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close']
    ))
    fig.update_layout(
        title=f"{selected} 주가 차트",
        xaxis_rangeslider_visible=False,
        template="plotly_dark"
    )
    st.plotly_chart(fig, use_container_width=True)

    # 거래량 차트
    fig2 = go.Figure(go.Bar(x=df.index, y=df['Volume'], marker_color='lightblue'))
    fig2.update_layout(title="거래량", template="plotly_dark")
    st.plotly_chart(fig2, use_container_width=True)

    # 데이터 테이블
    st.subheader("📋 최근 데이터")
    st.dataframe(df.tail(20), use_container_width=True)
