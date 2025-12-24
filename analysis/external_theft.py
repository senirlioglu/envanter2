# ==================== EXTERNAL THEFT ====================
# Dış hırsızlık tespiti

import pandas as pd
from .inventory_analysis import is_balanced


def detect_external_theft(df):
    """Dış hırsızlık - açık var ama fire/iptal yok"""
    results = []
    
    for idx, row in df.iterrows():
        if is_balanced(row):
            continue
        
        if row['Fark Miktarı'] < 0 and row['Fire Miktarı'] == 0 and row['İptal Satır Miktarı'] == 0:
            if abs(row['Fark Tutarı']) > 50:
                results.append({
                    'Malzeme Kodu': row.get('Malzeme Kodu', ''),
                    'Malzeme Adı': row.get('Malzeme Adı', ''),
                    'Ürün Grubu': row.get('Ürün Grubu', ''),
                    'Fark Miktarı': row['Fark Miktarı'],
                    'Fark Tutarı': row['Fark Tutarı'],
                    'Önceki Fark': row['Önceki Fark Miktarı'],
                    'Risk': 'DIŞ HIRSIZLIK / SAYIM HATASI'
                })
    
    result_df = pd.DataFrame(results)
    if len(result_df) > 0:
        result_df = result_df.sort_values('Fark Tutarı', ascending=True)
    
    return result_df
