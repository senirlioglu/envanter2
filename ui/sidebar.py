# ==================== SIDEBAR ====================
# Sidebar filtreleri

import streamlit as st
import pandas as pd
from database import get_sm_summary_from_view


def render_sidebar(user: str):
    """Sidebar render"""
    with st.sidebar:
        st.markdown(f"👤 **{user.upper()}**")
        
        if st.button("🚪 Çıkış", key="logout_btn", use_container_width=True):
            st.session_state.user = None
            st.rerun()
        
        st.divider()


def get_filter_values():
    """Filtre değerlerini session_state'ten al"""
    return {
        'satis_muduru': st.session_state.get('selected_sm', None),
        'donemler': st.session_state.get('selected_donemler', []),
        'magaza_kodu': st.session_state.get('selected_magaza', None),
    }


def render_period_filter(available_periods: list):
    """Dönem filtresi"""
    return st.multiselect(
        "📅 Dönem Seçin",
        options=available_periods,
        default=available_periods[:1] if available_periods else [],
        key="period_filter"
    )


def render_sm_filter(available_sms: list):
    """Satış Müdürü filtresi"""
    return st.selectbox(
        "👔 Satış Müdürü",
        options=["Tümü"] + available_sms,
        key="sm_filter"
    )


def render_store_filter(available_stores: dict):
    """Mağaza filtresi"""
    store_options = [""] + [f"{k} - {v}" for k, v in available_stores.items()]
    selected = st.selectbox(
        "🏪 Mağaza Seçin",
        options=store_options,
        key="store_filter"
    )
    
    if selected and " - " in selected:
        return selected.split(" - ")[0]
    return None


def render_date_filter():
    """Tarih aralığı filtresi"""
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Başlangıç", key="start_date")
    with col2:
        end_date = st.date_input("Bitiş", key="end_date")
    return start_date, end_date
