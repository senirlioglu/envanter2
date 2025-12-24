# ==================== INTERNAL THEFT ====================
# İç hırsızlık tespiti

import pandas as pd
from .inventory_analysis import is_balanced


def detect_internal_theft(df):
    """
    İÇ HIRSIZLIK TESPİTİ:
    - Satış Fiyatı >= 100 TL
    - Dengelenmemiş (Fark + Kısmi + Önceki ≠ 0)
    - |Toplam| ≈ İptal Satır, fark büyüdükçe risk AZALIR
    """
    results = []
    
    for idx, row in df.iterrows():
        # Dengelenmiş ise atla
        if is_balanced(row):
            continue
        
        satis_fiyati = row.get('Birim Fiyat', 0) or 0
        if satis_fiyati < 100:
            continue
        
        fark = row['Fark Miktarı']
        kismi = row['Kısmi Envanter Miktarı']
        onceki = row['Önceki Fark Miktarı']
        iptal = row['İptal Satır Miktarı']
        
        toplam = fark + kismi + onceki
        
        if toplam >= 0 or iptal <= 0:
            continue
        
        fark_mutlak = abs(abs(toplam) - iptal)
        
        if fark_mutlak == 0:
            risk = "ÇOK YÜKSEK"
            esitlik = "TAM EŞİT"
        elif fark_mutlak <= 2:
            risk = "YÜKSEK"
            esitlik = "YAKIN (±2)"
        elif fark_mutlak <= 5:
            risk = "ORTA"
            esitlik = "YAKIN (±5)"
        elif fark_mutlak <= 10:
            risk = "DÜŞÜK-ORTA"
            esitlik = f"FARK: {fark_mutlak}"
        else:
            continue
        
        results.append({
            'Malzeme Kodu': row.get('Malzeme Kodu', ''),
            'Malzeme Adı': row.get('Malzeme Adı', ''),
            'Ürün Grubu': row.get('Mal Grubu Tanımı', row.get('Ürün Grubu', '')),
            'Satış Fiyatı': satis_fiyati,
            'Fark Miktarı': fark,
            'Kısmi Env.': kismi,
            'Önceki Fark': onceki,
            'TOPLAM': toplam,
            'İptal Satır': iptal,
            'Fark': fark_mutlak,
            'Durum': esitlik,
            'Fark Tutarı (TL)': row['Fark Tutarı'],
            'Risk': risk
        })
    
    result_df = pd.DataFrame(results)
    
    if len(result_df) > 0:
        # DUPLICATE TEMİZLEME
        result_df = result_df.drop_duplicates(subset=['Malzeme Kodu'], keep='first')
        
        # Risk sıralaması
        risk_order = {'ÇOK YÜKSEK': 0, 'YÜKSEK': 1, 'ORTA': 2, 'DÜŞÜK-ORTA': 3}
        result_df['_risk_sort'] = result_df['Risk'].map(risk_order)
        result_df = result_df.sort_values(['_risk_sort', 'Fark Tutarı (TL)'], ascending=[True, True])
        result_df = result_df.drop('_risk_sort', axis=1)
    
    return result_df
