import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import plotly.graph_objects as go
import pandas as pd
import requests

# 1. 페이지 설정
st.set_page_config(page_title="2026 Global Terminal", layout="wide")
st.title("📈 2026 글로벌 자산 터미널 (맞춤형 정렬 시스템)")

# 2. 2026년 4월 시총 순위 데이터 (리스트 순서 자체가 시총순)
DEFAULT_TICKERS = {
    "코인": {
        "Bitcoin": "BTC", "Ethereum": "ETH", "Solana": "SOL", "XRP": "XRP", "BNB": "BNB",
        "Dogecoin": "DOGE", "Cardano": "ADA", "Avalanche": "AVAX", "Sui": "SUI", "Tron": "TRX",
        "Toncoin": "TON", "Chainlink": "LINK", "Pepe": "PEPE", "Aptos": "APT", "Near": "NEAR",
        "Polkadot": "DOT", "Litecoin": "LTC", "Bitcoin Cash": "BCH", "Uniswap": "UNI", "Polygon": "MATIC"
    },
    "나스닥": {
        "NVIDIA": "NVDA", "Apple": "AAPL", "Microsoft": "MSFT", "Amazon": "AMZN", "Alphabet(A)": "GOOGL",
        "Meta": "META", "Tesla": "TSLA", "Broadcom": "AVGO", "ASML": "ASML", "Costco": "COST",
        "Netflix": "NFLX", "AMD": "AMD", "Adobe": "ADBE", "Qualcomm": "QCOM", "Arm": "ARM",
        "Applied Materials": "AMAT", "Intuitive Surgical": "ISRG", "LRCX": "LRCX", "Micron": "MU", "Intel": "INTC"
    },
    "S&P500": {
        "Berkshire": "BRK-B", "Eli Lilly": "LLY", "JPMorgan": "JPM", "Visa": "V", "UnitedHealth": "UNH",
        "Exxon Mobil": "XOM", "Mastercard": "MA", "Johnson&Johnson": "JNJ", "Procter&Gamble": "PG", "Home Depot": "HD"
    },
    "코스피": {
        "삼성전자": "005930", "SK하이닉스": "000660", "LG엔솔": "373220", "삼성바이오": "207940", "현대차": "005380",
        "기아": "000270", "셀트리온": "068270", "KB금융": "105560", "NAVER": "035420", "신한지주": "055550"
    },
    "코스닥": {
        "에코프로비엠": "247540", "알테오젠": "196170", "에코프로": "086520", "HLB": "028300", "엔켐": "348370",
        "HPSP": "403870", "리노공업": "058470", "레인보우로보틱스": "277810", "클래시스": "214150", "삼천당제약": "000250"
    }
}

# 3. 데이터 엔진
@st.cache_data(ttl=5)
def get_upbit_prices():
    try:
        tickers = list(DEFAULT_TICKERS["코인"].values())
        markets = [f"KRW-{t}" for t in tickers]
        headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
        res = requests.get(f"https://api.upbit.com/v1/ticker?markets={','.join(markets)}", headers=headers, timeout=5).json()
        return {item['market'].split('-')[1]: float(item['trade_price']) for item in res}
    except: return {}

@st.cache_data(ttl=300)
def fetch_data(symbol, category, interval="1D"):
    int_map = {"1H": "1h", "4H": "1h", "1D": "1d", "1W": "1wk", "1M": "1mo"}
    yf_int = int_map.get(interval, "1d")
    try:
        if category in ["코스피", "코스닥"]:
            return fdr.DataReader(symbol, "1980-01-01").dropna()
        else:
            target = f"{symbol}-USD" if category == "코인" else symbol
            df = yf.download(target, period="max", interval=yf_int, progress=False)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            return df.dropna()
    except: return pd.DataFrame()

# 4. 환율 및 사이드바
fx_rate = 1385.0
try:
    fx = yf.download("USDKRW=X", period="1d", progress=False)
    if not fx.empty: fx_rate = float(fx['Close'].iloc[-1])
except: pass

with st.sidebar:
    category = st.selectbox("시장", list(DEFAULT_TICKERS.keys()))
    selected_name = st.selectbox("종목", list(DEFAULT_TICKERS[category].keys()))
    ticker = DEFAULT_TICKERS[category][selected_name]

# 5. 차트 섹션 (우상단 캔들 설정)
c_main, c_tool = st.columns([8, 2])
with c_tool:
    tf = st.pills("Interval", ["1H", "4H", "1D", "1W", "1M"], default="1D")

df = fetch_data(ticker, category, tf)

if not df.empty:
    c_p = float(df['Close'].iloc[-1])
    h_p = float(df['High'].max())
    m1, m2, m3, m4 = st.columns(4)
    if category == "코인":
        up_p = get_upbit_prices().get(ticker, 0)
        kp = ((up_p / (c_p * fx_rate)) - 1) * 100 if up_p > 0 else 0
        m1.metric("업비트 (KRW)", f"₩{up_p:,.0f}")
        m2.metric("해외 (USD)", f"${c_p:,.2f}")
        m3.metric("김치프리미엄", f"{kp:+.2f}%")
    else:
        unit = "₩" if category in ["코스피", "코스닥"] else "$"
        m1.metric("현재가", f"{unit}{c_p:,.0f}" if unit=="₩" else f"{unit}{c_p:,.2f}")
        m2.metric("최고가", f"{unit}{h_p:,.0f}" if unit=="₩" else f"{unit}{h_p:,.2f}")
        m3.metric("환율", f"₩{fx_rate:,.1f}")
    m4.metric("역대 MDD", f"{((c_p/h_p)-1)*100:.2f}%")

    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=450, margin=dict(t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)

# 6. 정렬 로직이 포함된 테이블 섹션
st.divider()
st.subheader(f"📊 {category} 상세 리포트 ({'시총순' if category=='코인' else '하락률순'})")

summary = []
up_all = get_upbit_prices() if category == "코인" else {}

for i, (name, tck) in enumerate(DEFAULT_TICKERS[category].items()):
    sdf = fetch_data(tck, category, "1D")
    if not sdf.empty:
        c = float(sdf['Close'].iloc[-1])
        h = float(sdf['High'].max())
        mdd_val = ((c / h) - 1) * 100
        row = {"종목명": name, "하락률(MDD)": f"{mdd_val:.2f}%", "_mdd": mdd_val, "_rank": i+1}
        
        if category == "코인":
            u_p = up_all.get(tck, 0)
            row["업비트가"] = f"₩{u_p:,.0f}"
            row["김프"] = f"{((u_p/(c*fx_rate))-1)*100:+.2f}%" if u_p > 0 else "-"
        else:
            unit = "₩" if category in ["코스피", "코스닥"] else "$"
            row["현재가"] = f"{unit}{c:,.0f}" if unit=="₩" else f"{unit}{c:,.2f}"
        summary.append(row)

# 데이터프레임 변환 후 정렬 적용
res_df = pd.DataFrame(summary)
if category == "코인":
    res_df = res_df.sort_values("_rank") # 시총 순위(딕셔너리 순서) 정렬
else:
    res_df = res_df.sort_values("_mdd")  # 하락률이 큰 순서(MDD가 낮은 순서) 정렬

# 불필요한 계산용 컬럼 제거 후 출력
st.table(res_df.drop(columns=["_mdd", "_rank"]))
