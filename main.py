import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import plotly.graph_objects as go
import pandas as pd
import requests
import json
import os

# 1. 영구 저장 및 데이터 로드 (기존 옵션 유지)
DB_FILE = "user_settings.json"
def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
    return {
        "코인": {"Bitcoin": "BTC", "Ethereum": "ETH", "Solana": "SOL", "XRP": "XRP", "BNB": "BNB", "Dogecoin": "DOGE"},
        "나스닥": {"NVIDIA": "NVDA", "Apple": "AAPL", "Microsoft": "MSFT", "Amazon": "AMZN", "Tesla": "TSLA"},
        "코스피": {"삼성전자": "005930", "SK하이닉스": "000660"},
        "코스닥": {"에코프로비엠": "247540"}
    }

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

if 'tickers_dict' not in st.session_state:
    st.session_state.tickers_dict = load_data()

# 2. 고난의 역사 분석 함수 (-10% 이상 필터링)
def get_hardship_history(df):
    if df.empty: return []
    df = df.copy()
    df['peak'] = df['Close'].cummax()
    
    history = []
    current_peak_date = df.index[0]
    current_peak_price = df['Close'].iloc[0]
    madi_min_price = df['Close'].iloc[0]
    madi_min_date = df.index[0]
    
    for i in range(1, len(df)):
        if df['Close'].iloc[i] > df['peak'].iloc[i-1]:
            drawdown = (madi_min_price / current_peak_price) - 1
            if drawdown <= -0.10: # 10% 이상 하락 시 기록
                history.append({
                    "고점일 (Start)": current_peak_date.strftime('%Y-%m-%d'),
                    "저점일 (Bottom)": madi_min_date.strftime('%Y-%m-%d'),
                    "고점가": f"{current_peak_price:,.2f}",
                    "저점가": f"{madi_min_price:,.2f}",
                    "하락률": f"{drawdown * 100:.2f}%",
                    "raw_mdd": drawdown
                })
            current_peak_date = df.index[i]
            current_peak_price = df['Close'].iloc[i]
            madi_min_price = current_peak_price
            madi_min_date = df.index[i]
        else:
            if df['Close'].iloc[i] < madi_min_price:
                madi_min_price = df['Close'].iloc[i]
                madi_min_date = df.index[i]
                
    final_dd = (madi_min_price / current_peak_price) - 1
    if final_dd <= -0.10:
        history.append({
            "고점일 (Start)": current_peak_date.strftime('%Y-%m-%d'),
            "저점일 (Bottom)": madi_min_date.strftime('%Y-%m-%d'),
            "고점가": f"{current_peak_price:,.2f}",
            "저점가": f"{madi_min_price:,.2f}",
            "하락률": f"{final_dd * 100:.2f}% (진행중)",
            "raw_mdd": final_dd
        })
    return sorted(history, key=lambda x: x['raw_mdd'])

# 3. 데이터 엔진 (환율, 빗썸 시세 등 기존 유지)
@st.cache_data(ttl=60)
def get_realtime_fx():
    try:
        fx = yf.download("USDKRW=X", period="1d", progress=False)
        return float(fx['Close'].iloc[-1])
    except: return 1480.85

@st.cache_data(ttl=5)
def get_korea_prices():
    try:
        res = requests.get("https://api.bithumb.com/public/ticker/ALL_KRW", timeout=5).json()
        return {k: float(v['closing_price']) for k, v in res['data'].items() if isinstance(v, dict)}
    except: return {}

@st.cache_data(ttl=300)
def fetch_data(symbol, category):
    try:
        if category in ["코스피", "코스닥"]: return fdr.DataReader(symbol, "1990-01-01").dropna()
        else:
            df = yf.download(f"{symbol}-USD" if category == "코인" else symbol, period="max", progress=False)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            return df.dropna()
    except: return pd.DataFrame()

# 4. 사이드바 UI
with st.sidebar:
    st.header("🔍 종목 조회")
    category = st.selectbox("시장 선택", list(st.session_state.tickers_dict.keys()))
    selected_name = st.selectbox("종목 선택", list(st.session_state.tickers_dict[category].keys()))
    ticker = st.session_state.tickers_dict[category][selected_name]
    
    st.divider()
    st.header("➕ 시장/종목 추가")
    new_cat = st.text_input("새 시장 이름")
    if st.button("시장 생성") and new_cat:
        st.session_state.tickers_dict[new_cat] = {}; save_data(st.session_state.tickers_dict); st.rerun()
    add_n = st.text_input("종목 별명")
    add_t = st.text_input("티커 입력")
    if st.button("종목 추가") and add_n and add_t:
        st.session_state.tickers_dict[category][add_n] = add_t; save_data(st.session_state.tickers_dict); st.rerun()

# 5. 메인 화면: 탭 시스템 적용
df = fetch_data(ticker, category)
if not df.empty:
    tab1, tab2 = st.tabs(["📊 실시간 분석 리포트", "🌋 고난의 역사 (-10% 이상)"])

    with tab1:
        fx_rate = get_realtime_fx()
        curr_p = df['Close'].iloc[-1]
        day_chg = ((curr_p / df['Close'].iloc[-2]) - 1) * 100 if len(df) > 1 else 0
        
        m1, m2, m3, m4 = st.columns(4)
        if category == "코인":
            krw_p = get_korea_prices().get(ticker, 0)
            diff = ((krw_p / (curr_p * fx_rate)) - 1) * 100 if krw_p > 0 else 0
            m1.metric("해외 ($)", f"${curr_p:,.2f}", delta=f"{day_chg:+.2f}%")
            m2.metric("국내 (₩)", f"₩{krw_p:,.0f}")
            m3.metric("차이 (%)", f"{diff:+.2f}%")
            m4.metric("환율", f"₩{fx_rate:,.1f}")
        else:
            m1.metric("현재가", f"{curr_p:,.2f}", delta=f"{day_chg:+.2f}%")
            m2.metric("역대 최고가", f"{df['Close'].max():,.2f}")
            m3.metric("환율", f"₩{fx_rate:,.1f}")
            m4.metric("현재 낙폭", f"{((curr_p/df['peak'].iloc[-1])-1)*100:.2f}%")

        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=450)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader(f"🌋 {selected_name}의 역사적 고통 구간 분석")
        st.caption("신고가를 향해 달려가는 과정에서 발생했던 '의미 있는 -10% 이상 하락' 기록입니다.")
        h_history = get_hardship_history(df)
        if h_history:
            h_df = pd.DataFrame(h_history).drop(columns=['raw_mdd'])
            st.table(h_df)
        else:
            st.info("이 종목은 상장 후 10% 이상의 하락을 겪지 않은 초우량 종목입니다.")
