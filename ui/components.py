# ==================== UI COMPONENTS ====================
# Ortak UI bileşenleri

import streamlit as st
import pandas as pd


def render_metrics_row(metrics: list, cols_count: int = 4):
    """Metrik kartları satırı"""
    cols = st.columns(cols_count)
    for i, (label, value, delta, color) in enumerate(metrics):
        with cols[i % cols_count]:
            st.metric(label, value, delta)


def render_risk_distribution(kritik: int, riskli: int, dikkat: int, temiz: int):
    """Risk dağılımı gösterimi"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div style="background: #FF4444; color: white; padding: 15px; border-radius: 10px; text-align: center;">
            <h3 style="margin: 0;">{kritik}</h3>
            <small>🔴 KRİTİK</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="background: #FF8800; color: white; padding: 15px; border-radius: 10px; text-align: center;">
            <h3 style="margin: 0;">{riskli}</h3>
            <small>🟠 RİSKLİ</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div style="background: #FFCC00; color: black; padding: 15px; border-radius: 10px; text-align: center;">
            <h3 style="margin: 0;">{dikkat}</h3>
            <small>🟡 DİKKAT</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div style="background: #00CC66; color: white; padding: 15px; border-radius: 10px; text-align: center;">
            <h3 style="margin: 0;">{temiz}</h3>
            <small>🟢 TEMİZ</small>
        </div>
        """, unsafe_allow_html=True)


def format_dataframe_for_display(df: pd.DataFrame, format_rules: dict = None) -> pd.DataFrame:
    """DataFrame'i görüntüleme için formatla"""
    if df is None or df.empty:
        return pd.DataFrame()
    
    display_df = df.copy()
    
    if format_rules is None:
        format_rules = {
            'currency': ['Satış', 'Fark', 'Fire', 'Toplam Açık', 'Tutar', 'Fark Tutarı', 'Fire Tutarı'],
            'percent': ['Fark %', 'Fire %', 'Toplam %'],
            'integer': ['İç Hırs.', 'Kronik', 'Sigara', 'Kr.Açık', 'Kr.Fire', 'Risk Puan']
        }
    
    for col in display_df.columns:
        if col in format_rules.get('currency', []):
            display_df[col] = display_df[col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "0")
        elif col in format_rules.get('percent', []):
            display_df[col] = display_df[col].apply(lambda x: f"%{x:.1f}" if pd.notna(x) else "%0.0")
        elif col in format_rules.get('integer', []):
            display_df[col] = display_df[col].apply(lambda x: f"{int(x)}" if pd.notna(x) else "0")
    
    return display_df


def render_download_button(data, filename: str, label: str = "📥 Excel İndir"):
    """Excel indirme butonu"""
    st.download_button(
        label=label,
        data=data,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def render_info_card(title: str, value, subtitle: str = "", color: str = "#1F4E79"):
    """Bilgi kartı"""
    st.markdown(f"""
    <div style="background: {color}; color: white; padding: 20px; border-radius: 10px; margin: 5px 0;">
        <h4 style="margin: 0; font-size: 0.9em;">{title}</h4>
        <h2 style="margin: 5px 0;">{value}</h2>
        <small>{subtitle}</small>
    </div>
    """, unsafe_allow_html=True)


def render_warning_box(message: str):
    """Uyarı kutusu"""
    st.warning(message)


def render_success_box(message: str):
    """Başarı kutusu"""
    st.success(message)


def render_error_box(message: str):
    """Hata kutusu"""
    st.error(message)
