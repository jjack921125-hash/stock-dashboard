import streamlit as st
import FinanceDataReader as fdr
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import json
import os
from datetime import datetime

st.set_page_config(page_title="주식/코인 대시보드", page_icon="📈", layout="wide")
st.title("📈 주식/코인 대시보드")

# ───────────────────────────────────────────
# 1. 데이터 저장 및 로드
# ───────────────────────────────────────────
SAVE_FILE = "data.json"
DEFAULT_TICKERS = {
    "코인": {"Bitcoin": "BTC", "Ethereum": "ETH", "Solana": "SOL", "XRP": "XRP"},
    "나스닥": {"Apple": "AAPL", "Microsoft": "MSFT", "NVIDIA": "NVDA", "Tesla": "TSLA"},
    "S&P500": {"JPMorgan": "JPM", "Visa": "V", "ExxonMobil": "XOM"},
    "코스피": {"삼성전자": "005930", "SK하이닉스": "000660", "현대차": "005380"},
    "코스닥": {"에코프로비엠": "247540", "HLB": "028300"}
}

if "tickers" not in st.session_state:
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            st.session_state.tickers = json.load(f)
    else:
        st.session_state.tickers = DEFAULT_TICKERS.copy()

def save_data(data):
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ───────────────────────────────────────────
# 2. [가장 중요한] 통합 데이터 호출 함수
# ───────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_any_data(symbol, market_name):
    try:
        if market_name == "코인":
            # 아까 성공했던 로직 그대로 적용
            target = f"{symbol}-USD"
            df = yf.download(target, period="1y", progress=False)
            if df.empty: return pd.DataFrame()
            
            # 멀티인덱스 평탄화
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # 환율 적용
            fx = yf.download("USDKRW=X", period="1d", progress=False)
            if not fx.empty:
                if isinstance(fx.columns, pd.MultiIndex):
                    fx.columns = fx.columns.get_level_values(0)
                rate = float(fx['Close'].iloc[-1])
            else:
                rate = 1380.0
                
            res = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
            for col in ['Open', 'High', 'Low', 'Close']:
                res[col] = res[col] * rate
            return res
        
        elif market_name in ["나스닥", "S&P500"]:
            # 미국 주식도 yfinance로 통일 (가장 안전함)
            df = yf.download(symbol, period="1y", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        
        else:
            # 한국 주식은 fdr 사용
            df = fdr.DataReader(symbol, "2024-01-01")
            return df
    except:
        return pd.DataFrame()

# ───────────────────────────────────────────
# 3. 사이드바 UI
# ───────────────────────────────────────────
st.sidebar.title("⚙️ 설정")
market_list = list(st.session_state.tickers.keys())
market = st.sidebar.selectbox("시장 선택", market_list)
ticker_dict = st.session_state.tickers[market]
selected_name = st.sidebar.selectbox("종목 선택", list(ticker_dict.keys()))
ticker = ticker_dict[selected_name]

# 종목 관리 (익스팬더로 깔끔하게 정리)
with st.sidebar.expander("➕ 종목 추가/삭제"):
    new_n = st.text_input("이름")
    new_t = st.text_input("티커")
    if st.button("추가"):
        if new_n and new_t:
            st.session_state.tickers[market][new_n] = new_t.strip().upper()
            save_data(st.session_state.tickers)
            st.rerun()
    if st.button("🗑️ 현재 종목 삭제"):
        if len(st.session_state.tickers[market]) > 1:
            del st.session_state.tickers[market][selected_name]
            save_data(st.session_state.tickers)
            st.rerun()

# ───────────────────────────────────────────
# 4. 메인 화면 출력
# ───────────────────────────────────────────
with st.spinner("데이터를 실시간으로 분석 중..."):
    main_df = fetch_any_data(ticker, market)

if main_df.empty:
    st.error(f"❌ '{selected_name}' 데이터를 불러올 수 없습니다.")
    st.info("야후 파이낸스 서버 지연일 수 있습니다. '시장 선택'을 다른 걸로 바꿨다가 다시 선택해 보세요.")
else:
    # 상단 지표 (float 변환으로 에러 원천 차단)
    c_p = float(main_df['Close'].iloc[-1])
    h_p = float(main_df['High'].max())
    p_p = float(main_df['Close'].iloc[-2]) if len(main_df) > 1 else c_p
    chg = ((c_p - p_p) / p_p) * 100
    
    unit = "₩" if market in ["코스피", "코스닥", "코인"] else "$"
    
    col1, col2, col3 = st.columns(3)
    col1.metric("현재가", f"{unit}{c_p:,.0f}" if unit=="₩" else f"{unit}{c_p:,.2f}", f"{chg:+.2f}%")
    col2.metric("기간 최고가", f"{unit}{h_p:,.0f}" if unit=="₩" else f"{unit}{h_p:,.2f}")
    col3.metric("최고점 대비 하락률", f"{((c_p/h_p)-1)*100:.2f}%")

    # 캔들 차트
    fig = go.Figure(data=[go.Candlestick(
        x=main_df.index,
        open=main_df['Open'], high=main_df['High'],
        low=main_df['Low'], close=main_df['Close'],
        increasing_line_color='red', decreasing_line_color='blue'
    )])
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=500, title=f"{selected_name} 차트")
    st.plotly_chart(fig, use_container_width=True)

    # 하단 종목 요약 테이블
    st.markdown("---")
    st.subheader(f"📊 {market} 전 종목 요약")
    
    summary_list = []
    for name, tck in ticker_dict.items():
        # 하단 리스트는 속도를 위해 캐싱된 데이터 사용
        s_df = fetch_any_data(tck, market)
        if not s_df.empty:
            curr = float(s_df['Close'].iloc[-1])
            high = float(s_df['High'].max())
            mdd = ((curr / high) - 1) * 100
            summary_list.append({
                "종목명": name,
                "현재가": f"{unit}{curr:,.0f}" if unit=="₩" else f"{unit}{curr:,.2f}",
                "하락률": f"{mdd:.2f}%",
                "raw_mdd": mdd
            })
    
    if summary_list:
        res_df = pd.DataFrame(summary_list).sort_values("raw_mdd")
        st.table(res_df.drop(columns=["raw_mdd"]))
