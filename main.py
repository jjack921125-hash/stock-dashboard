import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import plotly.graph_objects as go
import pandas as pd
import requests

# 1. 페이지 설정
st.set_page_config(page_title="2026 Global Terminal", layout="wide")
st.markdown("""
    <style>
    .up-ticker { color: #FF4B4B; font-weight: bold; }
    .down-ticker { color: #4B9BFF; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("📈 2026 글로벌 자산 터미널 (종목 커스텀 추가 버전)")

# 2. 기본 종목 리스트 (TOP 20)
DEFAULT_TICKERS = {
    "코인": {
        "Bitcoin": "BTC", "Ethereum": "ETH", "Solana": "SOL", "XRP": "XRP", "BNB": "BNB",
        "Dogecoin": "DOGE", "Cardano": "ADA", "Avalanche": "AVAX", "Sui": "SUI", "Tron": "TRX",
        "Toncoin": "TON", "Chainlink": "LINK", "Pepe": "PEPE", "Aptos": "APT", "Near": "NEAR",
        "Polkadot": "DOT", "Litecoin": "LTC", "Bitcoin Cash": "BCH", "Uniswap": "UNI", "Polygon": "MATIC"
    },
    "나스닥": { "NVIDIA": "NVDA", "Apple": "AAPL", "Microsoft": "MSFT", "Amazon": "AMZN", "Alphabet(A)": "GOOGL", "Meta": "META", "Tesla": "TSLA", "Broadcom": "AVGO", "ASML": "ASML", "Costco": "COST", "Netflix": "NFLX", "AMD": "AMD", "Adobe": "ADBE", "Qualcomm": "QCOM", "Arm": "ARM", "Applied Materials": "AMAT", "Intuitive Surgical": "ISRG", "LRCX": "LRCX", "Micron": "MU", "Intel": "INTC" },
    "S&P500": { "Berkshire": "BRK-B", "Eli Lilly": "LLY", "JPMorgan": "JPM", "Visa": "V", "UnitedHealth": "UNH", "Exxon Mobil": "XOM", "Mastercard": "MA", "Johnson&Johnson": "JNJ", "Procter&Gamble": "PG", "Home Depot": "HD" },
    "코스피": { "삼성전자": "005930", "SK하이닉스": "000660", "LG엔솔": "373220", "삼성바이오": "207940", "현대차": "005380", "기아": "000270", "셀트리온": "068270", "KB금융": "105560", "NAVER": "035420", "신한지주": "055550" },
    "코스닥": { "에코프로비엠": "247540", "알테오젠": "196170", "에코프로": "086520", "HLB": "028300", "엔켐": "348370", "HPSP": "403870", "리노공업": "058470", "레인보우로보틱스": "277810", "클래시스": "214150", "삼천당제약": "000250" }
}

# 3. 실시간 환율 및 데이터 엔진
@st.cache_data(ttl=60)
def get_realtime_fx():
    try:
        fx_data = yf.download("USDKRW=X", period="1d", progress=False)
        return float(fx_data['Close'].iloc[-1])
    except: return 1480.85 # 2026-04-23 기준가

fx_rate = get_realtime_fx()

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

# 4. 사이드바 메뉴 (종목 추가 기능 포함)
with st.sidebar:
    category = st.selectbox("1. 시장 선택", list(DEFAULT_TICKERS.keys()))
    
    # 종목 직접 추가 섹션
    st.divider()
    st.subheader("➕ 종목 커스텀 추가")
    custom_name = st.text_input("종목 별명 (예: 나의코인)", "")
    custom_ticker = st.text_input("티커 입력 (예: SEI, MSTR, 000660)", "")
    
    if st.button("목록에 추가하기"):
        if custom_name and custom_ticker:
            DEFAULT_TICKERS[category][custom_name] = custom_ticker
            st.success(f"'{custom_name}' 추가 완료!")
        else:
            st.warning("이름과 티커를 모두 입력하세요.")
    
    st.divider()
    selected_name = st.selectbox("2. 종목 조회", list(DEFAULT_TICKERS[category].keys()))
    ticker = DEFAULT_TICKERS[category][selected_name]

# 5. 메인 화면 출력
df = fetch_data(ticker, category)
if not df.empty:
    curr_p, day_chg, hist_mdd, mdd_d, p_d, curr_dd = analyze_asset(df)
    
    m1, m2, m3, m4 = st.columns(4)
    if category == "코인":
        k_prices = get_korea_prices()
        krw_p = k_prices.get(ticker, 0)
        price_diff = ((krw_p / (curr_p * fx_rate)) - 1) * 100 if krw_p > 0 else 0
        
        m1.metric("해외 가격 ($)", f"${curr_p:,.2f}", delta=f"{day_chg:+.2f}%")
        m2.metric("국내 가격 (₩)", f"₩{krw_p:,.0f}")
        m3.metric("가격 차이 (%)", f"{price_diff:+.2f}%")
        m4.metric("적용 환율 (₩/$)", f"{fx_rate:,.2f}")
    else:
        unit = "₩" if category in ["코스피", "코스닥"] else "$"
        m1.metric("현재가", f"{unit}{curr_p:,.2f}", delta=f"{day_chg:+.2f}%")
        m2.metric("역사상 최악 MDD", f"{hist_mdd:.2f}%")
        m3.metric("현재 낙폭(MDD)", f"{curr_dd:.2f}%")
        m4.metric("실시간 환율", f"₩{fx_rate:,.1f}")

    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=450)
    st.plotly_chart(fig, use_container_width=True)

# 6. 리포트 테이블 (시총순/하락률순 정렬 유지)
st.divider()
st.subheader(f"📊 {category} 상세 분석 리포트")
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
            kp = k_all.get(tck, 0)
            row["해외($)"] = f"${c_p:,.2f}"
            row["국내(₩)"] = f"₩{kp:,.0f}"
            row["차이(%)"] = f"{((kp/(c_p*fx_rate))-1)*100:+.2f}%" if kp > 0 else "-"
        else: row["현재가"] = f"{c_p:,.2f}"
        summary.append(row)

res_df = pd.DataFrame(summary)
sorted_df = res_df.sort_values("_rank" if category == "코인" else "_mdd")
cols = ["종목명", "당일 변동", "해외($)", "국내(₩)", "차이(%)", "역사상 최악 MDD", "현재 낙폭"] if category == "코인" else ["종목명", "당일 변동", "현재가", "역사상 최악 MDD", "현재 낙폭"]
st.write(sorted_df[cols].to_html(escape=False, index=False), unsafe_allow_html=True)
