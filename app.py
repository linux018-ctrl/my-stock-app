import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 網頁設定 ---
st.set_page_config(page_title="台股多頭獵人 V2.2", layout="wide")
st.title("📈 台股多頭獵人 V2.2 - 修正版")

# --- 1. 初始化 Session State (讓名單可以動態新增移除) ---
# 這是為了滿足您的第一個需求：動態管理觀察名單
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = {
        "2364": "倫飛",
        "2330": "台積電",
        "2317": "鴻海",
        "2454": "聯發科",
        "3005": "神基"
    }

# --- 側邊欄：名單管理區 ---
st.sidebar.header("📝 觀察名單管理")
with st.sidebar.expander("新增/移除個股"):
    # 新增功能
    c1, c2 = st.columns(2)
    new_code = c1.text_input("代號", placeholder="3008")
    new_name = c2.text_input("名稱", placeholder="大立光")
    if st.button("➕ 新增到名單"):
        if new_code and new_name:
            st.session_state.watchlist[new_code] = new_name
            st.success(f"已新增 {new_name}")
            st.rerun() # 重新整理畫面

    # 移除功能
    remove_target = st.selectbox("選擇要移除的股票", options=list(st.session_state.watchlist.keys()), format_func=lambda x: f"{x} {st.session_state.watchlist[x]}")
    if st.button("➖ 移除選定股票"):
        if remove_target in st.session_state.watchlist:
            del st.session_state.watchlist[remove_target]
            st.rerun()

# --- 側邊欄：選擇要分析的股票 ---
st.sidebar.markdown("---")
st.sidebar.header("🔍 股票分析設定")

# 下拉選單使用 session_state 裡面的最新名單
selected_code = st.sidebar.selectbox(
    "快速選擇", 
    options=list(st.session_state.watchlist.keys()), 
    format_func=lambda x: f"{x} {st.session_state.watchlist[x]}" 
)

# 自行輸入框
custom_stock = st.sidebar.text_input("自行輸入代號 (優先權高於選單)", "")

# 決定最終股票代號
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
    return df, stock # 多回傳一個 stock 物件用來查名字

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

# --- 主程式 ---
if stock_id:
    # 2. 解決全部個股顯示名稱問題
    # 先去我們自己的名單找，找不到再去問 Yahoo
    if stock_id in st.session_state.watchlist:
        stock_name = st.session_state.watchlist[stock_id]
    else:
        # 嘗試自動抓取名稱 (注意：Yahoo API 通常回傳英文名)
        try:
            # 這裡不呼叫 get_stock_data 以免重複請求，先設個預設值
            stock_name = "未知名稱" 
        except:
            stock_name = ""

    data, ticker_obj = get_stock_data(stock_id)
    
    if not data.empty:
        # 如果還沒有名字，試著從 ticker 物件抓取
        if stock_name == "未知名稱":
            try:
                info = ticker_obj.info
                # 優先抓中文簡稱，沒有就抓英文長名
                stock_name = info.get('longName') or info.get('shortName') or stock_id
            except:
                stock_name = stock_id

        df = calculate_indicators(data)
        df_view = df.tail(lookback_days).copy()
        
        # 3. 修復 K 線圖假日空缺 (關鍵步驟)
        # 將索引(日期)轉成文字格式，Plotly 就會把它當成「類別」而不是「時間軸」，從而忽略假日
        df_view.index = df_view.index.strftime('%Y-%m-%d')
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # --- 頂部資訊欄 ---
        st.subheader(f"📊 {stock_name} ({stock_id}) 個股儀表板")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("收盤價", round(latest['Close'], 2), round(latest['Close'] - prev['Close'], 2))
        
        # 4. 修正成交量標籤
        c2.metric("單日成交量", f"{int(latest['Volume'])} 張", int(latest['Volume'] - prev['Volume']))
        
        macd_hist_col = df.columns[df.columns.str.startswith('MACDh')][0] 
        hist_val = latest[macd_hist_col]
        hist_color = "🔴 多頭增強" if hist_val > 0 and hist_val > prev[macd_hist_col] else "🟢 空頭/回檔"
        c3.metric("MACD 動能", round(hist_val, 2), hist_color)

        ma_values = [latest['SMA5'], latest['SMA20'], latest['SMA60']]
        ma_spread = (max(ma_values) - min(ma_values)) / min(ma_values) * 100
        c4.metric("均線發散度", f"{round(ma_spread, 2)}%", "越低越好" if ma_spread < 5 else "發散中")

        # --- 繪圖區域 ---
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

        # 設定 X 軸為 category (類別) 模式，徹底移除假日空隙
        fig.update_layout(xaxis_type='category', xaxis_rangeslider_visible=False, height=800, showlegend=False)
        
        # 調整 X 軸標籤顯示頻率 (避免日期全部擠在一起)
        fig.update_xaxes(dtick=10) # 每 10 天顯示一次日期

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.error(f"查無 {stock_id} 資料，請確認代號。")import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 網頁設定 ---
st.set_page_config(page_title="台股多頭獵人 V2.1", layout="wide")
st.title("📈 台股多頭獵人 V2.1 - 趨勢與背離偵測")

# --- 1. 建立股票清單與名稱對照表 (您可以隨時在這裡增加) ---
# 格式： "代號": "中文名稱"
stock_map = {
    "2364": "倫飛",
    "2330": "台積電",
    "2317": "鴻海",
    "2454": "聯發科",
    "3231": "緯創",
    "2603": "長榮",
    "3035": "智原"
}

# --- 側邊欄：控制面板 ---
st.sidebar.header("控制面板")

# 下拉選單：顯示「代號 + 名稱」讓您好選
# format_func 是一個小技巧，用來把選單變漂亮
selected_code = st.sidebar.selectbox(
    "快速選擇觀察名單", 
    options=list(stock_map.keys()), 
    format_func=lambda x: f"{x} {stock_map[x]}" 
)

# 自行輸入框 (優先權高於選單)
custom_stock = st.sidebar.text_input("自行輸入代號 (如 3008)", "")

# 決定最終要查哪支股票
if custom_stock:
    stock_id = custom_stock
    # 如果輸入的代號剛好在我們的對照表裡，就抓出中文名，否則就留空
    stock_name = stock_map.get(custom_stock, "")
else:
    stock_id = selected_code
    stock_name = stock_map[selected_code]

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
    return df if not df.empty else None

def calculate_indicators(df):
    # 均線
    df['SMA5'] = ta.sma(df['Close'], length=5)
    df['SMA20'] = ta.sma(df['Close'], length=20)
    df['SMA60'] = ta.sma(df['Close'], length=60)
    
    # 成交量均量
    df['Vol_SMA5'] = ta.sma(df['Volume'], length=5)
    
    # MACD
    macd = ta.macd(df['Close'])
    df = pd.concat([df, macd], axis=1)
    
    # KD
    k_d = ta.stoch(df['High'], df['Low'], df['Close'])
    df = pd.concat([df, k_d], axis=1)
    
    return df

# --- 主程式 ---
if stock_id:
    data = get_stock_data(stock_id)
    
    if data is not None:
        df = calculate_indicators(data)
        df_view = df.tail(lookback_days).copy()
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # --- 頂部資訊欄 (這裡修改了標題顯示邏輯) ---
        # 如果有中文名就顯示 "倫飛 2364"，沒有就只顯示 "2364"
        title_text = f"{stock_name} {stock_id}" if stock_name else stock_id
        st.subheader(f"📊 {title_text} 個股儀表板")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("收盤價", round(latest['Close'], 2), round(latest['Close'] - prev['Close'], 2))
        c2.metric("成交量", int(latest['Volume']), int(latest['Volume'] - prev['Volume']))
        
        # MACD 邏輯
        macd_hist_col = df.columns[df.columns.str.startswith('MACDh')][0] 
        hist_val = latest[macd_hist_col]
        hist_color = "🔴 多頭增強" if hist_val > 0 and hist_val > prev[macd_hist_col] else "🟢 空頭/回檔"
        c3.metric("MACD 動能", round(hist_val, 2), hist_color)

        # 均線糾結邏輯
        ma_values = [latest['SMA5'], latest['SMA20'], latest['SMA60']]
        ma_spread = (max(ma_values) - min(ma_values)) / min(ma_values) * 100
        c4.metric("均線發散度", f"{round(ma_spread, 2)}%", "越低越好" if ma_spread < 5 else "發散中")

        # --- 繪圖區域 ---
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                            vertical_spacing=0.05, 
                            row_heights=[0.6, 0.2, 0.2],
                            subplot_titles=("K線圖 & 均線", "成交量 & MACD", "KD 指標"))

        # 1. K線
        fig.add_trace(go.Candlestick(x=df_view.index, open=df_view['Open'], high=df_view['High'],
                                     low=df_view['Low'], close=df_view['Close'], name='K線'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['SMA20'], line=dict(color='orange', width=1), name='月線'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['SMA60'], line=dict(color='green', width=1), name='季線'), row=1, col=1)

        # 2. MACD
        colors = ['red' if v >= 0 else 'green' for v in df_view[macd_hist_col]]
        fig.add_trace(go.Bar(x=df_view.index, y=df_view[macd_hist_col], marker_color=colors, name='MACD'), row=2, col=1)

        # 3. KD
        k_col = df.columns[df.columns.str.startswith('STOCHk')][0]
        d_col = df.columns[df.columns.str.startswith('STOCHd')][0]
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view[k_col], line=dict(color='purple', width=1), name='K值'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view[d_col], line=dict(color='orange', width=1, dash='dot'), name='D值'), row=3, col=1)
        
        fig.add_hline(y=80, line_dash="dash", line_color="gray", row=3, col=1)
        fig.add_hline(y=20, line_dash="dash", line_color="gray", row=3, col=1)

        fig.update_layout(xaxis_rangeslider_visible=False, height=800, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    else:

        st.error("查無資料，請確認代號。")
