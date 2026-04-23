import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import plotly.graph_objects as go
import pandas as pd
import requests
import json
import os

# 1. 영구 저장 로직 (유지)
DB_FILE = "user_settings.json"
def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
    return {
        "코인": {"Bitcoin": "BTC", "Ethereum": "ETH", "Solana": "SOL"},
        "나스닥": {"NVIDIA": "NVDA", "Apple": "AAPL", "Tesla": "TSLA"},
        "코스피": {"삼성전자": "005930"}
    }

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

if 'tickers_dict' not in st.session_state:
    st.session_state.tickers_dict = load_data()

# 2. 고난의 역사 핵심 로직 (날짜 정밀 추적 및 10% 필터링)
def get_hardship_history(df):
    if df.empty: return []
    df = df.copy()
    
    # 누적 고점 계산
    df['peak'] = df['Close'].cummax()
    
    history = []
    current_peak_date = df.index[0]
    current_peak_price = df['Close'].iloc[0]
    
    # 마디별 최저점 추적용 변수
    madi_min_price = df['Close'].iloc[0]
    madi_min_date = df.index[0]
    
    for i in range(1, len(df)):
        # 새로운 신고가를 경신했을 때
        if df['Close'].iloc[i] > df['peak'].iloc[i-1]:
            # 이전 마디의 최대 하락률 계산
            drawdown = (madi_min_price / current_peak_price) - 1
            
            # 하락률이 -10% 미만(즉, 10% 이상 폭락)인 경우만 기록
            if drawdown <= -0.10:
                history.append({
                    "고점일 (Start)": current_peak_date.strftime('%Y-%m-%d'),
                    "저점일 (Bottom)": madi_min_date.strftime('%Y-%m-%d'),
                    "고점가": f"{current_peak_price:,.2f}",
                    "저점가": f"{madi_min_price:,.2f}",
                    "하락률": f"{drawdown * 100:.2f}%",
                    "raw_mdd": drawdown
                })
            
            # 새로운 고점으로 기준점 이동
            current_peak_date = df.index[i]
            current_peak_price = df['Close'].iloc[i]
            madi_min_price = current_peak_price
            madi_min_date = df.index[i]
        else:
            # 신고가 경신 전까지 최저점 갱신 확인
            if df['Close'].iloc[i] < madi_min_price:
                madi_min_price = df['Close'].iloc[i]
                madi_min_date = df.index[i]
                
    # 현재 진행 중인 마지막 마디 처리
    final_drawdown = (madi_min_price / current_peak_price) - 1
    if final_drawdown <= -0.10:
        history.append({
            "고점일 (Start)": current_peak_date.strftime('%Y-%m-%d'),
            "저점일 (Bottom)": madi_min_date.strftime('%Y-%m-%d'),
            "고점가": f"{current_peak_price:,.2f}",
            "저점가": f"{madi_min_price:,.2f}",
            "하락률": f"{final_drawdown * 100:.2f}% (진행중)",
            "raw_mdd": final_drawdown
        })
    
    # 하락률이 큰 순서(고통스러운 순서)대로 정렬
    return sorted(history, key=lambda x: x['raw_mdd'])

# (중략: 데이터 엔진 및 사이드바 UI는 이전과 동일)
# ... (생략된 부분은 위에서 구현한 영구 저장 및 API 로직을 그대로 사용합니다)

# 5. 메인 탭 구성
df = fetch_data(ticker, category)
if not df.empty:
    tab1, tab2 = st.tabs(["📊 실시간 분석", "🌋 고난의 역사 (-10% 이상)"])

    with tab1:
        # (기존 실시간 분석 차트 및 지표 출력)
        curr_p = df['Close'].iloc[-1]
        st.metric("현재가", f"{curr_p:,.2f}")
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=500)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader(f"🌋 {selected_name} : 역대 10% 이상 하락 구간")
        st.caption("신고가를 경신하기 전까지 발생했던 '의미 있는 폭락'의 시작점과 바닥점을 추적한 결과입니다.")
        
        history_data = get_hardship_history(df)
        
        if history_data:
            h_df = pd.DataFrame(history_data).drop(columns=['raw_mdd'])
            # 테이블 가독성을 위해 인덱스를 1부터 시작
            h_df.index = h_df.index + 1
            st.table(h_df)
            
            st.warning(f"💡 이 종목은 상장 이후 총 **{len(history_data)}번**의 10% 이상 하락 구간을 견디며 성장해왔습니다.")
        else:
            st.info("이 종목은 상장 이후 10% 이상의 하락을 겪지 않은 매우 강한 우상향 종목입니다.")
