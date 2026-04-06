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
from io import BytesIO
from fpdf import FPDF
from supabase import create_client, Client

# 1. 페이지 설정 (최상단 고정 필수)
st.set_page_config(
    page_title="Amber Oracle | Strategic War Room",
    page_icon="🏛️",
    layout="wide"
)

# --- [DB 연결] ---
url = "https://rixjzhfjrmzppysxhvmb.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJpeGp6aGZqcm16cHB5c3hodm1iIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTQzMjQ5NywiZXhwIjoyMDkxMDA4NDk3fQ.42laWyEBMIwQ1p3p0NxhakVyMrabRHD3vVaIJvcfh5g"
supabase = create_client(url, key)

def save_to_cloud(month, df):
    try:
        json_data = df.to_json(orient='split')
        # on_conflict를 명시해서 'month'가 겹치면 업데이트하라고 확실히 말해줍니다.
        supabase.table("amber_snapshots").upsert(
            {"month": month, "data": json_data},
            on_conflict="month" 
        ).execute()
        st.success(f"✅ {month}월 데이터가 클라우드 DB에 영구 저장되었습니다.")
        return True
    except Exception as e:
        st.error(f"❌ 클라우드 저장 실패: {e}")
        return False

def load_from_cloud(month):
    # DB에서 해당 월의 데이터를 가져옵니다.
    response = supabase.table("amber_snapshots").select("data").eq("month", month).execute()
    if response.data:
        import io
        return pd.read_json(io.StringIO(response.data[0]['data']), orient='split')
    return None

def export_comprehensive_report(data):
    pdf = FPDF()
    pdf.set_margins(left=20, top=20, right=20) # 여백 확실히 고정
    pdf.add_page()
    
    # --- [PAGE 1: BRAND COVER] ---
    pdf.set_fill_color(26, 42, 68) # 엠버 네이비
    pdf.rect(0, 0, 210, 297, 'F')
    pdf.set_fill_color(166, 138, 86) # 엠버 골드
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

    # --- [PAGE 2: KPI & MINI CHARTS] ---
    pdf.add_page()
    pdf.set_text_color(26, 42, 68)
    pdf.set_font("helvetica", "B", 20)
    pdf.cell(0, 15, "01. KEY PERFORMANCE INDICATORS", ln=True)
    pdf.set_fill_color(166, 138, 86)
    pdf.rect(20, 35, 30, 2, 'F')
    
    pdf.ln(15)
    
    # --- [지능형 실적 분석 로직] ---
    rev_status = "OVER" if data['rev_pct'] >= 100 else "UNDER"
    adr_status = "STABLE" if data['adr_diff'] >= 0 else "WARNING"
    
    # 핵심 데이터 요약 테이블
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

    # --- [수현 님이 원하시는 시각화: 수동 바 차트 생성] ---
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, "Performance vs Target Visualization", ln=True)
    
    # 1. 매출 차트 그리기
    pdf.set_font("helvetica", "", 10)
    pdf.cell(0, 8, "Revenue Achievement Rate:", ln=True)
    # 배경 바
    pdf.set_fill_color(230, 230, 230)
    pdf.rect(20, pdf.get_y(), 170, 8, 'F')
    # 실적 바 (달성률에 따라 길이 조절, 최대 170mm)
    bar_width = min(170, (data['rev_pct'] / 100) * 170)
    pdf.set_fill_color(26, 42, 68) if data['rev_pct'] >= 100 else pdf.set_fill_color(158, 42, 43)
    pdf.rect(20, pdf.get_y(), bar_width, 8, 'F')
    pdf.ln(12)

    # 2. RN(객실수) 차트 그리기
    pdf.cell(0, 8, "Room Nights Achievement Rate:", ln=True)
    pdf.set_fill_color(230, 230, 230)
    pdf.rect(20, pdf.get_y(), 170, 8, 'F')
    bar_width_rn = min(170, (data['rn_pct'] / 100) * 170)
    pdf.set_fill_color(166, 138, 86)
    pdf.rect(20, pdf.get_y(), bar_width_rn, 8, 'F')
    pdf.ln(20)

    # --- [PAGE 3: STRATEGIC INSIGHT] ---
    pdf.add_page()
    pdf.set_font("helvetica", "B", 20)
    pdf.cell(0, 15, "02. STRATEGIC INSIGHTS", ln=True)
    pdf.set_fill_color(166, 138, 86)
    pdf.rect(20, 35, 30, 2, 'F')
    
    pdf.ln(10)
    
    # 아키텍트 전략 제언 박스 (에러 방지를 위해 epw 사용)
    pdf.set_font("helvetica", "B", 14)
    pdf.set_text_color(166, 138, 86)
    pdf.cell(0, 10, "Yielding Profitability Analysis", ln=True)
    
    pdf.set_fill_color(248, 245, 240)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("helvetica", "", 12)
    
    # 에러 났던 부분: 0 대신 pdf.epw(실제 너비)를 사용하여 안전하게 출력
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

# --- [유틸리티 엔진: 강력한 데이터 세척 및 정밀 추출] ---
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

def get_dynamic_bar_tier(occ, date_str):
    try:
        t_date = datetime.strptime(date_str, '%Y-%m-%d')
        month = t_date.month
    except:
        month = 4
        
    holidays_2026 = [
        '2026-02-15', '2026-02-16', '2026-02-17', '2026-02-18', 
        '2026-05-02', '2026-05-03', '2026-05-04', '2026-05-05', 
        '2026-09-23', '2026-09-24', '2026-09-25', '2026-09-26', 
        '2026-12-24', '2026-12-25', '2026-12-31'                
    ]
    
    if date_str in holidays_2026: base_tier = 4 
    elif month == 8: base_tier = 5 
    elif month == 7: base_tier = 6 
    elif month in [4, 5, 6, 9, 10]: base_tier = 7 
    else: base_tier = 8 
        
    if occ >= 95: jump = 7
    elif occ >= 90: jump = 6
    elif occ >= 85: jump = 5
    elif occ >= 75: jump = 4
    elif occ >= 65: jump = 3
    elif occ >= 45: jump = 2
    elif occ >= 25: jump = 1
    else: jump = 0
    
    final_tier = base_tier - jump
    return f"B{max(1, final_tier)}"

# --- [🌟 핵심 패치: 4D 정밀 마스터 타겟 뱅크 (RN, ADR, OCC, REV) - 완벽 교정] ---
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
# 하위 호환성을 위한 예산 자동 매핑
BUDGET_DATA = {m: TARGET_DATA[m]["rev"] for m in range(1, 13)}

BAR_PRICE_MATRIX = {
    "FDB": {"B8":315000, "B7":353000, "B6":396000, "B5":445000, "B4":502000, "B3":567000, "B2":642000, "B1":728000},
    "FDE": {"B8":352000, "B7":390000, "B6":433000, "B5":482000, "B4":539000, "B3":604000, "B2":679000, "B1":765000},
    "HDP": {"B8":280000, "B7":318000, "B6":361000, "B5":410000, "B4":467000, "B3":532000, "B2":607000, "B1":693000},
    "HDT": {"B8":250000, "B7":288000, "B6":331000, "B5":380000, "B4":437000, "B3":502000, "B2":577000, "B1":663000},
    "HDF": {"B8":420000, "B7":458000, "B6":501000, "B5":550000, "B4":607000, "B3":672000, "B2":747000, "B1":833000},
    "PPV": {"B8":1104000, "B7":1154000, "B6":1204000, "B5":1304000, "B4":1404000, "B3":1554000, "B2":1754000, "B1":1954000}
}
TOTAL_ROOM_CAPACITY = 131

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

# --- 3. 오라클 핵심 연산 함수 ---
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

# 🌟 에러 방지: 변수 최상단 초기화
yearly_data_store = {m: {"rev": 0.0, "occ": 0.0, "rn": 0.0, "adr": 0.0} for m in range(1, 13)}
df_full_pms = pd.DataFrame()
real_room_df = None
real_channel_df = None
actual_pace = []
actual_curve = []
avail_analysis = []

# --- 2. 사이드바 구성 및 통합 데이터 로직 ---
st.sidebar.title("🧬 Oracle Intelligence v5.4")
selected_month = st.sidebar.selectbox("🎯 분석 타겟 월 선택", range(1, 13), index=3)
demand_idx = st.sidebar.slider("시장 수요 지수 보정", 0.5, 2.0, 1.3)

st.sidebar.markdown("---")
st.sidebar.subheader("📂 전략 데이터 업로드 센터")

pms_files = st.sidebar.file_uploader("PMS 상세 리스트 (다중)", type=['csv', 'xlsx', 'xls'], accept_multiple_files=True)
sob_files = st.sidebar.file_uploader("영업 현황 SOB (다중)", type=['csv', 'xlsx', 'xls'], accept_multiple_files=True)
avail_files = st.sidebar.file_uploader("사용 가능 객실 현황 (다중)", type=['csv', 'xlsx', 'xls'], accept_multiple_files=True)

# 1. SOB 데이터 처리
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
        st.sidebar.success("✅ SOB 4D 정밀 데이터 연동 완료")
    except Exception as e: st.sidebar.error(f"SOB 처리 실패: {e}")

# 2. 객실 가용(Avail) 데이터 처리
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
                st.sidebar.success("✅ 재고 가속도 센싱 완료")
    except Exception as e: st.sidebar.error(f"재고 분석 에러: {e}")

# 3. 지능형 PMS 데이터 로드 & 분석 엔진
if not pms_files:
    cloud_df = load_from_cloud(selected_month)
    if cloud_df is not None and not cloud_df.empty:
        df_full_pms = cloud_df
        st.sidebar.info(f"☁️ {selected_month}월 클라우드 데이터를 성공적으로 불러왔습니다.")

if pms_files:
    try:
        all_pms = []
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
            df_full_pms = pd.concat(all_pms, ignore_index=True)
    except Exception as e: 
        st.sidebar.error(f"PMS 파일 분석 실패: {e}")

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

        st.sidebar.success("✅ PMS 데이터 세팅 완료")
    except Exception as e: 
        st.sidebar.error(f"PMS 지표 연산 실패: {e}")

# --- 사이드바 클라우드 관리 및 타겟 보드 UI ---
st.sidebar.markdown("---")
st.sidebar.subheader("☁️ 클라우드 데이터 관리")

if not pms_files:
    if df_full_pms.empty:
        st.sidebar.warning("🧐 저장된 데이터가 없습니다.")

if not df_full_pms.empty:
    if st.sidebar.button("🔄 현재 데이터를 클라우드에 고정", use_container_width=True):
        save_to_cloud(selected_month, df_full_pms)

with st.sidebar.expander("📊 2026년 마스터 타겟 보드 (항시 열람)", expanded=True):
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

# --- 4. 메인 대시보드 화면 구성 ---
cur_data = yearly_data_store[selected_month]
current_rev_total = cur_data['rev']
current_occ_pct = cur_data['occ']
current_rn_total = cur_data['rn']
current_adr_actual = cur_data['adr']

# --- [🌟 핵심 패치: 빈손 접속 시 클라우드(PMS) 데이터로 대시보드 자동 복구] ---
if current_rev_total == 0 and not df_full_pms.empty:
    try:
        c_rev_pms = find_column(df_full_pms, ['총금액', '합계', '매출'])
        c_rn_pms = find_column(df_full_pms, ['박수', '숙박일수'])
        c_in_pms = find_column(df_full_pms, ['입실일자', '체크인'])
        
        if c_rev_pms and c_rn_pms:
            # 선택한 월의 데이터만 필터링
            m_df = df_full_pms[df_full_pms[c_in_pms].dt.month == selected_month] if c_in_pms else df_full_pms
            
            if not m_df.empty:
                current_rev_total = m_df[c_rev_pms].sum()
                current_rn_total = m_df[c_rn_pms].sum()
                current_adr_actual = current_rev_total / current_rn_total if current_rn_total > 0 else 0
                
                # 점유율(OCC) 자동 계산
                num_days = calendar.monthrange(2026, selected_month)[1]
                t_cap = TOTAL_ROOM_CAPACITY * num_days
                current_occ_pct = (current_rn_total / t_cap * 100) if t_cap > 0 else 0.0
    except:
        pass
        
st.title("🏛️ AMBER ORACLE v5.4")
st.subheader("Revenue Architect Strategic War Room | 4D Target Mastery")
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
    st.subheader(f"📊 {selected_month}월 예약 가속도 모니터링")
    num_d = calendar.monthrange(2026, selected_month)[1]
    t_dt = pd.date_range(start=f"2026-{selected_month:02d}-01", end=f"2026-{selected_month:02d}-{num_d}")
    o_p, u_b, l_b = get_smart_corridor(tgt_m['rev']/100000000, t_dt, demand_idx)
    c1, c2 = st.columns(2)
    with c1:
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=t_dt, y=l_b, mode='lines', line_width=0, fill='tonexty', fillcolor='rgba(0,209,255,0.1)', name="Safe Zone"))
        fig1.add_trace(go.Scatter(x=t_dt, y=o_p, name="Oracle", line=dict(color="#00D1FF", width=2)))
        if len(actual_pace) > 0: fig1.add_trace(go.Scatter(x=t_dt, y=actual_pace, name="Actual", line=dict(color="#FF4B4B", width=4)))
        fig1.update_layout(template="plotly_dark", height=400); st.plotly_chart(fig1, use_container_width=True)
    with c2:
        _, t_c = get_booking_curve(tgt_m['rev']/100000000, 90, 1.0)
        fig2 = go.Figure(); fig2.add_trace(go.Scatter(x=np.arange(-90,1), y=t_c, name="Standard", line=dict(color='gray', dash='dash')))
        if len(actual_curve) > 0: fig2.add_trace(go.Scatter(x=np.arange(-90,1), y=actual_curve, name="Actual", line=dict(color='#FF4B4B', width=4)))
        fig2.update_layout(template="plotly_dark", height=400, xaxis_title="Days Before Arrival"); st.plotly_chart(fig2, use_container_width=True)

with tabs[1]:
    st.subheader("🏢 타입별 전체/객실 ADR 정밀 감사")
    if real_room_df is not None: 
        styled_room_df = real_room_df.style.format({
            '전체 매출(Total)': '{:,.0f}', '객실 매출(Room)': '{:,.0f}', 
            '판매 객실수(RN)': '{:,.0f}', '전체 ADR': '{:,.0f}', '객실 ADR': '{:,.0f}'
        })
        st.dataframe(styled_room_df, use_container_width=True, height=350)
    else: st.info("PMS 파일이 필요합니다.")

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
with tabs[6]: st.subheader("🛰️ 경쟁사 감시"); st.table(pd.DataFrame({'경쟁사':['A','B','C','엠버'], '상태':['임박','완판','임박','⚠️ 과잉']}))

with tabs[7]:
    st.markdown("---")
    st.subheader("📊 전략 보고서 정식 출력")
    if st.button("📄 회장님 보고용 종합 리포트 생성 (PDF)"):
        safe_adj_adr = adj_adr_pct if 'adj_adr_pct' in locals() else 0
        safe_gain = int(ar_net - act_net) if ('ar_net' in locals() and 'act_net' in locals()) else 0
        
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
            st.error(f"❌ PDF 생성 실패 (라이브러리 확인 필요): {e}")
            
    kst_now = datetime.now(timezone(timedelta(hours=9)))
    today_month = kst_now.month
    today_day = kst_now.day
    
    tgt_m = TARGET_DATA[selected_month]
    is_past = selected_month < today_month
    V_C = 50000 
    O_C = 0.0    
    
    if is_past:
        st.header(f"🏟️ {selected_month}월 전략 복기: Performance Review")
        st.info(f"✅ {selected_month}월은 영업이 종료된 달입니다. 슬라이더를 조절해 최적의 전략 스윗스팟을 찾아보세요.")
        
        st.markdown("### 🛠️ 아키텍트 전략 튜닝 (What-if Simulation)")
        c_s1, c_s2 = st.columns(2)
        with c_s1:
            adj_adr_pct = st.slider("📈 가상 ADR 상향폭 (%)", 0, 50, 15, key="past_adr_final")
        with c_s2:
            adj_churn_pct = st.slider("📉 예상 예약 이탈률 (%)", 0, 50, 10, key="past_churn_final")
        
        act_gross = current_rev_total
        act_rn = current_rn_total
        act_adr = current_adr_actual
        act_cost = act_rn * V_C
        act_net = act_gross - act_cost
        
        ar_adr = act_adr * (1 + adj_adr_pct / 100)
        ar_rn = act_rn * (1 - adj_churn_pct / 100)
        ar_gross = ar_adr * ar_rn
        ar_cost = ar_rn * V_C
        ar_net = ar_gross - ar_cost

        st.markdown("---")
        cl, cr = st.columns(2)
        with cl:
            st.subheader("👨‍💼 실제 운영 결과 (GM 방식)")
            st.markdown(f"**상태:** 기존 요금 정책 유지. 목표 대비 {int(act_gross/tgt_m['rev']*100)}% 달성.")
            st.metric("최종 총매출 (Gross)", f"₩{int(act_gross):,}")
            st.write(f"🏨 실적: {int(act_rn):,} RN | ADR ₩{int(act_adr):,}")
            st.error(f"💰 최종 순수익 (Net): ₩{int(act_net):,}")
            
        with cr:
            st.subheader("🏛️ 아키텍트 가상 복기 (전략 적용 시)")
            st.markdown(f"**전략:** 단가 {adj_adr_pct}% 상향 방어 시뮬레이션 결과")
            st.metric("가상 총매출 (Gross)", f"₩{int(ar_gross):,}", 
                      delta=f"{int(ar_gross - act_gross):+,} 원", delta_color="normal")
            st.write(f"🏨 예상: {int(ar_rn):,.0f} RN | ADR ₩{int(ar_adr):,}")
            st.success(f"💰 가상 순수익 (Net): ₩{int(ar_net):,}")
            
        st.markdown("---")
        gain = ar_net - act_net
        st.info(f"💡 **분석 결론:** 단가를 {adj_adr_pct}% 조절했을 때, 순수익은 실제보다 **₩{int(gain):,}원** 변화합니다.")
        
        comp_df = pd.DataFrame({
            "전략": ["Actual (GM)", "Actual (GM)", "What-if (Architect)", "What-if (Architect)"],
            "항목": ["1. 총매출(Gross)", "2. 순수익(Net)", "1. 총매출(Gross)", "2. 순수익(Net)"],
            "금액": [act_gross, act_net, ar_gross, ar_net]
        })
        fig_comp = px.bar(comp_df, x="항목", y="금액", color="전략", barmode="group", template="plotly_dark", 
                          color_discrete_sequence=['#9e2a2b', '#00D1FF'], title=f"{selected_month}월 수익 구조 정밀 분석")
        fig_comp.update_layout(yaxis_tickformat=',.0f')
        st.plotly_chart(fig_comp, use_container_width=True)

    else:
        st.header(f"⚔️ {selected_month}월 전략 대조: Target vs Actual vs Forecast")
        
        t_cap = TOTAL_ROOM_CAPACITY * calendar.monthrange(2026, selected_month)[1]
        rem_rn = max(0, t_cap - current_rn_total)
        proj_rn = int(rem_rn * 0.4) 
        is_over = current_rev_total >= tgt_m['rev']
        
        if is_over:
            st.success(f"🎉 **[Over Budget!]** 목표 초과액: ₩{int(current_rev_total - tgt_m['rev']):,}")
        else:
            st.warning(f"⚠️ **[목표 미달]** 목표까지 부족액: ₩{int(tgt_m['rev'] - current_rev_total):,}")
            
        st.markdown(f"현재 총 {t_cap:,}실 중 **{int(current_rn_total):,}실** 판매 완료. 월말 예상 추가 판매: **{proj_rn}실**")
        
        if proj_rn <= 0:
            st.info("잔여 객실이 없습니다.")
        else:
            gm_adr = max(tgt_m['adr'], BAR_PRICE_MATRIX["FDB"]["B7"])
            gm_add_rn = proj_rn
            gm_fcst_rn = current_rn_total + gm_add_rn
            gm_fcst_rev = current_rev_total + (gm_add_rn * gm_adr)
            gm_fcst_adr = gm_fcst_rev / gm_fcst_rn if gm_fcst_rn > 0 else 0
            gm_net = gm_fcst_rev - (gm_fcst_rn * V_C)
            
            ar_adr = BAR_PRICE_MATRIX["FDB"]["B5"]
            ar_add_rn = int(proj_rn * 0.7) 
            ar_fcst_rn = current_rn_total + ar_add_rn
            ar_fcst_rev = current_rev_total + (ar_add_rn * ar_adr)
            ar_fcst_adr = ar_fcst_rev / ar_fcst_rn if ar_fcst_rn > 0 else 0
            ar_net = ar_fcst_rev - (ar_fcst_rn * V_C)

            cl, cr = st.columns(2)
            with cl:
                st.subheader("👨‍💼 총지배인(GM) 방관 모드")
                st.metric("월말 예상 Gross", f"₩{int(gm_fcst_rev):,}")
                st.metric("월말 예상 RN", f"{int(gm_fcst_rn):,} RN")
                st.error(f"💰 예상 순수익: ₩{int(gm_net):,}")
            with cr:
                st.subheader("🏛️ 아키텍트 가치 방어 모드")
                st.metric("월말 예상 Gross", f"₩{int(ar_fcst_rev):,}")
                st.metric("월말 예상 RN", f"{int(ar_fcst_rn):,} RN")
                st.success(f"💰 예상 순수익: ₩{int(ar_net):,}")

            comp_df_f = pd.DataFrame({
                "전략": ["GM Mode", "GM Mode", "Architect Mode", "Architect Mode"],
                "항목": ["1. 총매출(Gross)", "2. 순수익(Net)", "1. 총매출(Gross)", "2. 순수익(Net)"],
                "금액": [gm_fcst_rev, gm_net, ar_fcst_rev, ar_net]
            })
            fig_comp_f = px.bar(comp_df_f, x="항목", y="금액", color="전략", barmode="group", template="plotly_dark", 
                                color_discrete_sequence=['#9e2a2b', '#00D1FF'], title="최종 예상 수익 구조 시뮬레이션")
            st.plotly_chart(fig_comp_f, use_container_width=True)

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
    else: st.info("PMS 파일을 업로드하세요.")

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
        st.warning("🧐 분석을 위해 서로 다른 날짜의 '사용 가능 객실' 파일을 2개 이상 업로드하세요.")

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

st.caption("본 분석 시스템은 전수현 팀장의 시즌 동적 지능 로직 및 엠버퓨어힐 공식 마스터 타겟을 근거로 구동됩니다.")
