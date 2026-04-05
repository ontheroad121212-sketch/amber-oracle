import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from datetime import datetime, timedelta, timezone # timezone 추가!
import calendar
import re
import os
from datetime import datetime, timedelta, timezone
import base64
from io import BytesIO
# PDF 생성을 위해 weasyprint가 필요합니다. 
# 로컬 개발 환경(VS Code)이라면 pip install weasyprint 하셔야 합니다.
from fpdf import FPDF

def export_comprehensive_report(data):
    # PDF 생성 엔진 설정 (기본 폰트 사용)
    pdf = FPDF()
    pdf.add_page()
    
    # 1. 제목 (엠버 퓨어힐 헤더)
    pdf.set_fill_color(26, 42, 68) # 다크 네이비
    pdf.rect(0, 0, 210, 40, 'F')
    
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("helvetica", "B", 24)
    pdf.cell(0, 20, "AMBER PURE HILL", ln=True, align='C')
    pdf.set_font("helvetica", "I", 12)
    pdf.cell(0, 10, "Strategic Performance & Yielding Report", ln=True, align='C')
    
    pdf.ln(20)
    
    # 2. 본문 (데이터 채우기)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, f"Analysis: {selected_month} Month Review", ln=True)
    pdf.set_font("helvetica", "", 10)
    pdf.cell(0, 10, f"Date: {data['date']} | Prepared by: Revenue Architect", ln=True)
    
    pdf.ln(10)
    
    # 3. 핵심 실적 테이블 (회장님 보고용)
    pdf.set_font("helvetica", "B", 12)
    pdf.set_fill_color(248, 245, 240)
    pdf.cell(60, 10, "KPI Item", 1, 0, 'C', True)
    pdf.cell(60, 10, "Target", 1, 0, 'C', True)
    pdf.cell(60, 10, "Actual", 1, 1, 'C', True)
    
    pdf.set_font("helvetica", "", 12)
    pdf.cell(60, 10, "Revenue", 1)
    pdf.cell(60, 10, f"{data['tgt_rev']:,.0f}", 1)
    pdf.cell(60, 10, f"{data['act_rev']:,.0f}", 1, 1)
    
    pdf.cell(60, 10, "Achievement", 1)
    pdf.cell(60, 10, "100%", 1)
    pdf.cell(60, 10, f"{data['rev_pct']:.1f}%", 1, 1)
    
    pdf.ln(15)
    
    # 4. 아키텍트 전략 제언
    pdf.set_font("helvetica", "B", 14)
    pdf.set_text_color(166, 138, 86) # 골드색
    pdf.cell(0, 10, "Strategic Insight (Architect's Note)", ln=True)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("helvetica", "", 11)
    note = (f"By implementing the Architect Strategy (ADR +{data['adj_adr']}%), "
            f"we could have generated an additional Net Profit of KRW {int(data['gain']):,}. "
            "This proves that high-tier yielding is more efficient than volume-driven sales.")
    pdf.multi_cell(0, 8, note)
    
    # PDF를 메모리에 생성하여 반환
    return pdf.output()

# --- [데이터 저장소 설정] ---
DB_PATH = "data_vault" # 데이터가 저장될 폴더 이름
if not os.path.exists(DB_PATH):
    os.makedirs(DB_PATH)

def get_snapshot_list():
    """저장된 스냅샷 날짜 목록 가져오기"""
    files = [f.replace(".parquet", "") for f in os.listdir(DB_PATH) if f.endswith(".parquet")]
    return sorted(files, reverse=True)

# 1. 페이지 설정 (최상단 고정 필수)
st.set_page_config(
    page_title="Amber Oracle | Strategic War Room",
    page_icon="🏛️",
    layout="wide"
)

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

# --- [보고서 엔진: PDF 생성 부품] ---
# 주의: 이 기능을 웹(Streamlit Cloud)에서 쓰려면 requirements.txt에 weasyprint를 추가해야 합니다.
try:
    from weasyprint import HTML
except:
    pass

def export_comprehensive_report(data):
    # 이 함수는 수현 님이 보신 구글 문서와 유사한 레이아웃의 HTML을 생성하여 
    # weasyprint를 통해 PDF 바이너리로 변환해줍니다.
    html_template = f"""
    <div style="font-family: 'Malgun Gothic'; padding: 40px;">
        <h1 style="color: #1a2a44; text-align: center; border-bottom: 2px solid #a68a56;">AMBER PURE HILL STRATEGY REPORT</h1>
        <p style="text-align: right;">보고일자: {data['date']}</p>
        <h2>1. 3월 실적 요약</h2>
        <p>총매출: ₩{int(data['act_rev']):,} (목표대비 {data['rev_pct']:.1f}%)</p>
        <h2>2. 아키텍트 제언</h2>
        <p>단가 상향 전략 시 순수익 <b>₩{int(data['gain']):,}</b> 추가 확보가 가능했음이 입증됨.</p>
        <div style="background: #f8f5f0; padding: 20px; border-left: 5px solid #a68a56;">
            <b>핵심 전략:</b> 볼륨 중심에서 가치(ADR) 중심으로의 체질 개선 필요.
        </div>
    </div>
    """
    # PDF 생성 로직 (생략 없이 리턴)
    return HTML(string=html_template).write_pdf()

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

# --- 2. 사이드바 구성 및 통합 데이터 로직 ---

st.sidebar.title("🧬 Oracle Intelligence v5.4")
selected_month = st.sidebar.selectbox("🎯 분석 타겟 월 선택", range(1, 13), index=3)
demand_idx = st.sidebar.slider("시장 수요 지수 보정", 0.5, 2.0, 1.3)

# 🌟 핵심 패치 2: 사이드바 마스터 타겟 보드 (어디서든 항시 열람 가능)
st.sidebar.markdown("---")
st.sidebar.subheader("📅 분석 스냅샷 선택")
saved_snapshots = get_snapshot_list()

if saved_snapshots:
    selected_snap = st.sidebar.selectbox("불러올 작업 일자", ["현재 업로드 데이터"] + saved_snapshots)
    if selected_snap != "현재 업로드 데이터":
        # 저장된 파일 읽어오기
        df_full_pms = pd.read_parquet(f"{DB_PATH}/{selected_snap}.parquet")
        st.sidebar.info(f"📁 {selected_snap} 데이터를 분석 중입니다.")
        # 여기서 actual_pace 등을 다시 계산하는 로직이 작동하게 함
else:
    st.sidebar.warning("🧐 저장된 스냅샷이 없습니다. 파일을 먼저 업로드하세요.")

with st.sidebar.expander("📊 2026년 마스터 타겟 보드 (항시 열람)", expanded=True):
    tgt_df = pd.DataFrame.from_dict(TARGET_DATA, orient='index')
    tgt_df.index.name = '월'
    tgt_df.rename(columns={'rn': '목표 RN', 'adr': '목표 ADR', 'occ': '목표 OCC(%)', 'rev': '목표 매출'}, inplace=True)
    # 총 합계 데이터
    tgt_df.loc['합계'] = [27117, 375346, 55.7, 10179268802]
    
    styled_tgt = tgt_df.style.format({
        '목표 RN': '{:,.0f}',
        '목표 ADR': '{:,.0f}',
        '목표 OCC(%)': '{:,.1f}',
        '목표 매출': '{:,.0f}'
    })
    st.dataframe(styled_tgt, use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.subheader("📂 전략 데이터 업로드 센터")

pms_files = st.sidebar.file_uploader("PMS 상세 리스트 (다중)", type=['csv', 'xlsx', 'xls'], accept_multiple_files=True)
sob_files = st.sidebar.file_uploader("영업 현황 SOB (다중)", type=['csv', 'xlsx', 'xls'], accept_multiple_files=True)
avail_files = st.sidebar.file_uploader("사용 가능 객실 현황 (다중)", type=['csv', 'xlsx', 'xls'], accept_multiple_files=True)

# 상태 변수 (RN, ADR까지 확장)
yearly_data_store = {m: {"rev": 0.0, "occ": 0.0, "rn": 0.0, "adr": 0.0} for m in range(1, 13)}
real_room_df = None; real_channel_df = None; actual_pace = []; actual_curve = []
df_full_pms = pd.DataFrame(); avail_analysis = []

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

cur_data = yearly_data_store[selected_month]
current_rev_total = cur_data['rev']
current_occ_pct = cur_data['occ']
current_rn_total = cur_data['rn']
current_adr_actual = cur_data['adr']

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

                # --- [스냅샷 저장 기능 추가] ---
            st.sidebar.markdown("---")
            save_name = st.sidebar.text_input("💾 스냅샷 명칭", value=datetime.now().strftime("%Y-%m-%d_%H%M"))
            if st.sidebar.button("📦 현재 데이터를 클라우드(로컬)에 저장"):
                df_full_pms.to_parquet(f"{DB_PATH}/{save_name}.parquet")
                st.sidebar.success(f"✅ {save_name} 버전 저장 완료!")
                st.rerun() # 목록 갱신을 위해 재실행

            st.sidebar.success("✅ PMS 데이터 분석 완료")
    except Exception as e: st.sidebar.error(f"PMS 분석 실패: {e}")

# --- 4. 메인 대시보드 화면 구성 ---

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
    
    # 1. 한국 시간 기준 오늘 날짜 계산
    kst_now = datetime.now(timezone(timedelta(hours=9)))
    today_month = kst_now.month
    today_day = kst_now.day
    
    num_days = calendar.monthrange(2026, selected_month)[1]
    dates = pd.date_range(start=f"2026-{selected_month:02d}-01", periods=num_days)
    
    # 2. 목표선 데이터 생성 (억 단위 환산: tgt_m['rev'] / 100,000,000)
    # get_smart_corridor 함수를 이용해 날짜별 목표 누적치 산출
    target_goal_unit = tgt_m['rev'] / 100000000
    o_p, _, _ = get_smart_corridor(target_goal_unit, dates, demand_idx)

    # 3. [핵심 수정] 실제 데이터 기반 경과일 계산
    # actual_pace의 길이를 통해 실제 데이터가 며칠치인지 판단합니다.
    data_count = len(actual_pace) 
    current_cum_rev = actual_pace[-1] if data_count > 0 else 0.0
    
    # 분석 시점의 '실제' 날짜 (오늘 날짜와 데이터 일수 중 작은 것을 선택)
    # 3월 데이터를 볼 때는 31일이 경과일이 되어야 하고, 4월 데이터를 볼 때는 오늘(5일)이 경과일이 됨
    if selected_month < kst_now.month:
        effective_days = num_days # 지난 달은 꽉 찬 데이터로 간주
    elif selected_month == kst_now.month:
        effective_days = max(data_count, kst_now.day) # 이번 달은 데이터 일수와 오늘 날짜 중 큰 값
    else:
        effective_days = data_count # 미래 달은 데이터 들어온 만큼만
    
    # 4. 마감 예상(Forecast) 로직 재설계
    if effective_days > 0 and current_cum_rev > 0:
        if effective_days >= num_days:
            # 이미 한 달이 다 찼다면 예측치는 현재 실적과 동일
            forecast_final = current_cum_rev
        else:
            # 현재 일평균 Pace 계산 (현재 매출 / 실제 경과일)
            avg_pace = current_cum_rev / effective_days
            # 남은 기간 예측 (현재 매출 + (일평균 * 남은 일수))
            forecast_final = current_cum_rev + (avg_pace * (num_days - effective_days))
    else:
        forecast_final = current_cum_rev

    # 예측 점선 생성
    forecast_line = [None] * num_days
    if 0 < effective_days < num_days:
        forecast_line[effective_days-1] = current_cum_rev
        step = (forecast_final - current_cum_rev) / (num_days - effective_days)
        for i in range(effective_days, num_days):
            forecast_line[i] = current_cum_rev + (step * (i - effective_days + 1))
    elif effective_days >= num_days:
        forecast_line = [None] * num_days # 한 달 다 찼으면 예측선 불필요

    # 5. 차트 시각화
    fig_fcst = go.Figure()
    fig_fcst.add_trace(go.Scatter(x=dates, y=o_p, name="Target", line=dict(color="rgba(0,209,255,0.4)", dash="dash")))
    if data_count > 0:
        fig_fcst.add_trace(go.Scatter(x=dates[:data_count], y=actual_pace, name="Actual (OTB)", line=dict(color="#FF4B4B", width=4)))
    if any(v is not None for v in forecast_line):
        fig_fcst.add_trace(go.Scatter(x=dates, y=forecast_line, name="Forecast", line=dict(color="#FFD700", width=2, dash="dot")))
    
    fig_fcst.update_layout(template="plotly_dark", height=450, title=f"{selected_month}월 매출 마감 예측 (단위: 억원)", yaxis_title="누적 매출 (억)")
    st.plotly_chart(fig_fcst, use_container_width=True)
    
    # 6. 하단 메트릭스
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
    # 함수에 전달할 데이터를 '안전한 공통 변수'로 교체합니다.
    report_payload = {
        'date': kst_now.strftime('%Y-%m-%d'),
        'act_rev': current_rev_total,  # act_gross 대신 current_rev_total 사용
        'rev_pct': (current_rev_total / tgt_m['rev'] * 100) if tgt_m['rev'] > 0 else 0,
        'tgt_rev': tgt_m['rev'],
        'act_rn': current_rn_total,    # act_rn 대신 current_rn_total 사용
        'tgt_rn': tgt_m['rn'],
        'rn_pct': (current_rn_total / tgt_m['rn'] * 100) if tgt_m['rn'] > 0 else 0,
        'act_adr': current_adr_actual, # act_adr 대신 current_adr_actual 사용
        'tgt_adr': tgt_m['adr'],
        'adr_diff': int(current_adr_actual - tgt_m['adr']),
        'adj_adr': adj_adr_pct if 'adj_adr_pct' in locals() else 0, # 변수가 없을 경우 대비
        'gain': int(ar_net - act_net) if ('ar_net' in locals() and 'act_net' in locals()) else 0
    }
        
        # PDF 생성 함수 호출
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
            
    # --- [1. 기초 환경 설정 및 데이터 재선언] ---
    kst_now = datetime.now(timezone(timedelta(hours=9)))
    today_month = kst_now.month
    today_day = kst_now.day
    
    tgt_m = TARGET_DATA[selected_month]
    is_past = selected_month < today_month
    V_C = 50000 
    O_C = 0.0    
    
    if is_past:
        # --- [CASE A: 과거 데이터 - 아키텍트 인터랙티브 실적 복기 모드] ---
        st.header(f"🏟️ {selected_month}월 전략 복기: Performance Review")
        st.info(f"✅ {selected_month}월은 영업이 종료된 달입니다. 슬라이더를 조절해 최적의 전략 스윗스팟을 찾아보세요.")
        
        # 🌟 수현 님을 위한 인터랙티브 시뮬레이션 바
        st.markdown("### 🛠️ 아키텍트 전략 튜닝 (What-if Simulation)")
        c_s1, c_s2 = st.columns(2)
        with c_s1:
            # 3월 25만원 ADR을 맞췄다면? 같은 고민을 여기서 %로 조절
            adj_adr_pct = st.slider("📈 가상 ADR 상향폭 (%)", 0, 50, 15, key="past_adr_final")
        with c_s2:
            adj_churn_pct = st.slider("📉 예상 예약 이탈률 (%)", 0, 50, 10, key="past_churn_final")
        
        # 1. 실제 결과 (GM 방식)
        act_gross = current_rev_total
        act_rn = current_rn_total
        act_adr = current_adr_actual
        act_cost = act_rn * V_C
        act_net = act_gross - act_cost
        
        # 2. 아키텍트 가상 복기 (슬라이더 값 반영)
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
        # --- [CASE B: 현재/미래 데이터 - 전략 예측 모드] ---
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
            # GM 시나리오
            gm_adr = max(tgt_m['adr'], BAR_PRICE_MATRIX["FDB"]["B7"])
            gm_add_rn = proj_rn
            gm_fcst_rn = current_rn_total + gm_add_rn
            gm_fcst_rev = current_rev_total + (gm_add_rn * gm_adr)
            gm_fcst_adr = gm_fcst_rev / gm_fcst_rn if gm_fcst_rn > 0 else 0
            gm_net = gm_fcst_rev - (gm_fcst_rn * V_C)
            
            # Architect 시나리오
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

            # 미래 예측 차트
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
