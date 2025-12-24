# ==================== ENVANTER RİSK ANALİZİ ====================
# Ana Uygulama - Modüler Yapı
# v2.1 - Fixed

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from io import BytesIO

# Sayfa ayarları
st.set_page_config(
    page_title="Envanter Risk Analizi",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================== MODÜL IMPORTLARI ====================
from config import RISK_CONFIG, load_json_data, SM_BS_MAGAZA, SEGMENT_URUN
from auth import login, logout, get_current_user

from database import (
    supabase,
    save_to_supabase,
    get_available_stores_from_supabase,
    get_single_store_data,
    get_data_from_supabase,
    get_sm_summary_from_view
)

from analysis import (
    analyze_inventory,
    is_balanced,
    detect_internal_theft,
    detect_chronic_products,
    detect_chronic_fire,
    detect_cigarette_shortage,
    find_product_families,
    detect_fire_manipulation,
    detect_external_theft,
    check_kasa_activity_products,
    load_kasa_activity_codes,
    analyze_region,
    generate_executive_summary,
    calculate_store_risk,
    create_top_20_risky
)

from analysis.region_analysis import aggregate_by_group

from camera import (
    get_iptal_verisi_from_sheets,
    get_iptal_timestamps_for_magaza,
    enrich_internal_theft_with_camera
)

from excel import (
    create_excel_report,
    create_region_excel_report,
    create_gm_excel_report,
    auto_adjust_column_width
)

from utils import filter_data

# Sürekli envanter modülü
try:
    from surekli_envanter_module import (
        detect_envanter_type,
        prepare_surekli_data,
        analyze_surekli_envanter,
        create_surekli_excel_report,
        detect_ic_hirsizlik_surekli,
        enrich_with_camera_surekli,
        create_ic_hirsizlik_excel_surekli
    )
    SUREKLI_MODULE_LOADED = True
except ImportError:
    SUREKLI_MODULE_LOADED = False

# ==================== CSS ====================
st.markdown("""
<style>
    .risk-kritik { background-color: #ff4444; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; }
    .risk-riskli { background-color: #ff8800; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; }
    .risk-dikkat { background-color: #ffcc00; color: black; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; }
    .risk-temiz { background-color: #00cc66; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; }
    
    @media (max-width: 768px) {
        .stMetric { font-size: 0.8rem; }
        .stDataFrame { font-size: 0.7rem; }
        div[data-testid="column"] { padding: 0.25rem !important; }
    }
    .stDataFrame { overflow-x: auto; }
</style>
""", unsafe_allow_html=True)

# ==================== LOGIN KONTROLÜ ====================
if not login():
    st.stop()

# ==================== ANA UYGULAMA ====================
col_title, col_user = st.columns([4, 1])
with col_title:
    st.title("🔍 Envanter Risk Analizi")
with col_user:
    st.markdown(f"👤 **{st.session_state.user.upper()}**")
    if st.button("🚪 Çıkış", key="logout_btn"):
        if "df_all" in st.session_state:
            del st.session_state.df_all
        logout()

# ==================== CACHE FONKSİYONLARI ====================
@st.cache_data(ttl=300)
def get_available_periods_cached():
    """Dönemleri al"""
    try:
        try:
            result = supabase.table('v_distinct_donem').select('envanter_donemi').execute()
        except Exception:
            result = supabase.table('envanter_veri').select('envanter_donemi').limit(1000).execute()
        
        if result.data:
            periods = list(set([r['envanter_donemi'] for r in result.data if r.get('envanter_donemi')]))
            return sorted(periods, reverse=True)
    except Exception:
        pass
    return []

@st.cache_data(ttl=300)
def get_available_sms_cached():
    """SM'leri al"""
    try:
        try:
            result = supabase.table('v_distinct_sm').select('satis_muduru').execute()
        except Exception:
            result = supabase.table('envanter_veri').select('satis_muduru').limit(1000).execute()
        
        if result.data:
            sms = list(set([r['satis_muduru'] for r in result.data if r.get('satis_muduru')]))
            return sorted(sms)
    except Exception:
        pass
    return []

def load_all_data_once():
    """Tüm veriyi bir kez yükle"""
    if "df_all" not in st.session_state or st.session_state.df_all is None:
        with st.spinner("📊 Veriler yükleniyor..."):
            df_raw = get_data_from_supabase(satis_muduru=None, donemler=None)
            
            if len(df_raw) > 0:
                df_analyzed = analyze_inventory(df_raw)
                st.session_state.df_all = df_analyzed
            else:
                st.session_state.df_all = pd.DataFrame()
    
    return st.session_state.df_all

# ==================== DOSYA YÜKLEME ====================
uploaded_file = st.file_uploader("📁 Excel dosyası yükleyin (Parçalı veya Sürekli)", type=['xlsx', 'xls'])

if uploaded_file is not None:
    try:
        xl = pd.ExcelFile(uploaded_file)
        best_sheet = None
        max_cols = 0
        for sheet in xl.sheet_names:
            temp_df = pd.read_excel(uploaded_file, sheet_name=sheet, nrows=5)
            if len(temp_df.columns) > max_cols:
                max_cols = len(temp_df.columns)
                best_sheet = sheet
        
        df_uploaded = pd.read_excel(uploaded_file, sheet_name=best_sheet)
        
        if SUREKLI_MODULE_LOADED:
            detected_type = detect_envanter_type(df_uploaded)
        else:
            detected_type = 'parcali'
        
        st.session_state['uploaded_df'] = df_uploaded
        st.session_state['uploaded_type'] = detected_type
        
        if detected_type == 'surekli':
            st.success(f"✅ **Sürekli Envanter** algılandı: {len(df_uploaded)} satır")
        else:
            st.success(f"✅ **Parçalı Envanter** algılandı: {len(df_uploaded)} satır")
            
    except Exception as e:
        st.error(f"Dosya okuma hatası: {str(e)}")

if uploaded_file is None and 'uploaded_df' in st.session_state:
    del st.session_state['uploaded_df']
    if 'uploaded_type' in st.session_state:
        del st.session_state['uploaded_type']

st.markdown("---")

# ==================== SEKMELER ====================
current_user = st.session_state.user
is_gm = current_user == "ziya"

if is_gm:
    ust_sekme = st.radio("📊 Görünüm", ["👤 SM Özet", "👥 BS Özet", "🌐 GM Özet"], horizontal=True)
else:
    ust_sekme = st.radio("📊 Görünüm", ["👤 SM Özet", "👥 BS Özet"], horizontal=True)

col_spacer, col_refresh = st.columns([10, 1])
with col_refresh:
    if st.button("🔄", help="Verileri yenile"):
        st.cache_data.clear()
        st.rerun()

alt_sekme = st.radio("📦 Envanter Tipi", ["📦 Parçalı", "🔄 Sürekli"], horizontal=True)

st.markdown("---")

# Analysis mode belirleme
if alt_sekme == "📦 Parçalı":
    if ust_sekme == "👤 SM Özet":
        analysis_mode = "SM_OZET"
    elif ust_sekme == "👥 BS Özet":
        analysis_mode = "BS_OZET"
    elif ust_sekme == "🌐 GM Özet":
        analysis_mode = "GM_OZET"
    else:
        analysis_mode = "PARCALI"
else:
    analysis_mode = "SUREKLI"
    if 'uploaded_df' in st.session_state:
        if st.session_state.get('uploaded_type') == 'surekli':
            st.session_state['df_surekli'] = st.session_state['uploaded_df']
        else:
            st.warning("⚠️ Yüklenen dosya parçalı envanter.")

# ==================== KASA AKTİVİTESİ KODLARI ====================
KASA_KODLARI = load_kasa_activity_codes()

# ==================== ANALİZ MODLARI ====================

if analysis_mode in ["SM_OZET", "BS_OZET", "GM_OZET"]:
    # ===== ÖZET MODLARI =====
    st.subheader(f"📊 {ust_sekme}")
    
    # Filtreler
    col1, col2 = st.columns(2)
    with col1:
        available_periods = get_available_periods_cached()
        selected_periods = st.multiselect("📅 Dönem", available_periods, default=available_periods[:1] if available_periods else [])
    
    with col2:
        if analysis_mode == "SM_OZET":
            available_sms = get_available_sms_cached()
            selected_sm = st.selectbox("👔 Satış Müdürü", ["Tümü"] + available_sms)
            if selected_sm == "Tümü":
                selected_sm = None
        else:
            selected_sm = None
    
    if selected_periods:
        # VIEW'den veri çek
        df_view = get_sm_summary_from_view(
            satis_muduru=selected_sm,
            donemler=selected_periods
        )
        
        if df_view is not None and len(df_view) > 0:
            # Risk dağılımı
            col1, col2, col3, col4 = st.columns(4)
            
            # Risk kolonu var mı kontrol et
            if 'Risk' in df_view.columns:
                kritik = len(df_view[df_view['Risk'].str.contains('KRİTİK', na=False)])
                riskli = len(df_view[df_view['Risk'].str.contains('RİSKLİ', na=False)])
                dikkat = len(df_view[df_view['Risk'].str.contains('DİKKAT', na=False)])
                temiz = len(df_view[df_view['Risk'].str.contains('TEMİZ', na=False)])
            else:
                kritik = riskli = dikkat = temiz = 0
            
            col1.metric("🔴 KRİTİK", kritik)
            col2.metric("🟠 RİSKLİ", riskli)
            col3.metric("🟡 DİKKAT", dikkat)
            col4.metric("🟢 TEMİZ", temiz)
            
            # Gruplama
            if analysis_mode == "GM_OZET" and 'Satış Müdürü' in df_view.columns:
                sm_grouped = aggregate_by_group(df_view, 'Satış Müdürü')
                if len(sm_grouped) > 0:
                    st.subheader("👔 SM Bazlı")
                    st.dataframe(sm_grouped, use_container_width=True)
            
            if analysis_mode in ["GM_OZET", "BS_OZET"] and 'BS' in df_view.columns:
                bs_grouped = aggregate_by_group(df_view, 'BS')
                if len(bs_grouped) > 0:
                    st.subheader("👥 BS Bazlı")
                    st.dataframe(bs_grouped, use_container_width=True)
            
            # Mağaza listesi
            st.subheader("🏪 Mağazalar")
            
            # Mevcut kolonları filtrele
            all_possible_cols = ['Mağaza Kodu', 'Mağaza Adı', 'Satış', 'Fark', 'Fire', 'Toplam %', 
                                'İç Hırs.', 'Kronik', 'Sigara', 'Risk', 'Risk Nedenleri', 'Risk Puan',
                                'toplam_satis', 'toplam_fark', 'toplam_fire', 'risk_puan']
            display_cols = [c for c in all_possible_cols if c in df_view.columns]
            
            # Eğer hiç kolon bulunamadıysa tüm kolonları göster
            if len(display_cols) == 0:
                display_cols = df_view.columns.tolist()
            
            # Sıralama kolonu bul
            sort_col = None
            for col in ['Risk Puan', 'risk_puan', 'Toplam %', 'toplam_oran', 'Fark', 'toplam_fark']:
                if col in df_view.columns:
                    sort_col = col
                    break
            
            # DataFrame göster
            try:
                if sort_col and sort_col in df_view.columns:
                    display_df = df_view[display_cols].sort_values(sort_col, ascending=False)
                else:
                    display_df = df_view[display_cols]
                
                st.dataframe(display_df, use_container_width=True, height=400)
            except Exception as e:
                st.error(f"Tablo gösterim hatası: {e}")
                st.dataframe(df_view, use_container_width=True, height=400)
            
            # Excel indirme
            if analysis_mode == "GM_OZET":
                try:
                    sm_grouped = aggregate_by_group(df_view, 'Satış Müdürü') if 'Satış Müdürü' in df_view.columns else pd.DataFrame()
                    bs_grouped = aggregate_by_group(df_view, 'BS') if 'BS' in df_view.columns else pd.DataFrame()
                    
                    excel_data = create_gm_excel_report(
                        df_view, sm_grouped, bs_grouped,
                        {'donem': ', '.join(selected_periods)}
                    )
                    
                    st.download_button(
                        "📥 Excel İndir",
                        data=excel_data,
                        file_name=f"GM_Dashboard_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except Exception as e:
                    st.error(f"Excel oluşturma hatası: {e}")
        else:
            st.info("📭 Seçilen kriterlere uygun veri bulunamadı.")
    else:
        st.info("📅 Lütfen en az bir dönem seçin.")

elif analysis_mode == "PARCALI":
    # ===== PARÇALI ENVANTER =====
    st.subheader("📦 Parçalı Envanter Analizi")
    
    if 'uploaded_df' in st.session_state and st.session_state.get('uploaded_type') == 'parcali':
        df = st.session_state['uploaded_df']
        df_analyzed = analyze_inventory(df)
        
        # Mağaza bilgisi
        magaza_kodu = df_analyzed['Mağaza Kodu'].iloc[0] if 'Mağaza Kodu' in df_analyzed.columns else 'Bilinmiyor'
        magaza_adi = df_analyzed['Mağaza Adı'].iloc[0] if 'Mağaza Adı' in df_analyzed.columns else ''
        
        st.info(f"🏪 Mağaza: **{magaza_kodu}** - {magaza_adi}")
        
        # Analizler
        internal_df = detect_internal_theft(df_analyzed)
        chronic_df = detect_chronic_products(df_analyzed)
        chronic_fire_df = detect_chronic_fire(df_analyzed)
        cigarette_df = detect_cigarette_shortage(df_analyzed)
        family_df = find_product_families(df_analyzed)
        fire_manip_df = detect_fire_manipulation(df_analyzed)
        external_df = detect_external_theft(df_analyzed)
        kasa_df, kasa_summary = check_kasa_activity_products(df_analyzed, KASA_KODLARI)
        
        # Metrikleri göster
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("İç Hırsızlık", len(internal_df))
        col2.metric("Kronik Açık", len(chronic_df))
        col3.metric("Sigara", len(cigarette_df) - 1 if len(cigarette_df) > 0 else 0)
        col4.metric("10TL Ürün", kasa_summary.get('sorunlu_urun', 0))
        
        # Tabs
        tabs = st.tabs(["🔒 İç Hırsızlık", "📊 Kronik", "🚬 Sigara", "👨‍👩‍👧 Aile", "💰 10TL"])
        
        with tabs[0]:
            if len(internal_df) > 0:
                envanter_tarihi = df_analyzed['Envanter Tarihi'].iloc[0] if 'Envanter Tarihi' in df_analyzed.columns else datetime.now()
                try:
                    internal_enriched = enrich_internal_theft_with_camera(internal_df, magaza_kodu, envanter_tarihi, df_analyzed)
                    st.dataframe(internal_enriched, use_container_width=True)
                except Exception:
                    st.dataframe(internal_df, use_container_width=True)
            else:
                st.success("✅ İç hırsızlık şüphesi yok")
        
        with tabs[1]:
            if len(chronic_df) > 0:
                st.dataframe(chronic_df, use_container_width=True)
            else:
                st.success("✅ Kronik açık yok")
        
        with tabs[2]:
            if len(cigarette_df) > 0:
                st.dataframe(cigarette_df, use_container_width=True)
            else:
                st.success("✅ Sigara açığı yok")
        
        with tabs[3]:
            if len(family_df) > 0:
                st.dataframe(family_df, use_container_width=True)
            else:
                st.info("Aile analizi sonucu yok")
        
        with tabs[4]:
            if len(kasa_df) > 0:
                st.markdown(f"**Toplam:** {kasa_summary.get('toplam_adet', 0):.0f} adet, {kasa_summary.get('toplam_tutar', 0):,.0f} TL")
                st.dataframe(kasa_df, use_container_width=True)
            else:
                st.success("✅ 10TL ürünlerinde sorun yok")
        
        # Excel indirme
        try:
            internal_codes = set(internal_df['Malzeme Kodu'].astype(str).tolist()) if len(internal_df) > 0 else set()
            chronic_codes = set(chronic_df['Malzeme Kodu'].astype(str).tolist()) if len(chronic_df) > 0 else set()
            family_balanced = set()
            
            top20_df = create_top_20_risky(df_analyzed, internal_codes, chronic_codes, family_balanced)
            exec_comments, group_stats = generate_executive_summary(df_analyzed, kasa_df, kasa_summary)
            
            excel_output = create_excel_report(
                df_analyzed, internal_df, chronic_df, chronic_fire_df, cigarette_df,
                external_df, family_df, fire_manip_df, kasa_df, top20_df,
                exec_comments, group_stats, magaza_kodu, magaza_adi,
                {'donem': '', 'tarih': datetime.now().strftime('%Y-%m-%d')}
            )
            
            st.download_button(
                "📥 Excel Rapor İndir",
                data=excel_output,
                file_name=f"Envanter_{magaza_kodu}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"Excel oluşturma hatası: {e}")
    else:
        st.info("📁 Parçalı envanter dosyası yükleyin veya Supabase'den mağaza seçin.")

elif analysis_mode == "SUREKLI":
    # ===== SÜREKLİ ENVANTER =====
    st.subheader("🔄 Sürekli Envanter Analizi")
    
    if not SUREKLI_MODULE_LOADED:
        st.error("❌ Sürekli envanter modülü yüklenemedi!")
        st.stop()
    
    if 'df_surekli' in st.session_state:
        df_raw = st.session_state['df_surekli']
        
        try:
            df_prepared = prepare_surekli_data(df_raw)
            
            magaza_kodu = df_prepared['Mağaza Kodu'].iloc[0] if 'Mağaza Kodu' in df_prepared.columns else 'Bilinmiyor'
            magaza_adi = df_prepared['Mağaza Adı'].iloc[0] if 'Mağaza Adı' in df_prepared.columns else ''
            
            st.info(f"🏪 Mağaza: **{magaza_kodu}** - {magaza_adi}")
            
            analysis_result = analyze_surekli_envanter(df_prepared)
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Toplam Ürün", analysis_result.get('toplam_urun', 0))
            col2.metric("Açık Ürün", analysis_result.get('acik_urun', 0))
            col3.metric("Toplam Açık", f"{analysis_result.get('toplam_acik', 0):,.0f} TL")
            col4.metric("Risk Seviyesi", analysis_result.get('risk_seviye', 'BELİRSİZ'))
            
            st.subheader("🔒 İç Hırsızlık Analizi")
            
            df_onceki = analysis_result.get('df_onceki', pd.DataFrame())
            ic_hirsizlik_df = detect_ic_hirsizlik_surekli(df_prepared, df_onceki)
            
            if len(ic_hirsizlik_df) > 0:
                try:
                    def get_iptal_func(mag, kodlar):
                        return get_iptal_timestamps_for_magaza(mag, kodlar)
                    
                    ic_hirsizlik_enriched = enrich_with_camera_surekli(
                        ic_hirsizlik_df, get_iptal_func, magaza_kodu, df_prepared
                    )
                    st.dataframe(ic_hirsizlik_enriched, use_container_width=True)
                    
                    excel_data = create_ic_hirsizlik_excel_surekli(ic_hirsizlik_enriched, magaza_kodu, magaza_adi)
                    st.download_button(
                        "📥 İç Hırsızlık Raporu İndir",
                        data=excel_data,
                        file_name=f"IcHirsizlik_{magaza_kodu}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except Exception as e:
                    st.dataframe(ic_hirsizlik_df, use_container_width=True)
                    st.warning(f"Kamera entegrasyonu hatası: {e}")
            else:
                st.success("✅ İç hırsızlık şüphesi tespit edilmedi")
            
            st.subheader("📊 Detaylı Rapor")
            try:
                excel_output = create_surekli_excel_report(df_prepared, analysis_result, magaza_kodu, magaza_adi)
                st.download_button(
                    "📥 Tam Rapor İndir",
                    data=excel_output,
                    file_name=f"SurekliEnvanter_{magaza_kodu}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Excel oluşturma hatası: {e}")
        except Exception as e:
            st.error(f"Veri işleme hatası: {e}")
    else:
        st.info("📁 Sürekli envanter dosyası yükleyin.")

# ==================== FOOTER ====================
st.markdown("---")
st.caption("📊 Envanter Risk Analizi v2.1 | Modüler Yapı")
