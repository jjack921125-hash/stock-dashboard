import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import plotly.graph_objects as go
import pandas as pd
import json
import os

st.set_page_config(page_title="주식/코인 대시보드", page_icon="📈", layout="wide")
st.title("📈 주식/코인 대시보드")

# 1. 데이터 저장 로직 (심플하게 유지)
SAVE_FILE = "data.json"
DEFAULT_TICKERS = {
    "코인": {"Bitcoin": "BTC", "Ethereum": "ETH", "Solana": "SOL"},
    "나스닥": {"NVIDIA": "NVDA", "Apple": "AAPL"},
    "코스피": {"삼성전자": "005930"}
}

if "tickers" not in st.session_state:
    st.session_state.tickers = DEFAULT_TICKERS.copy()

# 2. [강력한 데이터 수집기] - 이 부분이 핵심입니다.
@st.cache_data(ttl=300)
def get_any_data(symbol, market_type):
    try:
        if market_type == "코인":
            # 코인은 USD로 가져와야 가장 빠르고 정확함
            target = f"{symbol}-USD"
            df = yf.download(target, period="1y", progress=False)
            
            if df.empty: return pd.DataFrame()

            # [핵심] MultiIndex 층을 완전히 깨버리고 단일 층으로 강제 변환
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # 환율 계산 (최신 환율 정보 가져오기)
            fx = yf.download("USDKRW=X", period="1d", progress=False)
            if isinstance(fx.columns, pd.MultiIndex):
                fx.columns = fx.columns.get_level_values(0)
            
            # 환율이 있으면 곱하고, 없으면 대략적인 1380원 적용
            rate = float(fx['Close'].iloc[-1]) if not fx.empty else 1380.0
            
            # 필요한 가격 데이터만 복사해서 환율 곱하기
            final_df = df[['Open', 'High', 'Low', 'Close']].copy()
            return final_df * rate
        else:
            # 주식은 fdr 사용
            return fdr.DataReader(symbol, "2024-01-01")
    except:
        return pd.DataFrame()

# 3. 사이드바 구성
st.sidebar.title("⚙️ 설정")
market = st.sidebar.selectbox("시장 선택", list(st.session_state.tickers.keys()))
selected_name = st.sidebar.selectbox("종목 선택", list(st.session_state.tickers[market].keys()))
ticker = st.session_state.tickers[market][selected_name]

# 4. 메인 화면 출력
with st.spinner("데이터를 낚아채는 중..."):
    df = get_any_data(ticker, market)

if df.empty:
    st.error(f"❌ '{selected_name}' 데이터를 불러오지 못했습니다. 잠시 후 '시장 선택'을 다시 눌러주세요.")
else:
    # 상단 지표
    curr_p = float(df['Close'].iloc[-1])
    high_p = float(df['High'].max())
    
    col1, col2 = st.columns(2)
    unit = "₩" if market in ["코스피", "코인"] else "$"
    col1.metric("현재가", f"{unit}{curr_p:,.0f}" if unit == "₩" else f"{unit}{curr_p:,.2f}")
    col2.metric("최고점 대비", f"{((curr_p/high_p)-1)*100:.2f}%")

    # 캔들 차트
    fig = go.Figure(data=[go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        increasing_line_color='red', decreasing_line_color='blue'
    )])
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=500)
    st.plotly_chart(fig, use_container_width=True)
