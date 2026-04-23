import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import plotly.graph_objects as go
import pandas as pd
import requests
import time

# 1. 페이지 설정
st.set_page_config(page_title="2026 Upbit-Linked Terminal", layout="wide")
st.title("📈 2026 업비트 연동 글로벌 터미널")

# 2. 2026년 4월 시총 순위 고정 리스트 (시총 상위 순)
DEFAULT_TICKERS = {
    "코인": {
        "Bitcoin": "BTC", "Ethereum": "ETH", "Solana": "SOL", "XRP": "XRP", "BNB": "BNB",
        "Dogecoin": "DOGE", "Cardano": "ADA", "Avalanche": "AVAX", "Sui": "SUI", "Tron": "TRX",
        "Toncoin": "TON", "Chainlink": "LINK", "Pepe": "PEPE", "Aptos": "APT", "Near": "NEAR",
        "Polkadot": "DOT", "Litecoin": "LTC", "Bitcoin Cash": "BCH", "Uniswap": "UNI", "Polygon": "MATIC"
    },
    "나스닥": {
        "NVIDIA": "NVDA", "Apple": "AAPL", "Microsoft": "MSFT", "Amazon": "AMZN", "Alphabet(A)": "GOOGL",
        "Meta": "META", "Tesla": "TSLA", "Broadcom": "AVGO", "ASML": "ASML", "Costco": "COST"
    },
    "코스피": {
        "삼성전자": "005930", "SK하이닉스": "000660", "LG엔솔": "373220", "삼성바이오": "207940", "현대차": "005380"
    }
}

# 3. 데이터 엔진: 업비트 실시간 시세 호출
@st.cache_data(ttl=10) # 김프는 변동성이 크므로 짧은 캐시 적용
def get_upbit_prices():
    try:
        # 모든 코인의 마켓 코드를 한 번에 가져오기 위한 준비
        markets = [f"KRW-{t}" for t in DEFAULT_TICKERS["코인"].values()]
        url = f"https://api.upbit.com/v1/ticker?markets={','.join(markets)}"
        res = requests.get(url).json()
        # { 'BTC': 105000000, ... } 형태의 딕셔너리로 변환
        return {item['market'].split('-')[1]: item['trade_price'] for item in res}
    except:
        return {}

@st.cache_data(ttl=300)
def fetch_stock_data(symbol, category, interval="1D"):
    int_map = {"1H": "1h", "4H": "1h", "1D": "1d", "1W": "1wk", "1M": "1mo"}
    yf_int = int_map.get(interval, "1d")
    try:
        if category in ["코스피", "코스닥"]:
            df = fdr.DataReader(symbol, "1980-01-01")
        else:
            target = f"{symbol}-USD" if category == "코인" else symbol
            df = yf.download(target, period="max", interval=yf_int, progress=False)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        return df.dropna()
    except:
        return pd.DataFrame()

# 4. 사이드바 및 환율
fx_rate = yf.download("USDKRW=X", period="1d", progress=False).iloc[-1]['Close']

with st.sidebar:
    category = st.selectbox("시장", list(DEFAULT_TICKERS.keys()))
    selected_name = st.selectbox("종목", list(DEFAULT_TICKERS[category].keys()))
    ticker = DEFAULT_TICKERS[category][selected_name]

# 5. 메인 레이아웃 (차트 우상단 캔들 선택)
col_left, col_right = st.columns([8, 2])
with col_right:
    tf = st.pills("Timeframe", ["1H", "4H", "1D", "1W", "1M"], default="1D")

df = fetch_stock_data(ticker, category, tf)

if not df.empty:
    curr_usd = float(df['Close'].iloc[-1])
    high_all = float(df['High'].max())
    
    m1, m2, m3, m4 = st.columns(4)
    if category == "코인":
        upbit_data = get_upbit_prices()
        up_p = upbit_data.get(ticker, 0)
        kimpre = ((up_p / (curr_usd * fx_rate)) - 1) * 100 if up_p > 0 else 0
        
        m1.metric("업비트 실시간 (KRW)", f"₩{up_p:,.0f}")
        m2.metric("바이낸스 기준 (USD)", f"${curr_usd:,.2f}")
        m3.metric("실시간 김치프리미엄", f"{kimpre:+.2f}%")
    else:
        unit = "₩" if category == "코스피" else "$"
        m1.metric("현재가", f"{unit}{curr_usd:,.0f}" if unit=="₩" else f"{unit}{curr_usd:,.2f}")
        m2.metric("역대 최고가", f"{unit}{high_all:,.0f}" if unit=="₩" else f"{unit}{high_all:,.2f}")
    
    m4.metric("역대 MDD", f"{((curr_usd/high_all)-1)*100:.2f}%")

    # 차트 출력
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=500)
    st.plotly_chart(fig, use_container_width=True)

# 6. 시총 순위별 현황 테이블 (김치프리미엄 포함)
st.divider()
st.subheader(f"📊 {category} 시가총액 순위별 현황 (2026.04)")

summary = []
upbit_all = get_upbit_prices() if category == "코인" else {}

for i, (name, tck) in enumerate(DEFAULT_TICKERS[category].items()):
    sdf = fetch_stock_data(tck, category, "1D")
    if not sdf.empty:
        c_p = float(sdf['Close'].iloc[-1])
        h_p = float(sdf['High'].max())
        mdd = ((c_p / h_p) - 1) * 100
        
        item = {"순위": i+1, "종목명": name, "하락률(MDD)": f"{mdd:.2f}%"}
        
        if category == "코인":
            u_p = upbit_all.get(tck, 0)
            kp = ((u_p / (c_p * fx_rate)) -
