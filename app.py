import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from datetime import datetime, timedelta, timezone 
import calendar
import re
import os
import base64
import json
from io import BytesIO
from fpdf import FPDF
from supabase import create_client, Client
import firebase_admin
from firebase_admin import credentials, firestore

# 1. 페이지 설정 (최상단 고정 필수)
st.set_page_config(
    page_title="Amber Oracle | Strategic War Room",
    page_icon="🏛️",
    layout="wide"
)

# --- 🌟 Firebase 초기화 로직 (Streamlit Secrets 활용) ---
if not firebase_admin._apps:
    try:
        # Streamlit Secrets에서 Firebase 인증 정보 가져오기
        cred_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"🔥 Firebase 인증 실패. Streamlit Secrets에 [firebase] 항목이 정확히 입력되었는지 확인하세요: {e}")

# Supabase 연결
url = "https://rixjzhfjrmzppysxhvmb.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJpeGp6aGZqcm16cHB5c3hodm1iIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTQzMjQ5NywiZXhwIjoyMDkxMDA4NDk3fQ.42laWyEBMIwQ1p3p0NxhakVyMrabRHD3vVaIJvcfh5g"
supabase = create_client(url, key)

def datetime_handler(x):
    if isinstance(x, (datetime, pd.Timestamp)):
        return x.isoformat()
    raise TypeError(f"Object of type {type(x)} is not JSON serializable")

def save_to_cloud(save_name, pms_df, sob_data, avail_data):
    payload = {
        "save_name": save_name,
        "pms": pms_df.to_json(orient='split', date_format='iso') if not pms_df.empty else None,
        "sob": sob_data,
        "avail": avail_data
    }
    try:
        unique_master_id = int(datetime.now(timezone(timedelta(hours=9))).timestamp())
        
        supabase.table("amber_snapshots").upsert({
            "month": unique_master_id, 
            "data": json.dumps(payload, default=datetime_handler)
        }, on_conflict="month").execute()
        
        st.sidebar.success(f"✅ [{save_name}] 전체 데이터 통합 백업 완료!")
    except Exception as e:
        st.sidebar.error(f"❌ 저장 실패: {e}")

def get_snapshot_list():
    try:
        res = supabase.table("amber_snapshots").select("month, data").gte("month", 100).order("month", desc=True).execute()
        if res.data:
            snaps = []
            for row in res.data:
                try:
                    parsed = json.loads(row['data'])
                    name = parsed.get("save_name", "이름 없는 백업")
                    
                    dt_obj = datetime.fromtimestamp(row["month"], tz=timezone(timedelta(hours=9)))
                    time_str = dt_obj.strftime('%Y-%m-%d %H:%M')
                    
                    snaps.append({"id": row["month"], "name": name, "created_at": time_str})
                except:
                    pass
            return snaps
        return []
    except Exception as e:
        st.sidebar.error(f"스냅샷 목록 로드 에러: {e}")
        return []

def load_snapshot_data(snap_id):
    try:
        res = supabase.table("amber_snapshots").select("data").eq("month", snap_id).execute()
        if res.data and len(res.data) > 0:
            parsed = json.loads(res.data[0]['data'])
            pms_df = pd.DataFrame()
            if parsed.get('pms'):
                import io
                pms_df = pd.read_json(io.StringIO(parsed['pms']), orient='split')
            sob_data = parsed.get('sob') or {}
            avail_data = parsed.get('avail') or []
            return pms_df, sob_data, avail_data
    except Exception as e:
        st.error(f"데이터 로드 에러: {e}")
    return pd.DataFrame(), {}, []

def export_comprehensive_report(data):
    pdf = FPDF()
    pdf.set_margins(left=20, top=20, right=20) 
    pdf.add_page()
    
    pdf.set_fill_color(26, 42, 68) 
    pdf.rect(0, 0, 210, 297, 'F')
    pdf.set_fill_color(166, 138, 86) 
    pdf.rect(0, 100, 210, 5, 'F')
    
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("helvetica", "B", 35)
    pdf.set_xy(20, 120)
    pdf.cell(0, 20, "STRATEGIC REVENUE", ln=True)
    pdf.cell(0, 20, "ANALYSIS REPORT", ln=True)
    
    pdf.set_font("helvetica", "", 12)
    pdf.ln(80)
    pdf.cell(0, 10, f"TARGET PERIOD: 2026 / {data['month']}nd", ln=True, align='R')
    pdf.cell(0, 10, f"PREPARED BY: S&M ARCHITECT JEON", ln=True, align='R')
    pdf.cell(0, 10, f"REPORT DATE: {data['date']}", ln=True, align='R')

    pdf.add_page()
    pdf.set_text_color(26, 42, 68)
    pdf.set_font("helvetica", "B", 20)
    pdf.cell(0, 15, "01. KEY PERFORMANCE INDICATORS", ln=True)
    pdf.set_fill_color(166, 138, 86)
    pdf.rect(20, 35, 30, 2, 'F')
    
    pdf.ln(15)
    
    pdf.set_font("helvetica", "B", 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(60, 12, "METRIC", 1, 0, 'C', True)
    pdf.cell(55, 12, "ACTUAL", 1, 0, 'C', True)
    pdf.cell(55, 12, "ACHIEVEMENT", 1, 1, 'C', True)
    
    pdf.set_font("helvetica", "", 11)
    pdf.cell(60, 12, "Gross Revenue", 1)
    pdf.cell(55, 12, f"KRW {data['act_rev']:,.0f}", 1, 0, 'C')
    pdf.cell(55, 12, f"{data['rev_pct']:.1f}%", 1, 1, 'C')
    
    pdf.cell(60, 12, "Average ADR", 1)
    pdf.cell(55, 12, f"KRW {data['act_adr']:,.0f}", 1, 0, 'C')
    pdf.cell(55, 12, f"{data['adr_diff']:+,}", 1, 1, 'C')

    pdf.ln(15)

    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, "Performance vs Target Visualization", ln=True)
    
    pdf.set_font("helvetica", "", 10)
    pdf.cell(0, 8, "Revenue Achievement Rate:", ln=True)
    pdf.set_fill_color(230, 230, 230)
    pdf.rect(20, pdf.get_y(), 170, 8, 'F')
    bar_width = min(170, (data['rev_pct'] / 100) * 170)
    pdf.set_fill_color(26, 42, 68) if data['rev_pct'] >= 100 else pdf.set_fill_color(158, 42, 43)
    pdf.rect(20, pdf.get_y(), bar_width, 8, 'F')
    pdf.ln(12)

    pdf.cell(0, 8, "Room Nights Achievement Rate:", ln=True)
    pdf.set_fill_color(230, 230, 230)
    pdf.rect(20, pdf.get_y(), 170, 8, 'F')
    bar_width_rn = min(170, (data['rn_pct'] / 100) * 170)
    pdf.set_fill_color(166, 138, 86)
    pdf.rect(20, pdf.get_y(), bar_width_rn, 8, 'F')
    pdf.ln(20)

    pdf.add_page()
    pdf.set_font("helvetica", "B", 20)
    pdf.cell(0, 15, "02. STRATEGIC INSIGHTS", ln=True)
    pdf.set_fill_color(166, 138, 86)
    pdf.rect(20, 35, 30, 2, 'F')
    
    pdf.ln(10)
    
    pdf.set_font("helvetica", "B", 14)
    pdf.set_text_color(166, 138, 86)
    pdf.cell(0, 10, "Yielding Profitability Analysis", ln=True)
    
    pdf.set_fill_color(248, 245, 240)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("helvetica", "", 12)
    
    insight_msg = (
        f"By applying the 'Architect High-Tier Strategy' (ADR +{data['adj_adr']}%), "
        f"it is analyzed that a net gain of KRW {data['gain']:,} could be realized. "
        "This indicates a significant opportunity to shift from volume-driven "
        "to value-driven sales, reducing variable costs by up to 15%."
    )
    pdf.multi_cell(w=pdf.epw, h=10, txt=insight_msg, border=1, fill=True)
    
    pdf.ln(20)
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, "Market & Action Plan", ln=True)
    pdf.set_font("helvetica", "", 11)
    
    plans = [
        f"- Target ADR: Maintenance of KRW {data['act_adr']*1.1:,.0f} for next weekend peak.",
        "- Channel Mix: Reducing OTA dependency to increase Net RevPAR.",
        "- Yielding: Immediate Tier-Up (+1) recommended for upcoming sold-out dates."
    ]
    for plan in plans:
        pdf.cell(0, 8, plan, ln=True)

    pdf.set_y(275)
    pdf.set_font("helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 10, "CONFIDENTIAL | AMBER PURE HILL STRATEGY", 0, 0, 'C')

    return bytes(pdf.output())

def clean_numeric(val):
    if val is None: return 0.0
    if isinstance(val, pd.Series): val = val.iloc[-1] 
    if pd.isna(val): return 0.0
    try:
        s_val = str(val).replace(',', '').replace('%', '').replace('₩', '').strip()
        if s_val.lower() in ['', '-', 'nan', 'none', 'null']: return 0.0
        return float(s_val)
    except:
        return 0.0

def deduplicate_columns(cols):
    new_cols = []; seen = {}
    for c in cols:
        c_str = str(c).strip()
        if c_str in seen:
            seen[c_str] += 1
            new_cols.append(f"{c_str}_{seen[c_str]}")
        else:
            seen[c_str] = 0
            new_cols.append(c_str)
    return new_cols

def find_column(df, keywords):
    if df is None or df.empty: return None
    matched_cols = []
    for col in df.columns:
        clean_col = str(col).replace(' ', '').replace('\n', '').replace('\r', '')
        for kw in keywords:
            if kw in clean_col:
                matched_cols.append(col)
    return matched_cols[-1] if matched_cols else None

def extract_month_from_df(df):
    try:
        top_text = df.iloc[:10].astype(str).apply(lambda x: ' '.join(x), axis=1).str.cat(sep=' ')
        match = re.search(r'영업월\s*:\s*\d{4}-(\d{2})', top_text.replace(' ', '').replace('\n', ''))
        if match: return int(match.group(1))
        match2 = re.search(r'202\d-(\d{2})', top_text)
        if match2: return int(match2.group(1))
    except: pass
    return None

def extract_date_from_avail(df, file_name):
    try:
        top_text = df.iloc[:5].astype(str).apply(lambda x: ' '.join(x), axis=1).str.cat(sep=' ')
        match = re.search(r'시작일자\s*:\s*(\d{4}-\d{2}-\d{2})', top_text)
        if match: return datetime.strptime(match.group(1), '%Y-%m-%d')
    except: pass
    
    name_match = re.search(r'(\d{8})', str(file_name))
    if name_match:
        try: return datetime.strptime(name_match.group(1), '%Y%m%d')
        except: pass
    return datetime.now()

# ==========================================
# 🌟 글로벌 변수 및 시즌/티어 정밀 룰 세팅 🌟
# (기존 get_dynamic_bar_tier 및 BAR_PRICE_MATRIX 삭제 후 아래로 교체)
# ==========================================
TARGET_DATA = {
    1:  {"rn": 2270, "adr": 226869, "occ": 56.3, "rev": 514992575},
    2:  {"rn": 2577, "adr": 305227, "occ": 70.8, "rev": 786570856},
    3:  {"rn": 2248, "adr": 235587, "occ": 55.8, "rev": 529599040},
    4:  {"rn": 2414, "adr": 288049, "occ": 61.9, "rev": 695351004},
    5:  {"rn": 3082, "adr": 293220, "occ": 76.5, "rev": 903705440},
    6:  {"rn": 2776, "adr": 291140, "occ": 71.2, "rev": 808203820},
    7:  {"rn": 3671, "adr": 335590, "occ": 91.1, "rev": 1231949142},
    8:  {"rn": 3873, "adr": 358476, "occ": 96.1, "rev": 1388376999},
    9:  {"rn": 2932, "adr": 324752, "occ": 75.2, "rev": 952171506},
    10: {"rn": 3009, "adr": 298163, "occ": 74.7, "rev": 897171539},
    11: {"rn": 2402, "adr": 277746, "occ": 61.6, "rev": 667146771},
    12: {"rn": 2765, "adr": 290788, "occ": 68.6, "rev": 804030110}
}
BUDGET_DATA = {m: TARGET_DATA[m]["rev"] for m in range(1, 13)}
TOTAL_ROOM_CAPACITY = 131

WEEKDAYS_KR = ['월', '화', '수', '목', '금', '토', '일']
DYNAMIC_ROOMS = ["FDB", "FDE", "HDP", "HDT", "HDF"]
FIXED_ROOMS = ["GDB", "GDF", "FFD", "FPT", "PPV"]
ALL_ROOMS = DYNAMIC_ROOMS + FIXED_ROOMS

PRICE_TABLE = {
    "FDB": {"BAR0": 802000, "BAR8": 315000, "BAR7": 353000, "BAR6": 396000, "BAR5": 445000, "BAR4": 502000, "BAR3": 567000, "BAR2": 642000, "BAR1": 728000},
    "FDE": {"BAR0": 839000, "BAR8": 352000, "BAR7": 390000, "BAR6": 433000, "BAR5": 482000, "BAR4": 539000, "BAR3": 604000, "BAR2": 679000, "BAR1": 765000},
    "HDP": {"BAR0": 759000, "BAR8": 280000, "BAR7": 318000, "BAR6": 361000, "BAR5": 410000, "BAR4": 467000, "BAR3": 532000, "BAR2": 607000, "BAR1": 693000},
    "HDT": {"BAR0": 729000, "BAR8": 250000, "BAR7": 288000, "BAR6": 331000, "BAR5": 380000, "BAR4": 437000, "BAR3": 502000, "BAR2": 577000, "BAR1": 663000},
    "HDF": {"BAR0": 916000, "BAR8": 420000, "BAR7": 458000, "BAR6": 501000, "BAR5": 550000, "BAR4": 607000, "BAR3": 672000, "BAR2": 747000, "BAR1": 833000},
}

FIXED_PRICE_TABLE = {
    "GDB": {"UND1": 298000, "UND2": 298000, "MID1": 298000, "MID2": 298000, "UPP1": 298000, "UPP2": 298000, "UPP3":298000},
    "GDF": {"UND1": 375000, "UND2": 410000, "MID1": 410000, "MID2": 488000, "UPP1": 488000, "UPP2": 578000, "UPP3":678000},
    "FFD": {"UND1": 353000, "UND2": 393000, "MID1": 433000, "MID2": 482000, "UPP1": 539000, "UPP2": 604000, "UPP3":704000},
    "FPT": {"UND1": 500000, "UND2": 550000, "MID1": 600000, "MID2": 650000, "UPP1": 700000, "UPP2": 750000, "UPP3":850000},
    "PPV": {"UND1": 1104000, "UND2": 1154000, "MID1": 1154000, "MID2": 1304000, "UPP1": 1304000, "UPP2": 1554000, "UPP3":1704000},
}

FIXED_BAR0_TABLE = {"GDB": 298000, "GDF": 678000, "FFD": 704000, "FPT": 850000, "PPV": 1704000}

def get_season_details(date_obj):
    # 호환성: 문자열 날짜가 들어와도 에러 없이 처리하도록 강화
    if isinstance(date_obj, str):
        try: date_obj = datetime.strptime(date_obj[:10], '%Y-%m-%d')
        except: date_obj = datetime.now()
        
    m, d = date_obj.month, date_obj.day
    md = f"{m:02d}.{d:02d}"
    actual_is_weekend = date_obj.weekday() in [4, 5]
    
    if ("02.13" <= md <= "02.18") or ("09.23" <= md <= "09.28"):
        season, is_weekend = "UPP", True
    elif ("12.21" <= md <= "12.31") or ("10.01" <= md <= "10.08"):
        season, is_weekend = "UPP", False
    elif ("05.03" <= md <= "05.05") or ("05.24" <= md <= "05.26") or ("06.05" <= md <= "06.07"):
        season, is_weekend = "MID", True
    elif "07.17" <= md <= "08.29":
        season, is_weekend = "UPP", actual_is_weekend
    elif ("01.04" <= md <= "03.31") or ("11.01" <= md <= "12.20"):
        season, is_weekend = "UND", actual_is_weekend
    else:
        season, is_weekend = "MID", actual_is_weekend
        
    type_code = f"{season}{'2' if is_weekend else '1'}"
    return type_code, season, is_weekend

def determine_bar(season, is_weekend, occ):
    if season == "UPP":
        if is_weekend:
            if occ >= 81: return "BAR1"
            elif occ >= 51: return "BAR2"
            elif occ >= 31: return "BAR3"
            else: return "BAR4"
        else:
            if occ >= 81: return "BAR2"
            elif occ >= 51: return "BAR3"
            elif occ >= 31: return "BAR4"
            else: return "BAR5"
    elif season == "MID":
        if is_weekend:
            if occ >= 81: return "BAR3"
            elif occ >= 51: return "BAR4"
            elif occ >= 31: return "BAR5"
            else: return "BAR6"
        else:
            if occ >= 81: return "BAR4"
            elif occ >= 51: return "BAR5"
            elif occ >= 31: return "BAR6"
            else: return "BAR7"
    else: 
        if is_weekend:
            if occ >= 81: return "BAR4"
            elif occ >= 51: return "BAR5"
            elif occ >= 31: return "BAR6"
            else: return "BAR7"
        else:
            if occ >= 81: return "BAR5"
            elif occ >= 51: return "BAR6"
            elif occ >= 31: return "BAR7"
            else: return "BAR8"

def get_final_values(room_id, date_obj, avail, total, manual_bar=None):
    type_code, season, is_weekend = get_season_details(date_obj)
    try: current_avail = float(avail) if pd.notna(avail) else 0.0
    except: current_avail = 0.0
    occ = ((total - current_avail) / total * 100) if total > 0 else 0
    
    if manual_bar:
        bar = manual_bar
        if bar == "BAR0":
            if room_id in DYNAMIC_ROOMS: price = PRICE_TABLE.get(room_id, {}).get("BAR0", 0)
            else: price = FIXED_BAR0_TABLE.get(room_id, 0)
        else:
            if room_id in DYNAMIC_ROOMS: price = PRICE_TABLE.get(room_id, {}).get(bar, 0)
            else: price = FIXED_PRICE_TABLE.get(room_id, {}).get(bar, 0)
        return occ, bar, price, True 

    if room_id in DYNAMIC_ROOMS:
        bar = determine_bar(season, is_weekend, occ)
        price = PRICE_TABLE.get(room_id, {}).get(bar, 0)
    else:
        bar = type_code
        price = FIXED_PRICE_TABLE.get(room_id, {}).get(type_code, 0)
    return occ, bar, price, False 

# 🛠️ 이전 코드(재고 분석 탭 등)와의 에러/충돌을 막기 위한 호환성 래퍼 함수
def get_dynamic_bar_tier(occ, date_str):
    type_code, season, is_weekend = get_season_details(date_str)
    return determine_bar(season, is_weekend, occ)

def robust_read_all_sheets(file):
    dfs = []
    try:
        if file.name.endswith('.csv'):
            try: dfs.append(pd.read_csv(file, encoding='cp949', header=None))
            except: dfs.append(pd.read_csv(file, encoding='utf-8-sig', header=None))
        else:
            engine = 'xlrd' if file.name.endswith('.xls') else 'openpyxl'
            xls = pd.ExcelFile(file, engine=engine)
            for sn in xls.sheet_names:
                dfs.append(pd.read_excel(xls, sheet_name=sn, header=None))
    except Exception as e:
        st.sidebar.error(f"❌ '{file.name}' 로드 실패: {e}")
    return dfs

def get_smart_corridor(total_goal, dates, demand_index):
    day_weights = [1.0, 1.0, 1.0, 1.0, 1.8, 2.2, 1.2]
    adj_weights = [day_weights[d.weekday()] * demand_index for d in dates]
    total_w = sum(adj_weights)
    if total_w == 0: return np.zeros(len(dates)), np.zeros(len(dates)), np.zeros(len(dates))
    base = (np.cumsum(adj_weights) / total_w) * total_goal
    return base, base * 1.05, base * 0.95

def get_booking_curve(total_goal, lead_days, demand_idx):
    days = np.arange(-lead_days, 1)
    z = (days + (30 / demand_idx)) / 15
    s_curve = 1 / (1 + np.exp(-z))
    s_curve = (s_curve - s_curve.min()) / (s_curve.max() - s_curve.min())
    return days, s_curve * total_goal

# ==========================================
# 🌟 세션 및 초기 변수 세팅
# ==========================================
if 'loaded_snap' not in st.session_state:
    st.session_state['loaded_snap'] = None

yearly_data_store = {m: {"rev": 0.0, "occ": 0.0, "rn": 0.0, "adr": 0.0} for m in range(1, 13)}
df_full_pms = pd.DataFrame()
real_room_df = None
real_channel_df = None
actual_pace = []
actual_curve = []
avail_analysis = []

# ==========================================
# 사이드바 (상단)
# ==========================================
st.sidebar.title("🧬 Oracle Intelligence v5.4")
selected_month = st.sidebar.selectbox("🎯 분석 타겟 월 선택", range(1, 13), index=3)
demand_idx = st.sidebar.slider("시장 수요 지수 보정", 0.5, 2.0, 1.3)

st.sidebar.markdown("---")
st.sidebar.subheader("📂 전략 데이터 업로드 센터")

pms_files = st.sidebar.file_uploader("PMS 상세 리스트 (다중)", type=['csv', 'xlsx', 'xls'], accept_multiple_files=True)
sob_files = st.sidebar.file_uploader("영업 현황 SOB (다중)", type=['csv', 'xlsx', 'xls'], accept_multiple_files=True)
avail_files = st.sidebar.file_uploader("사용 가능 객실 현황 (다중)", type=['csv', 'xlsx', 'xls'], accept_multiple_files=True)

# ==========================================
# 데이터 파싱 (업로드 vs 클라우드 스냅샷 우선순위 병합)
# ==========================================
if st.session_state['loaded_snap'] is not None:
    st.sidebar.success("☁️ 클라우드 타임머신 모드 작동 중! (새 파일을 올리면 최신 데이터로 덮어씁니다)")
    df_full_pms = st.session_state['loaded_snap']['pms'].copy() if not st.session_state['loaded_snap']['pms'].empty else pd.DataFrame()
    cloud_sob = st.session_state['loaded_snap']['sob']
    for k, v in cloud_sob.items():
        if str(k).isdigit():
            yearly_data_store[int(k)] = v
    avail_analysis = st.session_state['loaded_snap']['avail']

# 1. SOB 데이터 처리 (스냅샷이 있든 없든 새 파일이 우선)
if sob_files:
    try:
        for f in sob_files:
            dfs = robust_read_all_sheets(f)
            for df_full in dfs:
                if df_full.empty: continue
                header_idx = -1
                for i in range(min(20, len(df_full))):
                    row_str = str(df_full.iloc[i].values).replace(' ', '')
                    if ('일자' in row_str or '날짜' in row_str) and ('매출' in row_str or '점유율' in row_str):
                        header_idx = i; break
                
                if header_idx != -1:
                    df_data = df_full.iloc[header_idx+1:].copy()
                    df_data.columns = deduplicate_columns(df_full.iloc[header_idx].values)
                    c_date = find_column(df_data, ['일자', '날짜', 'Date'])
                    c_occ = find_column(df_data, ['점유율', 'Occ'])
                    c_rev = find_column(df_data, ['매출', 'Revenue']) 
                    c_rn = find_column(df_data, ['객실수', 'RN']) 
                    c_adr = find_column(df_data, ['객단가', 'ADR']) 
                    
                    if c_date and c_rev:
                        f_m = None
                        for val in df_data[c_date].astype(str):
                            match = re.match(r'202\d-(\d{2})-\d{2}', val)
                            if match: f_m = int(match.group(1)); break
                        
                        if f_m:
                            df_clean = df_data.dropna(subset=[c_date], how='all')
                            sum_rows = df_clean[df_clean[c_date].astype(str).str.contains('합계|총계|Total', na=False)]
                            target_row = None
                            if not sum_rows.empty: target_row = sum_rows.iloc[-1]
                            else:
                                for idx in range(len(df_clean)-1, -1, -1):
                                    if clean_numeric(df_clean.iloc[idx][c_rev]) > 0:
                                        target_row = df_clean.iloc[idx]; break
                                        
                            if target_row is not None:
                                rev_val = clean_numeric(target_row[c_rev])
                                occ_val = clean_numeric(target_row[c_occ]) if c_occ else 0.0
                                rn_val = clean_numeric(target_row[c_rn]) if c_rn else 0.0
                                adr_val = clean_numeric(target_row[c_adr]) if c_adr else (rev_val/rn_val if rn_val>0 else 0)

                                if rev_val > yearly_data_store[f_m]['rev']:
                                    yearly_data_store[f_m] = {"rev": rev_val, "occ": occ_val, "rn": rn_val, "adr": adr_val}
        st.sidebar.success("✅ 최신 SOB 데이터로 업데이트 완료")
    except Exception as e: st.sidebar.error(f"SOB 처리 실패: {e}")

# 2. 객실 가용(Avail) 데이터 처리 (스냅샷이 있든 없든 새 파일이 우선)
if avail_files:
    try:
        avail_history = []
        for f in avail_files:
            dfs = robust_read_all_sheets(f)
            for df_a in dfs:
                if df_a.empty: continue
                up_date = extract_date_from_avail(df_a, f.name)
                type_idx = -1
                for i in range(min(15, len(df_a))):
                    if '객실타입' in str(df_a.iloc[i].values).replace(' ', ''):
                        type_idx = i; break
                
                if type_idx != -1:
                    d_headers = df_a.iloc[type_idx - 1].values[2:]
                    for i in range(type_idx + 1, len(df_a)):
                        r_type = str(df_a.iloc[i, 0]).strip()
                        if pd.isna(r_type) or r_type in ['nan', '합계', '예약객실', 'None', '']: continue
                        max_cap = clean_numeric(df_a.iloc[i, 1])
                        for j, d_str in enumerate(d_headers):
                            if pd.isna(d_str) or str(d_str).strip() in ['', 'nan']: continue
                            rem_val = clean_numeric(df_a.iloc[i, 2+j])
                            occ_val = ((max_cap - rem_val) / max_cap * 100) if max_cap > 0 else 0
                            clean_date = str(d_str).replace('.0', '').strip()
                            avail_history.append({"update_at": up_date, "date": f"2026-{clean_date}", "type": r_type, "occ": occ_val})
        
        df_h = pd.DataFrame(avail_history)
        if not df_h.empty:
            updates = sorted(df_h['update_at'].unique())
            if len(updates) >= 2:
                l_up, p_up = updates[-1], updates[-2]
                df_l, df_p = df_h[df_h['update_at'] == l_up], df_h[df_h['update_at'] == p_up]
                merged = pd.merge(df_l, df_p, on=['date', 'type'], suffixes=('_new', '_old'))
                merged['velocity'] = merged['occ_new'] - merged['occ_old']
                merged['suggested_tier'] = merged.apply(lambda row: get_dynamic_bar_tier(row['occ_new'], row['date']), axis=1)
                avail_analysis = merged[merged['velocity'] != 0].to_dict('records')
                st.sidebar.success("✅ 최신 재고 가속도 업데이트 완료")
    except Exception as e: st.sidebar.error(f"재고 분석 에러: {e}")

# 3. PMS 파일 파싱 (스냅샷 데이터와 병합)
if pms_files:
    try:
        all_pms = []
        if not df_full_pms.empty:
            all_pms.append(df_full_pms) # 기존 백업 데이터 유지
            
        for f in pms_files:
            dfs = robust_read_all_sheets(f)
            for df_raw in dfs:
                if df_raw.empty: continue
                h_idx = -1
                for i in range(min(15, len(df_raw))):
                    if '입실일자' in str(df_raw.iloc[i].values).replace(' ', ''):
                        h_idx = i; break
                
                if h_idx != -1:
                    df_data = df_raw.iloc[h_idx+1:].copy()
                    df_data.columns = deduplicate_columns(df_raw.iloc[h_idx].values)
                    all_pms.append(df_data)
        
        if all_pms:
            # 기존 데이터와 새 데이터를 병합 (중복 방지)
            df_full_pms = pd.concat(all_pms, ignore_index=True)
            # 혹시 모를 중복 인덱스나 완벽히 동일한 행 제거
            df_full_pms = df_full_pms.drop_duplicates()
            st.sidebar.success("✅ 최신 PMS 데이터 병합 완료")
    except Exception as e: 
        st.sidebar.error(f"PMS 파일 분석 실패: {e}")
        
# ==========================================
# 공통 지표 연산 (업로드든 클라우드든 여기서 가공)
# ==========================================
if not df_full_pms.empty:
    try:
        c_rev = find_column(df_full_pms, ['총금액', '합계', '매출'])
        c_room_rev = find_column(df_full_pms, ['객실료', '객실매출', 'RoomRate'])
        c_rn = find_column(df_full_pms, ['박수', '숙박일수'])
        c_in = find_column(df_full_pms, ['입실일자', '체크인'])
        c_bk = find_column(df_full_pms, ['예약일자', '예약일'])
        c_tp = find_column(df_full_pms, ['객실타입', 'RoomType'])
        c_st = find_column(df_full_pms, ['상태', 'Status'])
        c_path = find_column(df_full_pms, ['예약경로', 'Source'])
        
        if not c_room_rev:
            df_full_pms['객실료_추정'] = df_full_pms[c_rev]
            c_room_rev = '객실료_추정'

        for c in [c_rev, c_rn, c_room_rev]:
            if c: df_full_pms[c] = df_full_pms[c].apply(clean_numeric)
        if c_in: df_full_pms[c_in] = pd.to_datetime(df_full_pms[c_in], errors='coerce')
        if c_bk: df_full_pms[c_bk] = pd.to_datetime(df_full_pms[c_bk], errors='coerce')
        
        df_full_pms = df_full_pms.dropna(subset=[c_in, c_rev] if c_in and c_rev else [])
        if c_st: df_full_pms = df_full_pms[~df_full_pms[c_st].astype(str).str.contains('RC|취소|CXL', na=False)]

        num_d = calendar.monthrange(2026, selected_month)[1]
        t_dates_m = pd.date_range(start=f"2026-{selected_month:02d}-01", end=f"2026-{selected_month:02d}-{num_d}")
        target_df = df_full_pms[df_full_pms[c_in].dt.month == selected_month].copy() if c_in else pd.DataFrame()
        
        if not target_df.empty:
            daily_r = target_df.groupby(c_in)[c_rev].sum().reset_index()
            acc = 0.0; temp_p = []
            for d in t_dates_m:
                acc += daily_r[daily_r[c_in] == d][c_rev].sum() / 100000000
                temp_p.append(acc)
            actual_pace = temp_p
            
            if c_bk:
                target_df['LeadTime'] = (target_df[c_in] - target_df[c_bk]).dt.days
                actual_curve = [target_df[target_df['LeadTime'] >= -d][c_rev].sum() / 100000000 for d in np.arange(-90, 1)]
            
            if c_tp:
                real_room_df = target_df.groupby(c_tp).agg({c_rev:'sum', c_room_rev:'sum', c_rn:'sum'}).reset_index()
                real_room_df['전체 ADR'] = (real_room_df[c_rev] / real_room_df[c_rn]).fillna(0)
                real_room_df['객실 ADR'] = (real_room_df[c_room_rev] / real_room_df[c_rn]).fillna(0)
                real_room_df.rename(columns={c_tp: '객실타입', c_rev: '전체 매출(Total)', c_room_rev: '객실 매출(Room)', c_rn: '판매 객실수(RN)'}, inplace=True)
            
            if c_path:
                real_channel_df = target_df.groupby(c_path)[c_rev].sum().reset_index()

    except Exception as e: 
        pass

# ==========================================
# 사이드바 (하단) - 클라우드 타임머신 (저장/불러오기)
# ==========================================
st.sidebar.markdown("---")
st.sidebar.subheader("☁️ 글로벌 클라우드 백업")

snap_name = st.sidebar.text_input("💾 데이터 백업 이름", value=f"{datetime.now(timezone(timedelta(hours=9))).strftime('%m/%d %H:%M')} 마스터 백업")
if st.sidebar.button("📤 현재 전체 데이터를 클라우드에 백업", use_container_width=True):
    if not df_full_pms.empty or any(v['rev'] > 0 for v in yearly_data_store.values()):
        save_to_cloud(snap_name, df_full_pms, yearly_data_store, avail_analysis)
    else:
        st.sidebar.warning("저장할 데이터가 없습니다.")

st.sidebar.markdown("---")
st.sidebar.subheader("📥 과거 백업 불러오기")
snapshots = get_snapshot_list()

if snapshots:
    snap_opts = {s['id']: f"{s.get('name', '이름없음')} ({s.get('created_at', '')})" for s in snapshots}
    sel_snap_id = st.sidebar.selectbox("복구할 시점 선택", options=list(snap_opts.keys()), format_func=lambda x: snap_opts[x])
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("적용하기", use_container_width=True):
            pms_c, sob_c, avail_c = load_snapshot_data(sel_snap_id)
            st.session_state['loaded_snap'] = {'pms': pms_c, 'sob': sob_c, 'avail': avail_c}
            st.rerun()
    with col2:
        if st.button("초기화", use_container_width=True):
            st.session_state['loaded_snap'] = None
            st.rerun()
else:
    st.sidebar.info("저장된 백업 파일이 없습니다.")


with st.sidebar.expander("📊 2026년 마스터 타겟 보드 (항시 열람)", expanded=False):
    tgt_df = pd.DataFrame.from_dict(TARGET_DATA, orient='index')
    tgt_df.index.name = '월'
    tgt_df.rename(columns={'rn': '목표 RN', 'adr': '목표 ADR', 'occ': '목표 OCC(%)', 'rev': '목표 매출'}, inplace=True)
    tgt_df.loc['합계'] = [27117, 375346, 55.7, 10179268802]
    
    styled_tgt = tgt_df.style.format({
        '목표 RN': '{:,.0f}',
        '목표 ADR': '{:,.0f}',
        '목표 OCC(%)': '{:,.1f}',
        '목표 매출': '{:,.0f}'
    })
    st.dataframe(styled_tgt, use_container_width=True)
    
# ==========================================
# 4. 메인 대시보드 화면 구성
# ==========================================
cur_data = yearly_data_store[selected_month]
current_rev_total = cur_data['rev']
current_occ_pct = cur_data['occ']
current_rn_total = cur_data['rn']
current_adr_actual = cur_data['adr']

if current_rev_total == 0 and not df_full_pms.empty:
    try:
        c_rev_pms = find_column(df_full_pms, ['총금액', '합계', '매출'])
        c_rn_pms = find_column(df_full_pms, ['박수', '숙박일수'])
        c_in_pms = find_column(df_full_pms, ['입실일자', '체크인'])
        
        if c_rev_pms and c_rn_pms:
            m_df = df_full_pms[df_full_pms[c_in_pms].dt.month == selected_month] if c_in_pms else df_full_pms
            
            if not m_df.empty:
                current_rev_total = float(m_df[c_rev_pms].sum())
                current_rn_total = float(m_df[c_rn_pms].sum())
                current_adr_actual = current_rev_total / current_rn_total if current_rn_total > 0 else 0
                
                num_days = calendar.monthrange(2026, selected_month)[1]
                t_cap = TOTAL_ROOM_CAPACITY * num_days
                current_occ_pct = (current_rn_total / t_cap * 100) if t_cap > 0 else 0.0
    except:
        pass
        
st.title("🏛️ AMBER ORACLE v5.4")
st.subheader("Revenue Architect Strategic War Room | Global Cloud Mode")
st.markdown("---")

y_cols = st.columns(6)
for i in range(12):
    m = i + 1; m_data = yearly_data_store[m]; bud = TARGET_DATA[m]['rev']
    with y_cols[i % 6]:
        p = (m_data['rev'] / bud * 100) if bud > 0 else 0
        st.metric(f"{m}월 Revenue", f"₩{m_data['rev']/1000000:.0f}M", f"{p:.1f}% 달성")
st.markdown("---")

tgt_m = TARGET_DATA[selected_month]
st.markdown(f"### 🎯 {selected_month}월 4D 목표 대비 실적 (Target vs Actual)")
k1, k2, k3, k4 = st.columns(4)

with k1: 
    prog_rev = (current_rev_total/tgt_m['rev']*100) if tgt_m['rev']>0 else 0
    st.metric("Total Revenue (OTB)", f"₩{current_rev_total:,.0f}", f"목표 ₩{tgt_m['rev']:,.0f} ({prog_rev:.1f}%)")
with k2: 
    prog_rn = (current_rn_total/tgt_m['rn']*100) if tgt_m['rn']>0 else 0
    st.metric("Room Nights (RN)", f"{current_rn_total:,.0f} RN", f"목표 {tgt_m['rn']:,} RN ({prog_rn:.1f}%)")
with k3: 
    adr_diff = current_adr_actual - tgt_m['adr']
    st.metric("Actual ADR", f"₩{current_adr_actual:,.0f}", f"목표대비 ₩{adr_diff:,.0f}", delta_color="normal")
with k4: 
    occ_diff = current_occ_pct - tgt_m['occ']
    st.metric("Occupancy (OCC)", f"{current_occ_pct:.1f}%", f"목표대비 {occ_diff:.1f}%p", delta_color="normal")

st.markdown("---")

tabs = st.tabs([
    "🚀 페이스", "🏢 객실 감사", "🔗 시장", "💸 채널", 
    "🔮 예보", "🌟 리뷰", "🛰️ 감시", "⚔️ 대조(결론)", "🔮 AI 제안", "🎯 단가 조정"
])

with tabs[0]:
    st.subheader(f"📊 {selected_month}월 예약 가속도 모니터링 (4-Panel Analysis)")
    st.info(f"💡 {selected_month}월 투숙 데이터만을 엄격하게 필터링하여 순수한 예약 확보 궤도를 추적합니다.")
    
    num_d = calendar.monthrange(2026, selected_month)[1]
    t_dt = pd.date_range(start=f"2026-{selected_month:02d}-01", end=f"2026-{selected_month:02d}-{num_d}")
    
    start_trace = t_dt[0] - pd.DateOffset(months=3)
    trace_dt = pd.date_range(start=start_trace, end=t_dt[-1])
    
    kst_now = datetime.now(timezone(timedelta(hours=9)))
    today_date = kst_now.replace(tzinfo=None)
    
    if today_date.month == selected_month:
        cur_idx = min(today_date.day - 1, num_d - 1)
    elif today_date.month > selected_month:
        cur_idx = num_d - 1
    else:
        cur_idx = 0

    tgt_rev_100m = tgt_m['rev'] / 100000000
    base_otb_ratio = 0.50 
    days_arr = np.arange(1, num_d + 1)
    pacing_curve_ratio = base_otb_ratio + (1 - base_otb_ratio) * ((days_arr / num_d) ** 0.6)
    o_p = tgt_rev_100m * pacing_curve_ratio
    u_b = o_p * 1.08
    l_b = o_p * 0.92

    # ==========================================
    # 🧠 2. 데이터 연산 (투숙월 절대 필터링)
    # ==========================================
    stay_pace = []         
    booking_pace_m = []    
    booking_evolution = [] 
    velocity = 0
    
    if not df_full_pms.empty:
        c_bk = find_column(target_df, ['예약일자', '예약일', 'BookingDate'])
        c_in = find_column(target_df, ['입실일자', '체크인'])
        c_rev_col = find_column(target_df, ['총금액', '매출', '합계'])
        c_rn = find_column(target_df, ['박수', 'RN', '객실수'])
        
        if c_bk and c_rev_col and c_in and c_rn:
            v_df = target_df.copy()
            v_df['Temp_Bk_Date'] = pd.to_datetime(v_df[c_bk], errors='coerce')
            v_df['Temp_In_Date'] = pd.to_datetime(v_df[c_in], errors='coerce')
            v_df['Clean_Rev'] = pd.to_numeric(v_df[c_rev_col], errors='coerce').fillna(0)
            
            # 노이즈(합계 행 등) 및 박수가 없는 데이터 제거
            v_df = v_df[pd.to_numeric(v_df[c_rn], errors='coerce') > 0]
            
            # 🚨 진정한 해결책: '해당 월(selected_month)'에 입실하는 고객의 데이터만 남김!
            v_df = v_df[v_df['Temp_In_Date'].dt.month == selected_month]
            
            # 이 필터링을 거친 순수한 당월 투숙객의 총매출 합계가 진짜 cur_rev입니다.
            cur_rev = v_df['Clean_Rev'].sum()
            
            last_data_date = v_df['Temp_Bk_Date'].max()
            if pd.isna(last_data_date): last_data_date = today_date

            # 👉 1번 그래프: 실투숙 누적
            stay_daily = v_df.groupby(v_df['Temp_In_Date'].dt.day)['Clean_Rev'].sum()
            s_sum = 0
            for d in range(1, cur_idx + 2):
                s_sum += stay_daily.get(d, 0)
                stay_pace.append(s_sum / 100000000)

            # 👉 3번 그래프: 3개월 전부터의 예약 확보 진화
            plot_limit_date = min(today_date, last_data_date)
            for d in trace_dt:
                if d > plot_limit_date: break 
                check_ts = d.replace(hour=23, minute=59, second=59)
                evol_sum = v_df[v_df['Temp_Bk_Date'] <= check_ts]['Clean_Rev'].sum()
                booking_evolution.append(evol_sum / 100000000)
            
            # 👉 2번 그래프: 당월 예약 궤도
            start_idx_in_trace = (t_dt[0] - trace_dt[0]).days
            if start_idx_in_trace < len(booking_evolution):
                booking_pace_m = booking_evolution[start_idx_in_trace:]

            # 가속도 계산
            if len(booking_evolution) >= 8:
                velocity = ((booking_evolution[-1] - booking_evolution[-8]) / 7) * 100000000
    else:
        cur_rev = current_rev_total

    # ==========================================
    # 🌟 3. 지표 산출 및 상태 진단
    # ==========================================
    expected_completion_pct = pacing_curve_ratio[cur_idx] if cur_idx < len(pacing_curve_ratio) else 1.0
    forecast_rev = cur_rev / expected_completion_pct if expected_completion_pct > 0 else cur_rev
    
    ideal_rev = o_p[cur_idx] * 100000000
    cur_upper = u_b[cur_idx] * 100000000
    cur_lower = l_b[cur_idx] * 100000000

    if cur_rev > cur_upper:
        current_status, status_color = "🚨 예약 과속 (상한선 돌파)", "#FF4B4B"
        action_msg = "조기 완판 위험! 단가를 상향하여 예약 속도를 늦추십시오."
    elif cur_rev < cur_lower:
        current_status, status_color = "⚠️ 예약 미달 (하한선 이탈)", "#FFD700"
        action_msg = "전환율을 높이기 위한 타겟 프로모션이 필요합니다."
    else:
        current_status, status_color = "✅ 세이프 존 순항 중", "#00D1FF"
        action_msg = "현재 궤도를 유지하십시오."

    # UI 출력
    st.markdown(f"### 🧭 현재 궤도 상태: **<span style='color:{status_color}'>{current_status}</span>**", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("현재 순수 누적 (True OTB)", f"{int(cur_rev):,} 원")
    m2.metric("세이프존 기준점 (Oracle)", f"{int(ideal_rev):,} 원", f"{int(cur_rev - ideal_rev):+,} 원 격차")
    m3.metric("최근 일평균 픽업", f"{int(velocity):,} 원/일")
    m4.metric("월말 예상 마감 (Forecast)", f"{int(forecast_rev):,} 원")
    st.warning(f"**💡 아키텍트 액션 제안:** {action_msg}")
    st.markdown("---")

    # 📈 4. 시각화 차트
    r1c1, r1c2 = st.columns(2)
    with r1c1:
        st.markdown("#### 1️⃣ 실투숙 누적 궤도 (Stay Pace)")
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=t_dt, y=[tgt_rev_100m*(i/num_d) for i in range(1, num_d+1)], name="Linear Target", line=dict(color="gray", dash='dot')))
        if len(stay_pace) > 0:
            fig1.add_trace(go.Scatter(x=t_dt[:len(stay_pace)], y=stay_pace, name="Actual Stay", line=dict(color="#00D1FF", width=4)))
        fig1.update_layout(template="plotly_dark", height=300, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig1, use_container_width=True)
        
    with r1c2:
        st.markdown("#### 2️⃣ 당월 확보 매출 궤도 (Booking Pace)")
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=t_dt, y=l_b, mode='lines', line_width=0, fill='tonexty', fillcolor='rgba(0,209,255,0.1)', name="Safe Zone"))
        fig2.add_trace(go.Scatter(x=t_dt, y=o_p, name="Oracle S-Curve", line=dict(color="#00D1FF", width=2)))
        if len(booking_pace_m) > 0:
            fig2.add_trace(go.Scatter(x=t_dt[:len(booking_pace_m)], y=booking_pace_m, name="Actual Booking", line=dict(color="#FF4B4B", width=4)))
        fig2.update_layout(template="plotly_dark", height=300, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig2, use_container_width=True)

    r2c1, r2c2 = st.columns(2)
    with r2c1:
        st.markdown(f"#### 3️⃣ 3개월 전부터의 매출 진화 (Evolution)")
        fig3 = go.Figure()
        if len(booking_evolution) > 0:
            fig3.add_trace(go.Scatter(x=trace_dt[:len(booking_evolution)], y=booking_evolution, name="3-Month Evolution", line=dict(color="#FFD700", width=3)))
        fig3.add_vline(x=t_dt[0], line_width=1, line_dash="dash", line_color="white")
        fig3.update_layout(template="plotly_dark", height=300, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig3, use_container_width=True)

    with r2c2:
        st.markdown("#### ⏳ 4️⃣ 리드타임별 예약 곡선 (D-90)")
        _, t_c = get_booking_curve(tgt_m['rev']/100000000, 90, 1.0)
        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(x=np.arange(-90,1), y=t_c, name="Standard", line=dict(color="gray", dash='dash')))
        
        # 4번 그래프도 순수 필터링된 데이터 기반으로 재계산
        if not v_df.empty:
            act_c = []
            for d in range(-90, 1):
                # 투숙일(Temp_In_Date) 기준 d일 전(Temp_Bk_Date)까지 예약된 매출 누적
                d_sum = v_df[(v_df['Temp_In_Date'] - v_df['Temp_Bk_Date']).dt.days >= -d]['Clean_Rev'].sum()
                act_c.append(d_sum / 100000000)
            if any(val > 0 for val in act_c):
                fig4.add_trace(go.Scatter(x=np.arange(-90, 1), y=act_c, name="Actual", line=dict(color='#FF4B4B', width=4)))

        fig4.update_layout(template="plotly_dark", height=300, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig4, use_container_width=True)
        
with tabs[1]:
    st.subheader("🏢 타입별 전체/객실 ADR 정밀 감사")
    if real_room_df is not None: 
        styled_room_df = real_room_df.style.format({
            '전체 매출(Total)': '{:,.0f}', '객실 매출(Room)': '{:,.0f}', 
            '판매 객실수(RN)': '{:,.0f}', '전체 ADR': '{:,.0f}', '객실 ADR': '{:,.0f}'
        })
        st.dataframe(styled_room_df, use_container_width=True, height=350)
    else: st.info("데이터가 없습니다.")

with tabs[2]:
    fig3 = go.Figure(); fig3.add_trace(go.Bar(x=list(range(7)), y=[100, 150, 300, 500, 700, 900, 1000], name="수요", opacity=0.3))
    fig3.add_trace(go.Scatter(x=list(range(7)), y=[35]*7, name="ADR", yaxis="y2", line_width=4)); fig3.update_layout(template="plotly_dark", yaxis2=dict(overlaying="y", side="right")); st.plotly_chart(fig3, use_container_width=True)

with tabs[3]:
    if real_channel_df is not None: 
        c_col = real_channel_df.columns[0]; r_col = real_channel_df.columns[1]
        fig4 = px.pie(real_channel_df, values=r_col, names=c_col, hole=0.4, title="Channel Share", template="plotly_dark"); st.plotly_chart(fig4, use_container_width=True)

with tabs[4]:
    st.header(f"🔮 {selected_month}월 매출 마감 예보 시뮬레이션")
    
    kst_now = datetime.now(timezone(timedelta(hours=9)))
    today_month = kst_now.month
    today_day = kst_now.day
    
    num_days = calendar.monthrange(2026, selected_month)[1]
    dates = pd.date_range(start=f"2026-{selected_month:02d}-01", periods=num_days)
    
    target_goal_unit = tgt_m['rev'] / 100000000
    o_p, _, _ = get_smart_corridor(target_goal_unit, dates, demand_idx)

    data_count = len(actual_pace) 
    current_cum_rev = actual_pace[-1] if data_count > 0 else 0.0
    
    if selected_month < kst_now.month:
        effective_days = num_days 
    elif selected_month == kst_now.month:
        effective_days = max(data_count, kst_now.day) 
    else:
        effective_days = data_count 
    
    if effective_days > 0 and current_cum_rev > 0:
        if effective_days >= num_days:
            forecast_final = current_cum_rev
        else:
            avg_pace = current_cum_rev / effective_days
            forecast_final = current_cum_rev + (avg_pace * (num_days - effective_days))
    else:
        forecast_final = current_cum_rev

    forecast_line = [None] * num_days
    if 0 < effective_days < num_days:
        forecast_line[effective_days-1] = current_cum_rev
        step = (forecast_final - current_cum_rev) / (num_days - effective_days)
        for i in range(effective_days, num_days):
            forecast_line[i] = current_cum_rev + (step * (i - effective_days + 1))
    elif effective_days >= num_days:
        forecast_line = [None] * num_days 

    fig_fcst = go.Figure()
    fig_fcst.add_trace(go.Scatter(x=dates, y=o_p, name="Target", line=dict(color="rgba(0,209,255,0.4)", dash="dash")))
    if data_count > 0:
        fig_fcst.add_trace(go.Scatter(x=dates[:data_count], y=actual_pace, name="Actual (OTB)", line=dict(color="#FF4B4B", width=4)))
    if any(v is not None for v in forecast_line):
        fig_fcst.add_trace(go.Scatter(x=dates, y=forecast_line, name="Forecast", line=dict(color="#FFD700", width=2, dash="dot")))
    
    fig_fcst.update_layout(template="plotly_dark", height=450, title=f"{selected_month}월 매출 마감 예측 (단위: 억원)", yaxis_title="누적 매출 (억)")
    st.plotly_chart(fig_fcst, use_container_width=True)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("현재 누적 매출", f"{current_cum_rev:.2f} 억")
    with c2:
        target_diff = forecast_final - target_goal_unit
        st.metric("월말 예상 매출", f"{forecast_final:.2f} 억", f"{target_diff:+.2f} 억")
    with c3:
        achievement_rate = (forecast_final / target_goal_unit * 100) if target_goal_unit > 0 else 0
        st.metric("예상 달성률", f"{achievement_rate:.1f}%", delta=f"{achievement_rate-100:.1f}%")

with tabs[5]: st.subheader("🌟 리뷰 분석"); st.info("연동 대기 중")

# --- 🌟 핵심 패치: Firebase 실제 데이터 연동 (더미 데이터 삭제) ---
with tabs[6]:
    st.subheader("🛰️ 외부 시장 지표 감시 및 매출 상관관계 (Market Correlation)")
    st.info("💡 Firebase에서 수집된 실제 크롤링 데이터(항공, 렌터카, 개별 경쟁사)를 가져와 상관관계를 분석합니다.")
    
    if not df_full_pms.empty and firebase_admin._apps:
        c_in_corr = find_column(df_full_pms, ['입실일자', '체크인'])
        c_rev_corr = find_column(df_full_pms, ['총금액', '합계', '매출'])
        c_rn_corr = find_column(df_full_pms, ['박수', '숙박일수'])
        
        if c_in_corr and c_rev_corr and c_rn_corr:
            target_df_corr = df_full_pms[df_full_pms[c_in_corr].dt.month == selected_month].copy()
            if not target_df_corr.empty:
                daily_pms = target_df_corr.groupby(target_df_corr[c_in_corr].dt.date).agg(
                    rev=(c_rev_corr, 'sum'),
                    rn=(c_rn_corr, 'sum')
                ).reset_index()
                daily_pms.rename(columns={c_in_corr: 'date'}, inplace=True)
                daily_pms['date'] = pd.to_datetime(daily_pms['date'])
                daily_pms['adr'] = daily_pms['rev'] / daily_pms['rn']
                daily_pms['adr'] = daily_pms['adr'].fillna(0)
                
                # Firebase에서 실제 데이터 가져오기 로직
                db = firestore.client()
                
                # 날짜 리스트 추출 (YYYY-MM-DD 형식)
                date_list_str = daily_pms['date'].dt.strftime('%Y-%m-%d').tolist()
                
                flight_data = []
                rental_data = []
                comp_data = []
                
                # 주의: Firebase 'in' 쿼리는 한 번에 최대 10개(또는 30개)까지만 지원하므로,
                # 한 달치(30일)를 가져올 때는 전체를 가져오거나 청크로 나눠서 쿼리해야 합니다.
                # 여기서는 가장 안정적인 스트리밍 방식으로 해당 월의 데이터를 가져와서 필터링합니다.
                
                month_prefix = f"2026-{selected_month:02d}"
                
                try:
                    # 1. 항공권 데이터
                    flights_ref = db.collection('flight_prices').stream()
                    for doc in flights_ref:
                        d = doc.to_dict()
                        if d.get('date', '').startswith(month_prefix):
                            flight_data.append({'date': d.get('date'), 'flight_price': d.get('min_price', 0)})
                            
                    # 2. 렌터카 데이터
                    rentals_ref = db.collection('rental_prices').stream()
                    for doc in rentals_ref:
                        d = doc.to_dict()
                        if d.get('date', '').startswith(month_prefix):
                            # 여러 차종 중 대표값(예: Ray) 또는 평균값 사용
                            rental_data.append({'date': d.get('date'), 'rental_price': d.get('Ray_Price', 0)})
                            
                    # 3. 개별 호텔 데이터
                    comps_ref = db.collection('hotel_comp_prices').stream()
                    for doc in comps_ref:
                        d = doc.to_dict()
                        if d.get('date', '').startswith(month_prefix):
                            comp_data.append({
                                'date': d.get('date'), 
                                'hotel_name': d.get('hotel_name', 'Unknown'), 
                                'price': d.get('price', 0)
                            })
                            
                except Exception as e:
                    st.error(f"🔥 Firebase 데이터 로드 에러: {e}")

                # 데이터프레임 변환 및 날짜 병합
                df_flight = pd.DataFrame(flight_data)
                if not df_flight.empty: df_flight['date'] = pd.to_datetime(df_flight['date'])
                
                df_rental = pd.DataFrame(rental_data)
                if not df_rental.empty: df_rental['date'] = pd.to_datetime(df_rental['date'])
                
                df_comp = pd.DataFrame(comp_data)
                if not df_comp.empty: 
                    df_comp['date'] = pd.to_datetime(df_comp['date'])
                    # 호텔 이름을 컬럼으로 변환 (Pivot)
                    df_comp_pivot = df_comp.pivot_table(index='date', columns='hotel_name', values='price', aggfunc='mean').reset_index()
                else:
                    df_comp_pivot = pd.DataFrame()

                # PMS 데이터(daily_pms)에 시장 데이터 Left Join
                if not df_flight.empty: daily_pms = pd.merge(daily_pms, df_flight.groupby('date')['flight_price'].mean().reset_index(), on='date', how='left')
                else: daily_pms['flight_price'] = 0
                
                if not df_rental.empty: daily_pms = pd.merge(daily_pms, df_rental.groupby('date')['rental_price'].mean().reset_index(), on='date', how='left')
                else: daily_pms['rental_price'] = 0
                
                if not df_comp_pivot.empty: 
                    daily_pms = pd.merge(daily_pms, df_comp_pivot, on='date', how='left')
                
                # 병합 후 호텔 컬럼이 없으면 0으로 초기화
                for h in ['Parnas_Jeju', 'Grand_Josun', 'Amber_Pure_Hill']:
                    if h not in daily_pms.columns:
                        daily_pms[h] = 0

                # 결측치(데이터가 없는 날)는 이전/이후 값으로 채우거나 0으로 처리
                daily_pms.ffill(inplace=True)
                daily_pms.fillna(0, inplace=True)

                # 1. 시계열 트렌드 비교 차트
                st.markdown("#### 📈 실제 시장 요금 vs 엠버퓨어힐 매출 트렌드")
                fig_trend = go.Figure()
                fig_trend.add_trace(go.Bar(x=daily_pms['date'], y=daily_pms['rev'], name="우리 매출(Gross)", opacity=0.4, yaxis='y1', marker_color='#00D1FF'))
                fig_trend.add_trace(go.Scatter(x=daily_pms['date'], y=daily_pms['flight_price'], name="평균 항공권", mode='lines+markers', yaxis='y2', line=dict(color='#4CAF50')))
                fig_trend.add_trace(go.Scatter(x=daily_pms['date'], y=daily_pms['rental_price'], name="평균 렌터카", mode='lines+markers', yaxis='y2', line=dict(color='#FFD700')))
                
                # 개별 호텔 라인 그리기
                hotel_colors = {'Parnas_Jeju': '#FF4B4B', 'Grand_Josun': '#9370DB', 'Amber_Pure_Hill': '#FFFFFF'}
                hotel_labels = {'Parnas_Jeju': '파르나스', 'Grand_Josun': '그랜드조선', 'Amber_Pure_Hill': '엠버퓨어힐(크롤링)'}
                
                for h in ['Parnas_Jeju', 'Grand_Josun', 'Amber_Pure_Hill']:
                    if h in daily_pms.columns and not daily_pms[h].eq(0).all():
                        fig_trend.add_trace(go.Scatter(x=daily_pms['date'], y=daily_pms[h], name=hotel_labels.get(h, h), mode='lines+markers', yaxis='y2', line=dict(color=hotel_colors.get(h, '#9e2a2b'))))
                
                fig_trend.update_layout(
                    template="plotly_dark", height=450,
                    yaxis=dict(title="우측: 매출 (원)", side='right', showgrid=False),
                    yaxis2=dict(title="좌측: 시장 단가 (원)", overlaying='y', side='left', showgrid=True),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_trend, use_container_width=True)
                
                # 2. 상관관계 분석
                st.markdown("#### 🔄 핵심 지표 상관계수 (Correlation Coefficient)")
                
                # 데이터가 모두 0이면 상관관계 계산 시 에러 방지
                try:
                    corr_cols = ['rev', 'rn', 'adr', 'flight_price', 'rental_price'] + [h for h in ['Parnas_Jeju', 'Grand_Josun', 'Amber_Pure_Hill'] if h in daily_pms.columns]
                    corr_df = daily_pms[corr_cols].corr()
                    
                    c1, c2, c3 = st.columns(3)
                    corr_flight = corr_df.loc['rn', 'flight_price'] if 'flight_price' in corr_df else 0
                    corr_rent = corr_df.loc['rn', 'rental_price'] if 'rental_price' in corr_df else 0
                    
                    # 기준 경쟁사 동적 선택 (파르나스 우선, 없으면 그랜드조선)
                    target_comp = 'Parnas_Jeju' if 'Parnas_Jeju' in corr_df else 'Grand_Josun'
                    corr_comp = corr_df.loc['adr', target_comp] if target_comp in corr_df else 0
                    comp_label = "파르나스" if target_comp == 'Parnas_Jeju' else "그랜드조선"
                    
                    def get_corr_text(val):
                        if pd.isna(val): return "데이터 부족"
                        if val > 0.7: return "매우 강한 양의 상관관계"
                        elif val > 0.3: return "양의 상관관계"
                        elif val > -0.3: return "상관관계 미미"
                        elif val > -0.7: return "음의 상관관계"
                        else: return "매우 강한 음의 상관관계"
                        
                    with c1:
                        st.metric("✈️ 항공권 요금 vs 우리 호텔 판매량(RN)", f"{corr_flight:.2f}", get_corr_text(corr_flight), delta_color="off")
                    with c2:
                        st.metric("🚗 렌터카 요금 vs 우리 호텔 판매량(RN)", f"{corr_rent:.2f}", get_corr_text(corr_rent), delta_color="off")
                    with c3:
                        st.metric(f"🏨 {comp_label} 요금 vs 우리 호텔 ADR", f"{corr_comp:.2f}", get_corr_text(corr_comp), delta_color="off")
                        
                    st.markdown("---")
                    st.markdown("#### 🔬 상세 산점도 분석 (Scatter Plot)")
                    
                    x_options = ['flight_price', 'rental_price'] + [h for h in ['Parnas_Jeju', 'Grand_Josun', 'Amber_Pure_Hill'] if h in daily_pms.columns]
                    x_format = {'flight_price':'평균 항공권 요금', 'rental_price':'평균 렌터카 요금', 'Parnas_Jeju':'파르나스 요금', 'Grand_Josun':'그랜드조선 요금', 'Amber_Pure_Hill':'엠버퓨어힐(크롤링) 요금'}
                    
                    x_axis = st.selectbox("X축(원인) 지표 선택", x_options, format_func=lambda x: x_format.get(x, x))
                    y_axis = st.selectbox("Y축(결과) 지표 선택", ['rn', 'rev', 'adr'], format_func=lambda x: {'rn':'판매 객실수(RN)', 'rev':'총매출(Gross)', 'adr':'엠버퓨어힐 평균 ADR'}[x])
                    
                    if not daily_pms[x_axis].eq(0).all(): # x축 데이터가 0만 있는게 아니면 차트 그림
                        fig_scatter = px.scatter(daily_pms, x=x_axis, y=y_axis, template="plotly_dark", 
                                                 title=f"시장 지표에 따른 우리 호텔 실적 변화", opacity=0.7)
                        fig_scatter.update_traces(marker=dict(size=12, color='#00D1FF'))
                        st.plotly_chart(fig_scatter, use_container_width=True)
                    else:
                        st.warning("해당 지표의 시장 데이터가 아직 수집되지 않았습니다.")
                except Exception as e:
                    st.warning("상관관계를 분석할 데이터(분산)가 부족합니다. 크롤링 데이터가 더 수집되어야 합니다.")
            else:
                st.info("해당 월의 PMS 데이터가 부족하여 상관관계를 분석할 수 없습니다.")
        else:
            st.info("상관관계 분석에 필요한 '입실일자' 또는 '총매출' 컬럼을 찾을 수 없습니다.")
    else:
        if not firebase_admin._apps:
            st.error("🔥 Firebase 인증 설정이 필요합니다. Streamlit Secrets에 인증 키를 등록해 주세요.")
        else:
            st.info("상관관계 분석을 위해 PMS 데이터를 먼저 업로드(또는 로드)해 주세요.")

with tabs[7]:
    st.markdown("---")
    st.subheader("📊 전략 보고서 정식 출력")
    if st.button("📄 회장님 보고용 종합 리포트 생성 (PDF)"):
        # 기존 로직 유지
        safe_adj_adr = int(sim_adr - current_adr_actual) if 'sim_adr' in locals() else 0
        safe_gain = int(ar_net - base_net) if ('ar_net' in locals() and 'base_net' in locals()) else 0
        
        report_payload = {
            'date': kst_now.strftime('%Y-%m-%d'),
            'month': selected_month,
            'act_rev': current_rev_total,
            'tgt_rev': tgt_m['rev'],
            'rev_pct': (current_rev_total / tgt_m['rev'] * 100) if tgt_m['rev'] > 0 else 0,
            'act_rn': current_rn_total,
            'tgt_rn': tgt_m['rn'],
            'rn_pct': (current_rn_total / tgt_m['rn'] * 100) if tgt_m['rn'] > 0 else 0,
            'act_adr': current_adr_actual,
            'tgt_adr': tgt_m['adr'],
            'adr_diff': int(current_adr_actual - tgt_m['adr']),
            'adj_adr': safe_adj_adr,
            'gain': safe_gain
        }
        
        try:
            pdf_data = export_comprehensive_report(report_payload)
            st.download_button(
                label="📥 PDF 리포트 다운로드",
                data=pdf_data,
                file_name=f"Amber_Strategy_Report_{selected_month}월.pdf",
                mime="application/pdf"
            )
            st.success("✅ 보고서가 성공적으로 생성되었습니다!")
        except Exception as e:
            st.error(f"❌ PDF 생성 실패: {e}")

    # ==========================================
    # 🏛️ 아키텍트 전용: 총지배인 정책 오류 입증 섹션
    # ==========================================
    st.markdown("---")
    st.header(f"🏟️ {selected_month}월 수익 최적화 검증 (Architecture vs GM Policy)")
    
    # [1] 과거 데이터 기반 가격 탄력성 (Elasticity) 분석
    st.subheader("1️⃣ 과거 가격 탄력성 검증 (Price Elasticity)")
    if not df_full_pms.empty:
        try:
            # 일별 ADR과 RN의 상관관계 계산
            elasticity_df = target_df.groupby(c_in).agg({c_rev:'sum', c_rn:'sum'}).reset_index()
            elasticity_df['adr'] = elasticity_df[c_rev] / elasticity_df[c_rn]
            
            # 단순 탄력성 계산: (RN 변화율 / ADR 변화율)
            # 여기서는 분석을 위해 ADR과 RN의 상관계수를 활용
            corr_val = elasticity_df['adr'].corr(elasticity_df[c_rn])
            
            c_e1, c_e2 = st.columns([2, 1])
            with c_e1:
                fig_e = px.scatter(elasticity_df, x='adr', y=c_rn, trendline="ols", 
                                   title="우리 호텔 ADR 상승 시 물량 하락 변동성", template="plotly_dark")
                st.plotly_chart(fig_e, use_container_width=True)
            with c_e2:
                st.metric("가격 탄력성 지수", f"{corr_val:.2f}", 
                          "0에 가까울수록 가격저항 낮음" if corr_val > -0.3 else "가격저항 높음")
                st.write("💡 **분석 결과:**")
                if corr_val > -0.3:
                    st.success("현재 단가를 더 올려도 물량 이탈이 적습니다. GM의 '박리다매'는 명백한 수익 손실입니다.")
                else:
                    st.warning("가격 저항이 존재합니다. 단가 인상 시 정밀한 타겟 마케팅이 병행되어야 합니다.")
        except: st.info("탄력성 분석을 위한 데이터가 충분하지 않습니다.")

    # [2] 경쟁사 가격 격차 한계선 (Price Gap vs Pickup)
    st.subheader("2️⃣ 경쟁사 가격 격차 분석 (Price Gap Boundary)")
    try:
        # Tab 6에서 계산된 daily_pms 데이터 활용
        # 경쟁사 평균 가격 산출
        comp_cols = [h for h in ['Parnas_Jeju', 'Grand_Josun'] if h in daily_pms.columns]
        if comp_cols:
            avg_comp_price = daily_pms[comp_cols].mean(axis=1).mean()
            price_gap = current_adr_actual - avg_comp_price
            
            col_g1, col_g2, col_g3 = st.columns(3)
            col_g1.metric("경쟁사 평균 요금", f"₩{int(avg_comp_price):,}")
            col_g2.metric("엠버 현재 ADR", f"₩{int(current_adr_actual):,}")
            col_g3.metric("가격 격차 (Gap)", f"₩{int(price_gap):,}", 
                          delta="시장 우위" if price_gap < 0 else "프리미엄 포지셔닝")
            
            if price_gap > 50000:
                st.error("🚨 경고: 경쟁사 대비 가격이 너무 높습니다. 예약 속도가 둔화될 임계점에 도달했습니다.")
            elif price_gap < -30000:
                st.success("📢 기회: 경쟁사 대비 저렴합니다. 즉시 단가를 상향하여 수익을 보전해야 합니다.")
    except: st.info("경쟁사 가격 격차를 분석할 크롤링 데이터가 없습니다.")

    # [3] 조기 완판의 기회비용 (The Early Sellout Penalty)
    st.subheader("3️⃣ 조기 완판 기회비용 (Opportunity Cost of Early Sellout)")
    V_C = 50000 # 변동비
    
    # 🌟 데이터 기반 정밀 완판 시점 분석 (입금가 Net Rate 룰 적용) 🌟
    if not df_full_pms.empty:
        c_tp = find_column(df_full_pms, ['객실타입', '룸타입', 'RoomType']) # 객실타입 컬럼 찾기
        
        # 리드타임(예약일~입실일) 및 건별 실제 ADR 계산
        target_df['LeadTime'] = (target_df[c_in] - target_df[c_bk]).dt.days
        target_df['Booking_ADR'] = target_df[c_rev] / target_df[c_rn]
        
        if c_tp:
            def calculate_lost_revenue(row):
                # 1. D-14 이전이 아니면 정상 판매로 간주
                if row['LeadTime'] <= 14: return 0.0
                
                r_type = str(row[c_tp]).strip()
                d_in = row[c_in]
                
                # 2. 시즌 및 주말 여부 가져오기 (수현님 커스텀 함수)
                try:
                    type_code, season, is_weekend = get_season_details(d_in)
                except:
                    return 0.0 # 날짜 파싱 에러 시 스킵
                
                # 3. 타입별 최하단 Base 가격(BAR8 또는 시즌 기본가) 가져오기
                base_price = 0
                if r_type in DYNAMIC_ROOMS:
                    # 가동률 0% 기준 해당 시즌의 시작가 판별
                    starting_bar = determine_bar(season, is_weekend, 0)
                    base_price = PRICE_TABLE.get(r_type, {}).get(starting_bar, 0)
                elif r_type in FIXED_ROOMS:
                    base_price = FIXED_PRICE_TABLE.get(r_type, {}).get(type_code, 0)
                else:
                    base_price = 250000 # 매핑되지 않은 예외 타입의 기본값
                    
                # 4. 수현님 룰: 최대할인 20% + 수수료 15%를 제한 '최저 입금가 마지노선'
                floor_net_price = base_price * 0.80 * 0.85 
                actual_net_adr = row['Booking_ADR']
                
                # 5. 마지노선보다 싼 입금가로 털어버렸을 때만 손실로 산출
                if actual_net_adr < floor_net_price:
                    # 정상적으로 할인 없이 팔았다면 받았을 '정상 입금가' (수수료 15%만 공제)
                    potential_net_price = base_price * 0.85
                    return (potential_net_price - actual_net_adr) * row[c_rn]
                return 0.0

            # 손실액 계산 적용
            target_df['Lost_Revenue'] = target_df.apply(calculate_lost_revenue, axis=1)
            cheap_early_birds = target_df[target_df['Lost_Revenue'] > 0]
            
            early_rn = cheap_early_birds[c_rn].sum()
            early_adr = cheap_early_birds[c_rev].sum() / early_rn if early_rn > 0 else 0
            total_lost_revenue = cheap_early_birds['Lost_Revenue'].sum()

            c_l1, c_l2 = st.columns(2)
            with c_l1:
                st.metric("마지노선 이탈 덤핑 객실", f"{int(early_rn):,} RN", "할인율 20% 초과 위반 물량")
                st.metric("해당 물량 평균 입금가", f"₩{int(early_adr):,}")
            with c_l2:
                st.metric("⚠️ 누적 기회비용 손실액", f"₩{int(total_lost_revenue):,}", 
                          "덤핑 판매로 날린 순수익", delta_color="inverse")
                st.progress(min(1.0, total_lost_revenue / 100000000))
                st.write(f"📢 **결론:** 최대 할인 한도(-20%)를 초과하여 D-14 이전에 무리하게 덤핑된 **{int(early_rn):,}실**을 노디스카운트 정상 입금가(Base Net)로만 방어했어도, 최소 **₩{int(total_lost_revenue):,}**의 순수익을 더 보전할 수 있었습니다.")
        else:
            st.info("객실타입 컬럼을 찾을 수 없어 기회비용 정밀 분석이 불가능합니다.")
            
    # [4] 최종 통합 시뮬레이터 (What-if)
    st.markdown("---")
    st.subheader("🏟️ 최종 전략 시뮬레이션: GM vs Architect")
    
    base_gross = current_rev_total
    base_rn = current_rn_total
    base_adr = current_adr_actual
    base_net = base_gross - (base_rn * V_C)

    st.markdown("### 🛠️ 단가-물량-수익 상관 시뮬레이션")
    cs1, cs2, cs3 = st.columns(3)
    with cs1:
        sim_adr = st.number_input("💡 가상 타겟 ADR (원)", min_value=50000, value=int(base_adr) if base_adr > 0 else int(tgt_m['adr']))
    with cs2:
        sim_rn_pct = st.slider("📉 예상 물량 변동률 (%)", -50, 50, 0)
    with cs3:
        sim_ota_share = st.slider("💸 OTA 비중 (%)", 0, 100, 70)

    # 시뮬레이션 연산 (수수료 15% 가정)
    ar_rn = base_rn * (1 + sim_rn_pct / 100)
    ar_gross = sim_adr * ar_rn
    ar_comm = ar_gross * (sim_ota_share / 100) * 0.15
    ar_cost = ar_rn * V_C
    ar_net = ar_gross - ar_comm - ar_cost

    cl, cr = st.columns(2)
    with cl:
        st.subheader("👨‍💼 총지배인 정책 (Current)")
        st.metric("총매출 (Gross)", f"₩{int(base_gross):,}")
        st.error(f"순수익 (Net): ₩{int(base_net):,}")
        st.write(f"가동률: {current_occ_pct:.1f}%")
    with cr:
        st.subheader("🏛️ 아키텍트 전략 (Proposed)")
        gain = ar_net - base_net
        st.metric("가상 총매출 (Gross)", f"₩{int(ar_gross):,}", delta=f"{int(ar_gross - base_gross):+,}")
        st.success(f"가상 순수익 (Net): ₩{int(ar_net):,}")
        st.write(f"순수익 증감: **₩{int(gain):+,}**")

    # 결론 리포트
    if gain > 0:
        st.info(f"💡 **최종 검증:** 가동률을 일부 포기하더라도 단가를 상향하는 것이 순수익 면에서 **₩{int(gain):,}** 더 유리합니다. '채우는 것'이 목표가 아니라 '남기는 것'이 목표여야 합니다.")
    else:
        st.warning(f"⚠️ **최종 검증:** 현재 설정한 단가와 물량 감소폭으로는 수익 보전이 어렵습니다. 가격 저항선을 다시 확인하십시오.")

    # 비교 차트
    fig_final = px.bar(pd.DataFrame({
        "Strategy": ["GM Policy", "GM Policy", "Architect", "Architect"],
        "Metric": ["Gross Revenue", "Net Profit", "Gross Revenue", "Net Profit"],
        "Amount": [base_gross, base_net, ar_gross, ar_net]
    }), x="Metric", y="Amount", color="Strategy", barmode="group", template="plotly_dark", color_discrete_sequence=['#9e2a2b', '#00D1FF'])
    st.plotly_chart(fig_final, use_container_width=True)
    
with tabs[8]:
    st.header("🔮 AI 예약 과속 감시")
    if not df_full_pms.empty:
        c_bk_ai = find_column(df_full_pms, ['예약일자', 'Created']); c_in_ai = find_column(df_full_pms, ['입실일자', '체크인']); c_rn_ai = find_column(df_full_pms, ['박수', 'RN'])
        if c_bk_ai and c_in_ai:
            today_now = datetime(2026, 4, 5); df_r = df_full_pms[df_full_pms[c_bk_ai] >= (today_now - timedelta(days=7))]
            if not df_r.empty: 
                type_c = find_column(df_full_pms, ['객실타입', 'Room'])
                st.warning("🔥 최근 7일 내 예약이 급증한 일자 리스트입니다. (단가 상향 타겟)")
                ai_df = df_r.groupby([c_in_ai, type_c])[c_rn_ai].sum().reset_index()
                ai_df.columns = ['투숙일자', '객실타입', '최근 7일 유입 객실수(RN)']
                ai_df['투숙일자'] = ai_df['투숙일자'].dt.strftime('%Y-%m-%d')
                
                styled_ai_df = ai_df.style.format({'최근 7일 유입 객실수(RN)': '{:,.0f}'}).bar(subset=['최근 7일 유입 객실수(RN)'], color='#FF4B4B')
                st.dataframe(styled_ai_df, use_container_width=True, height=350)
    else: st.info("데이터가 없습니다.")

with tabs[9]:
    st.header("🎯 Dynamic Seasonality Price Guide")
    if avail_analysis:
        reco_df = pd.DataFrame(avail_analysis).sort_values(by='velocity', ascending=False)
        def oracle_rec(row):
            if row['velocity'] >= 10: return "🔥 Tier Jump (+2단계)"
            elif row['velocity'] >= 5: return "⚡ Tier Jump (+1단계)"
            return "표준 유지"
        
        reco_df['전략 제안'] = reco_df.apply(oracle_rec, axis=1)
        reco_df.rename(columns={'date': '투숙일자', 'type': '객실타입', 'occ_new': '현재 점유율(%)', 'velocity': '가속도(%p)', 'suggested_tier':'제안 티어'}, inplace=True)
        
        display_cols = ['투숙일자', '객실타입', '현재 점유율(%)', '가속도(%p)', '제안 티어', '전략 제안']
        styled_reco = reco_df[display_cols].style.format({
            '현재 점유율(%)': '{:,.1f}', '가속도(%p)': '{:,.1f}'
        }).map(lambda x: 'background-color: #9e2a2b; color: white; font-weight: bold;' if 'Jump' in str(x) else '', subset=['전략 제안'])
        
        st.dataframe(styled_reco, use_container_width=True, height=400)
        st.plotly_chart(px.density_heatmap(reco_df, x="투숙일자", y="객실타입", z="가속도(%p)", title="Booking Velocity Heatmap", color_continuous_scale="Reds", template="plotly_dark"), use_container_width=True)
    else:
        st.warning("🧐 분석할 재고 데이터가 없습니다.")

# --- 5. 하단 공통 구역 (Advanced Pro-Level Simulator) ---
st.markdown("---")
st.subheader("🔮 Pro-Level Yield Simulator (가격 저항성 기반 정밀 RM 시뮬레이터)")
st.markdown("단가를 올리는 시뮬레이션을 통해, 가격 저항에 따른 예약 이탈률(Churn Rate)을 예측하고 **최종 순수익(Net Revenue) 및 타겟 ADR 방어율**을 도출합니다.")

c1, c2, c3, c4 = st.columns(4)
with c1: sim_type = st.selectbox("🎯 타겟 객실 타입", ['FDB', 'FDE', 'HDP', 'HDT', 'HDF', 'PPV'])
with c2: current_tier = st.selectbox("📉 현재 판매 티어", ['B8', 'B7', 'B6', 'B5', 'B4', 'B3'], index=0)
with c3: target_tier = st.selectbox("📈 목표 상향 티어", ['B7', 'B6', 'B5', 'B4', 'B3', 'B2', 'B1'], index=2)
with c4: comp_adr = st.number_input("⚔️ 주변 경쟁사 최저가 (원)", value=380000, step=10000)

c5, c6, c7, c8 = st.columns(4)
with c5: est_rn = st.number_input("📅 타겟 기간 예상 판매 객실수(RN)", value=50, step=5)
with c6: elasticity = st.select_slider("📉 수요 탄력성 (가격 저항)", options=['낮음(비탄력)', '보통', '높음(탄력)'], value='보통')
with c7: st.markdown("<br>", unsafe_allow_html=True); run_sim = st.button("🚀 시뮬레이션 가동", use_container_width=True)

if run_sim:
    cur_price = BAR_PRICE_MATRIX[sim_type][current_tier]
    tgt_price = BAR_PRICE_MATRIX[sim_type][target_tier]

    price_gap_ratio = max(0, (tgt_price - cur_price) / cur_price)
    comp_gap_ratio = max(0, (tgt_price - comp_adr) / comp_adr)

    e_factor = {'낮음(비탄력)': 0.5, '보통': 1.0, '높음(탄력)': 1.8}[elasticity]
    churn_rate = min(1.0, (price_gap_ratio * 0.4 + comp_gap_ratio * 0.6) * e_factor)

    lost_rn = int(est_rn * churn_rate)
    final_rn = est_rn - lost_rn

    cur_rev = cur_price * est_rn
    final_rev = tgt_price * final_rn
    net_gain = final_rev - cur_rev

    st.markdown("#### 📊 Displacement Analysis Report (이탈 객실 vs 최종 수익)")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("현재 예상 매출 (상향 전)", f"₩{int(cur_rev):,}", f"단가 ₩{cur_price:,}")
    r2.metric("예상 이탈 객실 (Churn)", f"-{lost_rn} RN", f"이탈률 {churn_rate*100:.1f}%", delta_color="inverse")
    r3.metric("최종 판매 예상 (상향 후)", f"{final_rn} RN", f"단가 ₩{tgt_price:,}")
    r4.metric("💰 최종 넷 레비뉴 (Net Gain)", f"₩{int(final_rev):,}", f"{int(net_gain):,} 원")

    if net_gain > 0:
        st.success(f"✅ **[진행 권장]** 객실을 **{lost_rn}개 덜 팔더라도**, 단가 상승분이 볼륨 손실을 압도하여 최종적으로 **+{int(net_gain):,}원**의 추가 이익이 발생합니다. 이는 목표 ADR을 견인하는 핵심 동력이 됩니다.")
    else:
        st.error(f"⚠️ **[진행 보류]** 가격 저항과 경쟁사 단가({comp_adr:,}원)에 밀려, 단가를 올릴 경우 방이 안 팔려 오히려 **{int(net_gain):,}원**의 손실이 발생합니다. 이 구간은 가격 방어선을 유지하세요.")
