import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import requests
import json
import os

# 1. 초기 설정 및 스타일
DB_FILE = "user_settings.json"
DATA_VERSION = "2026.04.24.01" # 버전 업데이트를 통해 최신 로직 강제 반영

st.set_page_config(page_title="2026 Global Terminal", layout="wide")
st.markdown("""
    <style>
    .up-ticker { color: #FF4B4B; font-weight: bold; }
    .down-ticker { color: #4B9BFF; font-weight: bold; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 엔진 및 로드 로직 (버전 관리 포함)
def load_data():
    default_data = {
        "version": DATA_VERSION,
        "tickers": {
            "코인 (Top 20)": {
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
            "코스피": {
                "삼성전자": {"tck": "005930", "type": "주식"}, "SK하이닉스": {"tck": "000660", "type": "주식"},
                "현대차": {"tck": "005380", "type": "주식"}, "셀트리온": {"tck": "068270", "type": "주식"}
            }
        }
    }

    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if data.get("version") != DATA_VERSION:
                    save_data(default_data)
                    return default_data["tickers"]
                return data["tickers"]
            except: 
                save_data(default_data)
                return default_data["tickers"]
    else:
        save_data(default_data)
        return default_data["tickers"]

def save_data(data):
    save_obj = {"version": DATA_VERSION, "tickers": data if "tickers" not in data else data["tickers"]}
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(save_obj, f, ensure_ascii=False, indent=4)

if 'tickers_dict' not in st.session_state:
    st.session_state.tickers_dict = load_data()

# 3. 고난의 역사 분석 로직
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
                    "하락률": f"{dd * 100:.2f}%", "dt_key": cp_date
                })
            cp_date, cp_price = df.index[i], df['Close'].iloc[i]
            m_min_price, m_min_date = cp_price, df.index[i]
        elif df['Close'].iloc[i] < m_min_price:
            m_min_price, m_min_date = df['Close'].iloc[i], df.index[i]
            
    final_dd = (m_min_price / cp_price) - 1
    if final_dd <= -0.10:
        history.append({"고점일 (Start)": cp_date.strftime('%Y-%m-%d'), "저점일 (Bottom)": m_min_date.strftime('%Y-%m-%d'),
                        "하락률": f"{final_dd * 100:.2f}% (진행중)", "dt_key": cp_date})
    
    sorted_history = sorted(history, key=lambda x: x['dt_key'], reverse=True)
    for item in sorted_history: item.pop('dt_key', None)
    return sorted_history

# 4. 데이터 엔진
@st.cache_data(ttl=60)
def get_realtime_fx():
    try: return float(yf.download("USDKRW=X", period="1d", progress=False)['Close'].iloc[-1])
    except: return 1450.0

@st.cache_data(ttl=5)
def get_korea_prices():
    try:
        res = requests.get("https://api.bithumb.com/public/ticker/ALL_KRW", timeout=5).json()
        return {k: float(v['closing_price']) for k, v in res['data'].items() if isinstance(v, dict)}
    except: return {}

def fetch_data(symbol, asset_type, timeframe="1일"):
    tf_map = {"1h": ("2y", "60m"), "4h": ("2y", "90m"), "1일": ("max", "1d"), 
              "1주": ("max", "1wk"), "1달": ("max", "1mo"), "1년": ("max", "1y")}
    period, interval = tf_map.get(timeframe, ("max", "1d"))

    try:
        if asset_type == "주식" and symbol.isdigit(): 
            df = fdr.DataReader(symbol, "1990-01-01")
        else:
            target = f"{symbol}-USD" if asset_type == "코인" else symbol
            df = yf.download(target, period=period, interval=interval, progress=False)
        
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        return df.dropna(subset=['Close'])
    except: return pd.DataFrame()

# 5. 사이드바 관리
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
    with st.expander("➕ 시장/종목 추가"):
        new_c = st.text_input("새 시장 이름")
        if st.button("시장 생성") and new_c:
            st.session_state.tickers_dict[new_c] = {}; save_data(st.session_state.tickers_dict); st.rerun()
        if cat_list:
            target_cat = st.selectbox("대상 시장", cat_list, key="add_target")
            an, at = st.text_input("이름"), st.text_input("티커")
            aty = st.radio("타입", ["코인", "주식"])
            if st.button("추가 확정") and an and at:
                st.session_state.tickers_dict[target_cat][an] = {"tck": at, "type": aty}
                save_data(st.session_state.tickers_dict); st.rerun()

# 6. 메인 화면
if tk_info:
    c1, c2 = st.columns([7, 3])
    with c1: st.title(f"{selected_name} ({tk_info['tck']})")
    with c2: tf = st.segmented_control("봉 주기", ["1h", "4h", "1일", "1주", "1달", "1년"], default="1일")

    df = fetch_data(tk_info['tck'], tk_info['type'], tf)
    
    if not df.empty:
        tab1, tab2 = st.tabs(["📊 실시간 분석 차트", "🌋 고난의 역사"])
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

            # 서브플롯 차트 (캔들 70% : 거래량 30%)
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                               vertical_spacing=0.05, row_heights=[0.7, 0.3])

            # 1. 캔들차트
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                name="Price", increasing_line_color='#FF4B4B', decreasing_line_color='#4B9BFF'
            ), row=1, col=1)

            # 2. 거래량 바차트 (가독성 보정)
            colors = ['#FF4B4B' if c >= o else '#4B9BFF' for o, c in zip(df['Open'], df['Close'])]
            fig.add_trace(go.Bar(
                x=df.index, y=df['Volume'], name="Volume", 
                marker_color=colors, opacity=0.8, marker_line_width=0
            ), row=2, col=1)

            fig.update_layout(template="plotly_dark", height=700, showlegend=False, 
                              xaxis_rangeslider_visible=False, margin=dict(t=10, b=10, l=10, r=10))
            fig.update_yaxes(title_text="Price", row=1, col=1)
            fig.update_yaxes(title_text="Volume", showgrid=False, row=2, col=1) 
            
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            st.subheader(f"🌋 {selected_name} 역대 폭락 구간 (최신순)")
            df_full = fetch_data(tk_info['tck'], tk_info['type'], "1일")
            h_data = get_hardship_history(df_full)
            if h_data: st.table(pd.DataFrame(h_data))
            else: st.info("대상 구간이 없습니다.")

    st.divider()
    st.subheader(f"📊 {category} 전체 요약")
    summary, k_all = [], get_korea_prices()
    for i, (name, info) in enumerate(st.session_state.tickers_dict[category].items()):
        sdf = fetch_data(info['tck'], info['type'], "1일")
        if not sdf.empty:
            p = float(sdf['Close'].iloc[-1])
            pr = float(sdf['Close'].iloc[-2]) if len(sdf)>1 else p
            ch, hm = ((p/pr)-1)*100, ((sdf['Close']/sdf['Close'].cummax())-1).min()*100
            cd = ((p/sdf['Close'].max())-1)*100
            tag = "up-ticker" if ch >= 0 else "down-ticker"
            row = {"종목명": name, "변동": f'<span class="{tag}">{ch:+.2f}%</span>', "최악 MDD": f"{hm:.2f}%", "현재 낙폭": f"{cd:.2f}%", "_mdd": cd, "_rank": i}
            if info['type'] == "코인":
                kp = k_all.get(info['tck'], 0)
                row["해외($)"] = f"${p:,.2f}"; row["국내(₩)"] = f"₩{kp:,.0f}"
                row["차이(%)"] = f"{((kp/(p*fx_rate))-1)*100:+.2f}%" if kp > 0 else "-"
            else: row["현재가"] = f"{p:,.2f}"
            summary.append(row)
    if summary:
        res = pd.DataFrame(summary).sort_values("_rank" if "코인" in category else "_mdd")
        cols = ["종목명", "변동"]
        cols += ["해외($)", "국내(₩)", "차이(%)"] if "해외($)" in res.columns else ["현재가"]
        st.write(res[cols + ["최악 MDD", "현재 낙폭"]].to_html(escape=False, index=False), unsafe_allow_html=True)
else:
    st.warning("사이드바에서 종목을 선택해주세요.")
