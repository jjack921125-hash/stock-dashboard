import streamlit as st
import FinanceDataReader as fdr
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import json
import os
from datetime import datetime

st.set_page_config(page_title="주식/코인 대시보드", page_icon="📈", layout="wide")
st.title("📈 주식/코인 대시보드")

# ───────────────────────────────────────────
# 1. 데이터 저장 및 로드
# ───────────────────────────────────────────
SAVE_FILE = "data.json"

def load_data():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_TICKERS.copy()

def save_data(data):
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

DEFAULT_TICKERS = {
    "코인": {"Bitcoin": "BTC", "Ethereum": "ETH", "Solana": "SOL", "XRP": "XRP"},
    "나스닥": {"Apple": "AAPL", "Microsoft": "MSFT", "NVIDIA": "NVDA", "Tesla": "TSLA"},
    "S&P500": {"JPMorgan": "JPM", "Visa": "V", "ExxonMobil": "XOM"},
    "코스피": {"삼성전자": "005930", "SK하이닉스": "000660", "현대차": "005380"},
    "코스닥": {"에코프로비엠": "247540", "HLB": "028300"}
}

if "tickers" not in st.session_state:
    st.session_state.tickers = load_data()

# ───────────────────────────────────────────
# 2. [검증된] 데이터 수집 함수
# ───────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_data(symbol, market_name):
    try:
        if market_name == "코인":
            # 아까 성공했던 코인 전용 로직
            target = f"{symbol}-USD"
            df = yf.download(target, period="1y", progress=False)
            if df.empty: return pd.DataFrame()
            
            # Multi-index 평탄화 (성공의 핵심)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # 환율 적용
            fx = yf.download("USDKRW=X", period="1d", progress=False)
            if not fx.empty:
                if isinstance(fx.columns, pd.MultiIndex):
                    fx.columns = fx.columns.get_level_values(0)
                rate = float(fx['Close'].iloc[-1])
            else:
                rate = 1380.0
                
            res = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
            for col in ['Open', 'High', 'Low', 'Close']:
                res[col] = res[col] * rate
            return res
        else:
            # 주식 데이터 (fdr 또는 yf 선택적 사용)
            if market_name in ["나스닥", "S&P500"]:
                df = yf.download(symbol, period="1y", progress=False)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
            else:
                df = fdr.DataReader(symbol, "2023-01-01")
            return df
    except:
        return pd.DataFrame()

# ───────────────────────────────────────────
# 3. 사이드바 및 UI 설정
# ───────────────────────────────────────────
st.sidebar.title("⚙️ 설정")
market = st.sidebar.selectbox("시장 선택", list(st.session_state.tickers.keys()))
ticker_dict = st.session_state.tickers[market]
selected_name = st.sidebar.selectbox("종목 선택", list(ticker_dict.keys()))
ticker = ticker_dict[selected_name]

# 종목 관리 기능
with st.sidebar.expander("➕ 종목 추가/삭제"):
    new_n = st.text_input("이름 (예: 도지코인)")
    new_t = st.text_input("티커 (예: DOGE)")
    if st.button("추가"):
        if new_n and new_t:
            st.session_state.tickers[market][new_n] = new_t.strip().upper()
            save_data(st.session_state.tickers)
            st.rerun()
    
    if st.button("🗑️ 현재 종목 삭제"):
        if len(st.session_state.tickers[market]) > 1:
            del st.session_state.tickers[market][selected_name]
            save_data(st.session_state.tickers)
            st.rerun()
        else:
            st.warning("최소 한 종목은 남겨두어야 합니다.")

# ───────────────────────────────────────────
# 4. 메인 대시보드 출력
# ───────────────────────────────────────────
with st.spinner("실시간 데이터를 수집 중입니다..."):
    df = fetch_data(ticker, market)

if df is None or df.empty:
    st.error(f"❌ '{selected_name}' 데이터를 불러올 수 없습니다.")
    st.info("야후 파이낸스 서버 응답이 지연될 수 있습니다. 잠시 후 '시장 선택'을 다시 눌러주세요.")
else:
    # 상단 지표
    curr = float(df['Close'].iloc[-1])
    prev = float(df['Close'].iloc[-2]) if len(df) > 1 else curr
    high = float(df['High'].max())
    chg_pct = ((curr - prev) / prev) * 100
    
    unit = "₩" if market in ["코스피", "코스닥", "코인"] else "$"
    
    c1, c2, c3 = st.columns(3)
    c1.metric("현재가", f"{unit}{curr:,.0f}" if unit=="₩" else f"{unit}{curr:,.2f}", f"{chg_pct:+.2f}%")
    c2.metric("기간 최고가", f"{unit}{high:,.0f}" if unit=="₩" else f"{unit}{high:,.2f}")
    c3.metric("최고점 대비 하락률", f"{((curr/high)-1)*100:.2f}%")

    # 차트
    fig = go.Figure(data=[go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        increasing_line_color='red', decreasing_line_color='blue'
    )])
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=500, title=f"{selected_name} ({ticker}) 차트")
    st.plotly_chart(fig, use_container_width=True)

    # 하단 종목 리스트 테이블
    st.markdown("---")
    st.subheader(f"📊 {market} 종목 요약")
    
    summary_data = []
    for name, tck in ticker_dict.items():
        # 요약 테이블용은 캐시된 데이터를 사용하므로 속도가 빠름
        t_df = fetch_data(tck, market)
        if not t_df.empty:
            c_p = t_df['Close'].iloc[-1]
            h_p = t_df['High'].max()
            dd = ((c_p / h_p) - 1) * 100
            summary_data.append({
                "종목명": name,
                "현재가": f"{unit}{c_p:,.0f}" if unit=="₩" else f"{unit}{c_p:,.2f}",
                "하락률": f"{dd:.2f}%",
                "_val": dd
            })
    
    if summary_data:
        st.table(pd.DataFrame(summary_data).sort_values("_val").drop(columns=["_val"]))
