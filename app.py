import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import json
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import os
import feedparser
import time
from fugle_marketdata import RestClient
from datetime import datetime

# --- 網頁設定 ---
st.set_page_config(page_title="艾倫杭特 V18.4", layout="wide")
st.title("📈 艾倫杭特 V18.4 - 結構強化穩定版")

# ==========================================
# 🔑 API 金鑰設定區
# ==========================================
LINE_USER_ID = "U2e18c346fe075d2f62986166a4a6ef1c" 
LINE_CHANNEL_TOKEN = "DNsc+VqdlEliUHVd92ozW59gLdEDJULKIslQOqlTsP6qs5AY3Ydaj8X8l1iShfRHFzWpL++lbb5e4GiDHrioF6JdwmsiA/OHjaB4ZZYGG1TqwUth6hfcbHrHgVscPSZmVGIx4n/ZXYAZhPrvGCKqiwdB04t89/1O/w1cDnyilFU="
FUGLE_API_KEY = "NTBjOGQ4ODgtYjFlMi00MzdjLThiNTQtZGI1NGFkODlkZTMyIDg1NWRhZjhlLWY5YTQtNGU3OC1iOGJmLWRhNDQwNGU1MmZjNA==" 

# --- 建立 Fugle Client ---
try:
    fugle_client = RestClient(api_key=FUGLE_API_KEY)
except:
    fugle_client = None

# --- LINE 發送函數 ---
def send_line_message(message_text):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_CHANNEL_TOKEN}"}
    payload = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": message_text}]}
    try: requests.post(url, headers=headers, data=json.dumps(payload))
    except: pass

# --- 資料存取 ---
WATCHLIST_FILE = 'watchlist.json'
DEFAULT_WATCHLIST = {
    "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "2364": "倫飛",
    "3005": "神基", "2382": "廣達", "3231": "緯創", "2603": "長榮",
    "3004": "豐達科", "2850": "新產"
}
def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: return DEFAULT_WATCHLIST.copy()
    return DEFAULT_WATCHLIST.copy()

def save_watchlist(data):
    try:
        with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)
    except: pass

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
    "2880":"華南金", "2357":"華碩", "2301":"光寶科", "2850":"新產", "2451":"創見",
    "0050":"元大台灣50", "0056":"元大高股息", "00878":"國泰永續高股息", 
    "00929":"復華台灣科技優息", "00919":"群益台灣精選高息", "006208":"富邦台50"
}

# --- State ---
if 'watchlist' not in st.session_state: st.session_state.watchlist = load_watchlist()
if 'scan_result_tab2' not in st.session_state: st.session_state.scan_result_tab2 = None
if 'scan_result_tab3' not in st.session_state: st.session_state.scan_result_tab3 = None
if 'scan_result_tab4' not in st.session_state: st.session_state.scan_result_tab4 = None
if 'ai_data' not in st.session_state: st.session_state.ai_data = None
if 'sb_selected_code' not in st.session_state:
    if st.session_state.watchlist: st.session_state.sb_selected_code = list(st.session_state.watchlist.keys())[0]
    else: st.session_state.sb_selected_code = "2330"

if 'pending_update' in st.session_state and st.session_state.pending_update:
    update_data = st.session_state.pending_update
    new_code = update_data['code']; new_name = update_data['name']
    if new_code not in st.session_state.watchlist:
        st.session_state.watchlist[new_code] = new_name; save_watchlist(st.session_state.watchlist)
    st.session_state.sb_selected_code = new_code
    st.toast(f"✅ 已鎖定：{new_name} ({new_code})", icon="🎉")
    st.session_state.pending_update = None

# --- SECTOR_DICT ---
SECTOR_DICT = {
    "[熱門] 國民ETF": ["0050", "0056", "00878", "00929", "00919", "006208", "00713"],
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
                    t = yf.Ticker(f"{code}.TW"); name = t.info.get('longName') or t.info.get('shortName')
                    if not name: t = yf.Ticker(f"{code}.TWO"); name = t.info.get('longName') or t.info.get('shortName')
                    if name: st.session_state.input_name = name
                except: pass
    c1, c2 = st.columns(2)
    new_code = c1.text_input("代號", placeholder="2395", key="input_code", on_change=auto_fill_name)
    new_name = c2.text_input("名稱", placeholder="自動帶入...", key="input_name")
    if st.button("➕ 新增"):
        if new_code and new_name:
            st.session_state.watchlist[new_code] = new_name; save_watchlist(st.session_state.watchlist); st.rerun()
    remove_target = st.selectbox("移除股票", options=list(st.session_state.watchlist.keys()), format_func=lambda x: f"{x} {st.session_state.watchlist[x]}")
    if st.button("➖ 移除"):
        if remove_target in st.session_state.watchlist:
            del st.session_state.watchlist[remove_target]; save_watchlist(st.session_state.watchlist)
            if remove_target == st.session_state.sb_selected_code:
                if st.session_state.watchlist: st.session_state.sb_selected_code = list(st.session_state.watchlist.keys())[0]
            st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("📊 個股參數")
selected_code = st.sidebar.selectbox("選擇個股", options=list(st.session_state.watchlist.keys()), format_func=lambda x: f"{x} {st.session_state.watchlist[x]}", key="sb_selected_code")
timeframe = st.sidebar.selectbox("K線週期", ["日K", "週K", "月K", "季K"])
interval_map = {"日K": "1d", "週K": "1wk", "月K": "1mo", "季K": "3mo"}
yf_interval = interval_map[timeframe]
lookback_bars = st.sidebar.slider(f"顯示 K 棒數量 ({timeframe})", 60, 365, 150)

# --- V18.2: 安全數值讀取 helper ---
def safe_float(val):
    try: return float(val)
    except: return None

def get_realtime_quote_fugle(code):
    if not fugle_client: return None, None
    try:
        stock = fugle_client.stock
        quote = stock.intraday.quote(symbol=code)
        raw_json = quote
        if quote:
            price = safe_float(quote.get('lastTrade', {}).get('price'))
            if price is None: price = safe_float(quote.get('trade', {}).get('price'))
            change = safe_float(quote.get('change'))
            pct_change = 0
            if price is not None and change is not None:
                prev_close = price - change
                if prev_close > 0: pct_change = (change / prev_close) * 100
            open_p = safe_float(quote.get('priceOpen', {}).get('price')) or safe_float(quote.get('open'))
            high_p = safe_float(quote.get('priceHigh', {}).get('price')) or safe_float(quote.get('high'))
            low_p = safe_float(quote.get('priceLow', {}).get('price')) or safe_float(quote.get('low'))
            time_str = quote.get('lastUpdated')
            try:
                dt_object = datetime.fromtimestamp(time_str / 1000000)
                time_str = dt_object.strftime("%H:%M:%S")
            except: pass
            return {
                "price": price, "change": change, "changePercent": round(pct_change, 2),
                "open": open_p, "high": high_p, "low": low_p, "time": time_str
            }, raw_json
    except Exception as e: return None, str(e)
    return None, None

# --- 核心功能區 ---
def get_stock_data(symbol, bars=200, interval="1d"):
    ticker = f"{symbol}.TW"; stock = yf.Ticker(ticker)
    if interval == "1d": period_str = f"{bars + 200}d"
    elif interval == "1wk": period_str = "5y"
    else: period_str = "max"
    df = stock.history(period=period_str, interval=interval) 
    if df.empty: ticker = f"{symbol}.TWO"; stock = yf.Ticker(ticker); df = stock.history(period=period_str, interval=interval)
    return df, stock

def get_stock_news(stock_name):
    encoded_name = requests.utils.quote(stock_name)
    rss_url = f"https://news.google.com/rss/search?q={encoded_name}+stock&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    try:
        feed = feedparser.parse(rss_url)
        return [{"title": entry.title, "link": entry.link, "published": entry.published} for entry in feed.entries[:5]]
    except: return []

def calculate_indicators(df):
    df['SMA5'] = ta.sma(df['Close'], length=5); df['SMA10'] = ta.sma(df['Close'], length=10); df['SMA20'] = ta.sma(df['Close'], length=20); df['SMA60'] = ta.sma(df['Close'], length=60); df['Vol_SMA5'] = ta.sma(df['Volume'], length=5)
    macd = ta.macd(df['Close']); df = pd.concat([df, macd], axis=1)
    k_d = ta.stoch(df['High'], df['Low'], df['Close']); df = pd.concat([df, k_d], axis=1)
    bb = ta.bbands(df['Close'], length=20, std=2); df = pd.concat([df, bb], axis=1)
    df['RSI'] = ta.rsi(df['Close'], length=14); df['OBV'] = ta.obv(df['Close'], df['Volume']); df['AD'] = ta.ad(df['High'], df['Low'], df['Close'], df['Volume'])
    try: df['VWAP'] = ta.vwap(df['High'], df['Low'], df['Close'], df['Volume']) 
    except: pass
    return df

def get_fundamentals(stock_obj):
    try:
        info = stock_obj.info
        pe_raw = info.get('trailingPE'); pe_ratio = round(pe_raw, 2) if pe_raw else None
        div_yield = info.get('dividendYield', 0); div_yield_str = f"{round(div_yield*100, 2)}%" if div_yield and div_yield < 1 else f"{round(div_yield, 2)}%" if div_yield else "N/A"
        rev_growth = info.get('revenueGrowth', 0); yoy_str = f"{round(rev_growth * 100, 2)}%" if rev_growth else "N/A"; yoy_c = "normal" if isinstance(rev_growth, float) and rev_growth > 0 else "inverse"
        try:
            financials = stock_obj.quarterly_financials
            if 'Total Revenue' in financials.index:
                rev_curr = financials.loc['Total Revenue'].iloc[0]; rev_prev = financials.loc['Total Revenue'].iloc[1]; qoq_val = (rev_curr - rev_prev) / rev_prev
                qoq_str = f"{round(qoq_val * 100, 2)}%"; qoq_c = "normal" if qoq_val > 0 else "inverse"
            else: qoq_str = "N/A"; qoq_c = "off"
        except: qoq_str = "N/A"; qoq_c = "off"
        return pe_ratio, div_yield_str, yoy_str, qoq_str, yoy_c, qoq_c
    except: return None, "N/A", "N/A", "N/A", "off", "off"

def calculate_valuation_matrix(stock_obj, current_price):
    try:
        info = stock_obj.info; result = {}
        divs = stock_obj.dividends
        if not divs.empty:
            avg_div = divs.sort_index(ascending=False).head(5).mean()
            result['yield'] = {"base": round(avg_div, 2), "cheap": round(avg_div * 16.6, 1), "fair": round(avg_div * 20, 1), "expensive": round(avg_div * 25, 1), "status": "合理"}
            if current_price <= result['yield']['cheap']: result['yield']['status'] = "💰 便宜"
            elif current_price >= result['yield']['expensive']: result['yield']['status'] = "⚠️ 昂貴"
        eps = info.get('trailingEps')
        if eps and eps > 0:
            result['pe'] = {"base": round(eps, 2), "cheap": round(eps * 12, 1), "fair": round(eps * 16, 1), "expensive": round(eps * 20, 1), "status": "合理"}
            if current_price <= result['pe']['cheap']: result['pe']['status'] = "💰 便宜"
            elif current_price >= result['pe']['expensive']: result['pe']['status'] = "⚠️ 昂貴"
        bv = info.get('bookValue')
        if bv and bv > 0:
            result['pb'] = {"base": round(bv, 2), "cheap": round(bv * 1.0, 1), "fair": round(bv * 1.5, 1), "expensive": round(bv * 2.0, 1), "status": "合理"}
            if current_price <= result['pb']['cheap']: result['pb']['status'] = "💰 便宜"
            elif current_price >= result['pb']['expensive']: result['pb']['status'] = "⚠️ 昂貴"
        return result
    except: return None

def check_three_rates(stock_obj):
    try:
        fin = stock_obj.quarterly_financials
        if fin.empty or 'Total Revenue' not in fin.index or 'Gross Profit' not in fin.index: return False, {}
        fin = fin.sort_index(axis=1, ascending=False); q1 = fin.iloc[:, 0]; q2 = fin.iloc[:, 1]
        try:
            gm_q1 = q1['Gross Profit'] / q1['Total Revenue']; gm_q2 = q2['Gross Profit'] / q2['Total Revenue']
            op_label = 'Operating Income' if 'Operating Income' in fin.index else 'Operating Profit'
            om_q1 = q1[op_label] / q1['Total Revenue']; om_q2 = q2[op_label] / q2['Total Revenue']
            ni_label = 'Net Income'; nm_q1 = q1[ni_label] / q1['Total Revenue']; nm_q2 = q2[ni_label] / q2['Total Revenue']
            is_rising = (gm_q1 > gm_q2) and (om_q1 > om_q2) and (nm_q1 > nm_q2)
            return is_rising, {"gm": f"{round(gm_q1*100, 1)}% (↗)", "om": f"{round(om_q1*100, 1)}% (↗)", "nm": f"{round(nm_q1*100, 1)}% (↗)"}
        except: return False, {}
    except: return False, {}

def run_backtest(df, strategy, initial_capital=1000000, bb_threshold=0.05):
    cash = initial_capital; position = 0; equity_curve = []; trade_log = []; entry_cost = 0 
    for i in range(len(df)):
        if i < 20: continue
        today = df.iloc[i]; prev = df.iloc[i-1]; date = df.index[i]; price = today['Close']; action = None
        if strategy == "均線黃金交叉 (5MA穿過20MA)":
            if prev['SMA5'] < prev['SMA20'] and today['SMA5'] > today['SMA20'] and position == 0: action = "BUY"
            elif prev['SMA5'] > prev['SMA20'] and today['SMA5'] < today['SMA20'] and position > 0: action = "SELL"
        elif strategy == "KD 低檔金叉 (K<30買, K>80賣)":
            k_col = df.columns[df.columns.str.startswith('STOCHk')][0]; d_col = df.columns[df.columns.str.startswith('STOCHd')][0]
            k_curr = today[k_col]; k_prev = prev[k_col]; d_curr = today[d_col]; d_prev = prev[d_col]
            if k_prev < 30 and k_prev < d_prev and k_curr > d_curr and position == 0: action = "BUY"
            elif k_prev > 80 and k_prev > d_prev and k_curr < d_curr and position > 0: action = "SELL"
        elif strategy == "布林通道逆勢 (跌破下軌買/突破上軌賣)":
            bbl_col = [c for c in df.columns if c.startswith('BBL')][0]; bbu_col = [c for c in df.columns if c.startswith('BBU')][0]
            lower = prev[bbl_col]; upper = prev[bbu_col]
            if today['Close'] < lower * (1 - bb_threshold) and position == 0: action = "BUY"
            elif today['Close'] > upper * (1 + bb_threshold) and position > 0: action = "SELL"
        elif strategy == "多因子狙擊 (KD+布林+MACD+均線)":
            k_col = df.columns[df.columns.str.startswith('STOCHk')][0]; bbl_col = [c for c in df.columns if c.startswith('BBL')][0]; bbu_col = [c for c in df.columns if c.startswith('BBU')][0]; macd_col = df.columns[df.columns.str.startswith('MACDh')][0]
            recent_macd = df.iloc[i-9:i+1][macd_col]; min_macd_10 = recent_macd.min(); max_macd_10 = recent_macd.max()
            c1_buy = today[k_col] < 10; c2_buy = price < today[bbl_col]; c3_buy = today[macd_col] <= min_macd_10 + 0.01; c4_buy = price < today['SMA60']; c5_buy = today['SMA60'] < prev['SMA60']
            if c1_buy and c2_buy and c3_buy and c4_buy and c5_buy and position == 0: action = "BUY"
            c1_sell = today[k_col] > 85; c2_sell = price > today[bbu_col]; c3_sell = today[macd_col] >= max_macd_10 - 0.01; c4_sell = price > max(today['SMA5'], today['SMA10'], today['SMA20'], today['SMA60']); c5_sell = today['SMA60'] > prev['SMA60']
            if c1_sell and c2_sell and c3_sell and c4_sell and c5_sell and position > 0: action = "SELL"
        if action == "BUY":
            shares_to_buy = int(cash / (price * 1.001425)); cost = shares_to_buy * price * 1.001425; cash -= cost; position = shares_to_buy; entry_cost = cost
            trade_log.append({"日期": date.strftime('%Y-%m-%d'), "動作": "買進", "價格": round(price, 2), "股數": shares_to_buy, "損益": None, "報酬率(%)": None, "資產": int(cash + position * price)})
        elif action == "SELL":
            revenue = position * price * (1 - 0.001425 - 0.003); cash += revenue; pnl = revenue - entry_cost; roi = (pnl / entry_cost) * 100 if entry_cost > 0 else 0
            trade_log.append({"日期": date.strftime('%Y-%m-%d'), "動作": "賣出", "價格": round(price, 2), "股數": position, "損益": int(pnl), "報酬率(%)": round(roi, 2), "資產": int(cash)})
            position = 0; entry_cost = 0
        equity_curve.append({"Date": date, "Equity": cash + (position * price)})
    return pd.DataFrame(equity_curve), pd.DataFrame(trade_log), int(cash + (position * price))

def train_and_predict_ai(df):
    data = df.copy(); data['Target'] = (data['Close'].shift(-1) > data['Close']).astype(int)
    macd_col = data.columns[data.columns.str.startswith('MACDh')][0]; features = ['Close', 'Volume', 'RSI', macd_col]
    data = data.dropna(); X = data[features]; y = data['Target']
    split = int(len(X) * 0.8); X_train, X_test = X.iloc[:split], X.iloc[split:]; y_train, y_test = y.iloc[:split], y.iloc[split:]
    model = RandomForestClassifier(n_estimators=100, min_samples_split=10, random_state=42); model.fit(X_train, y_train)
    preds = model.predict(X_test); acc = accuracy_score(y_test, preds)
    latest_data = X.iloc[[-1]]; prediction = model.predict(latest_data); prob = model.predict_proba(latest_data)[0][1]
    return acc, prediction[0], prob, model.feature_importances_, features

# --- Header: 即時報價 ---
stock_name = st.session_state.watchlist.get(selected_code, selected_code)
c_head1, c_head2 = st.columns([3, 1])
with c_head1: st.markdown(f"### ⚡ 即時報價：{stock_name} ({selected_code})")
with c_head2:
    if st.button("🔄 立即更新報價"): st.rerun()
rt_data, raw_json = get_realtime_quote_fugle(selected_code)
if rt_data:
    r1, r2, r3, r4 = st.columns(4)
    price = rt_data.get('price', '—')
    change = rt_data.get('change', '—')
    pct = rt_data.get('changePercent', '—')
    r1.metric("成交價", f"{price}", f"{change} ({pct}%)")
    r2.metric("開盤", rt_data.get('open', '—')); r3.metric("最高", rt_data.get('high', '—')); r4.metric("最低", rt_data.get('low', '—'))
    st.caption(f"✅ 資料來源：Fugle 富果 API (更新時間: {rt_data.get('time', 'N/A')})")
else:
    st.warning("⚠️ 暫時無法取得 Fugle 即時連線，請檢查下方的原始資料或 API Key。")

with st.expander("🔍 [開發者模式] 查看 API 原始回傳資料 (Raw JSON)"):
    st.json(raw_json if raw_json else {"status": "No Data", "key_configured": bool(FUGLE_API_KEY)})

# --- 介面分頁 ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["📊 個股儀表板", "🤖 觀察名單掃描", "🔥 Goodinfo轉折", "💎 三率三升", "🧪 策略回測", "🔮 AI 趨勢預測", "🕵️‍♂️ 籌碼與股權"])

# 分頁 1: 個股詳細分析
with tab1:
    if selected_code:
        data, ticker_obj = get_stock_data(selected_code, lookback_bars, yf_interval)
        if not data.empty:
            df = calculate_indicators(data)
            df_view = df.tail(lookback_bars).copy()
            if yf_interval == "1d": df_view.index = df_view.index.strftime('%Y-%m-%d')
            else: df_view.index = df_view.index.strftime('%Y-%m-%d')
            latest = df.iloc[-1]
            pe, div, yoy, qoq, yoy_c, qoq_c = get_fundamentals(ticker_obj)
            val_matrix = calculate_valuation_matrix(ticker_obj, latest['Close'])
            st.subheader(f"{stock_name} ({selected_code}) - {timeframe}技術分析")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Yahoo 收盤價 (延遲)", round(latest['Close'], 2), round(latest['Close'] - df.iloc[-2]['Close'], 2))
            c2.metric("成交量", f"{int(latest['Volume']/1000)} 張", f"{int((latest['Volume']-df.iloc[-2]['Volume'])/1000)} 張")
            macd_col = df.columns[df.columns.str.startswith('MACDh')][0]
            hist_val = latest[macd_col]
            c3.metric("MACD 動能", round(hist_val, 2), "🔴 增強" if hist_val > 0 and hist_val > df.iloc[-2][macd_col] else "🟢 減弱")
            ma_values = [latest['SMA5'], latest['SMA20'], latest['SMA60']]
            ma_spread = (max(ma_values) - min(ma_values)) / min(ma_values) * 100
            c4.metric("均線發散度", f"{round(ma_spread, 2)}%", "越低越好" if ma_spread < 5 else "發散中")
            if val_matrix:
                with st.expander("💰 全方位價值估價 (點擊展開)", expanded=True):
                    v_cols = st.columns(3)
                    if 'yield' in val_matrix:
                        v_cols[0].markdown(f"### 📅 殖利率法")
                        v_cols[0].caption(f"基礎：5年平均股利 {val_matrix['yield']['base']} 元")
                        v_cols[0].metric("目前狀態", val_matrix['yield']['status'], help="便宜: >6% / 昂貴: <4%")
                    if 'pe' in val_matrix:
                        v_cols[1].markdown(f"### 🚀 本益比法 (PE)")
                        v_cols[1].caption(f"基礎：近四季 EPS {val_matrix['pe']['base']} 元")
                        v_cols[1].metric("目前狀態", val_matrix['pe']['status'], help="便宜: <12倍 / 昂貴: >20倍")
                    if 'pb' in val_matrix:
                        v_cols[2].markdown(f"### 🏭 淨值比法 (PB)")
                        v_cols[2].caption(f"基礎：每股淨值 {val_matrix['pb']['base']} 元")
                        v_cols[2].metric("目前狀態", val_matrix['pb']['status'], help="便宜: <1倍 / 昂貴: >2倍")
            if st.button(f"📤 傳送 {stock_name} 診斷到 LINE"):
                msg = f"\n🔔 【個股診斷】{stock_name} ({selected_code})\n💰 收盤價：{round(latest['Close'], 2)}\n📊 MACD：{'紅柱增強' if hist_val > 0 and hist_val > df.iloc[-2][macd_col] else '動能減弱'}\n📅 殖利率估價：{val_matrix['yield']['status'] if val_matrix else 'N/A'}\n"
                send_line_message(msg)
            st.markdown("---")
            f1, f2, f3, f4 = st.columns(4)
            f1.metric("本益比", pe); f2.metric("殖利率", div); f3.metric("營收 YoY", yoy, delta_color=yoy_c); f4.metric("營收 QoQ", qoq, delta_color=qoq_c)
            fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.2, 0.15, 0.15], subplot_titles=("K線 & 布林通道", "成交量", "MACD", "KD"))
            fig.add_trace(go.Candlestick(x=df_view.index, open=df_view['Open'], high=df_view['High'], low=df_view['Low'], close=df_view['Close'], name='K線', increasing_line_color='red', decreasing_line_color='green'), row=1, col=1)
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
            st.subheader(f"📰 {stock_name} 最新相關新聞")
            try:
                news_items = get_stock_news(stock_name)
                if news_items:
                    for news in news_items: st.markdown(f"- [{news['title']}]({news['link']}) <span style='color:gray; font-size:0.8em'>({news['published']})</span>", unsafe_allow_html=True)
                else: st.info("暫無相關新聞")
            except: st.warning("新聞載入失敗。")

# 分頁 2: 觀察名單掃描器
with tab2:
    st.subheader("🤖 觀察名單掃描器")
    st.info("💡 提示：點擊表格中的任一行，即可自動切換至該個股的詳細分析。")
    if st.button("🚀 掃描觀察名單"):
        scan_results = []
        progress_bar = st.progress(0)
        stocks_list = list(st.session_state.watchlist.items())
        total = len(stocks_list)
        for i, (code, name) in enumerate(stocks_list):
            time.sleep(0.5)
            try:
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
                        # V18.4: 拆解長代碼
                        item = {
                            "代號": code, "名稱": name, "收盤價": latest['Close'], 
                            "漲幅%": ((latest['Close'] - prev['Close']) / prev['Close']) * 100, 
                            "站上月線": "✅" if cond_above_ma20 else "❌", 
                            "量能爆發": "🔥" if cond_volume else "➖", 
                            "KD金叉": "✅" if cond_kd_gold else "➖", 
                            "MACD多頭": "✅" if cond_macd else "➖", 
                            "均線排列": "🌟" if cond_align else "➖"
                        }
                        scan_results.append(item)
                    except: pass
            except Exception as e: pass
            progress_bar.progress((i+1)/total)
        progress.empty()
        st.session_state.scan_result_tab2 = pd.DataFrame(scan_results)

    if st.session_state.scan_result_tab2 is not None and not st.session_state.scan_result_tab2.empty:
        res_df = st.session_state.scan_result_tab2
        if st.button("📤 將掃描結果傳送到 LINE (Tab2)"):
            msg = "🤖 【觀察名單掃描報告】\n"
            for index, row in res_df.iterrows():
                if row['KD金叉'] == '✅' or row['量能爆發'] == '🔥': msg += f"{row['名稱']} ({row['代號']}): {row['漲幅%']}%\n"
            if len(msg) > 20: send_line_message(msg)
        event = st.dataframe(res_df.style.applymap(lambda x: 'color: red' if isinstance(x, float) and x > 0 else 'color: green' if isinstance(x, float) and x < 0 else '', subset=['漲幅%']), column_config={"收盤價": st.column_config.NumberColumn(format="%.2f"), "漲幅%": st.column_config.NumberColumn(format="%.2f%%")}, use_container_width=True, height=500, on_select="rerun", selection_mode="single-row")
        if event.selection.rows:
            selected_index = event.selection.rows[0]
            clicked_code = res_df.iloc[selected_index]["代號"]
            clicked_name = res_df.iloc[selected_index]["名稱"]
            if clicked_code != st.session_state.sb_selected_code:
                st.session_state.pending_update = {"code": clicked_code, "name": clicked_name}
                st.rerun()
    elif st.session_state.scan_result_tab2 is not None: st.info("無資料")

# 分頁 3: 轉折獵人
with tab3:
    st.subheader("🔥 Goodinfo 風格 - 轉折獵人")
    target_sector = st.selectbox("請選擇掃描分類", options=list(SECTOR_DICT.keys()))
    if st.button("🎯 開始掃描"):
        if target_sector == "你的觀察名單": scan_list = list(st.session_state.watchlist.keys())
        else: scan_list = SECTOR_DICT[target_sector]
        reversal_stocks = []
        progress = st.progress(0)
        total_scan = len(scan_list)
        for i, code in enumerate(scan_list):
            time.sleep(0.5)
            try:
                df_s, _ = get_stock_data(code, 120, interval="1d")
                if not df_s.empty:
                    try:
                        df_s = calculate_indicators(df_s)
                        curr = df_s.iloc[-1]; prev = df_s.iloc[-2]
                        is_above_ma20 = curr['Close'] > curr['SMA20']
                        k_col = df_s.columns[df_s.columns.str.startswith('STOCHk')][0]
                        d_col = df_s.columns[df_s.columns.str.startswith('STOCHd')][0]
                        is_kd_cross = (curr[k_col] > curr[d_col]) and (prev[k_col] < prev[d_col]) and (curr[k_col] < 50)
                        macd_col = df_s.columns[df_s.columns.str.startswith('MACDh')][0]
                        is_macd_turning = curr[macd_col] > prev[macd_col]
                        is_break_ma60 = (curr['Close'] > curr['SMA60']) and (prev['Close'] < prev['SMA60'])
                        score = 0; reasons = []
                        if is_kd_cross: score += 1; reasons.append("KD低檔金叉")
                        if is_break_ma60: score += 1; reasons.append("突破季線")
                        if is_above_ma20 and is_macd_turning: score += 1; reasons.append("站穩月線+動能")
                        if score >= 1:
                            name = st.session_state.watchlist.get(code, STOCK_NAMES.get(code, code))
                            # V18.4: 拆解長代碼
                            item = {
                                "代號": code, 
                                "名稱": name, 
                                "收盤價": curr['Close'], 
                                "訊號強度": "⭐⭐⭐" if score >= 2 else "⭐", 
                                "觸發條件": " + ".join(reasons), 
                                "KD值": f"{int(curr[k_col])}", 
                                "季線乖離": f"{round(((curr['Close'] - curr['SMA60'])/curr['SMA60'])*100, 1)}%"
                            }
                            reversal_stocks.append(item)
                    except: pass
            except: pass
            progress.progress((i+1)/total_scan)
        progress.empty()
        st.session_state.scan_result_tab3 = pd.DataFrame(reversal_stocks)

    if st.session_state.scan_result_tab3 is not None and not st.session_state.scan_result_tab3.empty:
        rev_df = st.session_state.scan_result_tab3
        st.success(f"發現 {len(rev_df)} 檔潛在轉折股！")
        if st.button("📤 將轉折清單傳送到 LINE (Tab3)"):
            msg = f"🔥 【轉折獵人】發現 {len(rev_df)} 檔潛力股\n板塊：{target_sector}\n"
            for index, row in rev_df.iterrows(): msg += f"✅ {row['名稱']} ({row['代號']}) - {row['收盤價']}\n   理由：{row['觸發條件']}\n"
            send_line_message(msg)
        event = st.dataframe(rev_df, column_config={"收盤價": st.column_config.NumberColumn(format="%.2f")}, use_container_width=True, on_select="rerun", selection_mode="single-row")
        if event.selection.rows:
            selected_index = event.selection.rows[0]
            clicked_code = rev_df.iloc[selected_index]["代號"]
            clicked_name = rev_df.iloc[selected_index]["名稱"]
            if clicked_code != st.session_state.sb_selected_code:
                st.session_state.pending_update = {"code": clicked_code, "name": clicked_name}
                st.rerun()
    elif st.session_state.scan_result_tab3 is not None: st.info("未發現明顯訊號。")

with tab4:
    st.subheader("💎 三率三升選股 - 基本面掃描")
    target_sector_f = st.selectbox("選擇掃描板塊", options=list(SECTOR_DICT.keys()), key="fund_sector")
    if st.button("🔍 開始基本面掃描"):
        if target_sector_f == "你的觀察名單": scan_list_f = list(st.session_state.watchlist.keys())
        else: scan_list_f = SECTOR_DICT[target_sector_f]
        fund_results = []
        progress = st.progress(0)
        status = st.empty()
        total_scan = len(scan_list_f)
        for i, code in enumerate(scan_list_f):
            status.text(f"正在分析財報：{code}...")
            time.sleep(0.5)
            try:
                t_obj = yf.Ticker(f"{code}.TW")
                is_3_up, metrics = check_three_rates(t_obj)
                if is_3_up:
                    name = st.session_state.watchlist.get(code, STOCK_NAMES.get(code, code))
                    # V18.4: 拆解長代碼
                    item = {
                        "代號": code, "名稱": name, 
                        "毛利率": metrics['gm'], "營益率": metrics['om'], "淨利率": metrics['nm']
                    }
                    fund_results.append(item)
            except: pass
            progress.progress((i+1)/total_scan)
        progress.empty()
        st.session_state.scan_result_tab4 = pd.DataFrame(fund_results)
    if st.session_state.scan_result_tab4 is not None and not st.session_state.scan_result_tab4.empty:
        fund_df = st.session_state.scan_result_tab4
        st.balloons()
        st.success(f"恭喜！在「{target_sector_f}」中發現 {len(fund_df)} 檔【三率三升】績優股！")
        event = st.dataframe(fund_df, use_container_width=True, on_select="rerun", selection_mode="single-row")
        if event.selection.rows:
            selected_index = event.selection.rows[0]
            clicked_code = fund_df.iloc[selected_index]["代號"]
            clicked_name = fund_df.iloc[selected_index]["名稱"]
            if clicked_code != st.session_state.sb_selected_code:
                st.session_state.pending_update = {"code": clicked_code, "name": clicked_name}
                st.rerun()
    elif st.session_state.scan_result_tab4 is not None: st.info("可惜，沒有發現三率三升的股票。")

# Tab 5, 6, 7 (保持 V16.4 內容，無需更動，請直接複製貼上)
# ... (以下請貼上 V16.4 / V17.3 的 Tab 5, 6, 7 程式碼) ...

with tab5:
    st.subheader("🧪 策略回測實驗室 - 驗證你的交易策略")
    STRATEGY_DESC = {
        "均線黃金交叉 (5MA穿過20MA)": "📈 **趨勢順勢策略**：當短期成本(5日)超過長期成本(20日)時追價買進。適合波段明顯的股票。",
        "KD 低檔金叉 (K<30買, K>80賣)": "📉 **震盪操作策略**：在超賣區(K<30)買進，超買區(K>80)賣出。適合箱型整理的股票。",
        "布林通道逆勢 (跌破下軌買/突破上軌賣)": "🛡️ **逆勢回歸策略**：當股價偏離標準差過大(跌破下軌)時接刀。適合抓反彈。",
        "多因子狙擊 (KD+布林+MACD+均線)": "🎯 **高勝率濾網策略**：同時滿足低檔、超跌、動能轉強等多重條件才出手。交易次數少但精準。"
    }
    col1, col2, col3 = st.columns(3)
    bt_strategy = col1.selectbox("選擇回測策略", list(STRATEGY_DESC.keys()))
    bt_period = col2.selectbox("回測時間長度", ["1年 (短線)", "3年 (中線)", "5年 (長線)"])
    period_map = {"1年 (短線)": "1y", "3年 (中線)": "3y", "5年 (長線)": "5y"}
    bb_thresh = 0.05
    if "布林" in bt_strategy or "狙擊" in bt_strategy: bb_thresh = col3.slider("布林乖離門檻", 0.01, 0.10, 0.05, 0.01, format="%.2f")
    
    c_act1, c_act2 = st.columns([1, 2])
    
    if c_act1.button("▶️ 開始回測 (單一策略)"):
        target_name = st.session_state.watchlist.get(selected_code, selected_code)
        st.write(f"正在回測：**{target_name} ({selected_code})** | 策略：{bt_strategy}...")
        t = yf.Ticker(f"{selected_code}.TW")
        df_bt = t.history(period=period_map[bt_period])
        if not df_bt.empty:
            df_bt = calculate_indicators(df_bt)
            equity_df, trade_df, final_asset = run_backtest(df_bt, bt_strategy, bb_threshold=bb_thresh)
            total_return = ((final_asset - 1000000) / 1000000) * 100
            r1, r2, r3 = st.columns(3)
            r1.metric("最終資產", f"${final_asset:,}", f"{round(total_return, 2)}%")
            r2.metric("總交易次數", len(trade_df))
            if not trade_df.empty:
                def highlight_trade(row):
                    if row['動作'] == '買進': return ['background-color: rgba(144, 238, 144, 0.3)'] * len(row)
                    elif row['動作'] == '賣出': return ['background-color: rgba(255, 99, 71, 0.3)'] * len(row)
                    return [''] * len(row)
                st.dataframe(trade_df.style.apply(highlight_trade, axis=1), use_container_width=True, column_config={"報酬率(%)": st.column_config.NumberColumn(format="%.2f%%"), "損益": st.column_config.NumberColumn(format="$%d")})
            else: st.warning("此期間內無符合策略的交易訊號。")
            st.subheader("📈 資產累積曲線")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=equity_df['Date'], y=equity_df['Equity'], mode='lines', name='總資產', fill='tozeroy'))
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else: st.error("無法取得歷史數據。")

    if c_act2.button("🏆 策略大亂鬥 (一鍵比較所有策略)"):
        target_name = st.session_state.watchlist.get(selected_code, selected_code)
        st.write(f"🔥 正在進行策略 PK：**{target_name} ({selected_code})** ...")
        t = yf.Ticker(f"{selected_code}.TW")
        df_bt = t.history(period=period_map[bt_period])
        if not df_bt.empty:
            df_bt = calculate_indicators(df_bt)
            strategies_to_test = ["均線黃金交叉 (5MA穿過20MA)", "KD 低檔金叉 (K<30買, K>80賣)", "布林通道逆勢 (跌破下軌買/突破上軌賣)", "多因子狙擊 (KD+布林+MACD+均線)"]
            pk_results = []
            all_trade_logs = {}
            for strat in strategies_to_test:
                _, trade_df, final_val = run_backtest(df_bt, strat, bb_threshold=0.05)
                roi = ((final_val - 1000000) / 1000000) * 100
                pk_results.append({"策略名稱": strat, "最終資產": f"${final_val:,}", "報酬率(%)": round(roi, 2), "交易次數": len(trade_df)})
                all_trade_logs[strat] = trade_df
            pk_df = pd.DataFrame(pk_results).sort_values(by="報酬率(%)", ascending=False)
            winner = pk_df.iloc[0]
            st.success(f"🏆 獲勝策略：**{winner['策略名稱']}** (報酬率 {winner['報酬率(%)']}%)")
            st.dataframe(pk_df.style.applymap(lambda x: 'color: red' if x > 0 else 'color: green', subset=['報酬率(%)']), use_container_width=True, column_config={"報酬率(%)": st.column_config.NumberColumn(format="%.2f%%")})
            st.markdown("### 📝 策略邏輯與詳細交易紀錄")
            for index, row in pk_df.iterrows():
                strat_name = row['策略名稱']
                rank_icon = "🥇" if index == 0 else "🥈" if index == 1 else "🥉" if index == 2 else "🔹"
                with st.expander(f"{rank_icon} {strat_name} (點擊查看明細)"):
                    st.info(STRATEGY_DESC.get(strat_name))
                    t_log = all_trade_logs[strat_name]
                    if not t_log.empty:
                        def highlight_trade(row):
                            if row['動作'] == '買進': return ['background-color: rgba(144, 238, 144, 0.3)'] * len(row)
                            elif row['動作'] == '賣出': return ['background-color: rgba(255, 99, 71, 0.3)'] * len(row)
                            return [''] * len(row)
                        st.dataframe(t_log.style.apply(highlight_trade, axis=1), use_container_width=True, column_config={"報酬率(%)": st.column_config.NumberColumn(format="%.2f%%"), "損益": st.column_config.NumberColumn(format="$%d")})
                    else: st.caption("此策略在測試期間內無交易訊號。")
        else: st.error("無法取得歷史數據。")

with tab6:
    st.subheader("🔮 AI 趨勢預測 (Random Forest)")
    st.markdown("""**原理：** 利用機器學習模型，分析過去的 **收盤價、成交量、RSI、MACD** 與隔日漲跌的關係，預測明日走勢。""")
    if st.button("🧠 啟動 AI 模型運算"):
        target_name = st.session_state.watchlist.get(selected_code, selected_code)
        df_ai, _ = get_stock_data(selected_code, 0, interval="1d")
        t_ai = yf.Ticker(f"{selected_code}.TW")
        df_ai = t_ai.history(period="max")
        if len(df_ai) > 200:
            df_ai = calculate_indicators(df_ai)
            with st.spinner(f"AI 正在學習 {target_name} 的歷史股性..."):
                acc, pred, prob, importances, feature_names = train_and_predict_ai(df_ai)
            st.session_state.ai_data = {"target_name": target_name, "code": selected_code, "acc": acc, "pred": pred, "prob": prob, "importances": importances, "feature_names": feature_names}
        else: st.error("歷史資料不足，無法進行 AI 訓練。")

    if st.session_state.ai_data:
        ai = st.session_state.ai_data
        col1, col2 = st.columns(2)
        result_text = "📈 看漲 (Bullish)" if ai['pred'] == 1 else "📉 看跌 (Bearish)"
        result_color = "green" if ai['pred'] == 0 else "red"
        col1.markdown(f"### AI 預測明日 ({ai['target_name']})： :{result_color}[{result_text}]")
        col1.metric("上漲機率", f"{round(ai['prob'] * 100, 1)}%")
        col1.metric("模型回測準確度", f"{round(ai['acc'] * 100, 1)}%")
        if ai['acc'] < 0.5: col1.warning("⚠️ 模型準確度低於 50%，參考價值較低。")
        if st.button("📤 將 AI 預測結果傳送到 LINE"):
            msg = f"🔮 【AI 預測】{ai['target_name']} ({ai['code']})\n🤖 預測：{result_text}\n📈 上漲機率：{round(ai['prob']*100, 1)}%\n🎯 模型準確度：{round(ai['acc']*100, 1)}%"
            send_line_message(msg)
        col2.markdown("### 🔍 關鍵影響因子")
        importance_df = pd.DataFrame({"指標": ai['feature_names'], "重要性": ai['importances']})
        importance_df = importance_df.sort_values(by="重要性", ascending=False)
        col2.dataframe(importance_df, use_container_width=True, hide_index=True)

with tab7:
    st.subheader("🕵️‍♂️ 籌碼與股權透視 - 追蹤大戶動向")
    target_name = st.session_state.watchlist.get(selected_code, selected_code)
    st.info(f"目前分析標的：**{target_name} ({selected_code})**")
    chip_mode = st.radio("📊 選擇分析模式", ["📅 波段籌碼 (60日趨勢)", "⚡ 當沖籌碼 (今日 5分K)"], horizontal=True, key="chip_mode_key")
    if "波段" in chip_mode:
        c_interval = "1d"; c_days = 100; c_view = 60; c_title = "近期主力籌碼動能 (近60日)"
    else:
        c_interval = "5m"; c_days = 5; c_view = 100; c_title = "當日即時籌碼動能 (5分K)"
    data_chip, _ = get_stock_data(selected_code, c_days, interval=c_interval)
    if not data_chip.empty:
        data_chip = calculate_indicators(data_chip)
        if "當沖" in chip_mode:
            try: data_chip['VWAP'] = ta.vwap(data_chip['High'], data_chip['Low'], data_chip['Close'], data_chip['Volume'])
            except: pass
        df_view = data_chip.tail(c_view)
        if c_interval == "1d": df_view.index = df_view.index.strftime('%Y-%m-%d')
        else: df_view.index = df_view.index.strftime('%m-%d %H:%M')
        if "波段" in chip_mode:
            st.markdown("### 🤖 艾倫杭特・籌碼AI診斷")
            price_trend = df_view.iloc[-1]['Close'] - df_view.iloc[0]['Close']
            obv_trend = df_view.iloc[-1]['OBV'] - df_view.iloc[0]['OBV']
            c_sum1, c_sum2 = st.columns(2)
            c_sum1.metric("區間股價漲跌", f"{round(price_trend, 2)}", delta_color="normal" if price_trend > 0 else "inverse")
            c_sum1.metric("區間 OBV 變化", f"{int(obv_trend)}", delta="大戶進貨" if obv_trend > 0 else "大戶出貨", delta_color="normal" if obv_trend > 0 else "inverse")
            if price_trend < 0 and obv_trend > 0: st.success("🔥 **主力背離吸籌**：股價跌但籌碼增加，關注低接機會。")
            elif price_trend > 0 and obv_trend > 0: st.success("✅ **量價齊揚**：趨勢健康。")
            elif price_trend > 0 and obv_trend < 0: st.error("⚠️ **主力背離出貨**：股價漲但籌碼流出，小心回檔。")
            else: st.warning("❌ **量價同步殺盤**：趨勢偏空。")
        st.markdown(f"### 🐋 {c_title}")
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.6, 0.4])
        fig.add_trace(go.Candlestick(x=df_view.index, open=df_view['Open'], high=df_view['High'], low=df_view['Low'], close=df_view['Close'], name='股價', increasing_line_color='red', decreasing_line_color='green'), row=1, col=1)
        if "當沖" in chip_mode and 'VWAP' in df_view.columns:
            fig.add_trace(go.Scatter(x=df_view.index, y=df_view['VWAP'], line=dict(color='purple', width=2, dash='dot'), name='VWAP (當日均價)'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['OBV'], line=dict(color='orange', width=2), name='OBV (能量潮)'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['AD'], line=dict(color='cyan', width=2, dash='dot'), name='A/D Line (累積派發)'), row=2, col=1)
        fig.update_xaxes(type='category', dtick=10 if c_interval=="1d" else 6)
        fig.update_layout(height=600, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        if "當沖" in chip_mode: st.info("💡 **當沖心法**：股價站穩 **VWAP (紫色虛線)** 之上且 **OBV 向上**，為強勢多方格局；反之則偏空。")
    else: st.error("無法取得籌碼數據 (可能是盤前或資料源延遲)。")
    st.markdown("---")
    st.markdown("### 🚀 外部籌碼傳送門")
    c_link1, c_link2, c_link3 = st.columns(3)
    c_link1.link_button(f"📊 集保分佈 (Goodinfo)", f"https://goodinfo.tw/tw/EquityDistributionClassHis.asp?STOCK_ID={selected_code}", icon="🔗", type="primary")
    c_link2.link_button(f"🐳 主力動向 (Goodinfo)", f"https://goodinfo.tw/tw/ShowK_Chart.asp?STOCK_ID={selected_code}&CHT_CAT2=DATE", icon="🌊")
    c_link3.link_button("🏛️ 集保結算所 (官方)", "https://www.tdcc.com.tw/portal/zh/smWeb/qryStock", icon="🇹🇼")
