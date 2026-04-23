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
# 데이터 저장 및 로드
# ───────────────────────────────────────────
SAVE_FILE = "data.json"
DEFAULT_TICKERS = {
    "S&P500": {"JPMorgan": "JPM", "Berkshire": "BRK-B", "Eli Lilly": "LLY"},
    "나스닥": {"Apple": "AAPL", "Microsoft": "MSFT", "NVIDIA": "NVDA"},
    "코스피": {"삼성전자": "005930", "SK하이닉스": "000660"},
    "코스닥": {"에코프로비엠": "247540", "HLB": "028300"},
    "코인": {"Bitcoin": "BTC", "Ethereum": "ETH", "Solana": "SOL", "XRP": "XRP"}
}

if "tickers" not in st.session_state:
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            st.session_state.tickers = json.load(f)
    else:
        st.session_state.tickers = DEFAULT_TICKERS.copy()

# ───────────────────────────────────────────
# [핵심 수정] 안정적인 데이터 추출 함수
# ───────────────────────────────────────────
@st.cache_data(ttl=300)
def get_market_data(symbol, market_type):
    try:
        if market_type == "코인":
            # 1. 코인은 USD 티커로 다운로드
            target = f"{symbol}-USD"
            data = yf.download(target, start="2023-01-01", progress=False)
            
            if data.empty: return pd.DataFrame()

            # 2. [에러 해결 포인트] pandas 표준 방식으로 MultiIndex 체크
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            # 3. 환율 데이터 가져오기 및 원화 환산
            fx = yf.download("USDKRW=X", period="1d", progress=False)
            if isinstance(fx.columns, pd.MultiIndex):
                fx.columns = fx.columns.get_level_values(0)
                
            rate = float(fx['Close'].iloc[-1])
            
            # 필요한 컬럼만 추출하여 환율 곱하기
            res_df = data[['Open', 'High', 'Low', 'Close']].copy()
            for col in res_df.columns:
                res_df[col] = res_df[col] * rate
            return res_df
        else:
            # 주식은 기존 fdr 방식 유지
            df = fdr.DataReader(symbol, "2023-01-01")
            return df
    except Exception as e:
        return pd.DataFrame()

# ───────────────────────────────────────────
# 사이드바 및 메인 로직
# ───────────────────────────────────────────
st.sidebar.title("⚙️ 설정")
market = st.sidebar.selectbox("시장 선택", list(st.session_state.tickers.keys()))
selected_name = st.sidebar.selectbox("종목 선택", list(st.session_state.tickers[market].keys()))
ticker = st.session_state.tickers[market][selected_name]

with st.spinner("데이터 로딩 중..."):
    df = get_market_data(ticker, market)

if df.empty:
    st.error(f"❌ '{selected_name}' 데이터를 불러오지 못했습니다.")
else:
    # 지표 계산 (안정성을 위해 float 변환)
    curr_price = float(df['Close'].iloc[-1])
    prev_price = float(df['Close'].iloc[-2])
    pct_change = ((curr_price - prev_price) / prev_price) * 100
    
    col1, col2, col3 = st.columns(3)
    unit = "₩" if market in ["코스피", "코스닥", "코인"] else "$"
    
    col1.metric("현재가", f"{unit}{curr_price:,.0f}" if unit == "₩" else f"{unit}{curr_price:,.2f}", f"{pct_change:+.2f}%")
    col2.metric("기간 최고가", f"{unit}{df['High'].max():,.0f}" if unit == "₩" else f"{unit}{df['High'].max():,.2f}")
    col3.metric("전고점 대비", f"{((curr_price/df['High'].max())-1)*100:.2f}%")

    # 차트 출력
    fig = go.Figure(data=[go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'],
        increasing_line_color='red', decreasing_line_color='blue'
    )])
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=600)
    st.plotly_chart(fig, use_container_width=True)
