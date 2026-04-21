import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="주식 대시보드", page_icon="📈", layout="wide")
st.title("📈 한국/미국 주식 대시보드")

# 사이드바 - 시장 선택
market = st.sidebar.selectbox("시장 선택", ["🇺🇸 미국", "🇰🇷 한국"])

if market == "🇰🇷 한국":
    tickers = {"삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "NAVER": "035420.KS", "카카오": "035720.KS", "현대차": "005380.KS"}
else:
    tickers = {"Apple": "AAPL", "Microsoft": "MSFT", "NVIDIA": "NVDA", "Tesla": "TSLA", "Google": "GOOGL"}

selected = st.sidebar.selectbox("종목 선택", list(tickers.keys()))
ticker = tickers[selected]
period = st.sidebar.selectbox("기간", ["1mo", "3mo", "6mo", "1y", "3y"], index=1)

# 데이터 가져오기
stock = yf.Ticker(ticker)
df = stock.history(period=period)
info = stock.info

# 현재가 표시
col1, col2, col3 = st.columns(3)
price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
prev = info.get("previousClose", 0)
change = price - prev
change_pct = (change / prev * 100) if prev else 0

col1.metric("현재가", f"{price:,.0f}", f"{change_pct:+.2f}%")
col2.metric("52주 최고", f"{info.get('fiftyTwoWeekHigh', 0):,.0f}")
col3.metric("52주 최저", f"{info.get('fiftyTwoWeekLow', 0):,.0f}")

# 차트
fig = go.Figure(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']))
fig.update_layout(title=f"{selected} 주가 차트", xaxis_rangeslider_visible=False, template="plotly_dark")
st.plotly_chart(fig, use_container_width=True)

# 종목 정보
st.subheader("📊 종목 정보")
st.write(f"**업종:** {info.get('sector', 'N/A')} | **시가총액:** {info.get('marketCap', 0):,} | **PER:** {info.get('trailingPE', 'N/A')}")
