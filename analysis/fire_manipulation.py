# ==================== FIRE MANIPULATION ====================
# Fire manipülasyonu tespiti

import pandas as pd
from .inventory_analysis import is_balanced


def detect_fire_manipulation(df):
    """Fire manipülasyonu: Fire var AMA Fark+Kısmi > 0 VE dengelenmemiş"""
    results = []
    
    for idx, row in df.iterrows():
        fark = row['Fark Miktarı']
        kismi = row['Kısmi Envanter Miktarı']
        onceki_fark = row.get('Önceki Fark Miktarı', 0) or 0
        fire = row['Fire Miktarı']
        
        fark_kismi = fark + kismi
        
        if abs(onceki_fark + fark) <= 0.01:
            continue
        
        if fire < 0 and fark_kismi > 0:
            results.append({
                'Malzeme Kodu': row.get('Malzeme Kodu', ''),
                'Malzeme Adı': row.get('Malzeme Adı', ''),
                'Ürün Grubu': row.get('Mal Grubu Tanımı', row.get('Ürün Grubu', '')),
                'Fark Miktarı': fark,
                'Kısmi Env.': kismi,
                'Önceki Fark': onceki_fark,
                'Fark + Kısmi': fark_kismi,
                'Fire Miktarı': fire,
                'Fire Tutarı': row['Fire Tutarı'],
                'Sonuç': 'FAZLA FİRE GİRİLMİŞ'
            })
    
    result_df = pd.DataFrame(results)
    if len(result_df) > 0:
        result_df = result_df.drop_duplicates(subset=['Malzeme Kodu'], keep='first')
        result_df = result_df.sort_values('Fire Tutarı', ascending=True)
    
    return result_df
