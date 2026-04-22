import streamlit as st
import FinanceDataReader as fdr
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import json
import os
from datetime import datetime, timedelta

st.set_page_config(page_title="통합 금융 대시보드", page_icon="📈", layout="wide")

# ───────────────────────────────────────────
# 1. 초기 설정
# ───────────────────────────────────────────
SAVE_FILE = "data.json"

# 코인 티커 형식을 yfinance에 맞게 변경 (BTC/USDT -> BTC-USD)
DEFAULT_TICKERS = {
    "S&P500": {"JPMorgan": "JPM", "Visa": "V", "ExxonMobil": "XOM"},
    "나스닥": {"Apple": "AAPL", "Microsoft": "MSFT", "NVIDIA": "NVDA"},
    "코스피": {"삼성전자": "005930", "SK하이닉스": "000660"},
    "코인": {"Bitcoin": "BTC-USD", "Ethereum": "ETH-USD", "Solana": "SOL-USD", "XRP": "XRP-USD"},
}

if "tickers" not in st.session_state:
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            st.session_state.tickers = json.load(f)
    else:
        st.session_state.tickers = DEFAULT_TICKERS.copy()

# ───────────────────────────────────────────
# 2. 데이터 수집 함수 (우회 전략 반영)
# ───────────────────────────────────────────

@st.cache_data(ttl=300)
def get_combined_data(ticker, interval_label, market_type):
    try:
        # 1. 코인인 경우 (yfinance 사용 - 바이낸스 차단 우회)
        if "코인" in market_type:
            int_map = {"1분":"1m", "5분":"5m", "15분":"15m", "1시간":"1h", "1일":"1d"}
            # 코인은 24시간 돌아가므로 period를 넉넉히 잡음
            df = yf.download(ticker, period="7d" if "분" in interval_label else "max", 
                             interval=int_map.get(interval_label, "1d"), progress=False)
        
        # 2. 주식 분봉/시간봉 (yfinance)
        elif "분" in interval_label or "시간" in interval_label:
            yf_ticker = f"{ticker}.KS" if market_type == "코스피" else f"{ticker}.KQ" if market_type == "코스닥" else ticker
            int_map = {"1분":"1m", "5분":"5m", "15분":"15m", "1시간":"1h"}
            df = yf.download(yf_ticker, period="5d", interval=int_map.get(interval_label, "5m"), progress=False)
        
        # 3. 주식 일봉 이상 (FinanceDataReader)
        else:
            df = fdr.DataReader(ticker, '2020-01-01')
            
        if df.empty:
            return pd.DataFrame()
            
        # 데이터프레임 컬럼이 MultiIndex로 오는 경우 처리 (yfinance 최신버전 대응)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        return df
    except Exception as e:
        st.error(f"데이터 로드 에러: {e}")
        return pd.DataFrame()

# ───────────────────────────────────────────
# 3. UI 및 출력
# ───────────────────────────────────────────
st.sidebar.title("⚙️ 설정")
market = st.sidebar.selectbox("시장 선택", list(st.session_state.tickers.keys()))
ticker_dict = st.session_state.tickers[market]
selected_name = st.sidebar.selectbox("종목 선택", list(ticker_dict.keys()))
selected_ticker = ticker_dict[selected_name]

candle_op = ["1분", "5분", "15분", "1시간", "1일"]
interval = st.sidebar.selectbox("캔들 단위", candle_op, index=4)

df = get_combined_data(selected_ticker, interval, market)

if not df.empty:
    st.title(f"📈 {selected_name} ({selected_ticker})")
    
    # 지표 계산
    curr_price = float(df['Close'].iloc[-1])
    prev_price = float(df['Close'].iloc[-2]) if len(df) > 1 else curr_price
    change_pct = (curr_price - prev_price) / prev_price * 100
    
    c1, c2, c3 = st.columns(3)
    c1.metric("현재가", f"{curr_price:,.2f}", f"{change_pct:+.2f}%")
    c2.metric("기간 최고가", f"{df['High'].max():,.2f}")
    c3.metric("기간 최저가", f"{df['Low'].min():,.2f}")

    # 차트
    fig = go.Figure(data=[go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        increasing_line_color='red', decreasing_line_color='blue'
    )])
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=500)
    st.plotly_chart(fig, use_container_width=True)

    # 하락률(Drawdown) 섹션 - 에러 방지 로직 포함
    st.markdown("---")
    st.subheader("📉 전고점 대비 하락률 (Drawdown)")
    all_time_high = df['High'].max()
    dd = (curr_price - all_time_high) / all_time_high * 100
    st.write(f"현재 선택된 기간 내 최고점({all_time_high:,.2f}) 대비 **{dd:.2f}%** 상태입니다.")

else:
    st.error("데이터를 가져오지 못했습니다. 시장이나 티커 설정을 확인해주세요.")
    st.info("💡 팁: 코인의 경우 BTC-USD 처럼 하이픈(-) 형식을 사용해 보세요.")
