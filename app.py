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
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

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

