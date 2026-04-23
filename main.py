import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

st.title("코인 데이터 연결 테스트")

ticker = "BTC-USD" # 비트코인 달러 티커
data = yf.download(ticker, start="2024-01-01", progress=False)

if not data.empty:
    # 1. 멀티인덱스 강제 평탄화 (최신 yfinance 대응)
    if isinstance(data.columns, yf.pandas_dm.pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    st.success(f"{ticker} 데이터를 성공적으로 불러왔습니다!")
    
    # 2. 현재가 지표
    curr_price = float(data['Close'].iloc[-1])
    st.metric("현재가 (USD)", f"${curr_price:,.2f}")
    
    # 3. 테스트 차트
    fig = go.Figure(data=[go.Candlestick(
        x=data.index,
        open=data['Open'], high=data['High'],
        low=data['Low'], close=data['Close']
    )])
    st.plotly_chart(fig)
    
    # 4. 실제 데이터 구조 확인
    st.write("데이터프레임 상단 5행:")
    st.dataframe(data.head())
else:
    st.error("데이터를 불러오지 못했습니다. 네트워크나 라이브러리 버전을 확인하세요.")
