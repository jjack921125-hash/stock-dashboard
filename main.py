import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import plotly.graph_objects as go
import pandas as pd
import json
import os

# 1. 기본 설정 및 데이터 로드 (간결화)
st.set_page_config(page_title="주식/코인 대시보드", layout="wide")
st.title("📈 주식/코인 대시보드")

SAVE_FILE = "data_v2.json"
if "tickers" not in st.session_state:
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            st.session_state.tickers = json.load(f)
    else:
        st.session_state.tickers = {
            "코인": {"Bitcoin": "BTC", "Ethereum": "ETH", "Solana": "SOL"},
            "해외주식": {"NVIDIA": "NVDA", "Apple": "AAPL", "Tesla": "TSLA"},
            "국내주식": {"삼성전자": "005930", "SK하이닉스": "000660"}
        }

def save_data():
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.tickers, f, ensure_ascii=False, indent=2)

# 2. [검증된] 핵심 데이터 수집기
@st.cache_data(ttl=300)
def get_clean_data(symbol, category):
    try:
        if category == "국내주식":
            # 한국 주식은 fdr이 가장 깔끔함
            df = fdr.DataReader(symbol, "2024-01-01")
        else:
            # 코인과 해외주식은 성공했던 yfinance 로직 적용
            target = f"{symbol}-USD" if category == "코인" else symbol
            df = yf.download(target, period="1y", progress=False)
            
            if df.empty: return pd.DataFrame()

            # MultiIndex 평탄화 (가장 중요한 부분)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # 코인이면 환율 적용
            if category == "코인":
                fx = yf.download("USDKRW=X", period="1d", progress=False)
                if isinstance(fx.columns, pd.MultiIndex):
                    fx.columns = fx.columns.get_level_values(0)
                rate = float(fx['Close'].iloc[-1]) if not fx.empty else 1380.0
                for col in ['Open', 'High', 'Low', 'Close']:
                    df[col] = df[col] * rate
        
        return df.dropna()
    except:
        return pd.DataFrame()

# 3. 사이드바 (기능 압축)
st.sidebar.header("⚙️ 컨트롤러")
category = st.sidebar.selectbox("카테고리", list(st.session_state.tickers.keys()))
names = list(st.session_state.tickers[category].keys())
selected_name = st.sidebar.selectbox("종목 선택", names)
ticker = st.session_state.tickers[category][selected_name]

# 종목 추가/삭제
with st.sidebar.expander("➕ 종목 편집"):
    new_n = st.text_input("이름")
    new_t = st.text_input("티커")
    if st.button("추가"):
        st.session_state.tickers[category][new_n] = new_t.upper()
        save_data()
        st.rerun()
    if st.button("현재 종목 삭제"):
        if len(st.session_state.tickers[category]) > 1:
            del st.session_state.tickers[category][selected_name]
            save_data()
            st.rerun()

# 4. 메인 대시보드
with st.spinner("데이터 동기화 중..."):
    df = get_clean_data(ticker, category)

if df.empty:
    st.error("데이터를 가져오는 데 실패했습니다. 잠시 후 다시 시도해 주세요.")
else:
    # 지표 산출
    curr = float(df['Close'].iloc[-1])
    high = float(df['High'].max())
    low = float(df['Low'].min())
    prev = float(df['Close'].iloc[-2])
    chg = ((curr - prev) / prev) * 100
    mdd = ((curr / high) - 1) * 100
    
    unit = "$" if category == "해외주식" else "₩"
    
    col1, col2, col3 = st.columns(3)
    col1.metric("현재가", f"{unit}{curr:,.0f}" if unit=="₩" else f"{unit}{curr:,.2f}", f"{chg:+.2f}%")
    col2.metric("전고점 대비", f"{mdd:.2f}%", help="최고가 대비 현재 하락률")
    col3.metric("기간 최저가", f"{unit}{low:,.0f}" if unit=="₩" else f"{unit}{low:,.2f}")

    # 캔들 차트
    fig = go.Figure(data=[go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        increasing_line_color='red', decreasing_line_color='blue'
    )])
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=500)
    st.plotly_chart(fig, use_container_width=True)

    # 하락률 랭킹 테이블
    st.markdown("---")
    st.subheader(f"📊 {category} 하락률 순위")
    
    rank_list = []
    for n, t in st.session_state.tickers[category].items():
        tdf = get_clean_data(t, category)
        if not tdf.empty:
            tc = float(tdf['Close'].iloc[-1])
            th = float(tdf['High'].max())
            tmdd = ((tc / th) - 1) * 100
            rank_list.append({"종목": n, "현재가": f"{unit}{tc:,.0f}" if unit=="₩" else f"{unit}{tc:,.2f}", "하락률": f"{tmdd:.2f}%", "sort": tmdd})
    
    if rank_list:
        rdf = pd.DataFrame(rank_list).sort_values("sort")
        st.table(rdf.drop(columns="sort"))
