import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import plotly.graph_objects as go
import pandas as pd
import requests
import json
import os

# 1. 영구 저장 로직
DB_FILE = "user_settings.json"
def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
    return {
        "코인": {"Bitcoin": "BTC", "Ethereum": "ETH", "Solana": "SOL"},
        "나스닥": {"NVIDIA": "NVDA", "Apple": "AAPL", "Tesla": "TSLA"},
        "코스피": {"삼성전자": "005930"}
    }

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

if 'tickers_dict' not in st.session_state:
    st.session_state.tickers_dict = load_data()

# 2. 마디별 MDD 계산 함수 (핵심 분석 로직)
def get_drawdown_cycles(df):
    if df.empty: return []
    df = df.copy()
    df['peak'] = df['Close'].cummax()
    df['is_new_high'] = df['Close'] >= df['peak']
    
    cycles = []
    current_cycle_min_drawdown = 0
    peak_price = df['Close'].iloc[0]
    peak_date = df.index[0]
    
    for i in range(1, len(df)):
        if df['is_new_high'].iloc[i]:
            if current_cycle_min_drawdown < 0:
                cycles.append({
                    "신고가 날짜": peak_date.strftime('%Y-%m-%d'),
                    "당시 가격": f"{peak_price:,.2f}",
                    "신고가 경신 전 최대 하락률": f"{current_cycle_min_drawdown * 100:.2f}%",
                    "raw_mdd": current_cycle_min_drawdown
                })
            peak_price = df['Close'].iloc[i]
            peak_date = df.index[i]
            current_cycle_min_drawdown = 0
        else:
            drawdown = (df['Close'].iloc[i] / peak_price) - 1
            if drawdown < current_cycle_min_drawdown:
                current_cycle_min_drawdown = drawdown
    
    # 현재 마디 추가
    cycles.append({
        "신고가 날짜": peak_date.strftime('%Y-%m-%d'),
        "당시 가격": f"{peak_price:,.2f}",
        "신고가 경신 전 최대 하락률": f"{current_cycle_min_drawdown * 100:.2f}% (현재 진행중)",
        "raw_mdd": current_cycle_min_drawdown
    })
    return sorted(cycles, key=lambda x: x['raw_mdd'])

# 3. 데이터 로드 엔진
@st.cache_data(ttl=60)
def get_realtime_fx():
    try:
        fx = yf.download("USDKRW=X", period="1d", progress=False)
        return float(fx['Close'].iloc[-1])
    except: return 1480.85

@st.cache_data(ttl=300)
def fetch_data(symbol, category):
    try:
        if category in ["코스피", "코스닥"]: return fdr.DataReader(symbol, "1990-01-01").dropna()
        else:
            df = yf.download(f"{symbol}-USD" if category == "코인" else symbol, period="max", progress=False)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            return df.dropna()
    except: return pd.DataFrame()

# 4. 사이드바 (조회 및 추가 메뉴)
with st.sidebar:
    st.header("🔍 종목 조회")
    category = st.selectbox("시장 선택", list(st.session_state.tickers_dict.keys()))
    selected_name = st.selectbox("종목 선택", list(st.session_state.tickers_dict[category].keys()))
    ticker = st.session_state.tickers_dict[category][selected_name]
    
    st.divider()
    st.header("➕ 관리 메뉴")
    new_cat = st.text_input("새 시장 생성")
    if st.button("시장 추가"):
        if new_cat: st.session_state.tickers_dict[new_cat] = {}; save_data(st.session_state.tickers_dict); st.rerun()
    
    add_n = st.text_input("종목 별명")
    add_t = st.text_input("티커 입력")
    if st.button("종목 추가"):
        if add_n and add_t: st.session_state.tickers_dict[category][add_n] = add_t; save_data(st.session_state.tickers_dict); st.rerun()

# 5. 메인 탭 구성
df = fetch_data(ticker, category)
if not df.empty:
    tab1, tab2 = st.tabs(["📊 실시간 분석", "🌋 고난의 역사"])

    with tab1:
        fx_rate = get_realtime_fx()
        curr_p = df['Close'].iloc[-1]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("현재가", f"{curr_p:,.2f}")
        m2.metric("역대 최고가", f"{df['Close'].max():,.2f}")
        m3.metric("현재 환율", f"₩{fx_rate:,.1f}")
        m4.metric("현재 낙폭", f"{((curr_p/df['Close'].max())-1)*100:.2f}%")
        
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=500)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader(f"🌋 {selected_name}의 고난의 역사 (마디별 하락 분석)")
        st.write("이 데이터는 과거 신고가를 경신하는 과정에서 투자자들이 견뎌내야 했던 **최악의 순간들**을 보여줍니다.")
        
        cycle_data = get_drawdown_cycles(df)
        if cycle_data:
            cycle_df = pd.DataFrame(cycle_data).drop(columns=['raw_mdd'])
            st.table(cycle_df)
            
            worst = cycle_data[0]
            st.error(f"⚠️ 가장 고통스러웠던 순간: {worst['신고가 날짜']} 고점 이후 **{worst['신고가 경신 전 최대 하락률']}** 폭락")
