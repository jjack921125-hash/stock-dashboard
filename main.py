import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import plotly.graph_objects as go
import pandas as pd
import requests
import json
import os

# 1. 초기 설정 및 스타일
DB_FILE = "user_settings.json"
st.set_page_config(page_title="2026 Global Terminal", layout="wide")
st.markdown("""
    <style>
    .up-ticker { color: #FF4B4B; font-weight: bold; }
    .down-ticker { color: #4B9BFF; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 로드 및 2026년 4월 기준 시총 상위 20 종목 셋팅
def load_data():
    default_data = {
        "코인 (스테이블 제외)": {
            "Bitcoin": {"tck": "BTC", "type": "코인"}, "Ethereum": {"tck": "ETH", "type": "코인"},
            "Solana": {"tck": "SOL", "type": "코인"}, "XRP": {"tck": "XRP", "type": "코인"},
            "BNB": {"tck": "BNB", "type": "코인"}, "Dogecoin": {"tck": "DOGE", "type": "코인"},
            "Cardano": {"tck": "ADA", "type": "코인"}, "Avalanche": {"tck": "AVAX", "type": "코인"},
            "Sui": {"tck": "SUI", "type": "코인"}, "Polkadot": {"tck": "DOT", "type": "코인"},
            "Chainlink": {"tck": "LINK", "type": "코인"}, "Polygon": {"tck": "MATIC", "type": "코인"},
            "Near": {"tck": "NEAR", "type": "코인"}, "Litecoin": {"tck": "LTC", "type": "코인"},
            "Pepe": {"tck": "PEPE", "type": "코인"}, "Aptos": {"tck": "APT", "type": "코인"},
            "Uniswap": {"tck": "UNI", "type": "코인"}, "Stacks": {"tck": "STX", "type": "코인"},
            "Arbitrum": {"tck": "ARB", "type": "코인"}, "Bittensor": {"tck": "TAO", "type": "코인"}
        },
        "나스닥 100": {
            "NVIDIA": {"tck": "NVDA", "type": "주식"}, "Apple": {"tck": "AAPL", "type": "주식"},
            "Microsoft": {"tck": "MSFT", "type": "주식"}, "Amazon": {"tck": "AMZN", "type": "주식"},
            "Meta": {"tck": "META", "type": "주식"}, "Broadcom": {"tck": "AVGO", "type": "주식"},
            "Tesla": {"tck": "TSLA", "type": "주식"}, "Alphabet A": {"tck": "GOOGL", "type": "주식"},
            "Alphabet C": {"tck": "GOOG", "type": "주식"}, "Costco": {"tck": "COST", "type": "주식"},
            "Netflix": {"tck": "NFLX", "type": "주식"}, "AMD": {"tck": "AMD", "type": "주식"},
            "Adobe": {"tck": "ADBE", "type": "주식"}, "PepsiCo": {"tck": "PEP", "type": "주식"},
            "Linde": {"tck": "LIN", "type": "주식"}, "T-Mobile": {"tck": "TMUS", "type": "주식"},
            "Qualcomm": {"tck": "QCOM", "type": "주식"}, "Cisco": {"tck": "CSCO", "type": "주식"},
            "Intuit": {"tck": "INTU", "type": "주식"}, "Amgen": {"tck": "AMGN", "type": "주식"}
        },
        "S&P 500 (나스닥 중복제외)": {
            "Berkshire Hathaway": {"tck": "BRK-B", "type": "주식"}, "Eli Lilly": {"tck": "LLY", "type": "주식"},
            "JPMorgan Chase": {"tck": "JPM", "type": "주식"}, "UnitedHealth": {"tck": "UNH", "type": "주식"},
            "Visa": {"tck": "V", "type": "주식"}, "Exxon Mobil": {"tck": "XOM", "type": "주식"},
            "Mastercard": {"tck": "MA", "type": "주식"}, "Johnson & Johnson": {"tck": "JNJ", "type": "주식"},
            "Procter & Gamble": {"tck": "PG", "type": "주식"}, "Home Depot": {"tck": "HD", "type": "주식"},
            "AbbVie": {"tck": "ABBV", "type": "주식"}, "Chevron": {"tck": "CVX", "type": "주식"},
            "Walmart": {"tck": "WMT", "type": "주식"}, "Merck": {"tck": "MRK", "type": "주식"},
            "Coca-Cola": {"tck": "KO", "type": "주식"}, "Bank of America": {"tck": "BAC", "type": "주식"},
            "Thermo Fisher": {"tck": "TMO", "type": "주식"}, "Pfizer": {"tck": "PFE", "type": "주식"},
            "McDonald's": {"tck": "MCD", "type": "주식"}, "Danaher": {"tck": "DHR", "type": "주식"}
        },
        "코스피": {
            "삼성전자": {"tck": "005930", "type": "주식"}, "SK하이닉스": {"tck": "000660", "type": "주식"},
            "LG에너지솔루션": {"tck": "373220", "type": "주식"}, "삼성바이오로직스": {"tck": "207940", "type": "주식"},
            "현대차": {"tck": "005380", "type": "주식"}, "기아": {"tck": "000270", "type": "주식"},
            "셀트리온": {"tck": "068270", "type": "주식"}, "KB금융": {"tck": "105560", "type": "주식"},
            "POSCO홀딩스": {"tck": "005490", "type": "주식"}, "NAVER": {"tck": "035420", "type": "주식"},
            "신한지주": {"tck": "055550", "type": "주식"}, "삼성SDI": {"tck": "006400", "type": "주식"},
            "LG화학": {"tck": "051910", "type": "주식"}, "삼성생명": {"tck": "032830", "type": "주식"},
            "카카오": {"tck": "035720", "type": "주식"}, "메리츠금융지주": {"tck": "138040", "type": "주식"},
            "현대모비스": {"tck": "012330", "type": "주식"}, "하나금융지주": {"tck": "086790", "type": "주식"},
            "삼성물산": {"tck": "028260", "type": "주식"}, "LG전자": {"tck": "066570", "type": "주식"}
        },
        "코스닥": {
            "에코프로비엠": {"tck": "247540", "type": "주식"}, "에코프로": {"tck": "086520", "type": "주식"},
            "HLB": {"tck": "028300", "type": "주식"}, "알테오젠": {"tck": "191170", "type": "주식"},
            "엔켐": {"tck": "348370", "type": "주식"}, "리노공업": {"tck": "058470", "type": "주식"},
            "셀트리온제약": {"tck": "068760", "type": "주식"}, "레인보우로보틱스": {"tck": "277810", "type": "주식"},
            "HPSP": {"tck": "403870", "type": "주식"}, "삼천당제약": {"tck": "000250", "type": "주식"},
            "클래시스": {"tck": "214150", "type": "주식"}, "이오테크닉스": {"tck": "039030", "type": "주식"},
            "신성델타테크": {"tck": "065350", "type": "주식"}, "휴젤": {"tck": "145020", "type": "주식"},
            "동진쎄미켐": {"tck": "005290", "type": "주식"}, "실리콘투": {"tck": "257720", "type": "주식"},
            "솔브레인": {"tck": "357780", "type": "주식"}, "JYP Ent.": {"tck": "035900", "type": "주식"},
            "펄어비스": {"tck": "263750", "type": "주식"}, "리가켐바이오": {"tck": "141080", "type": "주식"}
        }
    }
    
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                # 마이그레이션 로직
                for cat in data:
                    for name in data[cat]:
                        if isinstance(data[cat][name], str):
                            data[cat][name] = {"tck": data[cat][name], "type": "코인" if "코인" in cat else "주식"}
                return data
            except: return default_data
    return default_data

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if 'tickers_dict' not in st.session_state:
    st.session_state.tickers_dict = load_data()

# 3. 고난의 역사 분석
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
            if dd <= -0.10:
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

# 4. 데이터 엔진
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
        target = f"{symbol}-USD" if asset_type == "코인" else symbol
        df = yf.download(target, period="max", progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        return df.dropna()
    except: return pd.DataFrame()

# 5. 사이드바
with st.sidebar:
    st.header("🔍 종목 조회")
    cat_list = list(st.session_state.tickers_dict.keys())
    category = st.selectbox("시장 선택", cat_list) if cat_list else None
    if category:
        name_list = list(st.session_state.tickers_dict[category].keys())
        selected_name = st.selectbox("종목 선택", name_list) if name_list else None
        tk_info = st.session_state.tickers_dict[category][selected_name] if selected_name else None
    else: tk_info = None
    
    st.divider()
    st.header("⚙️ 관리 메뉴")
    with st.expander("➕ 시장/종목 추가"):
        new_c = st.text_input("새 시장 이름")
        if st.button("시장 생성") and new_c:
            st.session_state.tickers_dict[new_c] = {}; save_data(st.session_state.tickers_dict); st.rerun()
        st.divider()
        if cat_list:
            target_cat = st.selectbox("추가할 시장", cat_list, key="add_cat")
            an, at = st.text_input("이름"), st.text_input("티커")
            aty = st.radio("타입", ["코인", "주식"])
            if st.button("추가 확정") and an and at:
                st.session_state.tickers_dict[target_cat][an] = {"tck": at, "type": aty}
                save_data(st.session_state.tickers_dict); st.rerun()

    with st.expander("🗑️ 종목 삭제"):
        if cat_list:
            dc = st.selectbox("시장", cat_list, key="d_c")
            dn = list(st.session_state.tickers_dict[dc].keys())
            if dn:
                dt = st.selectbox("종목", dn, key="d_t")
                if st.button("삭제 실행"):
                    del st.session_state.tickers_dict[dc][dt]
                    save_data(st.session_state.tickers_dict); st.rerun()

# 6. 메인 화면
if tk_info:
    df = fetch_data(tk_info['tck'], tk_info['type'])
    if not df.empty:
        tab1, tab2 = st.tabs(["📊 실시간 리포트", "🌋 고난의 역사"])
        fx_rate = get_realtime_fx()
        with tab1:
            cp = float(df['Close'].iloc[-1])
            dc = ((cp / df['Close'].iloc[-2]) - 1) * 100 if len(df) > 1 else 0
            hm = ((df['Close'] / df['Close'].cummax()) - 1).min() * 100
            cd = ((cp / df['Close'].max()) - 1) * 100
            m1, m2, m3, m4 = st.columns(4)
            if tk_info['type'] == "코인":
                kp = get_korea_prices().get(tk_info['tck'], 0)
                df_kr = ((kp / (cp * fx_rate)) - 1) * 100 if kp > 0 else 0
                m1.metric("해외 ($)", f"${cp:,.2f}", delta=f"{dc:+.2f}%")
                m2.metric("국내 (₩)", f"₩{kp:,.0f}"); m3.metric("김프 (%)", f"{df_kr:+.2f}%")
            else:
                m1.metric("현재가", f"{cp:,.2f}", delta=f"{dc:+.2f}%")
                m2.metric("최악 MDD", f"{hm:.2f}%"); m3.metric("현재 낙폭", f"{cd:.2f}%")
            m4.metric("실시간 환율", f"₩{fx_rate:,.1f}")
            fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
            fig.update_layout(template="plotly_dark", height=450, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
        with tab2:
            st.subheader(f"🌋 {selected_name} 역대 폭락 구간 (-10% 이상)")
            h_data = get_hardship_history(df)
            if h_data: st.table(pd.DataFrame(h_data).drop(columns=['raw_mdd']))
            else: st.info("대상 구간이 없습니다.")

    st.divider()
    st.subheader(f"📊 {category} 요약 테이블")
    summary, k_all = [], get_korea_prices()
    for i, (name, info) in enumerate(st.session_state.tickers_dict[category].items()):
        sdf = fetch_data(info['tck'], info['type'])
        if not sdf.empty:
            p, pr = float(sdf['Close'].iloc[-1]), float(sdf['Close'].iloc[-2]) if len(sdf)>1 else float(sdf['Close'].iloc[-1])
            ch = ((p / pr) - 1) * 100
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
        res = pd.DataFrame(summary).sort_values("_rank" if "코인" in category else "_mdd")
        cols = ["종목명", "변동"]
        if "해외($)" in res.columns: cols += ["해외($)", "국내(₩)", "차이(%)"]
        else: cols += ["현재가"]
        st.write(res[cols + ["최악 MDD", "현재 낙폭"]].to_html(escape=False, index=False), unsafe_allow_html=True)
else: st.warning("등록된 종목이 없습니다.")
