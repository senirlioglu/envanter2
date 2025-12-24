# ==================== HELPERS ====================
# Yardımcı fonksiyonlar

import pandas as pd
import re


def get_price_col(df: pd.DataFrame) -> pd.Series:
    """Fiyat kolonunu bul - farklı kolon isimlerini destekler"""
    if 'Satış Fiyatı' in df.columns:
        return pd.to_numeric(df['Satış Fiyatı'], errors='coerce').fillna(0)
    if 'Birim Fiyat' in df.columns:
        return pd.to_numeric(df['Birim Fiyat'], errors='coerce').fillna(0)
    if 'satis_fiyati' in df.columns:
        return pd.to_numeric(df['satis_fiyati'], errors='coerce').fillna(0)
    return pd.Series(0, index=df.index, dtype=float)


def get_first_two_words(text):
    """Metinden ilk iki kelimeyi al"""
    if pd.isna(text) or not text:
        return ""
    words = str(text).strip().split()
    return " ".join(words[:2]) if len(words) >= 2 else str(text).strip()


def get_last_word(text):
    """Metinden son kelimeyi al"""
    if pd.isna(text) or not text:
        return ""
    words = str(text).strip().split()
    return words[-1] if words else ""


def extract_quantity(text):
    """
    Ürün adından miktar ve birimi çıkar
    Örnek: "DETERJAN 2 LT" -> (2.0, "LT")
    """
    if pd.isna(text):
        return None, None
    
    text = str(text).upper()
    
    # Miktar pattern'leri
    patterns = [
        r'(\d+[.,]?\d*)\s*(KG|G|GR|LT|L|ML|M|CM|MM|ADET|AD|PK|PAKET)',
        r'(\d+[.,]?\d*)\s*X\s*(\d+[.,]?\d*)\s*(KG|G|GR|LT|L|ML)',
        r'(\d+)\s*\'?LI',
        r'(\d+)\s*\'?LU',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            groups = match.groups()
            if len(groups) >= 2:
                qty = float(groups[0].replace(',', '.'))
                unit = groups[1] if len(groups) > 1 else 'ADET'
                return qty, unit
            elif len(groups) == 1:
                return float(groups[0].replace(',', '.')), 'ADET'
    
    return None, None


def is_quantity_similar(qty1, unit1, qty2, unit2, tolerance=0.30):
    """
    İki miktarın benzer olup olmadığını kontrol et
    Birim dönüşümleri yaparak karşılaştır
    """
    if qty1 is None or qty2 is None:
        return False
    
    # Birim standardizasyonu
    unit_map = {
        'G': 'G', 'GR': 'G', 'GRAM': 'G',
        'KG': 'KG', 'KILO': 'KG',
        'ML': 'ML', 'MILILITRE': 'ML',
        'L': 'L', 'LT': 'L', 'LITRE': 'L',
        'ADET': 'ADET', 'AD': 'ADET', 'PK': 'ADET', 'PAKET': 'ADET'
    }
    
    u1 = unit_map.get(str(unit1).upper(), 'ADET') if unit1 else 'ADET'
    u2 = unit_map.get(str(unit2).upper(), 'ADET') if unit2 else 'ADET'
    
    # Birim dönüşümü
    if u1 != u2:
        # G <-> KG
        if u1 == 'G' and u2 == 'KG':
            qty1 = qty1 / 1000
            u1 = 'KG'
        elif u1 == 'KG' and u2 == 'G':
            qty2 = qty2 / 1000
            u2 = 'KG'
        # ML <-> L
        elif u1 == 'ML' and u2 == 'L':
            qty1 = qty1 / 1000
            u1 = 'L'
        elif u1 == 'L' and u2 == 'ML':
            qty2 = qty2 / 1000
            u2 = 'L'
        else:
            return False
    
    # Tolerans kontrolü
    if qty1 == 0 or qty2 == 0:
        return qty1 == qty2
    
    diff = abs(qty1 - qty2) / max(qty1, qty2)
    return diff <= tolerance


def format_currency(value):
    """Para formatı"""
    if pd.isna(value):
        return "0 TL"
    return f"{value:,.0f} TL".replace(",", ".")


def format_percent(value):
    """Yüzde formatı"""
    if pd.isna(value):
        return "%0.0"
    return f"%{value:.1f}"
