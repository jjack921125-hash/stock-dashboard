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
# 데이터 로드 (기존 유지)
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
# [핵심] 안정적인 데이터 추출 함수
# ───────────────────────────────────────────
def get_clean_df(ticker_symbol):
    """yfinance의 Multi-index 구조를 완벽하게 평탄화하여 DF 반환"""
    data = yf.download(ticker_symbol, start="2023-01-01", progress=False)
    
    if data.empty:
        return pd.DataFrame()
    
    # 1. Multi-index 컬럼일 경우 처리 (가장 중요한 부분)
    if isinstance(data.columns, pd.MultiIndex):
        # 'Price' 레벨이 있는 경우 해당 레벨만 추출
        if 'Price' in data.columns.names:
            data = data.xs(ticker_symbol, axis=1, level=1)
        else:
            data.columns = data.columns.get_level_values(0)
            
    # 2. 중복 컬럼 제거 및 필요한 컬럼만 추출
    data = data[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
    
    # 3. 누락된 데이터 제거
    data = data.dropna()
    
    return data

@st.cache_data(ttl=300)
def get_market_data(symbol, market_type):
    try:
        if market_type == "코인":
            # 코인은 USD로 가져와서 계산하는 것이 가장 안정적
            df = get_clean_df(f"{symbol}-USD")
            # 환율 적용 (최신 환율 근사치 적용)
            fx_data = yf.download("USDKRW=X", period="1d", progress=False)
            if not fx_data.empty:
                # 환율 데이터 구조 처리
                if isinstance(fx_data.columns, pd.MultiIndex):
                    rate = float(fx_data['Close'].iloc[-1].iloc[0])
                else:
                    rate = float(fx_data['Close'].iloc[-1])
                
                for col in ['Open', 'High', 'Low', 'Close']:
                    df[col] = df[col] * rate
            return df
        else:
            # 주식은 fdr이 여전히 한국 시장에선 우수함
            df = fdr.DataReader(symbol, "2023-01-01")
            return df
    except:
        return pd.DataFrame()

# ───────────────────────────────────────────
# 사이드바 및 메인 로직
# ───────────────────────────────────────────
st.sidebar.title("⚙️ 설정")
market = st.sidebar.selectbox("시장 선택", list(st.session_state.tickers.keys()))
selected_name = st.sidebar.selectbox("종목 선택", list(st.session_state.tickers[market].keys()))
ticker = st.session_state.tickers[market][selected_name]

with st.spinner("데이터를 실시간으로 불러오는 중..."):
    df = get_market_data(ticker, market)

if df is None or df.empty:
    st.error(f"❌ '{selected_name}({ticker})' 데이터를 불러오는데 실패했습니다.")
    st.warning("라이브러리 응답 지연일 수 있습니다. '시장 선택'을 다시 한 번 클릭해 보세요.")
else:
    # 지표 계산
    curr_price = float(df['Close'].iloc[-1])
    prev_price = float(df['Close'].iloc[-2])
    change = curr_price - prev_price
    pct_change = (change / prev_price) * 100
    
    # 상단 지표
    col1, col2, col3 = st.columns(3)
    unit = "₩" if market in ["코스피", "코스닥", "코인"] else "$"
    col1.metric("현재가", f"{unit}{curr_price:,.0f}" if unit == "₩" else f"{unit}{curr_p:,.2f}", f"{pct_change:+.2f}%")
    col2.metric("기간 최고가", f"{unit}{df['High'].max():,.0f}" if unit == "₩" else f"{unit}{df['High'].max():,.2f}")
    col3.metric("최고점 대비 하락률", f"{( (curr_price / df['High'].max()) - 1) * 100:.2f}%")

    # 차트
    fig = go.Figure(data=[go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'],
        increasing_line_color='red', decreasing_line_color='blue'
    )])
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=600, title=f"{selected_name} 차트 (일봉)")
    st.plotly_chart(fig, use_container_width=True)

    # 데이터 테이블
    with st.expander("상세 데이터 보기"):
        st.dataframe(df.sort_index(ascending=False), use_container_width=True)
