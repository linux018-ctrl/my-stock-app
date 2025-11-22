import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 網頁設定 ---
st.set_page_config(page_title="台股多頭獵人 V5.12", layout="wide")
st.title("📈 台股多頭獵人 V5.12 - 顯示邏輯優化版")

# --- 0.1 中文名稱對照表 ---
STOCK_NAMES = {
    "2330":"台積電", "2317":"鴻海", "2454":"聯發科", "2308":"台達電", "2303":"聯電", 
    "2881":"富邦金", "2882":"國泰金", "2412":"中華電", "1303":"南亞", "2002":"中鋼",
    "2382":"廣達", "3231":"緯創", "2356":"英業達", "6669":"緯穎", "2376":"技嘉", 
    "3017":"奇鋐", "2421":"建準", "3324":"雙鴻", "3338":"泰碩", "6230":"尼得科超眾",
    "3131":"弘塑", "3583":"辛耘", "6187":"萬潤", "3413":"京鼎", "3680":"家登", 
    "2449":"京元電", "3711":"日月光投控", "3081":"聯亞", "3450":"聯鈞", "3363":"上詮", 
    "4979":"華星光", "4908":"前鼎", "6442":"光聖", "2345":"智邦", "8996":"高力",
    "3661":"世芯-KY", "3443":"創意", "3035":"智原", "3529":"力旺", "6531":"愛普*", 
    "6643":"M31", "1513":"中興電", "1519":"華城", "1503":"士電", "1504":"東元", 
    "1609":"大亞", "6806":"森崴能源", "3708":"上緯投控", "9958":"世紀鋼",
    "2634":"漢翔", "8222":"寶一", "3005":"神基", "2630":"亞航", "5284":"jpp-KY", 
    "8033":"雷虎", "2646":"星宇航空", "3034":"聯詠", "2379":"瑞昱", 
    "2408":"南亞科", "2344":"華邦電", "8299":"群聯", "3260":"威剛", "2337":"旺宏", 
    "4967":"十銓", "3006":"晶豪科", "2451":"創見", "3037":"欣興", "8046":"南電", 
    "3189":"景碩", "2313":"華通", "2368":"金像電", "6269":"台郡", "2355":"敬鵬", 
    "5469":"瀚宇博", "5388":"中磊", "3704":"合勤控", "4977":"眾達-KY", "4906":"正文", 
    "5353":"台林", "2395":"研華", "6414":"樺漢", "6166":"凌華", "8050":"廣積", 
    "8114":"振樺電", "2327":"國巨", "2492":"華新科", "2456":"奇力新", "3026":"禾伸堂", 
    "6173":"信昌電", "5328":"華容", "3706":"神達", "2347":"聯強", "3004":"豐達科", 
    "1229":"聯華", "1231":"聯華食", "1605":"華新", "8163":"達方", "3049":"和鑫",
    "2328":"廣宇", "2354":"鴻準", "4958":"臻鼎-KY", "5243":"乙盛-KY",
    "1301":"台塑", "1326":"台化", "6505":"台塑化", "8039":"台抱",
    "2603":"長榮", "2609":"陽明", "2615":"萬海", "2637":"慧洋-KY", "2606":"裕民", 
    "2605":"新興", "2618":"長榮航", "2501":"國建", "2542":"興富發", "5522":"遠雄", 
    "2548":"華固", "2520":"冠德", "2505":"國揚", "1402":"遠東新",
    "6446":"藥華藥", "6472":"保瑞", "1795":"美時", "4105":"東洋", "4114":"健喬", 
    "1760":"中天", "2886":"兆豐金", "2891":"中信金", "2892":"第一金", "2884":"玉山金", 
    "2880":"華南金", "2357":"華碩", "2301":"光寶科", "2850":"新產"
}

# --- 1. 初始化 Session State ---
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = {
        "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "2364": "倫飛",
        "3005": "神基", "2382": "廣達", "3231": "緯創", "2603": "長榮",
        "3004": "豐達科", "2850": "新產"
    }
if 'scan_result_tab2' not in st.session_state: st.session_state.scan_result_tab2 = None
if 'scan_result_tab3' not in st.session_state: st.session_state.scan_result_tab3 = None
if 'sb_selected_code' not in st.session_state:
    st.session_state.sb_selected_code = list(st.session_state.watchlist.keys())[0]

# ==========================================
# 🛠️ 狀態管理中樞
# ==========================================
if 'pending_update' in st.session_state and st.session_state.pending_update:
    update_data = st.session_state.pending_update
    new_code = update_data['code']
    new_name = update_data['name']
    
    if new_code not in st.session_state.watchlist:
        st.session_state.watchlist[new_code] = new_name
    
    st.session_state.sb_selected_code = new_code
    st.toast(f"✅ 已鎖定：{new_name} ({new_code})，請查看儀表板", icon="🎉")
    st.session_state.pending_update = None

# --- 0. 內建熱門產業清單 ---
SECTOR_DICT = {
    "[概念] AI 伺服器/PC": ["2382", "3231", "2356", "6669", "2376", "3017", "2421", "2357", "2301"],
    "[概念] CoWoS/先進封裝": ["3131", "3583", "6187", "3413", "3680", "2449", "2330", "3711"],
    "[概念] 矽光子/CPO": ["3081", "3450", "3363", "4979", "4908", "6442", "2345"],
    "[概念] 散熱模組": ["3017", "3324", "2421", "3338", "6230", "8996"],
    "[概念] IP/ASIC設計": ["3661", "3443", "3035", "3529", "6531", "6643"],
    "[概念] 重電/綠能": ["1513", "1519", "1503", "1504", "1609", "6806", "3708", "9958"],
    "[概念] 軍工/無人機": ["2634", "8222", "3005", "2630", "5284", "8033", "2646"],
    "[電子] 半導體權值": ["2330", "2454", "2303", "3711", "2379", "3034"],
    "[電子] 記憶體族群": ["2408", "2344", "8299", "3260", "2337", "4967", "3006", "2451"],
    "[電子] PCB/載板": ["3037", "8046", "3189", "2313", "2368", "6269", "2355", "5469"],
    "[電子] 網通/光通訊": ["2345", "5388", "3704", "4977", "4906", "5353"],
    "[電子] 工業電腦(IPC)": ["2395", "6414", "3005", "6166", "8050", "8114"],
    "[電子] 被動元件": ["2327", "2492", "2456", "3026", "6173", "5328"],
    "[集團] 聯華神通集團": ["3005", "3706", "2347", "3004", "1229", "1231"],
    "[集團] 華新麗華集團": ["1605", "2344", "2492", "6173", "8163", "5469", "3049"],
    "[集團] 鴻海家族": ["2317", "2328", "2354", "3413", "6414", "4958", "5243"],
    "[集團] 台塑四寶": ["1301", "1303", "1326", "6505", "8039"],
    "[傳產] 航運/散裝": ["2603", "2609", "2615", "2637", "2606", "2605", "2618"],
    "[傳產] 營建資產": ["2501", "2542", "5522", "2548", "2520", "2505", "1402"],
    "[傳產] 生技醫療": ["6446", "6472", "1795", "4105", "4114", "1760"],
    "[金融] 金控雙雄+": ["2881", "2882", "2886", "2891", "2892", "2884", "2880"],
    "你的觀察名單": [] 
}

# --- 側邊欄：名單管理 ---
st.sidebar.header("📝 觀察名單管理")
with st.sidebar.expander("新增/移除個股"):
    def auto_fill_name():
        code = st.session_state.input_code
        if code:
            if code in STOCK_NAMES:
                st.session_state.input_name = STOCK_NAMES[code]
            else:
                try:
                    t = yf.Ticker(f"{code}.TW")
                    info = t.info
                    name = info.get('longName') or info.get('shortName')
                    if name:
                        st.session_state.input_name = name
                except:
                    pass

    c1, c2 = st.columns(2)
    new_code = c1.text_input("代號", placeholder="2395", key="input_code", on_change=auto_fill_name)
    new_name = c2.text_input("名稱", placeholder="自動帶入...", key="input_name")
    
    if st.button("➕ 新增"):
        if new_code and new_name:
            st.session_state.watchlist[new_code] = new_name
            st.rerun()

    remove_target = st.selectbox("移除股票", options=list(st.session_state.watchlist.keys()), format_func=lambda x: f"{x} {st.session_state.watchlist[x]}")
    if st.button("➖ 移除"):
        if remove_target in st.session_state.watchlist:
            del st.session_state.watchlist[remove_target]
            if remove_target == st.session_state.sb_selected_code:
                st.session_state.sb_selected_code = list(st.session_state.watchlist.keys())[0]
            st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("📊 個股參數")

selected_code = st.sidebar.selectbox(
    "選擇個股", 
    options=list(st.session_state.watchlist.keys()), 
    format_func=lambda x: f"{x} {st.session_state.watchlist[x]}",
    key="sb_selected_code" 
)

timeframe = st.sidebar.selectbox("K線週期", ["日K", "週K", "月K", "季K"])
interval_map = {"日K": "1d", "週K": "1wk", "月K": "1mo", "季K": "3mo"}
yf_interval = interval_map[timeframe]
lookback_bars = st.sidebar.slider(f"顯示 K 棒數量 ({timeframe})", 60, 365, 150)

# --- 共用函數 ---
def get_stock_data(symbol, bars=200, interval="1d"):
    ticker = f"{symbol}.TW"
    stock = yf.Ticker(ticker)
    if interval == "1d": period_str = f"{bars + 200}d"
    elif interval == "1wk": period_str = "5y"
    elif interval == "1mo": period_str = "max"
    elif interval == "3mo": period_str = "max"
    else: period_str = "2y"

    df = stock.history(period=period_str, interval=interval) 
    if df.empty:
        ticker = f"{symbol}.TWO" 
        stock = yf.Ticker(ticker)
        df = stock.history(period=period_str, interval=interval)
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
    bb = ta.bbands(df['Close'], length=20, std=2)
    df = pd.concat([df, bb], axis=1)
    return df

def get_fundamentals(stock_obj):
    try:
        info = stock_obj.info
        pe_raw = info.get('trailingPE')
        pe_ratio = round(pe_raw, 2) if pe_raw else "N/A"
        div_yield = info.get('dividendYield', 0)
        div_yield_str = f"{round(div_yield, 2)}%" if div_yield > 1 else f"{round(div_yield * 100, 2)}%" if div_yield else "N/A"
        rev_growth = info.get('revenueGrowth', 0)
        yoy_str = f"{round(rev_growth * 100, 2)}%" if rev_growth else "N/A"
        yoy_c = "normal" if isinstance(rev_growth, float) and rev_growth > 0 else "inverse"
        try:
            financials = stock_obj.quarterly_financials
            if 'Total Revenue' in financials.index:
                rev_curr = financials.loc['Total Revenue'].iloc[0]
                rev_prev = financials.loc['Total Revenue'].iloc[1]
                qoq_val = (rev_curr - rev_prev) / rev_prev
                qoq_str = f"{round(qoq_val * 100, 2)}%"
                qoq_c = "normal" if qoq_val > 0 else "inverse"
            else:
                qoq_str = "N/A"; qoq_c = "off"
        except:
            qoq_str = "N/A"; qoq_c = "off"
        return pe_ratio, div_yield_str, yoy_str, qoq_str, yoy_c, qoq_c
    except:
        return "N/A", "N/A", "N/A", "N/A", "off", "off"

# --- 介面分頁 ---
tab1, tab2, tab3 = st.tabs(["📊 個股儀表板", "🤖 觀察名單掃描", "🔥 Goodinfo轉折獵人"])

# ==========================================
# 分頁 1: 個股詳細分析
# ==========================================
with tab1:
    if selected_code:
        stock_name = st.session_state.watchlist.get(selected_code, selected_code)
        data, ticker_obj = get_stock_data(selected_code, lookback_bars, yf_interval)
        
        if not data.empty:
            df = calculate_indicators(data)
            df_view = df.tail(lookback_bars).copy()
            if yf_interval == "1d": df_view.index = df_view.index.strftime('%Y-%m-%d')
            else: df_view.index = df_view.index.strftime('%Y-%m-%d')

            latest = df.iloc[-1]
            prev = df.iloc[-2]
            pe, div, yoy, qoq, yoy_c, qoq_c = get_fundamentals(ticker_obj)

            st.subheader(f"{stock_name} ({selected_code}) - {timeframe}分析")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("收盤價", round(latest['Close'], 2), round(latest['Close'] - prev['Close'], 2))
            c2.metric("成交量", f"{int(latest['Volume']/1000)} 張", f"{int((latest['Volume']-prev['Volume'])/1000)} 張")
            macd_col = df.columns[df.columns.str.startswith('MACDh')][0]
            hist_val = latest[macd_col]
            c3.metric("MACD 動能", round(hist_val, 2), "🔴 增強" if hist_val > 0 and hist_val > prev[macd_col] else "🟢 減弱")
            ma_values = [latest['SMA5'], latest['SMA20'], latest['SMA60']]
            ma_spread = (max(ma_values) - min(ma_values)) / min(ma_values) * 100
            c4.metric("均線發散度", f"{round(ma_spread, 2)}%", "越低越好" if ma_spread < 5 else "發散中")

            f1, f2, f3, f4 = st.columns(4)
            f1.metric("本益比", pe)
            f2.metric("殖利率", div)
            f3.metric("營收 YoY", yoy, delta_color=yoy_c)
            f4.metric("營收 QoQ", qoq, delta_color=qoq_c)

            fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.2, 0.15, 0.15], subplot_titles=("K線 & 布林通道", "成交量", "MACD", "KD"))
            
            fig.add_trace(go.Candlestick(x=df_view.index, open=df_view['Open'], high=df_view['High'], low=df_view['Low'], close=df_view['Close'], name='K線'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_view.index, y=df_view['SMA20'], line=dict(color='orange', width=1), name='月線'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_view.index, y=df_view['SMA60'], line=dict(color='green', width=1), name='季線'), row=1, col=1)
            bbu_col = df.columns[df.columns.str.startswith('BBU')][0]
            bbl_col = df.columns[df.columns.str.startswith('BBL')][0]
            fig.add_trace(go.Scatter(x=df_view.index, y=df_view[bbu_col], line=dict(color='rgba(0, 0, 255, 0.3)', width=1), name='上軌'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_view.index, y=df_view[bbl_col], line=dict(color='rgba(0, 0, 255, 0.3)', width=1), name='下軌'), row=1, col=1)

            vol_colors = ['red' if c >= o else 'green' for c, o in zip(df_view['Close'], df_view['Open'])]
            fig.add_trace(go.Bar(x=df_view.index, y=df_view['Volume'], marker_color=vol_colors, name='成交量'), row=2, col=1)

            colors = ['red' if v >= 0 else 'green' for v in df_view[macd_col]]
            fig.add_trace(go.Bar(x=df_view.index, y=df_view[macd_col], marker_color=colors, name='MACD'), row=3, col=1)
            
            k_col = df.columns[df.columns.str.startswith('STOCHk')][0]
            d_col = df.columns[df.columns.str.startswith('STOCHd')][0]
            fig.add_trace(go.Scatter(x=df_view.index, y=df_view[k_col], line=dict(color='purple', width=1), name='K值'), row=4, col=1)
            fig.add_trace(go.Scatter(x=df_view.index, y=df_view[d_col], line=dict(color='orange', width=1, dash='dot'), name='D值'), row=4, col=1)
            fig.add_hline(y=80, line_dash="dash", line_color="gray", row=4, col=1)
            fig.add_hline(y=20, line_dash="dash", line_color="gray", row=4, col=1)
            
            fig.update_xaxes(type='category', dtick=10 if yf_interval=="1d" else 5) 
            fig.update_layout(height=900, showlegend=True, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 分頁 2: 觀察名單掃描器
# ==========================================
with tab2:
    st.subheader("🤖 觀察名單掃描器")
    st.info("💡 提示：點擊表格中的任一行，即可自動切換至該個股的詳細分析。")
    
    if st.button("🚀 掃描觀察名單"):
        scan_results = []
        progress_bar = st.progress(0)
        stocks_list = list(st.session_state.watchlist.items())
        total = len(stocks_list)
        
        for i, (code, name) in enumerate(stocks_list):
            df_scan, _ = get_stock_data(code, 100, interval="1d")
            if not df_scan.empty:
                try:
                    df_scan = calculate_indicators(df_scan)
                    latest = df_scan.iloc[-1]
                    prev = df_scan.iloc[-2]
                    cond_above_ma20 = latest['Close'] > latest['SMA20']
                    cond_volume = latest['Volume'] > latest['Vol_SMA5']
                    k_col = df_scan.columns[df_scan.columns.str.startswith('STOCHk')][0]
                    d_col = df_scan.columns[df_scan.columns.str.startswith('STOCHd')][0]
                    cond_kd_gold = latest[k_col] > latest[d_col] and prev[k_col] < prev[d_col]
                    macd_col = df_scan.columns[df_scan.columns.str.startswith('MACDh')][0]
                    cond_macd = latest[macd_col] > 0
                    cond_align = latest['SMA5'] > latest['SMA20'] > latest['SMA60']

                    scan_results.append({
                        "代號": code, "名稱": name,
                        "收盤價": latest['Close'], "漲幅%": ((latest['Close'] - prev['Close']) / prev['Close']) * 100,
                        "站上月線": "✅" if cond_above_ma20 else "❌",
                        "量能爆發": "🔥" if cond_volume else "➖",
                        "KD金叉": "✅" if cond_kd_gold else "➖",
                        "MACD多頭": "✅" if cond_macd else "➖",
                        "均線排列": "🌟" if cond_align else "➖"
                    })
                except: pass
            progress_bar.progress((i+1)/total)
        progress_bar.empty()
        st.session_state.scan_result_tab2 = pd.DataFrame(scan_results)

    if st.session_state.scan_result_tab2 is not None:
        res_df = st.session_state.scan_result_tab2
        
        # [V5.12 修正] 加入空值檢查
        if not res_df.empty:
            event = st.dataframe(
                res_df.style.applymap(lambda x: 'color: red' if isinstance(x, float) and x > 0 else 'color: green' if isinstance(x, float) and x < 0 else '', subset=['漲幅%']), 
                column_config={"收盤價": st.column_config.NumberColumn(format="%.2f"), "漲幅%": st.column_config.NumberColumn(format="%.2f%%")}, 
                use_container_width=True, height=500,
                on_select="rerun",
                selection_mode="single-row"
            )
            
            if event.selection.rows:
                selected_index = event.selection.rows[0]
                clicked_code = res_df.iloc[selected_index]["代號"]
                clicked_name = res_df.iloc[selected_index]["名稱"]
                
                if clicked_code != st.session_state.sb_selected_code:
                    st.session_state.pending_update = {"code": clicked_code, "name": clicked_name}
                    st.rerun()
        else:
            st.info("目前名單中未發現符合條件的數據。")

# ==========================================
# 分頁 3: 市場轉折獵人
# ==========================================
with tab3:
    st.subheader("🔥 Goodinfo 風格 - 轉折獵人")
    target_sector = st.selectbox("請選擇掃描分類", options=list(SECTOR_DICT.keys()))
    
    if st.button("🎯 開始掃描"):
        if target_sector == "你的觀察名單":
            scan_list = list(st.session_state.watchlist.keys())
        else:
            scan_list = SECTOR_DICT[target_sector]

        reversal_stocks = []
        progress = st.progress(0)
        total_scan = len(scan_list)

        for i, code in enumerate(scan_list):
            df_s, _ = get_stock_data(code, 120, interval="1d")
            if not df_s.empty:
                try:
                    df_s = calculate_indicators(df_s)
                    curr = df_s.iloc[-1]
                    prev = df_s.iloc[-2]
                    is_above_ma20 = curr['Close'] > curr['SMA20']
                    k_col = df_s.columns[df_s.columns.str.startswith('STOCHk')][0]
                    d_col = df_s.columns[df_s.columns.str.startswith('STOCHd')][0]
                    is_kd_cross = (curr[k_col] > curr[d_col]) and (prev[k_col] < prev[d_col]) and (curr[k_col] < 50)
                    macd_col = df_s.columns[df_s.columns.str.startswith('MACDh')][0]
                    is_macd_turning = curr[macd_col] > prev[macd_col]
                    is_break_ma60 = (curr['Close'] > curr['SMA60']) and (prev['Close'] < prev['SMA60'])
                    score = 0
                    reasons = []
                    if is_kd_cross: score += 1; reasons.append("KD低檔金叉")
                    if is_break_ma60: score += 1; reasons.append("突破季線")
                    if is_above_ma20 and is_macd_turning: score += 1; reasons.append("站穩月線+動能")

                    if score >= 1:
                        name = st.session_state.watchlist.get(code, STOCK_NAMES.get(code, code))
                        reversal_stocks.append({
                            "代號": code, "名稱": name, "收盤價": curr['Close'],
                            "訊號強度": "⭐⭐⭐" if score >= 2 else "⭐",
                            "觸發條件": " + ".join(reasons),
                            "KD值": f"{int(curr[k_col])}",
                            "季線乖離": f"{round(((curr['Close'] - curr['SMA60'])/curr['SMA60'])*100, 1)}%"
                        })
                except: pass
            progress.progress((i+1)/total_scan)
        progress.empty()
        st.session_state.scan_result_tab3 = pd.DataFrame(reversal_stocks)

    if st.session_state.scan_result_tab3 is not None:
        rev_df = st.session_state.scan_result_tab3
        
        # [V5.12 修正] 加入空值檢查
        if not rev_df.empty:
            st.success(f"在「{target_sector}」中發現 {len(rev_df)} 檔潛在轉折股！")
            event = st.dataframe(
                rev_df, 
                column_config={"收盤價": st.column_config.NumberColumn(format="%.2f")}, 
                use_container_width=True,
                on_select="rerun",
                selection_mode="single-row"
            )
            
            if event.selection.rows:
                selected_index = event.selection.rows[0]
                clicked_code = rev_df.iloc[selected_index]["代號"]
                clicked_name = rev_df.iloc[selected_index]["名稱"]
                
                if clicked_code != st.session_state.sb_selected_code:
                    st.session_state.pending_update = {"code": clicked_code, "name": clicked_name}
                    st.rerun()
        else:
            st.info(f"在「{target_sector}」中未發現明顯訊號。")
