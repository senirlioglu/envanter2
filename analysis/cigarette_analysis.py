# ==================== CIGARETTE ANALYSIS ====================
# Sigara açığı tespiti

import pandas as pd


def detect_cigarette_shortage(df):
    """
    Sigara açığı - Tüm sigaraların TOPLAM (Fark + Kısmi + Önceki) değerine bakılır
    Eğer toplam < 0 ise sigara açığı var demektir
    
    NET = Fark Miktarı + Kısmi Envanter Miktarı + Önceki Fark Miktarı
    """
    
    check_cols = []
    for col in ['Mal Grubu Tanımı', 'Ürün Grubu', 'Ana Grup']:
        if col in df.columns:
            check_cols.append(col)
    
    if not check_cols:
        return pd.DataFrame()
    
    # Sigara mask oluştur
    sigara_mask = pd.Series([False] * len(df), index=df.index)
    
    for col in check_cols:
        col_values = df[col].fillna('').astype(str).str.upper()
        col_values = col_values.str.replace('İ', 'I', regex=False)
        col_values = col_values.str.replace('Ş', 'S', regex=False)
        col_values = col_values.str.replace('Ğ', 'G', regex=False)
        col_values = col_values.str.replace('Ü', 'U', regex=False)
        col_values = col_values.str.replace('Ö', 'O', regex=False)
        col_values = col_values.str.replace('Ç', 'C', regex=False)
        col_values = col_values.str.replace('ı', 'I', regex=False)
        
        mask = col_values.str.contains('SIGARA|TUTUN', case=False, na=False, regex=True)
        sigara_mask = sigara_mask | mask
    
    sigara_df = df[sigara_mask].copy()
    
    if len(sigara_df) == 0:
        return pd.DataFrame()
    
    # Net hesapla
    toplam_fark = sigara_df['Fark Miktarı'].fillna(0).sum()
    toplam_kismi = sigara_df['Kısmi Envanter Miktarı'].fillna(0).sum()
    toplam_onceki = sigara_df['Önceki Fark Miktarı'].fillna(0).sum()
    net_toplam = toplam_fark + toplam_kismi + toplam_onceki
    
    if net_toplam >= 0:
        return pd.DataFrame()
    
    # Açık varsa detay göster
    results = []
    for idx, row in sigara_df.iterrows():
        fark = row['Fark Miktarı'] if pd.notna(row['Fark Miktarı']) else 0
        kismi = row['Kısmi Envanter Miktarı'] if pd.notna(row['Kısmi Envanter Miktarı']) else 0
        onceki = row['Önceki Fark Miktarı'] if pd.notna(row['Önceki Fark Miktarı']) else 0
        urun_net = fark + kismi + onceki
        
        if fark != 0 or kismi != 0 or onceki != 0:
            results.append({
                'Malzeme Kodu': row.get('Malzeme Kodu', ''),
                'Malzeme Adı': row.get('Malzeme Adı', ''),
                'Fark': fark,
                'Kısmi': kismi,
                'Önceki': onceki,
                'Ürün Toplam': urun_net,
                'Risk': 'SİGARA'
            })
    
    result_df = pd.DataFrame(results)
    if len(result_df) > 0:
        result_df = result_df.drop_duplicates(subset=['Malzeme Kodu'], keep='first')
        result_df = result_df.sort_values('Ürün Toplam', ascending=True)
        
        # Toplam satırı ekle
        toplam_row = pd.DataFrame([{
            'Malzeme Kodu': '*** TOPLAM ***',
            'Malzeme Adı': f'SİGARA AÇIĞI: {abs(net_toplam):.0f} adet',
            'Fark': toplam_fark,
            'Kısmi': toplam_kismi,
            'Önceki': toplam_onceki,
            'Ürün Toplam': net_toplam,
            'Risk': '⚠️ AÇIK VAR'
        }])
        result_df = pd.concat([result_df, toplam_row], ignore_index=True)
    
    return result_df
