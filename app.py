import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 網頁設定 ---
st.set_page_config(page_title="台股多頭獵人 V3.2", layout="wide")
st.title("📈 台股多頭獵人 V3.2 - 圖表完美對齊版")

# --- 1. Session State 初始化 ---
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = {
        "2364": "倫飛",
        "2330": "台積電",
        "2317": "鴻海",
        "2454": "聯發科",
        "3005": "神基"
    }

# --- 側邊欄 ---
st.sidebar.header("📝 觀察名單管理")
with st.sidebar.expander("新增/移除個股"):
    c1, c2 = st.columns(2)
    new_code = c1.text_input("代號", placeholder="3008")
    new_name = c2.text_input("名稱", placeholder="大立光")
    if st.button("➕ 新增"):
        if new_code and new_name:
            st.session_state.watchlist[new_code] = new_name
            st.rerun()

    remove_target = st.selectbox("移除股票", options=list(st.session_state.watchlist.keys()), format_func=lambda x: f"{x} {st.session_state.watchlist[x]}")
    if st.button("➖ 移除"):
        if remove_target in st.session_state.watchlist:
            del st.session_state.watchlist[remove_target]
            st.rerun()

st.sidebar.markdown("---")
selected_code = st.sidebar.selectbox("快速選擇", options=list(st.session_state.watchlist.keys()), format_func=lambda x: f"{x} {st.session_state.watchlist[x]}")
custom_stock = st.sidebar.text_input("自行輸入代號", "")
stock_id = custom_stock if custom_stock else selected_code
lookback_days = st.sidebar.slider("K棒觀察天數", 60, 365, 180)

# --- 核心函數 ---
def get_stock_data(symbol):
    ticker = f"{symbol}.TW"
    stock = yf.Ticker(ticker)
    df = stock.history(period=f"{lookback_days + 150}d") 
    if df.empty:
        ticker = f"{symbol}.TWO" 
        stock = yf.Ticker(ticker)
        df = stock.history(period=f"{lookback_days + 150}d")
    return df, stock

def calculate_indicators(df):
    df['SMA5'] = ta.sma(df['Close'], length=5)
    df['SMA20'] = ta.sma(df['Close'], length=20)
    df['SMA60'] = ta.sma(df['Close'], length=60)
    df['Vol_SMA5'] = ta.sma(df['Volume'], length=5)
    
    macd = ta.macd(df['Close'])
    df = pd.concat([df, macd], axis=1)
    
    k_d = ta.stoch(df['High'], df['Low'], df['Close'])
    df = pd.concat([df, k_d], axis=1)
    return df

def get_fundamentals(stock_obj):
    try:
        info = stock_obj.info
        
        # 本益比
        pe_raw = info.get('trailingPE')
        if pe_raw:
            pe_ratio = round(pe_raw, 2)
        else:
            pe_ratio = "N/A"
        
        # 殖利率
        div_yield = info.get('dividendYield', 0)
        if div_yield:
            if div_yield > 1:
                div_yield_str = f"{round(div_yield, 2)}%"
            else:
                div_yield_str = f"{round(div_yield * 100, 2)}%"
        else:
            div_yield_str = "N/A"
        
        # YoY
        rev_growth = info.get('revenueGrowth', 0)
        yoy_str = f"{round(rev_growth * 100, 2)}%" if rev_growth else "N/A"
        yoy_color = "off"
        if isinstance(rev_growth, float):
            yoy_color = "normal" if rev_growth > 0 else "inverse"

        # QoQ
        try:
            financials = stock_obj.quarterly_financials
            if 'Total Revenue' in financials.index:
                rev_data = financials.loc['Total Revenue']
                rev_curr = rev_data.iloc[0]
                rev_prev = rev_data.iloc[1]
                qoq_val = (rev_curr - rev_prev) / rev_prev
                qoq_str = f"{round(qoq_val * 100, 2)}%"
                qoq_color = "normal" if qoq_val > 0 else "inverse"
            else:
                qoq_str = "N/A"
                qoq_color = "off"
        except:
            qoq_str = "N/A (資料不足)"
            qoq_color = "off"

        return pe_ratio, div_yield_str, yoy_str, qoq_str, yoy_color, qoq_color
    except:
        return "N/A", "N/A", "N/A", "N/A", "off", "off"

# --- 主程式 ---
if stock_id:
    if stock_id in st.session_state.watchlist:
        stock_name = st.session_state.watchlist[stock_id]
    else:
        try:
            stock_name = "未知名稱"
        except:
            stock_name = ""

    data, ticker_obj = get_stock_data(stock_id)
    
    if not data.empty:
        if stock_name == "未知名稱":
            try:
                info = ticker_obj.info
                stock_name = info.get('longName') or info.get('shortName') or stock_id
            except:
                stock_name = stock_id

        df = calculate_indicators(data)
        df_view = df.tail(lookback_days).copy()
        
        # 關鍵：將索引轉為文字，這是移除假日的第一步
        df_view.index = df_view.index.strftime('%Y-%m-%d')
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        pe, div, yoy, qoq, yoy_c, qoq_c = get_fundamentals(ticker_obj)

        st.subheader(f"📊 {stock_name} ({stock_id}) 個股儀表板")
        
        # 第一列
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("收盤價", round(latest['Close'], 2), round(latest['Close'] - prev['Close'], 2))
        
        vol_today_lots = int(latest['Volume'] / 1000)
        vol_delta_lots = int((latest['Volume'] - prev['Volume']) / 1000)
        c2.metric("單日成交量", f"{vol_today_lots} 張", f"{vol_delta_lots} 張")
        
        macd_hist_col = df.columns[df.columns.str.startswith('MACDh')][0] 
        hist_val = latest[macd_hist_col]
        hist_color = "🔴 多頭增強" if hist_val > 0 and hist_val > prev[macd_hist_col] else "🟢 空頭/回檔"
        c3.metric("MACD 動能", round(hist_val, 2), hist_color)

        ma_values = [latest['SMA5'], latest['SMA20'], latest['SMA60']]
        ma_spread = (max(ma_values) - min(ma_values)) / min(ma_values) * 100
        c4.metric("均線發散度", f"{round(ma_spread, 2)}%", "越低越好" if ma_spread < 5 else "發散中")

        # 第二列
        st.markdown("### 🏥 基本面體質檢查")
        f1, f2, f3, f4 = st.columns(4)
        f1.metric("本益比 (P/E)", pe)
        f2.metric("殖利率 (Yield)", div)
        f3.metric("營收年增率 (YoY)", yoy, delta_color=yoy_c)
        f4.metric("營收季增率 (QoQ)", qoq, delta_color=qoq_c)

        # 繪圖
        st.markdown("---")
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                            vertical_spacing=0.05, 
                            row_heights=[0.6, 0.2, 0.2],
                            subplot_titles=("K線圖 & 均線", "成交量 & MACD", "KD 指標"))

        # K線
        fig.add_trace(go.Candlestick(x=df_view.index, open=df_view['Open'], high=df_view['High'],
                                     low=df_view['Low'], close=df_view['Close'], name='K線'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['SMA20'], line=dict(color='orange', width=1), name='月線'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['SMA60'], line=dict(color='green', width=1), name='季線'), row=1, col=1)

        # MACD
        colors = ['red' if v >= 0 else 'green' for v in df_view[macd_hist_col]]
        fig.add_trace(go.Bar(x=df_view.index, y=df_view[macd_hist_col], marker_color=colors, name='MACD'), row=2, col=1)

        # KD
        k_col = df.columns[df.columns.str.startswith('STOCHk')][0]
        d_col = df.columns[df.columns.str.startswith('STOCHd')][0]
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view[k_col], line=dict(color='purple', width=1), name='K值'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view[d_col], line=dict(color='orange', width=1, dash='dot'), name='D值'), row=3, col=1)
        
        fig.add_hline(y=80, line_dash="dash", line_color="gray", row=3, col=1)
        fig.add_hline(y=20, line_dash="dash", line_color="gray", row=3, col=1)

        # --- 🛠️ V3.2 修正重點 ---
        # 使用 update_xaxes 確保「所有」子圖表都忽略假日空隙
        fig.update_xaxes(type='category', dtick=10) 
        fig.update_layout(height=800, showlegend=False, xaxis_rangeslider_visible=False)

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.error(f"查無 {stock_id} 資料，請確認代號。")
