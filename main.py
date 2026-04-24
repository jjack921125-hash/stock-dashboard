import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import requests
import json
import os

# 1. 초기 설정
DB_FILE = "user_settings.json"
DATA_VERSION = "2026.04.24.15" 

st.set_page_config(page_title="2026 Global Terminal", layout="wide")
st.markdown("""
    <style>
    .up-ticker { color: #F23645; font-weight: bold; } /* 상승 Red */
    .down-ticker { color: #0000FF; font-weight: bold; } /* 하락 Blue */
    .stMetric { background-color: #131722; border: 1px solid #363a45; padding: 15px; border-radius: 5px; }
    th { background-color: #1e222d !important; color: #d1d4dc !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 엔진 (코드ref 보존)
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
            "S&P 500 (나스닥 제외 20위)": {
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
                "알테오젠": {"tck": "191170", "type": "주식"}, "HLB": {"tck": "028300", "type": "주식"},
                "에코프로비엠": {"tck": "247540", "type": "주식"}, "에코프로": {"tck": "086520", "type": "주식"},
                "엔켐": {"tck": "348370", "type": "주식"}, "리노공업": {"tck": "058470", "type": "주식"},
                "삼천당제약": {"tck": "000250", "type": "주식"}, "셀트리온제약": {"tck": "068760", "type": "주식"},
                "레인보우로보틱스": {"tck": "277810", "type": "주식"}, "HPSP": {"tck": "403870", "type": "주식"},
                "클래시스": {"tck": "214150", "type": "주식"}, "이오테크닉스": {"tck": "039030", "type": "주식"},
                "신성델타테크": {"tck": "065350", "type": "주식"}, "휴젤": {"tck": "145020", "type": "주식"},
                "동진쎄미켐": {"tck": "005290", "type": "주식"}, "실리콘투": {"tck": "257720", "type": "주식"},
                "솔브레인": {"tck": "357780", "type": "주식"}, "JYP Ent.": {"tck": "035900", "type": "주식"},
                "펄어비스": {"tck": "263750", "type": "주식"}, "리가켐바이오": {"tck": "141080", "type": "주식"}
            }
        }
    }
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if data.get("version") == DATA_VERSION: return data["tickers"]
            except: pass
    save_data(default_data["tickers"])
    return default_data["tickers"]

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump({"version": DATA_VERSION, "tickers": data}, f, ensure_ascii=False, indent=4)

if 'tickers_dict' not in st.session_state:
    st.session_state.tickers_dict = load_data()

# 3. 고난의 역사 분석 함수 (코드ref 보존)
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
                history.append({"고점일": cp_date.strftime('%Y-%m-%d'), "저점일": m_min_date.strftime('%Y-%m-%d'), "하락률": f"{dd * 100:.2f}%", "dt_key": cp_date})
            cp_date, cp_price = df.index[i], df['Close'].iloc[i]
            m_min_price, m_min_date = cp_price, df.index[i]
        elif df['Close'].iloc[i] < m_min_price:
            m_min_price, m_min_date = df['Close'].iloc[i], df.index[i]
    final_dd = (m_min_price / cp_price) - 1
    if final_dd <= -0.10:
        history.append({"고점일": cp_date.strftime('%Y-%m-%d'), "저점일": m_min_date.strftime('%Y-%m-%d'), "하락률": f"{final_dd * 100:.2f}% (진행중)", "dt_key": cp_date})
    return sorted(history, key=lambda x: x['dt_key'], reverse=True)

# 4. 데이터 페칭 (변경점 2 반영: 시간봉 처리 최적화)
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
    # [설명] yfinance 정책상 1h/4h 봉은 데이터 기간(period)이 최근 730일 이내여야 조회가 가능합니다.
    tf_map = {
        "1h": ("730d", "60m"), 
        "4h": ("730d", "90m"), # yf는 공식 4h를 미지원하므로 90m 혹은 1d 권장하나 90m으로 설정
        "1일": ("max", "1d"), 
        "1주": ("max", "1wk"), 
        "1달": ("max", "1mo"), 
        "1년": ("max", "3mo")
    }
    period, interval = tf_map.get(timeframe, ("max", "1d"))
    try:
        if asset_type == "주식" and symbol.isdigit():
            # 한국 주식의 시간봉 데이터는 yf에서 제한적이므로 fdr 사용 (fdr은 일봉 이상 최적화됨)
            if timeframe in ["1h", "4h"]:
                df = yf.download(f"{symbol}.KS", period="730d", interval=interval, progress=False)
                if df.empty: df = yf.download(f"{symbol}.KQ", period="730d", interval=interval, progress=False)
            else:
                df = fdr.DataReader(symbol, "1990-01-01")
                if timeframe == "1주": df = df.resample('W').last()
                elif timeframe == "1달": df = df.resample('M').last()
                elif timeframe == "1년": df = df.resample('Y').last()
            return df.dropna()
        
        target = f"{symbol}-USD" if asset_type == "코인" else symbol
        df = yf.download(target, period=period, interval=interval, progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        return df.dropna()
    except: return pd.DataFrame()

# 5. 사이드바 (코드ref 보존)
with st.sidebar:
    st.header("🔍 Market Explorer")
    cat_list = list(st.session_state.tickers_dict.keys())
    category = st.selectbox("시장", cat_list)
    selected_name = st.selectbox("종목", list(st.session_state.tickers_dict[category].keys()))
    tk_info = st.session_state.tickers_dict[category][selected_name]

    st.divider()
    with st.expander("➕ 종목 추가 / 시장 생성"):
        an, at = st.text_input("종목명"), st.text_input("티커")
        aty = st.radio("유형", ["주식", "코인"], horizontal=True)
        if st.button("추가") and an and at:
            st.session_state.tickers_dict[category][an] = {"tck": at, "type": aty}
            save_data(st.session_state.tickers_dict); st.rerun()
        st.divider()
        new_c = st.text_input("새 시장 이름")
        if st.button("시장 생성") and new_c:
            st.session_state.tickers_dict[new_c] = {}; save_data(st.session_state.tickers_dict); st.rerun()

    with st.expander("🗑️ 삭제"):
        dt = st.selectbox("삭제 대상", list(st.session_state.tickers_dict[category].keys()))
        if st.button("종목 삭제"):
            del st.session_state.tickers_dict[category][dt]
            save_data(st.session_state.tickers_dict); st.rerun()

# 6. 메인 화면
if tk_info:
    c1, c2 = st.columns([7, 3])
    with c1: st.title(f"{selected_name} · {tk_info['tck']}")
    # [설명] 시간봉(1h, 4h) 선택 시 주식은 yfinance 서버 상황에 따라 캔들이 누락될 수 있으며, 이때는 일봉으로 자동 대체되거나 공백으로 나옵니다.
    with c2: tf = st.segmented_control("Interval", ["1h", "4h", "1일", "1주", "1달", "1년"], default="1일")

    df = fetch_data(tk_info['tck'], tk_info['type'], tf)
    if not df.empty:
        fx_rate = get_realtime_fx()
        cp = float(df['Close'].iloc[-1]); dc = ((cp / df['Close'].iloc[-2]) - 1) * 100 if len(df) > 1 else 0
        hm = ((df['Close'] / df['Close'].cummax()) - 1).min() * 100; cd = ((cp / df['Close'].max()) - 1) * 100
        
        m1, m2, m3, m4 = st.columns(4)
        if tk_info['type'] == "코인":
            kp = get_korea_prices().get(tk_info['tck'], 0)
            m1.metric("Price ($)", f"${cp:,.2f}", delta=f"{dc:+.2f}%")
            m2.metric("KRW (₩)", f"₩{kp:,.0f}")
            m3.metric("Kimchi (%)", f"{((kp/(cp*fx_rate))-1)*100:+.2f}%" if kp>0 else "-")
        else:
            m1.metric("Current", f"{cp:,.2f}", delta=f"{dc:+.2f}%")
            m2.metric("Max MDD", f"{hm:.2f}%"); m3.metric("Drawdown", f"{cd:.2f}%")
        m4.metric("FX Rate", f"₩{fx_rate:,.1f}")

        # [변경점 1] 가격 및 거래량 색상 변경 (상승 Red, 하락 Blue)
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.8, 0.2])
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                                     increasing_fillcolor='#F23645', increasing_line_color='#F23645', # 상승 Red
                                     decreasing_fillcolor='#0000FF', decreasing_line_color='#0000FF'), row=1, col=1) # 하락 Blue
        
        vol_colors = ['rgba(242, 54, 69, 0.5)' if c >= o else 'rgba(0, 0, 255, 0.5)' for o, c in zip(df['Open'], df['Close'])]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=vol_colors, marker_line_width=0), row=2, col=1)
        
        fig.update_layout(template="plotly_dark", paper_bgcolor='#131722', plot_bgcolor='#131722', height=800, 
                          xaxis_rangeslider_visible=False, margin=dict(t=10, b=10, l=10, r=10), hovermode='x unified')
        fig.update_yaxes(side="right"); st.plotly_chart(fig, use_container_width=True)

        # [보존] 고난의 역사
        st.subheader("🌋 고난의 역사 (Major Drawdowns)")
        df_daily = fetch_data(tk_info['tck'], tk_info['type'], "1일")
        h_data = get_hardship_history(df_daily)
        if h_data: st.table(pd.DataFrame(h_data).drop(columns=['dt_key']))
        
        # [변경점 3] 일괄 분석 테이블 (코인 카테고리만 시총순 정렬 유지)
        st.divider()
        st.subheader(f"📊 {category} 일괄 분석")
        summary_data, k_all = [], get_korea_prices()
        
        # [설명] 원본 리스트 순서가 시총 순이므로 정렬 없이 그대로 순회하면 시총 순이 유지됩니다.
        for name, info in st.session_state.tickers_dict[category].items():
            sdf = fetch_data(info['tck'], info['type'], "1일")
            if not sdf.empty:
                cur_p = float(sdf['Close'].iloc[-1])
                chg = ((cur_p / sdf['Close'].iloc[-2]) - 1) * 100 if len(sdf) > 1 else 0
                mdd = ((cur_p / sdf['Close'].max()) - 1) * 100
                tag = "up-ticker" if chg >= 0 else "down-ticker"
                row = {"종목": name, "변동": f'<span class="{tag}">{chg:+.2f}%</span>', "낙폭": f"{mdd:.2f}%"}
                if info['type'] == "코인":
                    kp = k_all.get(info['tck'], 0)
                    row["해외($)"] = f"{cur_p:,.2f}"; row["국내(₩)"] = f"{kp:,.0f}"
                else: row["현재가"] = f"{cur_p:,.2f}"
                summary_data.append(row)
        
        if summary_data:
            # [변경점 3 적용] '코인' 시장일 때는 사용자 입력 순서(시총순)를 보존하고, 주식은 기존처럼 낙폭순 정렬을 원하시면 sort_values를 사용하세요.
            # 여기서는 요청하신 대로 코인은 입력 순(시총순) 그대로 노출합니다.
            res_df = pd.DataFrame(summary_data)
            st.write(res_df.to_html(escape=False, index=False), unsafe_allow_html=True)
