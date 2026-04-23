import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import plotly.graph_objects as go
import pandas as pd
import requests
import json
import os

# 1. 환경 설정 및 스타일 (기존 옵션)
DB_FILE = "user_settings.json"
st.set_page_config(page_title="2026 Global Terminal", layout="wide")
st.markdown("""
    <style>
    .up-ticker { color: #FF4B4B; font-weight: bold; }
    .down-ticker { color: #4B9BFF; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 2. 영구 저장 시스템 (초기 20위권 종목 세팅 포함)
def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
    return {
        "코인 (Top 20)": {
            "Bitcoin": {"tck": "BTC", "type": "코인"}, "Ethereum": {"tck": "ETH", "type": "코인"},
            "Solana": {"tck": "SOL", "type": "코인"}, "XRP": {"tck": "XRP", "type": "코인"},
            "BNB": {"tck": "BNB", "type": "코인"}, "Dogecoin": {"tck": "DOGE", "type": "코인"},
            "Cardano": {"tck": "ADA", "type": "코인"}, "Sui": {"tck": "SUI", "type": "코인"}
        },
        "나스닥": {
            "NVIDIA": {"tck": "NVDA", "type": "주식"}, "Apple": {"tck": "AAPL", "type": "주식"},
            "Tesla": {"tck": "TSLA", "type": "주식"}, "Microsoft": {"tck": "MSFT", "type": "주식"}
        },
        "코스피/코스닥": {
            "삼성전자": {"tck": "005930", "type": "주식"}, "SK하이닉스": {"tck": "000660", "type": "주식"}
        }
    }

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

if 'tickers_dict' not in st.session_state:
    st.session_state.tickers_dict = load_data()

# 3. 고난의 역사 분석 (10% 필터링 + 날짜 추적)
def get_hardship_history(df):
    if df.empty: return []
    df = df.copy()
    df['peak'] = df['Close'].cummax()
    history, cp_date = [], df.index[0]
    cp_price = m_min_price = df['Close'].iloc[0]
    m_min_date = df.index[0]
    
    for i in range(1, len(df)):
        if df['Close'].iloc[i] > df['peak'].iloc[i-1]:
            dd = (m_min_price / cp_price) - 1
            if dd <= -0.10: # 10% 이상 폭락만
                history.append({
                    "고점일 (Start)": cp_date.strftime('%Y-%m-%d'),
                    "저점일 (Bottom)": m_min_date.strftime('%Y-%m-%d'),
                    "고점가": f"{cp_price:,.2f}", "저점가": f"{m_min_price:,.2f}",
                    "하락률": f"{dd * 100:.2f}%", "raw_mdd": dd
                })
            cp_date, cp_price = df.index[i], df['Close'].iloc[i]
            m_min_price, m_min_date = cp_price, df.index[i]
        elif df['Close'].iloc[i] < m_min_price:
            m_min_price, m_min_date = df['Close'].iloc[i], df.index[i]
            
    final_dd = (m_min_price / cp_price) - 1
    if final_dd <= -0.10:
        history.append({"고점일 (Start)": cp_date.strftime('%Y-%m-%d'), "저점일 (Bottom)": m_min_date.strftime('%Y-%m-%d'),
                        "하락률": f"{final_dd * 100:.2f}% (진행중)", "raw_mdd": final_dd})
    return sorted(history, key=lambda x: x['raw_mdd'])

# 4. 실시간 데이터 엔진 (환율, 빗썸, 정밀 MDD)
@st.cache_data(ttl=60)
def get_realtime_fx():
    try: return float(yf.download("USDKRW=X", period="1d", progress=False)['Close'].iloc[-1])
    except: return 1480.0

@st.cache_data(ttl=5)
def get_korea_prices():
    try:
        res = requests.get("https://api.bithumb.com/public/ticker/ALL_KRW", timeout=5).json()
        return {k: float(v['closing_price']) for k, v in res['data'].items() if isinstance(v, dict)}
    except: return {}

def fetch_data(symbol, asset_type):
    try:
        if asset_type == "주식" and symbol.isdigit(): return fdr.DataReader(symbol, "1990-01-01").dropna()
        df = yf.download(f"{symbol}-USD" if asset_type == "코인" else symbol, period="max", progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        return df.dropna()
    except: return pd.DataFrame()

# 5. 사이드바 (종목 조회 -> 추가/삭제 순서)
with st.sidebar:
    st.header("🔍 종목 조회")
    cat = st.selectbox("시장 선택", list(st.session_state.tickers_dict.keys()))
    sel_name = st.selectbox("종목 선택", list(st.session_state.tickers_dict[cat].keys()))
    tk_info = st.session_state.tickers_dict[cat][sel_name]
    
    st.divider()
    st.header("⚙️ 관리 메뉴")
    with st.expander("➕ 시장/종목 추가"):
        new_c = st.text_input("새 시장 이름")
        if st.button("시장 생성") and new_c:
            st.session_state.tickers_dict[new_c] = {}; save_data(st.session_state.tickers_dict); st.rerun()
        st.divider()
        target_cat = st.selectbox("추가할 시장", list(st.session_state.tickers_dict.keys()), key="add_cat")
        add_n, add_t = st.text_input("이름"), st.text_input("티커")
        add_ty = st.radio("타입", ["코인", "주식"])
        if st.button("추가 확정") and add_n and add_t:
            st.session_state.tickers_dict[target_cat][add_n] = {"tck": add_t, "type": add_ty}
            save_data(st.session_state.tickers_dict); st.rerun()

    with st.expander("🗑️ 종목 삭제"):
        d_cat = st.selectbox("시장", list(st.session_state.tickers_dict.keys()), key="d_c")
        d_target = st.selectbox("종목", list(st.session_state.tickers_dict[d_cat].keys()), key="d_t")
        if st.button("삭제 실행"):
            del st.session_state.tickers_dict[d_cat][d_target]
            save_data(st.session_state.tickers_dict); st.rerun()

# 6. 메인 화면 (탭 구성)
df = fetch_data(tk_info['tck'], tk_info['type'])
if not df.empty:
    tab1, tab2 = st.tabs(["📊 실시간 리포트", "🌋 고난의 역사"])
    fx_rate = get_realtime_fx()
    
    with tab1:
        cp = float(df['Close'].iloc[-1])
        dc = ((cp / df['Close'].iloc[-2]) - 1) * 100 if len(df) > 1 else 0
        roll_max = df['Close'].cummax()
        h_mdd = ((df['Close'] / roll_max) - 1).min() * 100
        c_dd = ((cp / df['Close'].max()) - 1) * 100
        
        m1, m2, m3, m4 = st.columns(4)
        if tk_info['type'] == "코인":
            kp = get_korea_prices().get(tk_info['tck'], 0)
            diff = ((kp / (cp * fx_rate)) - 1) * 100 if kp > 0 else 0
            m1.metric("해외 ($)", f"${cp:,.2f}", delta=f"{dc:+.2f}%")
            m2.metric("국내 (₩)", f"₩{kp:,.0f}"); m3.metric("김프 (%)", f"{diff:+.2f}%")
        else:
            m1.metric("현재가", f"{cp:,.2f}", delta=f"{dc:+.2f}%")
            m2.metric("최악 MDD", f"{h_mdd:.2f}%"); m3.metric("현재 낙폭", f"{c_dd:.2f}%")
        m4.metric("실시간 환율", f"₩{fx_rate:,.1f}")

        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        fig.update_layout(template="plotly_dark", height=450, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader(f"🌋 {sel_name} 역대 폭락 구간 (-10% 이상)")
        h_data = get_hardship_history(df)
        if h_data: st.table(pd.DataFrame(h_data).drop(columns=['raw_mdd']))
        else: st.info("대상 구간이 없습니다.")

# 7. 하단 전체 리포트 (색상/정렬 옵션 완벽 복구)
st.divider()
st.subheader(f"📊 {cat} 실시간 요약 테이블")
summary, k_all = [], get_korea_prices()
for i, (name, info) in enumerate(st.session_state.tickers_dict[cat].items()):
    sdf = fetch_data(info['tck'], info['type'])
    if not sdf.empty:
        p = float(sdf['Close'].iloc[-1])
        ch = ((p / sdf['Close'].iloc[-2]) - 1) * 100 if len(sdf) > 1 else 0
        hm = ((sdf['Close'] / sdf['Close'].cummax()) - 1).min() * 100
        cd = ((p / sdf['Close'].max()) - 1) * 100
        tag = "up-ticker" if ch >= 0 else "down-ticker"
        row = {"종목명": name, "변동": f'<span class="{tag}">{ch:+.2f}%</span>', "최악 MDD": f"{hm:.2f}%", "현재 낙폭": f"{cd:.2f}%", "_mdd": cd, "_rank": i, "_type": info['type']}
        if info['type'] == "코인":
            kp = k_all.get(info['tck'], 0); row["해외($)"] = f"${p:,.2f}"; row["국내(₩)"] = f"₩{kp:,.0f}"
            row["차이(%)"] = f"{((kp/(p*fx_rate))-1)*100:+.2f}%" if kp > 0 else "-"
        else: row["현재가"] = f"{p:,.2f}"
        summary.append(row)

if summary:
    res = pd.DataFrame(summary).sort_values("_rank" if cat == "코인 (Top 20)" else "_mdd")
    cols = ["종목명", "변동"]
    if "해외($)" in res.columns: cols += ["해외($)", "국내(₩)", "차이(%)"]
    else: cols += ["현재가"]
    st.write(res[cols + ["최악 MDD", "현재 낙폭"]].to_html(escape=False, index=False), unsafe_allow_html=True)
