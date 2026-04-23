import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import plotly.graph_objects as go
import pandas as pd
import requests

# 1. 페이지 설정
st.set_page_config(page_title="2026 Global Terminal", layout="wide")

# CSS를 이용해 텍스트 색상 지정 (상승: 빨강, 하락: 파랑)
st.markdown("""
    <style>
    .up-ticker { color: #FF4B4B; font-weight: bold; }
    .down-ticker { color: #4B9BFF; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("📈 2026 글로벌 자산 터미널 (실시간 변동률 & MDD)")

# 2. 종목 데이터 세팅 (이전과 동일)
DEFAULT_TICKERS = {
    "코인": {"Bitcoin": "BTC", "Ethereum": "ETH", "Solana": "SOL", "XRP": "XRP", "BNB": "BNB", "Dogecoin": "DOGE", "Sui": "SUI", "Aptos": "APT"},
    "나스닥": {"NVIDIA": "NVDA", "Apple": "AAPL", "Microsoft": "MSFT", "Amazon": "AMZN", "Tesla": "TSLA", "Meta": "META"},
    "S&P500": {"Berkshire": "BRK-B", "Eli Lilly": "LLY", "JPMorgan": "JPM", "Visa": "V", "UnitedHealth": "UNH"},
    "코스피": {"삼성전자": "005930", "SK하이닉스": "000660", "LG엔솔": "373220", "현대차": "005380"},
    "코스닥": {"에코프로비엠": "247540", "알테오젠": "196170", "에코프로": "086520", "HLB": "028300"}
}

# 3. 핵심 분석 함수: 역사상 최악의 MDD 및 변동률 계산
def analyze_asset(df):
    if df.empty: return 0, 0, 0, "N/A", "N/A", 0
    
    # 당일 변동률 계산 (마지막 종가 vs 전일 종가)
    curr_price = df['Close'].iloc[-1]
    prev_price = df['Close'].iloc[-2] if len(df) > 1 else curr_price
    day_change_pct = ((curr_price / prev_price) - 1) * 100
    
    # 전구간 MDD 계산 (과거 모든 고점-저점 전수 조사)
    rolling_max = df['Close'].cummax()
    drawdowns = (df['Close'] / rolling_max) - 1.0
    
    max_mdd = drawdowns.min() * 100
    max_mdd_date = drawdowns.idxmin().strftime('%Y-%m-%d')
    peak_date = rolling_max[:drawdowns.idxmin()].idxmax().strftime('%Y-%m-%d')
    
    # 현재 낙폭 (전고점 대비 현재)
    curr_drawdown = ((curr_price / df['Close'].max()) - 1) * 100
    
    return curr_price, day_change_pct, max_mdd, max_mdd_date, peak_date, curr_drawdown

# 4. 데이터 엔진 (빗썸 & 야후파이낸스)
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

# 5. 사이드바 및 환율
fx_rate = 1385.0
try:
    fx = yf.download("USDKRW=X", period="1d", progress=False)
    if not fx.empty: fx_rate = float(fx['Close'].iloc[-1])
except: pass

with st.sidebar:
    category = st.selectbox("시장", list(DEFAULT_TICKERS.keys()))
    selected_name = st.selectbox("종목", list(DEFAULT_TICKERS[category].keys()))
    ticker = DEFAULT_TICKERS[category][selected_name]

# 6. 메인 화면: 선택 종목 상세 분석
df = fetch_data(ticker, category)
if not df.empty:
    curr_p, day_chg, hist_mdd, mdd_d, p_d, curr_dd = analyze_asset(df)
    
    # 당일 변동률 색상 결정
    color = "red" if day_chg >= 0 else "blue"
    chg_sign = "+" if day_chg >= 0 else ""

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("현재가", f"{curr_p:,.2f}", delta=f"{chg_sign}{day_chg:.2f}%", delta_color="normal")
    m2.metric("역사상 최악의 MDD", f"{hist_mdd:.2f}%", help=f"고점({p_d}) -> 저점({mdd_d})")
    m3.metric("현재의 낙폭", f"{curr_dd:.2f}%")
    m4.metric("실시간 환율", f"₩{fx_rate:,.1f}")

    # 차트 주기 설정 및 캔들차트
    tf = st.pills("차트 주기", ["1D", "1W", "1M"], default="1D")
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=400)
    st.plotly_chart(fig, use_container_width=True)

# 7. 하단 리포트 테이블 (당일 변동률 색상 적용)
st.divider()
st.subheader(f"📊 {category} 상세 분석 리포트")

summary = []
k_all = get_korea_prices() if category == "코인" else {}

for name, tck in DEFAULT_TICKERS[category].items():
    sdf = fetch_data(tck, category)
    if not sdf.empty:
        c_p, d_c, h_m, h_d, p_d, c_d = analyze_asset(sdf)
        
        # 색상 태그 적용 (HTML 스타일)
        tag = "up-ticker" if d_c >= 0 else "down-ticker"
        colored_chg = f'<span class="{tag}">{"+" if d_c >= 0 else ""}{d_c:.2f}%</span>'
        
        row = {
            "종목명": name,
            "당일 변동률": colored_chg,
            "역사상 최악 MDD": f"{h_m:.2f}%",
            "현재 낙폭": f"{c_d:.2f}%",
            "최악의 시기": h_d,
            "_mdd": c_d # 정렬용
        }
        
        if category == "코인":
            row["국내(빗썸)"] = f"₩{k_all.get(tck, 0):,.0f}"
            row["해외(USD)"] = f"${c_p:,.2f}"
        else:
            row["현재가"] = f"{c_p:,.2f}"
            
        summary.append(row)

res_df = pd.DataFrame(summary)
# 주식은 낙폭 순, 코인은 시총 순 정렬 유지
sorted_df = res_df.sort_values("_mdd" if category != "코인" else "종목명") 

# HTML 테이블로 렌더링 (색상 적용을 위해)
st.write(sorted_df.drop(columns=["_mdd"]).to_html(escape=False, index=False), unsafe_allow_html=True)
