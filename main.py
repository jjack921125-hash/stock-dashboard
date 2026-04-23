import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import plotly.graph_objects as go
import pandas as pd
import requests

# 1. 페이지 설정
st.set_page_config(page_title="2026 Global Terminal", layout="wide")
st.title("📈 2026 글로벌 자산 터미널 (역사적 최대 낙폭 분석)")

# 2. 데이터 리스트 (생략 - 이전과 동일)
DEFAULT_TICKERS = {
    "코인": {"Bitcoin": "BTC", "Ethereum": "ETH", "Solana": "SOL", "XRP": "XRP", "BNB": "BNB", "Dogecoin": "DOGE"},
    "나스닥": {"NVIDIA": "NVDA", "Apple": "AAPL", "Microsoft": "MSFT", "Amazon": "AMZN", "Tesla": "TSLA"},
    "S&P500": {"Berkshire": "BRK-B", "Eli Lilly": "LLY", "JPMorgan": "JPM", "Visa": "V"},
    "코스피": {"삼성전자": "005930", "SK하이닉스": "000660", "LG엔솔": "373220"},
    "코스닥": {"에코프로비엠": "247540", "알테오젠": "196170"}
}

# 3. 핵심 함수: 역사상 최악의 MDD(Max MDD) 계산
def calculate_historical_mdd(df):
    if df.empty: return 0, None, None, 0
    
    # 누적 최고점 계산 (Running Maximum)
    rolling_max = df['Close'].cummax()
    
    # 고점 대비 하락률 계산
    drawdowns = (df['Close'] / rolling_max) - 1.0
    
    # 1. 역사상 최악의 낙폭 (Max MDD)
    max_mdd = drawdowns.min()
    max_mdd_date = drawdowns.idxmin().strftime('%Y-%m-%d')
    # 당시의 고점 날짜 찾기
    peak_date = rolling_max[:drawdowns.idxmin()].idxmax().strftime('%Y-%m-%d')
    
    # 2. 현재 시점의 낙폭 (Current Drawdown)
    current_drawdown = drawdowns.iloc[-1]
    
    return max_mdd * 100, max_mdd_date, peak_date, current_drawdown * 100

# (중략 - 데이터 엔진 및 환율 로직은 이전과 동일)
@st.cache_data(ttl=5)
def get_korea_prices():
    try:
        url = "https://api.bithumb.com/public/ticker/ALL_KRW"
        res = requests.get(url, timeout=5).json()
        return {k: float(v['closing_price']) for k, v in res['data'].items() if isinstance(v, dict) and 'closing_price' in v}
    except: return {}

@st.cache_data(ttl=300)
def fetch_data(symbol, category, interval="1D"):
    try:
        if category in ["코스피", "코스닥"]: return fdr.DataReader(symbol, "1980-01-01").dropna()
        else:
            df = yf.download(f"{symbol}-USD" if category == "코인" else symbol, period="max", progress=False)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            return df.dropna()
    except: return pd.DataFrame()

# 4. 사이드바 및 실행
with st.sidebar:
    category = st.selectbox("시장", list(DEFAULT_TICKERS.keys()))
    selected_name = st.selectbox("종목", list(DEFAULT_TICKERS[category].keys()))
    ticker = DEFAULT_TICKERS[category][selected_name]

df = fetch_data(ticker, category, "1D")
if not df.empty:
    # 역사적 MDD 분석 수행
    hist_mdd, mdd_date, p_date, curr_dd = calculate_historical_mdd(df)
    
    # 상단 지표 출력
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("현재가", f"{df['Close'].iloc[-1]:,.2f}")
    m2.metric("역대 최고가(ATH)", f"{df['Close'].max():,.2f}")
    m3.metric("역사상 최악의 MDD", f"{hist_mdd:.2f}%", help=f"고점({p_date}) -> 저점({mdd_date})")
    m4.metric("현재의 낙폭", f"{curr_dd:.2f}%")

    st.subheader(f"📊 {category} 상세 분석 리포트")
    
    # 리포트 생성 로직
    summary = []
    for name, tck in DEFAULT_TICKERS[category].items():
        sdf = fetch_data(tck, category, "1D")
        if not sdf.empty:
            h_mdd, h_date, p_date, c_dd = calculate_historical_mdd(sdf)
            summary.append({
                "종목명": name,
                "역사상 최악의 MDD": f"{h_mdd:.2f}%",
                "최악의 시기(저점일)": h_date,
                "현재의 낙폭": f"{c_dd:.2f}%",
                "현재 상태": "신고가" if c_dd > -0.01 else "하락 중",
                "_mdd": c_dd, "_rank": len(summary)
            })
    
    res_df = pd.DataFrame(summary)
    # 정렬 규칙 유지 (주식은 현재 낙폭이 큰 순서)
    st.table(res_df.sort_values("_mdd" if category != "코인" else "_rank").drop(columns=["_mdd", "_rank"]))
