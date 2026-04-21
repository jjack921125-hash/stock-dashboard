import streamlit as st
import FinanceDataReader as fdr
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="주식 대시보드", page_icon="📈", layout="wide")
st.title("📈 한국/미국 주식 대시보드")

market = st.sidebar.selectbox("시장 선택", ["🇺🇸 미국", "🇰🇷 한국"])

if market == "🇰🇷 한국":
    tickers = {"삼성전자": "005930", "SK하이닉스": "000660", "NAVER": "035420", "카카오": "035720", "현대차": "005380"}
else:
    tickers = {"Apple": "AAPL", "Microsoft": "MSFT", "NVIDIA": "NVDA", "Tesla": "TSLA", "Google": "GOOGL"}

selected = st.sidebar.selectbox("종목 선택", list(tickers.keys()))
ticker = tickers[selected]

period = st.sidebar.selectbox("기간", ["1개월", "3개월", "6개월", "1년", "3년"], index=1)
period_map = {"1개월": 30, "3개월": 90, "6개월": 180, "1년": 365, "3년": 1095}
days = period_map[period]

end = datetime.today()
start = end - timedelta(days=days)

with st.spinner("데이터 불러오는 중..."):
    df = fdr.DataReader(ticker, start, end)

if df.empty:
    st.error("데이터를 불러올 수 없습니다.")
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
    fig.update_layout(title=f"{selected} 주가 차트", xaxis_rangeslider_visible=False, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

    # 거래량 차트
    fig2 = go.Figure(go.Bar(x=df.index, y=df['Volume'], marker_color='lightblue'))
    fig2.update_layout(title="거래량", template="plotly_dark")
    st.plotly_chart(fig2, use_container_width=True)

    # 데이터 테이블
    st.subheader("📋 데이터 테이블")
    st.dataframe(df.tail(20), use_container_width=True)
