# ==================== REGION ANALYSIS ====================
# Bölge geneli analiz

import pandas as pd
from config import RISK_CONFIG


def get_price_col(df):
    """Fiyat kolonunu bul"""
    if 'Satış Fiyatı' in df.columns:
        return pd.to_numeric(df['Satış Fiyatı'], errors='coerce').fillna(0)
    if 'Birim Fiyat' in df.columns:
        return pd.to_numeric(df['Birim Fiyat'], errors='coerce').fillna(0)
    return pd.Series(0, index=df.index, dtype=float)


def compute_sigara_acik_by_store(df):
    """Sigara açığını mağaza bazında vektörel hesapla"""
    cols = [c for c in ['Mal Grubu Tanımı', 'Ürün Grubu', 'Ana Grup'] if c in df.columns]
    if not cols:
        return pd.Series(dtype=float)
    
    def norm_turkish(s):
        s = s.fillna('').astype(str).str.upper()
        return (s.str.replace('İ', 'I', regex=False)
                 .str.replace('Ş', 'S', regex=False)
                 .str.replace('Ğ', 'G', regex=False)
                 .str.replace('Ü', 'U', regex=False)
                 .str.replace('Ö', 'O', regex=False)
                 .str.replace('Ç', 'C', regex=False)
                 .str.replace('ı', 'I', regex=False))
    
    masks = []
    for c in cols:
        v = norm_turkish(df[c])
        masks.append(v.str.contains(r'SIGARA|TUTUN', regex=True, na=False))
    
    sig_mask = masks[0]
    for m in masks[1:]:
        sig_mask = sig_mask | m
    
    required_cols = ['Mağaza Kodu', 'Fark Miktarı', 'Kısmi Envanter Miktarı', 'Önceki Fark Miktarı']
    available_cols = [c for c in required_cols if c in df.columns]
    
    if 'Mağaza Kodu' not in available_cols:
        return pd.Series(dtype=float)
    
    sig_df = df.loc[sig_mask, available_cols].copy()
    
    if sig_df.empty:
        return pd.Series(dtype=float)
    
    sig_df['net'] = 0.0
    if 'Fark Miktarı' in sig_df.columns:
        sig_df['net'] += sig_df['Fark Miktarı'].fillna(0)
    if 'Kısmi Envanter Miktarı' in sig_df.columns:
        sig_df['net'] += sig_df['Kısmi Envanter Miktarı'].fillna(0)
    if 'Önceki Fark Miktarı' in sig_df.columns:
        sig_df['net'] += sig_df['Önceki Fark Miktarı'].fillna(0)
    
    net_by_store = sig_df.groupby('Mağaza Kodu')['net'].sum()
    sigara_acik = (-net_by_store).clip(lower=0)
    
    return sigara_acik


def analyze_region(df, kasa_kodlari):
    """Bölge geneli analiz - HIZLI VERSİYON"""
    
    magazalar = df['Mağaza Kodu'].dropna().unique().tolist()
    
    if len(magazalar) == 0:
        return pd.DataFrame()
    
    # Temel metrikleri hesapla
    agg_dict = {
        'Mağaza Adı': 'first',
        'Bölge Sorumlusu': 'first',
        'Satış Tutarı': 'sum',
        'Fark Tutarı': 'sum',
        'Kısmi Envanter Tutarı': 'sum',
        'Fire Tutarı': 'sum',
        'Envanter Tarihi': 'first',
        'Envanter Başlangıç Tarihi': 'first',
    }
    
    if 'Satış Müdürü' in df.columns:
        agg_dict['Satış Müdürü'] = 'first'
    
    store_metrics = df.groupby('Mağaza Kodu').agg(agg_dict).reset_index()
    
    if 'Satış Müdürü' not in store_metrics.columns:
        store_metrics['Satış Müdürü'] = ''
    
    # Hesaplamalar
    store_metrics['Fark'] = store_metrics['Fark Tutarı'].fillna(0) + store_metrics['Kısmi Envanter Tutarı'].fillna(0)
    store_metrics['Fire'] = store_metrics['Fire Tutarı'].fillna(0)
    store_metrics['Toplam Açık'] = store_metrics['Fark'] + store_metrics['Fire']
    store_metrics['Satış'] = store_metrics['Satış Tutarı'].fillna(0)
    
    # Oranlar
    store_metrics['Fark %'] = abs(store_metrics['Fark']) / store_metrics['Satış'].replace(0, 1) * 100
    store_metrics['Fire %'] = abs(store_metrics['Fire']) / store_metrics['Satış'].replace(0, 1) * 100
    store_metrics['Toplam %'] = abs(store_metrics['Toplam Açık']) / store_metrics['Satış'].replace(0, 1) * 100
    
    # Gün hesabı
    try:
        store_metrics['Gün'] = (pd.to_datetime(store_metrics['Envanter Tarihi']) - 
                                pd.to_datetime(store_metrics['Envanter Başlangıç Tarihi'])).dt.days
        store_metrics['Gün'] = store_metrics['Gün'].apply(lambda x: max(1, x) if pd.notna(x) else 1)
    except:
        store_metrics['Gün'] = 1
    
    store_metrics['Günlük Fark'] = store_metrics['Fark'] / store_metrics['Gün']
    store_metrics['Günlük Fire'] = store_metrics['Fire'] / store_metrics['Gün']
    
    # Risk analizleri
    price = get_price_col(df)
    ic_hirsizlik = df[(price >= 100) & (df['Fark Miktarı'] < 0)].groupby('Mağaza Kodu').size()
    kronik = df[(df['Önceki Fark Miktarı'] < 0) & (df['Fark Miktarı'] < 0)].groupby('Mağaza Kodu').size()
    
    if 'Önceki Fire Miktarı' in df.columns:
        kronik_fire = df[(df['Önceki Fire Miktarı'] < 0) & (df['Fire Miktarı'] < 0)].groupby('Mağaza Kodu').size()
    else:
        kronik_fire = pd.Series(0, index=magazalar)
    
    sigara_acik_series = compute_sigara_acik_by_store(df)
    fire_manip = df[abs(df['Fire Miktarı']) > abs(df['Fark Miktarı'].fillna(0) + df['Kısmi Envanter Miktarı'].fillna(0))].groupby('Mağaza Kodu').size()
    
    # 10TL ürünleri
    kasa_set = set(str(k) for k in kasa_kodlari) if kasa_kodlari else set()
    if len(kasa_set) > 0:
        kasa_mask = df['Malzeme Kodu'].astype(str).isin(kasa_set)
        kasa_agg = df[kasa_mask].groupby('Mağaza Kodu').agg({
            'Fark Miktarı': 'sum',
            'Kısmi Envanter Miktarı': 'sum',
            'Fark Tutarı': 'sum',
            'Kısmi Envanter Tutarı': 'sum'
        })
        if len(kasa_agg) > 0:
            kasa_agg['10TL Adet'] = kasa_agg['Fark Miktarı'].fillna(0) + kasa_agg['Kısmi Envanter Miktarı'].fillna(0)
            kasa_agg['10TL Tutar'] = kasa_agg['Fark Tutarı'].fillna(0) + kasa_agg['Kısmi Envanter Tutarı'].fillna(0)
        else:
            kasa_agg = pd.DataFrame({'10TL Adet': [], '10TL Tutar': []})
    else:
        kasa_agg = pd.DataFrame({'10TL Adet': [], '10TL Tutar': []})
    
    # Sonuçları birleştir
    results = []
    rw = RISK_CONFIG.get('risk_weights', {})
    rl = RISK_CONFIG.get('risk_levels', {})
    max_score = RISK_CONFIG.get('max_risk_score', 100)
    
    for _, row in store_metrics.iterrows():
        mag = row['Mağaza Kodu']
        
        ic_hrs = ic_hirsizlik.get(mag, 0)
        kr_acik = kronik.get(mag, 0)
        kr_fire = kronik_fire.get(mag, 0) if mag in kronik_fire.index else 0
        sig_acik = sigara_acik_series.get(mag, 0) if mag in sigara_acik_series.index else 0
        fire_man = fire_manip.get(mag, 0) if mag in fire_manip.index else 0
        kasa_adet = kasa_agg.loc[mag, '10TL Adet'] if mag in kasa_agg.index else 0
        kasa_tutar = kasa_agg.loc[mag, '10TL Tutar'] if mag in kasa_agg.index else 0
        
        # Risk puanı hesapla
        risk_puan = 0
        risk_nedenler = []
        toplam_oran = row['Toplam %']
        
        to = rw.get('toplam_oran', {})
        if toplam_oran > to.get('high', {}).get('threshold', 2):
            risk_puan += to.get('high', {}).get('points', 40)
            risk_nedenler.append(f"Toplam %{toplam_oran:.1f}")
        elif toplam_oran > to.get('medium', {}).get('threshold', 1.5):
            risk_puan += to.get('medium', {}).get('points', 25)
        elif toplam_oran > to.get('low', {}).get('threshold', 1):
            risk_puan += to.get('low', {}).get('points', 15)
        
        ih = rw.get('ic_hirsizlik', {})
        if ic_hrs > ih.get('high', {}).get('threshold', 50):
            risk_puan += ih.get('high', {}).get('points', 30)
            risk_nedenler.append(f"İç hırs. {ic_hrs}")
        elif ic_hrs > ih.get('medium', {}).get('threshold', 30):
            risk_puan += ih.get('medium', {}).get('points', 20)
        elif ic_hrs > ih.get('low', {}).get('threshold', 15):
            risk_puan += ih.get('low', {}).get('points', 10)
        
        sg = rw.get('sigara', {})
        if sig_acik > sg.get('high', {}).get('threshold', 5):
            risk_puan += sg.get('high', {}).get('points', 35)
            risk_nedenler.append(f"🚬 SİGARA {sig_acik:.0f}")
        elif sig_acik > sg.get('low', {}).get('threshold', 0):
            risk_puan += sg.get('low', {}).get('points', 20)
        
        kr = rw.get('kronik', {})
        if kr_acik > kr.get('high', {}).get('threshold', 100):
            risk_puan += kr.get('high', {}).get('points', 15)
        elif kr_acik > kr.get('low', {}).get('threshold', 50):
            risk_puan += kr.get('low', {}).get('points', 10)
        
        fm = rw.get('fire_manipulasyon', {})
        if fire_man > fm.get('high', {}).get('threshold', 10):
            risk_puan += fm.get('high', {}).get('points', 20)
        elif fire_man > fm.get('low', {}).get('threshold', 5):
            risk_puan += fm.get('low', {}).get('points', 10)
        
        kt = rw.get('kasa_10tl', {})
        if kasa_adet > kt.get('high', {}).get('threshold', 20):
            risk_puan += kt.get('high', {}).get('points', 15)
        elif kasa_adet > kt.get('low', {}).get('threshold', 10):
            risk_puan += kt.get('low', {}).get('points', 10)
        
        risk_puan = min(risk_puan, max_score)
        
        if risk_puan >= rl.get('kritik', 60):
            risk_seviye = "🔴 KRİTİK"
        elif risk_puan >= rl.get('riskli', 40):
            risk_seviye = "🟠 RİSKLİ"
        elif risk_puan >= rl.get('dikkat', 20):
            risk_seviye = "🟡 DİKKAT"
        else:
            risk_seviye = "🟢 TEMİZ"
        
        results.append({
            'Mağaza Kodu': mag,
            'Mağaza Adı': row['Mağaza Adı'],
            'SM': row.get('Satış Müdürü', ''),
            'BS': row['Bölge Sorumlusu'],
            'Satış': row['Satış'],
            'Fark': row['Fark'],
            'Fire': row['Fire'],
            'Toplam Açık': row['Toplam Açık'],
            'Fark %': row['Fark %'],
            'Fire %': row['Fire %'],
            'Toplam %': row['Toplam %'],
            'Gün': row['Gün'],
            'Günlük Fark': row['Günlük Fark'],
            'Günlük Fire': row['Günlük Fire'],
            'İç Hırs.': ic_hrs,
            'Kr.Açık': kr_acik,
            'Kr.Fire': kr_fire,
            'Sigara': sig_acik,
            'Fire Man.': fire_man,
            '10TL Adet': kasa_adet,
            '10TL Tutar': kasa_tutar,
            'Risk Puan': risk_puan,
            'Risk': risk_seviye,
            'Risk Nedenleri': " | ".join(risk_nedenler) if risk_nedenler else "-"
        })
    
    result_df = pd.DataFrame(results)
    if len(result_df) > 0:
        result_df = result_df.sort_values('Risk Puan', ascending=False)
    
    return result_df


def generate_executive_summary(df, kasa_activity_df=None, kasa_summary=None):
    """Yönetici özeti - mal grubu bazlı yorumlar"""
    comments = []
    
    df_copy = df.copy()
    df_copy['Kısmi Envanter Tutarı'] = df_copy.get('Kısmi Envanter Tutarı', pd.Series(0)).fillna(0)
    df_copy['Önceki Fark Tutarı'] = df_copy.get('Önceki Fark Tutarı', pd.Series(0)).fillna(0)
    df_copy['Toplam Tutar'] = df_copy['Fark Tutarı'] + df_copy['Kısmi Envanter Tutarı'] + df_copy['Önceki Fark Tutarı']
    
    group_stats = df_copy.groupby('Ürün Grubu').agg({
        'Toplam Tutar': 'sum',
        'Fire Tutarı': 'sum',
        'Satış Tutarı': 'sum',
        'Fark Miktarı': lambda x: (x < 0).sum()
    }).reset_index()
    
    group_stats.columns = ['Ürün Grubu', 'Toplam Fark', 'Toplam Fire', 'Toplam Satış', 'Açık Ürün Sayısı']
    group_stats['Açık Oranı'] = abs(group_stats['Toplam Fark']) / group_stats['Toplam Satış'].replace(0, 1) * 100
    
    top_acik = group_stats.nsmallest(3, 'Toplam Fark')
    for _, row in top_acik.iterrows():
        if row['Toplam Fark'] < -500:
            comments.append(f"⚠️ {row['Ürün Grubu']}: {row['Toplam Fark']:,.0f} TL açık ({row['Açık Ürün Sayısı']} ürün)")
    
    top_fire = group_stats.nsmallest(3, 'Toplam Fire')
    for _, row in top_fire.iterrows():
        if row['Toplam Fire'] < -500:
            comments.append(f"🔥 {row['Ürün Grubu']}: {row['Toplam Fire']:,.0f} TL fire")
    
    if kasa_summary is not None:
        toplam_adet = kasa_summary.get('toplam_adet', 0)
        toplam_tutar = kasa_summary.get('toplam_tutar', 0)
        
        if toplam_adet > 0:
            comments.append(f"💰 10 TL ÜRÜNLERİ: NET +{toplam_adet:.0f} adet / {toplam_tutar:,.0f} TL FAZLA")
        elif toplam_adet < 0:
            comments.append(f"💰 10 TL ÜRÜNLERİ: NET {toplam_adet:.0f} adet / {toplam_tutar:,.0f} TL AÇIK")
    
    return comments, group_stats


def aggregate_by_group(store_df, group_col):
    """SM veya BS bazında gruplama"""
    if group_col not in store_df.columns:
        return pd.DataFrame()
    
    kronik_col = 'Kronik' if 'Kronik' in store_df.columns else 'Kr.Açık'
    kasa_adet_col = 'Kasa Adet' if 'Kasa Adet' in store_df.columns else '10TL Adet'
    kasa_tutar_col = 'Kasa Tutar' if 'Kasa Tutar' in store_df.columns else '10TL Tutar'
    
    for col in [kronik_col, kasa_adet_col, kasa_tutar_col]:
        if col not in store_df.columns:
            store_df[col] = 0
    
    agg_dict = {
        'Mağaza Kodu': 'nunique',
        'Satış': 'sum',
        'Fark': 'sum',
        'Fire': 'sum',
        'Toplam Açık': 'sum',
        'İç Hırs.': 'sum',
        kronik_col: 'sum',
        'Sigara': 'sum',
        kasa_adet_col: 'sum',
        kasa_tutar_col: 'sum',
        'Risk Puan': 'mean',
    }
    
    result = store_df.groupby(group_col).agg(agg_dict).reset_index()
    result.columns = [group_col, 'Mağaza Sayısı', 'Satış', 'Fark', 'Fire', 'Toplam Açık', 
                      'İç Hırs.', 'Kronik', 'Sigara', '10TL Adet', '10TL Tutar', 'Ort. Risk']
    
    result['Fark %'] = abs(result['Fark']) / result['Satış'].replace(0, 1) * 100
    result['Fire %'] = abs(result['Fire']) / result['Satış'].replace(0, 1) * 100
    result['Toplam %'] = abs(result['Toplam Açık']) / result['Satış'].replace(0, 1) * 100
    
    return result.sort_values('Ort. Risk', ascending=False)
