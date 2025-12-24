# ==================== SUPABASE CRUD ====================
# Supabase veri okuma/yazma işlemleri

import streamlit as st
import pandas as pd
import numpy as np
from .supabase_client import supabase


def save_to_supabase(df_original):
    """
    Excel verisini Supabase'e kaydet
    
    Duplicate kontrolü: Mağaza Kodu + Envanter Dönemi + Depolama Koşulu Grubu
    - Aynı kombinasyon zaten varsa → O envanter ATLANIR
    - Yoksa → Yüklenir
    """
    try:
        df = df_original.copy()
        
        # Gerekli sütunlar var mı kontrol
        required_cols = ['Mağaza Kodu', 'Depolama Koşulu Grubu', 'Envanter Dönemi', 'Malzeme Kodu']
        for col in required_cols:
            if col not in df.columns:
                return 0, 0, f"'{col}' sütunu bulunamadı"
        
        # Unique envanter kombinasyonları bul
        df['_env_key'] = (df['Mağaza Kodu'].astype(str) + '|' + 
                         df['Envanter Dönemi'].astype(str) + '|' + 
                         df['Depolama Koşulu Grubu'].astype(str))
        
        unique_envs = df[['Mağaza Kodu', 'Envanter Dönemi', 'Depolama Koşulu Grubu', '_env_key']].drop_duplicates()
        
        # Supabase'de hangileri mevcut kontrol et
        existing_envs = set()
        for _, env_row in unique_envs.iterrows():
            try:
                result = supabase.table('envanter_veri').select('id').eq(
                    'magaza_kodu', str(env_row['Mağaza Kodu'])
                ).eq(
                    'envanter_donemi', str(env_row['Envanter Dönemi'])
                ).eq(
                    'depolama_kosulu_grubu', str(env_row['Depolama Koşulu Grubu'])
                ).limit(1).execute()
                
                if result.data and len(result.data) > 0:
                    existing_envs.add(env_row['_env_key'])
            except:
                pass
        
        # Sadece yeni envanterler
        new_env_keys = set(unique_envs['_env_key']) - existing_envs
        skipped_env_keys = existing_envs
        
        if not new_env_keys:
            skipped_list = [k.replace('|', ' / ') for k in skipped_env_keys]
            return 0, len(skipped_env_keys), f"Tüm envanterler zaten mevcut: {', '.join(skipped_list[:3])}..."
        
        # Sadece yeni envanterlerin verilerini filtrele
        df_new = df[df['_env_key'].isin(new_env_keys)].copy()
        
        # Duplicate satırları kaldır
        duplicate_key_cols = ['Mağaza Kodu', 'Envanter Dönemi', 'Depolama Koşulu Grubu', 'Malzeme Kodu']
        df_new = df_new.drop_duplicates(subset=duplicate_key_cols, keep='last')
        
        # Sütun mapping
        col_mapping = {
            'Mağaza Kodu': 'magaza_kodu',
            'Mağaza Tanım': 'magaza_tanim',
            'Satış Müdürü': 'satis_muduru',
            'Bölge Sorumlusu': 'bolge_sorumlusu',
            'Depolama Koşulu Grubu': 'depolama_kosulu_grubu',
            'Depolama Koşulu': 'depolama_kosulu',
            'Envanter Dönemi': 'envanter_donemi',
            'Envanter Tarihi': 'envanter_tarihi',
            'Envanter Başlangıç Tarihi': 'envanter_baslangic_tarihi',
            'Ürün Grubu Kodu': 'urun_grubu_kodu',
            'Ürün Grubu Tanımı': 'urun_grubu_tanimi',
            'Mal Grubu Kodu': 'mal_grubu_kodu',
            'Mal Grubu Tanımı': 'mal_grubu_tanimi',
            'Malzeme Kodu': 'malzeme_kodu',
            'Malzeme Tanımı': 'malzeme_tanimi',
            'Satış Fiyatı': 'satis_fiyati',
            'Sayım Miktarı': 'sayim_miktari',
            'Sayım Tutarı': 'sayim_tutari',
            'Kaydi Miktar': 'kaydi_miktar',
            'Kaydi Tutar': 'kaydi_tutar',
            'Fark Miktarı': 'fark_miktari',
            'Fark Tutarı': 'fark_tutari',
            'Kısmi Envanter Miktarı': 'kismi_envanter_miktari',
            'Kısmi Envanter Tutarı': 'kismi_envanter_tutari',
            'Fire Miktarı': 'fire_miktari',
            'Fire Tutarı': 'fire_tutari',
            'Önceki Fark Miktarı': 'onceki_fark_miktari',
            'Önceki Fark Tutarı': 'onceki_fark_tutari',
            'Önceki Fire Miktarı': 'onceki_fire_miktari',
            'Önceki Fire Tutarı': 'onceki_fire_tutari',
            'Satış Miktarı': 'satis_miktari',
            'Satış Hasılatı': 'satis_hasilati',
            'İade Miktarı': 'iade_miktari',
            'İade Tutarı': 'iade_tutari',
            'İptal Fişteki Miktar': 'iptal_fisteki_miktar',
            'İptal Fiş Tutarı': 'iptal_fis_tutari',
            'İptal GP Miktarı': 'iptal_gp_miktari',
            'İptal GP Tutarı': 'iptal_gp_tutari',
            'İptal Satır Miktarı': 'iptal_satir_miktari',
            'İptal Satır Tutarı': 'iptal_satir_tutari',
        }
        
        # Veriyi hazırla
        records = []
        for _, row in df_new.iterrows():
            record = {}
            for excel_col, db_col in col_mapping.items():
                if excel_col in row.index:
                    val = row[excel_col]
                    if pd.isna(val):
                        val = None
                    elif isinstance(val, pd.Timestamp):
                        val = val.strftime('%Y-%m-%d')
                    elif isinstance(val, (np.integer, np.int64)):
                        val = int(val)
                    elif isinstance(val, (np.floating, np.float64)):
                        val = float(val) if not np.isnan(val) else None
                    record[db_col] = val
            records.append(record)
        
        # Batch insert
        batch_size = 500
        inserted = 0
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i+batch_size]
            try:
                supabase.table('envanter_veri').insert(batch).execute()
                inserted += len(batch)
            except Exception as e:
                st.warning(f"Batch {i//batch_size + 1} hatası: {str(e)[:100]}")
        
        # Materialized view refresh
        if inserted > 0:
            try:
                supabase.rpc('refresh_mv_magaza_ozet').execute()
            except:
                pass
        
        new_list = [k.replace('|', ' / ') for k in new_env_keys]
        return inserted, len(skipped_env_keys), f"Yüklenen: {', '.join(new_list[:3])}..."
        
    except Exception as e:
        return 0, 0, f"Hata: {str(e)}"


@st.cache_data(ttl=600)
def get_available_stores_from_supabase():
    """Mevcut mağazaları al - dropdown için"""
    try:
        all_stores = {}
        offset = 0
        batch_size = 1000
        
        while True:
            result = supabase.table('envanter_veri').select('magaza_kodu,magaza_tanim').range(offset, offset + batch_size - 1).execute()
            if not result.data:
                break
            
            for r in result.data:
                if r.get('magaza_kodu'):
                    all_stores[r['magaza_kodu']] = r.get('magaza_tanim', '')
            
            if len(result.data) < batch_size:
                break
            offset += batch_size
            
            if offset > 50000:
                break
        
        return all_stores
    except:
        return {}


@st.cache_data(ttl=300, show_spinner=False)
def get_single_store_data(magaza_kodu, donemler=None):
    """Tek mağaza için veri çek - HIZLI"""
    try:
        all_data = []
        batch_size = 1000
        offset = 0
        
        required_columns = ','.join([
            'magaza_kodu', 'magaza_tanim', 'satis_muduru', 'bolge_sorumlusu',
            'depolama_kosulu_grubu', 'depolama_kosulu', 'envanter_donemi', 'envanter_tarihi', 'envanter_baslangic_tarihi',
            'mal_grubu_tanimi', 'malzeme_kodu', 'malzeme_tanimi', 'satis_fiyati',
            'fark_miktari', 'fark_tutari', 'kismi_envanter_miktari', 'kismi_envanter_tutari',
            'fire_miktari', 'fire_tutari', 'onceki_fark_miktari', 'onceki_fire_miktari',
            'satis_miktari', 'satis_hasilati', 'iptal_satir_miktari'
        ])
        
        for _ in range(50):
            query = supabase.table('envanter_veri').select(required_columns)
            query = query.eq('magaza_kodu', str(magaza_kodu))
            
            if donemler and len(donemler) > 0:
                query = query.in_('envanter_donemi', list(donemler))
            
            query = query.order('id')
            query = query.range(offset, offset + batch_size - 1)
            result = query.execute()
            
            if not result.data:
                break
            
            all_data.extend(result.data)
            
            if len(result.data) < batch_size:
                break
            
            offset += batch_size
        
        if not all_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_data)
        
        reverse_mapping = {
            'magaza_kodu': 'Mağaza Kodu',
            'magaza_tanim': 'Mağaza Adı',
            'satis_muduru': 'Satış Müdürü',
            'bolge_sorumlusu': 'Bölge Sorumlusu',
            'depolama_kosulu_grubu': 'Depolama Koşulu Grubu',
            'depolama_kosulu': 'Depolama Koşulu',
            'envanter_donemi': 'Envanter Dönemi',
            'envanter_tarihi': 'Envanter Tarihi',
            'envanter_baslangic_tarihi': 'Envanter Başlangıç Tarihi',
            'mal_grubu_tanimi': 'Mal Grubu Tanımı',
            'malzeme_kodu': 'Malzeme Kodu',
            'malzeme_tanimi': 'Malzeme Tanımı',
            'satis_fiyati': 'Satış Fiyatı',
            'fark_miktari': 'Fark Miktarı',
            'fark_tutari': 'Fark Tutarı',
            'kismi_envanter_miktari': 'Kısmi Envanter Miktarı',
            'kismi_envanter_tutari': 'Kısmi Envanter Tutarı',
            'fire_miktari': 'Fire Miktarı',
            'fire_tutari': 'Fire Tutarı',
            'onceki_fark_miktari': 'Önceki Fark Miktarı',
            'onceki_fire_miktari': 'Önceki Fire Miktarı',
            'satis_miktari': 'Satış Miktarı',
            'satis_hasilati': 'Satış Tutarı',
            'iptal_satir_miktari': 'İptal Satır Miktarı'
        }
        
        df = df.rename(columns=reverse_mapping)
        return df
        
    except Exception as e:
        st.error(f"Veri çekme hatası: {e}")
        return pd.DataFrame()


def get_data_from_supabase(satis_muduru=None, donemler=None):
    """Supabase'den veri çek ve DataFrame'e çevir"""
    try:
        all_data = []
        batch_size = 1000
        offset = 0
        max_iterations = 500
        
        required_columns = ','.join([
            'magaza_kodu', 'magaza_tanim', 'satis_muduru', 'bolge_sorumlusu',
            'depolama_kosulu_grubu', 'depolama_kosulu', 'envanter_donemi', 'envanter_tarihi', 'envanter_baslangic_tarihi',
            'mal_grubu_tanimi', 'malzeme_kodu', 'malzeme_tanimi', 'satis_fiyati',
            'fark_miktari', 'fark_tutari', 'kismi_envanter_miktari', 'kismi_envanter_tutari',
            'fire_miktari', 'fire_tutari', 'onceki_fark_miktari', 'onceki_fire_miktari',
            'satis_miktari', 'satis_hasilati', 'iptal_satir_miktari'
        ])
        
        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            
            query = supabase.table('envanter_veri').select(required_columns)
            
            if satis_muduru:
                query = query.eq('satis_muduru', satis_muduru)
            
            if donemler and len(donemler) > 0:
                query = query.in_('envanter_donemi', donemler)
            
            query = query.order('id')
            query = query.range(offset, offset + batch_size - 1)
            
            result = query.execute()
            
            if not result.data or len(result.data) == 0:
                break
            
            all_data.extend(result.data)
            
            if len(result.data) < batch_size:
                break
            
            offset += batch_size
        
        if not all_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_data)
        
        reverse_mapping = {
            'magaza_kodu': 'Mağaza Kodu',
            'magaza_tanim': 'Mağaza Adı',
            'satis_muduru': 'Satış Müdürü',
            'bolge_sorumlusu': 'Bölge Sorumlusu',
            'depolama_kosulu_grubu': 'Depolama Koşulu Grubu',
            'depolama_kosulu': 'Depolama Koşulu',
            'envanter_donemi': 'Envanter Dönemi',
            'envanter_tarihi': 'Envanter Tarihi',
            'envanter_baslangic_tarihi': 'Envanter Başlangıç Tarihi',
            'mal_grubu_tanimi': 'Mal Grubu Tanımı',
            'malzeme_kodu': 'Malzeme Kodu',
            'malzeme_tanimi': 'Malzeme Adı',
            'satis_fiyati': 'Satış Fiyatı',
            'fark_miktari': 'Fark Miktarı',
            'fark_tutari': 'Fark Tutarı',
            'kismi_envanter_miktari': 'Kısmi Envanter Miktarı',
            'kismi_envanter_tutari': 'Kısmi Envanter Tutarı',
            'fire_miktari': 'Fire Miktarı',
            'fire_tutari': 'Fire Tutarı',
            'onceki_fark_miktari': 'Önceki Fark Miktarı',
            'onceki_fire_miktari': 'Önceki Fire Miktarı',
            'satis_miktari': 'Satış Miktarı',
            'satis_hasilati': 'Satış Tutarı',
            'iptal_satir_miktari': 'İptal Satır Miktarı',
        }
        
        df = df.rename(columns=reverse_mapping)
        return df
        
    except Exception as e:
        st.error(f"Supabase hatası: {str(e)}")
        return pd.DataFrame()
