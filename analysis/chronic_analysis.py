# ==================== CHRONIC ANALYSIS ====================
# Kronik açık ve kronik fire tespiti

import pandas as pd
from .inventory_analysis import is_balanced


def detect_chronic_products(df):
    """Kronik açık - her iki dönemde de Fark < 0"""
    results = []
    
    for idx, row in df.iterrows():
        if is_balanced(row):
            continue
        
        if row['Önceki Fark Miktarı'] < 0 and row['Fark Miktarı'] < 0:
            results.append({
                'Malzeme Kodu': row.get('Malzeme Kodu', ''),
                'Malzeme Adı': row.get('Malzeme Adı', ''),
                'Ürün Grubu': row.get('Mal Grubu Tanımı', row.get('Ürün Grubu', '')),
                'Bu Dönem Fark': row['Fark Miktarı'],
                'Bu Dönem Tutar': row['Fark Tutarı'],
                'Önceki Fark': row['Önceki Fark Miktarı'],
                'Önceki Tutar': row['Önceki Fark Tutarı'],
                'Toplam Tutar': row['Fark Tutarı'] + row['Önceki Fark Tutarı']
            })
    
    result_df = pd.DataFrame(results)
    if len(result_df) > 0:
        result_df = result_df.drop_duplicates(subset=['Malzeme Kodu'], keep='first')
        result_df = result_df.sort_values('Bu Dönem Tutar', ascending=True)
    
    return result_df


def detect_chronic_fire(df):
    """Kronik Fire - her iki dönemde de fire var VE dengelenmemiş"""
    results = []
    
    for idx, row in df.iterrows():
        onceki_fire = row.get('Önceki Fire Miktarı', 0) or 0
        bu_fire = row['Fire Miktarı']
        
        if onceki_fire != 0 and bu_fire != 0:
            onceki_fark = row.get('Önceki Fark Miktarı', 0) or 0
            bu_fark = row['Fark Miktarı']
            
            if abs(onceki_fark + bu_fark) <= 0.01:
                continue
            
            results.append({
                'Malzeme Kodu': row.get('Malzeme Kodu', ''),
                'Malzeme Adı': row.get('Malzeme Adı', ''),
                'Ürün Grubu': row.get('Mal Grubu Tanımı', row.get('Ürün Grubu', '')),
                'Bu Dönem Fire': bu_fire,
                'Bu Dönem Fire Tutarı': row['Fire Tutarı'],
                'Önceki Fire': onceki_fire,
                'Önceki Fire Tutarı': row.get('Önceki Fire Tutarı', 0),
                'Toplam Fire Tutarı': row['Fire Tutarı'] + row.get('Önceki Fire Tutarı', 0)
            })
    
    result_df = pd.DataFrame(results)
    if len(result_df) > 0:
        result_df = result_df.drop_duplicates(subset=['Malzeme Kodu'], keep='first')
        result_df = result_df.sort_values('Bu Dönem Fire Tutarı', ascending=True)
    
    return result_df
