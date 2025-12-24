# ==================== FAMILY ANALYSIS ====================
# Ürün ailesi analizi

import pandas as pd
import re


def get_first_two_words(text):
    """İlk 2 kelimeyi al"""
    if pd.isna(text):
        return ""
    words = str(text).strip().split()
    return " ".join(words[:2]).upper() if len(words) >= 2 else str(text).upper()


def get_last_word(text):
    """Son kelimeyi (marka) al"""
    if pd.isna(text):
        return ""
    words = str(text).strip().split()
    return words[-1].upper() if words else ""


def extract_quantity(text):
    """Gramaj/ML çıkar: '750 ML' → 750, 'ML'"""
    if pd.isna(text):
        return None, None
    
    text = str(text).upper()
    
    patterns = [
        r'(\d+[.,]?\d*)\s*(ML|LT|L|G|GR|KG|MG)\b',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value = float(match.group(1).replace(',', '.'))
            unit = match.group(2)
            
            if unit in ['LT', 'L']:
                value = value * 1000
                unit = 'ML'
            elif unit == 'KG':
                value = value * 1000
                unit = 'G'
            elif unit == 'GR':
                unit = 'G'
            
            return value, unit
    
    return None, None


def is_quantity_similar(qty1, unit1, qty2, unit2, tolerance=0.30):
    """Gramaj benzer mi?"""
    if qty1 is None or qty2 is None:
        return True
    
    if unit1 != unit2:
        return False
    
    if qty1 == 0 or qty2 == 0:
        return True
    
    ratio = max(qty1, qty2) / min(qty1, qty2)
    if ratio > 3:
        return False
    
    def get_size_category(qty, unit):
        if unit == 'ML':
            if qty <= 400: return 'S'
            elif qty <= 1000: return 'M'
            else: return 'L'
        elif unit == 'G':
            if qty <= 100: return 'S'
            elif qty <= 400: return 'M'
            else: return 'L'
        return 'M'
    
    cat1 = get_size_category(qty1, unit1)
    cat2 = get_size_category(qty2, unit2)
    
    return cat1 == cat2


def find_product_families(df):
    """
    Benzer ürün ailesi analizi
    Kural: İlk 2 kelime + Son kelime (marka) + Mal Grubu + Gramaj (±%30) aynıysa = AİLE
    """
    df_copy = df.copy()
    df_copy['İlk2Kelime'] = df_copy['Malzeme Adı'].apply(get_first_two_words)
    df_copy['Marka'] = df_copy['Malzeme Adı'].apply(get_last_word)
    df_copy['Gramaj'] = df_copy['Malzeme Adı'].apply(lambda x: extract_quantity(x)[0])
    df_copy['GramajBirim'] = df_copy['Malzeme Adı'].apply(lambda x: extract_quantity(x)[1])
    
    families = []
    processed_indices = set()
    
    for idx, row in df_copy.iterrows():
        if idx in processed_indices:
            continue
        
        ilk2 = row['İlk2Kelime']
        marka = row['Marka']
        urun_grubu = row['Ürün Grubu']
        gramaj = row['Gramaj']
        birim = row['GramajBirim']
        
        if not ilk2 or not marka:
            continue
        
        family_mask = (
            (df_copy['İlk2Kelime'] == ilk2) & 
            (df_copy['Marka'] == marka) & 
            (df_copy['Ürün Grubu'] == urun_grubu)
        )
        
        potential_family = df_copy[family_mask]
        
        if len(potential_family) <= 1:
            continue
        
        family_members = []
        for fam_idx, fam_row in potential_family.iterrows():
            if is_quantity_similar(gramaj, birim, fam_row['Gramaj'], fam_row['GramajBirim']):
                family_members.append(fam_idx)
                processed_indices.add(fam_idx)
        
        if len(family_members) <= 1:
            continue
        
        family_df = df_copy.loc[family_members]
        
        toplam_fark = family_df['Fark Miktarı'].sum()
        toplam_kismi = family_df['Kısmi Envanter Miktarı'].sum()
        toplam_onceki = family_df['Önceki Fark Miktarı'].sum()
        aile_toplami = toplam_fark + toplam_kismi + toplam_onceki
        
        if family_df['Fark Miktarı'].abs().sum() > 0:
            if abs(aile_toplami) <= 2:
                sonuc = "KOD KARIŞIKLIĞI - HIRSIZLIK DEĞİL"
                risk = "DÜŞÜK"
            elif aile_toplami < -2:
                sonuc = "AİLEDE NET AÇIK VAR"
                risk = "ORTA"
            else:
                sonuc = "AİLEDE FAZLA VAR"
                risk = "DÜŞÜK"
            
            urunler = family_df['Malzeme Adı'].tolist()
            farklar = family_df['Fark Miktarı'].tolist()
            
            families.append({
                'Mal Grubu': urun_grubu,
                'İlk 2 Kelime': ilk2,
                'Marka': marka,
                'Ürün Sayısı': len(family_members),
                'Toplam Fark': toplam_fark,
                'Toplam Kısmi': toplam_kismi,
                'Toplam Önceki': toplam_onceki,
                'AİLE TOPLAMI': aile_toplami,
                'Sonuç': sonuc,
                'Risk': risk,
                'Ürünler': ' | '.join([f"{u[:25]}({f})" for u, f in zip(urunler[:5], farklar[:5])])
            })
    
    result_df = pd.DataFrame(families)
    if len(result_df) > 0:
        result_df = result_df.sort_values('AİLE TOPLAMI', ascending=True)
    
    return result_df
