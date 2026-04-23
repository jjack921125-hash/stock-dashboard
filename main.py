import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import plotly.graph_objects as go
import pandas as pd
import json
import os
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="2026 Global Asset Dashboard", layout="wide")
st.title("📈 2026 글로벌 자산 대시보드 (4월 업데이트)")

SAVE_FILE = "data_2026.json"

# 2. 2026년 4월 시총 기준 종목 리스트 (나스닥/S&P500 중복 제거 및 시총순)
DEFAULT_TICKERS = {
    "코인": {
        "Bitcoin": "BTC", "Ethereum": "ETH", "Solana": "SOL", "XRP": "XRP", "BNB": "BNB",
        "Dogecoin": "DOGE", "Cardano": "ADA", "Avalanche": "AVAX", "Tron": "TRX", "Chainlink": "LINK",
        "Sui": "SUI", "Aptos": "APT", "Polkadot": "DOT", "Polygon": "MATIC", "Toncoin": "TON",
        "Near": "NEAR", "Pepe": "PEPE", "Litecoin": "LTC", "Bitcoin Cash": "BCH", "Uniswap": "UNI"
    },
    "나스닥": {
        "NVIDIA": "NVDA", "Apple": "AAPL", "Microsoft": "MSFT", "Amazon": "AMZN", "Alphabet(A)": "GOOGL",
        "Meta": "META", "Tesla": "TSLA", "Broadcom": "AVGO", "ASML": "ASML", "Costco": "COST",
        "Netflix": "NFLX", "AMD": "AMD", "Adobe": "ADBE", "Qualcomm": "QCOM", "Arm": "ARM",
        "Intel": "INTC", "Applied Materials": "AMAT", "Intuitive Surgical": "ISRG", "LRCX": "LRCX", "Micron": "MU"
    },
    "S&P500": {
        "Berkshire": "BRK-B", "Eli Lilly": "LLY", "JPMorgan": "JPM", "Visa": "V", "UnitedHealth": "UNH",
        "Exxon Mobil": "XOM", "Mastercard": "MA", "Johnson&Johnson": "JNJ", "Procter&Gamble": "PG", "Home Depot": "HD",
        "AbbVie": "ABBV", "Chevron": "CVX", "Merck": "MRK", "Bank of America": "BAC", "Coca-Cola": "KO",
        "Salesforce": "CRM", "Walmart": "WMT", "Oracle": "ORCL", "Accenture": "ACN", "McDonald's": "MCD"
    },
    "코스피": {
        "삼성전자": "005930", "SK하이닉스": "000660", "LG엔솔": "373220", "삼성바이오": "207940", "현대차": "005380",
        "기아": "000270", "셀트리온": "068270", "KB금융": "105560", "NAVER": "035420", "신한지주": "055550",
        "POSCO홀딩스": "005490", "현대모비스": "012330", "삼성물산": "028260", "LG화학": "051910", "하나금융": "086790",
        "삼성SDI": "006400", "메리츠금융": "138040", "카카오": "035720", "삼성생명": "032830", "포스코퓨처엠": "003670"
    },
    "코스닥": {
        "에코프로비엠": "247540", "에코프로": "086520", "알테오젠": "196170", "HLB": "028300", "엔켐": "348370",
        "HPSP": "403870", "리노공업": "058470", "레인보우로보틱스": "277810", "셀트리온제약": "068760", "클래시스": "214150",
        "삼천당제약": "000250", "휴젤": "145020", "이오테크닉스": "039030", "솔브레인": "357780", "동진쎄미켐": "005290",
        "실리콘투": "257720", "펄어비스": "263750", "카카오게임즈": "293490", "주성엔지니어링": "036930", "파마리서치": "214450"
    }
}

if "tickers" not in st.session_state:
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            st.session_state.tickers = json.load(f)
    else:
        st.session_state.tickers = DEFAULT_TICKERS.copy()

# 3. 데이터 수집 엔진
@st.cache_data(ttl=300)
def fetch_comprehensive_data(symbol, category, interval="1일"):
    try:
        int_map = {"1시간": "1h", "4시간": "1h", "1일": "1d", "1주": "1wk", "1달": "1mo"}
        yf_int = int_map.get(interval, "1d")
        
        if category in ["코스피", "코스닥"]:
            # 국내주식 전체 기간 (fdr 사용)
            df = fdr.DataReader(symbol, "1970-01-01")
            if interval == "1주": df = df.resample('W').agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'})
            elif interval == "1달": df = df.resample('ME').agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'})
            return df.dropna()
        else:
            # 코인/해외주식 전체 기간 (yf 사용)
            target = f"{symbol}-USD" if category == "코인" else symbol
            df = yf.download(target, period="max", interval=yf_int, progress=False)
            if df.empty: return pd.DataFrame()
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            if interval == "4시간":
                df = df.resample('4h').agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'})
            return df.dropna()
    except:
        return pd.DataFrame()

# 4. 사이드바 및 환율 설정
st.sidebar.header("🧭 메뉴")
category = st.sidebar.selectbox("시장", list(st.session_state.tickers.keys()))
selected_name = st.sidebar.selectbox("종목", list(st.session_state.tickers[category].keys()))
ticker = st.session_state.tickers[category][selected_name]
time_frame = st.sidebar.select_slider("캔들", options=["1시간", "4시간", "1일", "1주", "1달"])

@st.cache_data(ttl=3600)
def get_2026_fx():
    fx = yf.download("USDKRW=X", period="1d", progress=False)
    if isinstance(fx.columns, pd.MultiIndex): fx.columns = fx.columns.get_level_values(0)
    return float(fx['Close'].iloc[-1])

# 5. 메인 레이아웃
with st.spinner("2026년 실시간 데이터 동기화 중..."):
    df = fetch_comprehensive_data(ticker, category, time_frame)

if df.empty:
    st.error("데이터 로드 실패")
else:
    curr_p = float(df['Close'].iloc[-1])
    high_all = float(df['High'].max())
    
    # 상단 정보창
    c1, c2, c3 = st.columns(3)
    if category == "코인":
        rate = get_2026_fx()
        c1.metric("현재가 (KRW)", f"₩{curr_p * rate:,.0f}")
        c2.metric("현재가 (USD)", f"${curr_p:,.2f}")
    else:
        unit = "₩" if category in ["코스피", "코스닥"] else "$"
        c1.metric("현재가", f"{unit}{curr_p:,.0f}" if unit=="₩" else f"{unit}{curr_p:,.2f}")
    
    c3.metric("역대 최고점 대비(MDD)", f"{((curr_p/high_all)-1)*100:.2f}%")

    # 캔들스틱 차트
    fig = go.Figure(data=[go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        increasing_line_color='#FF3232', decreasing_line_color='#0064FF'
    )])
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=600, title=f"{selected_name} - {time_frame} 전체 차트")
    st.plotly_chart(fig, use_container_width=True)

    # 거래량
    fig_vol = go.Figure(go.Bar(x=df.index, y=df['Volume'], marker_color='#555555'))
    fig_vol.update_layout(template="plotly_dark", height=200, margin=dict(t=0))
    st.plotly_chart(fig_vol, use_container_width=True)

    # 6. 카테고리 내 시총 상위 MDD 순위 (20개)
    st.markdown("---")
    st.subheader(f"📊 2026년 4월 {category} 시총 상위 MDD 현황")
    
    rank_rows = []
    for n, t in st.session_state.tickers[category].items():
        # 순위표는 '1일' 기준으로 고정하여 연산 속도 확보
        rdf = fetch_comprehensive_data(t, category, "1일")
        if not rdf.empty:
            cp = float(rdf['Close'].iloc[-1])
            hp = float(rdf['High'].max())
            mdd = ((cp / hp) - 1) * 100
            rank_rows.append({"종목명": n, "하락률": f"{mdd:.2f}%", "_val": mdd})
    
    if rank_rows:
        res_df = pd.DataFrame(rank_rows).sort_values("_val")
        st.dataframe(res_df.drop(columns="_val"), use_container_width=True, hide_index=True)
