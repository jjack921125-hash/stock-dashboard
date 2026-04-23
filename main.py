import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import plotly.graph_objects as go
import pandas as pd
import requests

# 1. 페이지 설정
st.set_page_config(page_title="2026 Global Terminal", layout="wide")
st.title("📈 2026 글로벌 자산 터미널 (CoinGecko 시세 연동)")

# 2. 2026년 4월 시총 순위 데이터 (리스트 순서 자체가 시총순)
# 코인게코 연동을 위해 ID값(api_id)을 추가했습니다.
DEFAULT_TICKERS = {
    "코인": {
        "Bitcoin": {"ticker": "BTC", "id": "bitcoin"},
        "Ethereum": {"ticker": "ETH", "id": "ethereum"},
        "Solana": {"ticker": "SOL", "id": "solana"},
        "XRP": {"ticker": "XRP", "id": "ripple"},
        "BNB": {"ticker": "BNB", "id": "binancecoin"},
        "Dogecoin": {"ticker": "DOGE", "id": "dogecoin"},
        "Cardano": {"ticker": "ADA", "id": "cardano"},
        "Avalanche": {"ticker": "AVAX", "id": "avalanche-2"},
        "Sui": {"ticker": "SUI", "id": "sui"},
        "Tron": {"ticker": "TRX", "id": "tron"},
        "Toncoin": {"ticker": "TON", "id": "the-open-network"},
        "Chainlink": {"ticker": "LINK", "id": "chainlink"},
        "Pepe": {"ticker": "PEPE", "id": "pepe"},
        "Aptos": {"ticker": "APT", "id": "aptos"},
        "Near": {"ticker": "NEAR", "id": "near"},
        "Polkadot": {"ticker": "DOT", "id": "polkadot"},
        "Litecoin": {"ticker": "LTC", "id": "litecoin"},
        "Bitcoin Cash": {"ticker": "BCH", "id": "bitcoin-cash"},
        "Uniswap": {"ticker": "UNI", "id": "uniswap"},
        "Polygon": {"ticker": "MATIC", "id": "matic-network"}
    },
    "나스닥": {
        "NVIDIA": "NVDA", "Apple": "AAPL", "Microsoft": "MSFT", "Amazon": "AMZN", "Alphabet(A)": "GOOGL",
        "Meta": "META", "Tesla": "TSLA", "Broadcom": "AVGO", "ASML": "ASML", "Costco": "COST"
    },
    "S&P500": {
        "Berkshire": "BRK-B", "Eli Lilly": "LLY", "JPMorgan": "JPM", "Visa": "V", "UnitedHealth": "UNH"
    },
    "코스피": {
        "삼성전자": "005930", "SK하이닉스": "000660", "LG엔솔": "373220", "삼성바이오": "207940", "현대차": "005380"
    },
    "코스닥": {
        "에코프로비엠": "247540", "알테오젠": "196170", "에코프로": "086520", "HLB": "028300", "엔켐": "348370"
    }
}

# 3. 데이터 엔진: 코인게코 실시간 KRW 가격 호출
@st.cache_data(ttl=30)
def get_korea_crypto_prices():
    try:
        # 코인 카테고리의 모든 ID 추출
        ids = [val["id"] for val in DEFAULT_TICKERS["코인"].values()]
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={','.join(ids)}&vs_currencies=krw"
        res = requests.get(url, timeout=10).json()
        # { 'bitcoin': {'krw': 105000000}, ... } -> { 'BTC': 105000000 } 형태로 변환
        price_map = {}
        for name, info in DEFAULT_TICKERS["코인"].items():
            c_id = info["id"]
            if c_id in res:
                price_map[info["ticker"]] = float(res[c_id]["krw"])
        return price_map
    except:
        return {}

@st.cache_data(ttl=300)
def fetch_data(symbol, category, interval="1D"):
    int_map = {"1H": "1h", "4H": "1h", "1D": "1d", "1W": "1wk", "1M": "1mo"}
    yf_int = int_map.get(interval, "1d")
    try:
        if category in ["코스피", "코스닥"]:
            return fdr.DataReader(symbol, "1980-01-01").dropna()
        else:
            # 코인의 경우 딕셔너리에서 티커만 추출
            tck = symbol["ticker"] if isinstance(symbol, dict) else symbol
            target = f"{tck}-USD" if category == "코인" else tck
            df = yf.download(target, period="max", interval=yf_int, progress=False)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            return df.dropna()
    except: return pd.DataFrame()

# 4. 환율 및 사이드바
fx_rate = 1385.0
try:
    fx = yf.download("USDKRW=X", period="1d", progress=False)
    if not fx.empty:
        if isinstance(fx.columns, pd.MultiIndex): fx.columns = fx.columns.get_level_values(0)
        fx_rate = float(fx['Close'].iloc[-1])
except: pass

with st.sidebar:
    category = st.selectbox("시장", list(DEFAULT_TICKERS.keys()))
    selected_name = st.selectbox("종목", list(DEFAULT_TICKERS[category].keys()))
    ticker_data = DEFAULT_TICKERS[category][selected_name]

# 5. 차트 섹션
c_main, c_tool = st.columns([8, 2])
with c_tool:
    tf = st.pills("Interval", ["1H", "4H", "1D", "1W", "1M"], default="1D")

df = fetch_data(ticker_data, category, tf)

if not df.empty:
    c_p = float(df['Close'].iloc[-1])
    h_p = float(df['High'].max())
    m1, m2, m3, m4 = st.columns(4)
    
    if category == "코인":
        korea_prices = get_korea_crypto_prices()
        tck_only = ticker_data["ticker"]
        krw_p = korea_prices.get(tck_only, 0)
        kp = ((krw_p / (c_p * fx_rate)) - 1) * 100 if krw_p > 0 else 0
        
        m1.metric("국내 평균 (KRW)", f"₩{krw_p:,.0f}")
        m2.metric("해외 시세 (USD)", f"${c_p:,.2f}")
        m3.metric("김치프리미엄", f"{kp:+.2f}%")
    else:
        unit = "₩" if category in ["코스피", "코스닥"] else "$"
        m1.metric("현재가", f"{unit}{c_p:,.0f}" if unit=="₩" else f"{unit}{c_p:,.2f}")
        m2.metric("역대 최고가", f"{unit}{h_p:,.0f}" if unit=="₩" else f"{unit}{h_p:,.2f}")
        m3.metric("실시간 환율", f"₩{fx_rate:,.1f}")
        
    m4.metric("역대 MDD", f"{((c_p/h_p)-1)*100:.2f}%")

    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=450, margin=dict(t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)

# 6. 테이블 섹션 (코인: 시총순 / 주식: 하락률순)
st.divider()
st.subheader(f"📊 {category} 상세 리포트 ({'시총순' if category=='코인' else '하락률순'})")

summary = []
korea_all = get_korea_crypto_prices() if category == "코인" else {}

for i, (name, tck_info) in enumerate(DEFAULT_TICKERS[category].items()):
    sdf = fetch_data(tck_info, category, "1D")
    if not sdf.empty:
        c = float(sdf['Close'].iloc[-1])
        h = float(sdf['High'].max())
        mdd_val = ((c / h) - 1) * 100
        row = {"종목명": name, "하락률(MDD)": f"{mdd_val:.2f}%", "_mdd": mdd_val, "_rank": i+1}
        
        if category == "코인":
            t_symbol = tck_info["ticker"]
            k_p = korea_all.get(t_symbol, 0)
            row["국내 평균가"] = f"₩{k_p:,.0f}" if k_p > 0 else "N/A"
            row["김프"] = f"{((k_p/(c*fx_rate))-1)*100:+.2f}%" if k_p > 0 else "-"
        else:
            unit = "₩" if category in ["코스피", "코스닥"] else "$"
            row["현재가"] = f"{unit}{c:,.0f}" if unit=="₩" else f"{unit}{c:,.2f}"
        summary.append(row)

res_df = pd.DataFrame(summary)
if category == "코인":
    res_df = res_df.sort_values("_rank")
else:
    res_df = res_df.sort_values("_mdd")

st.table(res_df.drop(columns=["_mdd", "_rank"]))
