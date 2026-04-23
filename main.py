import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import plotly.graph_objects as go
import pandas as pd
import requests

# 1. 페이지 설정 및 디자인
st.set_page_config(page_title="2026 Global Terminal", layout="wide")
st.markdown("""
    <style>
    .up-ticker { color: #FF4B4B; font-weight: bold; }
    .down-ticker { color: #4B9BFF; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("📈 글로벌 자산 시세 (TOP 20)")

# 2. 2026년 4월 기준 시총 TOP 20 종목 리스트
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
        "Exxon Mobil": "XOM", "Mastercard": "MA", "Johnson&Johnson": "JNJ", "Procter&Gamble": "PG", "Home Depot": "HD",
        "AbbVie": "ABBV", "Chevron": "CVX", "Merck": "MRK", "Bank of America": "BAC", "Coca-Cola": "KO",
        "PepsiCo": "PEP", "Oracle": "ORCL", "Walmart": "WMT", "Costco": "COST", "McDonald's": "MCD"
    },
    "코스피": {
        "삼성전자": "005930", "SK하이닉스": "000660", "LG엔솔": "373220", "삼성바이오": "207940", "현대차": "005380",
        "기아": "000270", "셀트리온": "068270", "KB금융": "105560", "NAVER": "035420", "신한지주": "055550",
        "POSCO홀딩스": "005490", "삼성물산": "028260", "현대모비스": "012330", "LG화학": "051910", "하나금융지주": "086790",
        "삼성생명": "032830", "메리츠금융": "138040", "카카오": "035720", "삼성SDI": "006400", "LG전자": "066570"
    },
    "코스닥": {
        "에코프로비엠": "247540", "알테오젠": "196170", "에코프로": "086520", "HLB": "028300", "엔켐": "348370",
        "HPSP": "403870", "리노공업": "058470", "레인보우로보틱스": "277810", "클래시스": "214150", "삼천당제약": "000250",
        "셀트리온제약": "068760", "실리콘투": "257720", "휴젤": "145020", "리가켐바이오": "141080", "리노공업": "058470",
        "솔브레인": "357780", "동진쎄미켐": "005290", "펄어비스": "263750", "JYP Ent.": "035900", "에스티팜": "237690"
    }
}

# 3. 핵심 분석 함수 (전구간 MDD 및 변동률)
def analyze_asset(df):
    if df.empty: return 0, 0, 0, "N/A", "N/A", 0
    curr_price = float(df['Close'].iloc[-1])
    prev_price = float(df['Close'].iloc[-2]) if len(df) > 1 else curr_price
    day_change_pct = ((curr_price / prev_price) - 1) * 100
    
    rolling_max = df['Close'].cummax()
    drawdowns = (df['Close'] / rolling_max) - 1.0
    max_mdd = drawdowns.min() * 100
    max_mdd_date = drawdowns.idxmin().strftime('%Y-%m-%d')
    peak_date = rolling_max[:drawdowns.idxmin()].idxmax().strftime('%Y-%m-%d')
    curr_drawdown = ((curr_price / df['Close'].max()) - 1) * 100
    
    return curr_price, day_change_pct, max_mdd, max_mdd_date, peak_date, curr_drawdown

# 4. 데이터 엔진
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
            target = f"{symbol}-USD" if category == "코인" else symbol
            df = yf.download(target, period="max", progress=False)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            return df.dropna()
    except: return pd.DataFrame()

# 5. 환율 및 사이드바
fx_rate = 1385.0
try:
    fx = yf.download("USDKRW=X", period="1d", progress=False)
    if not fx.empty: fx_rate = float(fx['Close'].iloc[-1])
except: pass

with st.sidebar:
    category = st.selectbox("시장", list(DEFAULT_TICKERS.keys()))
    selected_name = st.selectbox("종목", list(DEFAULT_TICKERS[category].keys()))
    ticker = DEFAULT_TICKERS[category][selected_name]

# 6. 메인 화면
df = fetch_data(ticker, category)
if not df.empty:
    curr_p, day_chg, hist_mdd, mdd_d, p_d, curr_dd = analyze_asset(df)
    
    m1, m2, m3, m4 = st.columns(4)
    if category == "코인":
        k_prices = get_korea_prices()
        krw_p = k_prices.get(ticker, 0)
        # 달러를 환율로 계산한 값과 실제 국내가의 차이 (%)
        price_diff = ((krw_p / (curr_p * fx_rate)) - 1) * 100 if krw_p > 0 else 0
        
        m1.metric("해외가 (USD)", f"${curr_p:,.2f}", delta=f"{day_chg:+.2f}%")
        m1.write(f"**원화 환산가:** ₩{(curr_p * fx_rate):,.0f}")
        m2.metric("국내 가격 (KRW)", f"₩{krw_p:,.0f}")
        m2.write(f"**가격 차이:** {price_diff:+.2f}%") # 달러가 대비 프리미엄
        m3.metric("역사상 최악 MDD", f"{hist_mdd:.2f}%")
    else:
        unit = "₩" if category in ["코스피", "코스닥"] else "$"
        m1.metric("현재가", f"{unit}{curr_p:,.2f}", delta=f"{day_chg:+.2f}%")
        m2.metric("역사상 최악 MDD", f"{hist_mdd:.2f}%", help=f"고점({p_d}) -> 저점({mdd_d})")
        m3.metric("현재 낙폭", f"{curr_dd:.2f}%")
    m4.metric("실시간 환율", f"₩{fx_rate:,.1f}")

    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=400)
    st.plotly_chart(fig, use_container_width=True)

# 7. 하단 상세 분석 리포트
st.divider()
st.subheader(f"📊 {category} TOP 20 분석 리포트")

summary = []
k_all = get_korea_prices() if category == "코인" else {}

for i, (name, tck) in enumerate(DEFAULT_TICKERS[category].items()):
    sdf = fetch_data(tck, category)
    if not sdf.empty:
        c_p, d_c, h_m, h_d, p_d, c_d = analyze_asset(sdf)
        tag = "up-ticker" if d_c >= 0 else "down-ticker"
        colored_chg = f'<span class="{tag}">{d_c:+.2f}%</span>'
        
        row = {"종목명": name, "당일 변동": colored_chg, "역사상 최악 MDD": f"{h_m:.2f}%", "현재 낙폭": f"{c_d:.2f}%", "_mdd": c_d, "_rank": i}
        
        if category == "코인":
            krw_p = k_all.get(tck, 0)
            diff = ((krw_p / (c_p * fx_rate)) - 1) * 100 if krw_p > 0 and c_p > 0 else 0
            row["해외($)"] = f"${c_p:,.2f}"
            row["국내(₩)"] = f"₩{krw_p:,.0f}"
            row["차이(%)"] = f"{diff:+.2f}%"
        else:
            row["현재가"] = f"{c_p:,.2f}"
        summary.append(row)

res_df = pd.DataFrame(summary)
# 코인은 시총순(순서대로), 주식은 하락률순 정렬
sorted_df = res_df.sort_values("_rank" if category == "코인" else "_mdd")

# 컬럼 순서 조정
if category == "코인":
    cols = ["종목명", "당일 변동", "해외($)", "국내(₩)", "차이(%)", "역사상 최악 MDD", "현재 낙폭"]
else:
    cols = ["종목명", "당일 변동", "현재가", "역사상 최악 MDD", "현재 낙폭"]

st.write(sorted_df[cols].to_html(escape=False, index=False), unsafe_allow_html=True)
