# ==================== DATA FILTERS ====================
# Veri filtreleme fonksiyonları

import pandas as pd


def filter_data(df, satis_muduru=None, donemler=None, magaza_kodu=None):
    """DataFrame'i filtrele"""
    if df is None or df.empty:
        return pd.DataFrame()
    
    filtered = df.copy()
    
    if satis_muduru and 'Satış Müdürü' in filtered.columns:
        filtered = filtered[filtered['Satış Müdürü'] == satis_muduru]
    
    if donemler and len(donemler) > 0 and 'Envanter Dönemi' in filtered.columns:
        filtered = filtered[filtered['Envanter Dönemi'].isin(donemler)]
    
    if magaza_kodu and 'Mağaza Kodu' in filtered.columns:
        filtered = filtered[filtered['Mağaza Kodu'] == magaza_kodu]
    
    return filtered


def get_unique_values(df, column):
    """Benzersiz değerleri al"""
    if df is None or df.empty or column not in df.columns:
        return []
    return sorted(df[column].dropna().unique().tolist())


def get_store_list(df):
    """Mağaza listesi al"""
    if df is None or df.empty:
        return {}
    
    stores = {}
    if 'Mağaza Kodu' in df.columns:
        for _, row in df.drop_duplicates('Mağaza Kodu').iterrows():
            kod = row['Mağaza Kodu']
            ad = row.get('Mağaza Adı', '') or row.get('Mağaza Tanım', '')
            stores[kod] = ad
    
    return stores
