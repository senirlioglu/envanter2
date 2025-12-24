# ==================== RISK CALCULATOR ====================
# Risk puanı hesaplama

import pandas as pd


def calculate_store_risk(df, internal_df, chronic_df, cigarette_df):
    """Mağaza risk puanı hesapla"""
    risk_score = 0
    risk_details = []
    
    # Toplam açık
    toplam_fark = df['Fark Tutarı'].sum()
    toplam_kismi = df['Kısmi Envanter Tutarı'].sum() if 'Kısmi Envanter Tutarı' in df.columns else 0
    toplam_fire = df['Fire Tutarı'].sum()
    toplam_satis = df['Satış Tutarı'].sum() if 'Satış Tutarı' in df.columns else 1
    
    toplam_acik = abs(toplam_fark + toplam_kismi + toplam_fire)
    acik_oran = (toplam_acik / max(toplam_satis, 1)) * 100
    
    if acik_oran > 2:
        risk_score += 30
        risk_details.append(f"Yüksek açık oranı: %{acik_oran:.1f}")
    elif acik_oran > 1:
        risk_score += 15
    
    # İç hırsızlık
    if len(internal_df) > 0:
        cok_yuksek = len(internal_df[internal_df['Risk'] == 'ÇOK YÜKSEK'])
        yuksek = len(internal_df[internal_df['Risk'] == 'YÜKSEK'])
        
        if cok_yuksek > 0:
            risk_score += 25
            risk_details.append(f"{cok_yuksek} üründe iç hırsızlık şüphesi")
        elif yuksek > 0:
            risk_score += 15
    
    # Kronik açık
    if len(chronic_df) > 0:
        kronik_tutar = chronic_df['Toplam Tutar'].sum() if 'Toplam Tutar' in chronic_df.columns else 0
        if abs(kronik_tutar) > 5000:
            risk_score += 20
            risk_details.append(f"Kronik açık: {kronik_tutar:,.0f} TL")
        elif abs(kronik_tutar) > 2000:
            risk_score += 10
    
    # Sigara
    if len(cigarette_df) > 0:
        toplam_row = cigarette_df[cigarette_df['Malzeme Kodu'] == '*** TOPLAM ***']
        if len(toplam_row) > 0:
            sigara_acik = abs(toplam_row['Ürün Toplam'].iloc[0])
            if sigara_acik > 5:
                risk_score += 25
                risk_details.append(f"Sigara açığı: {sigara_acik:.0f} adet")
            elif sigara_acik > 0:
                risk_score += 15
    
    # Risk seviyesi
    if risk_score >= 60:
        risk_level = "🔴 KRİTİK"
    elif risk_score >= 40:
        risk_level = "🟠 RİSKLİ"
    elif risk_score >= 20:
        risk_level = "🟡 DİKKAT"
    else:
        risk_level = "🟢 TEMİZ"
    
    return {
        'score': min(risk_score, 100),
        'level': risk_level,
        'details': risk_details,
        'acik_oran': acik_oran
    }


def create_top_20_risky(df, internal_codes, chronic_codes, family_balanced_codes):
    """En riskli 20 ürünü bul"""
    results = []
    
    for idx, row in df.iterrows():
        kod = str(row.get('Malzeme Kodu', ''))
        if not kod:
            continue
        
        risk_puan = 0
        risk_nedenler = []
        
        # İç hırsızlık
        if kod in internal_codes:
            risk_puan += 40
            risk_nedenler.append("İç Hırs.")
        
        # Kronik
        if kod in chronic_codes:
            risk_puan += 25
            risk_nedenler.append("Kronik")
        
        # Aile dengesiz (kod karışıklığı değil, gerçek açık)
        if kod in family_balanced_codes:
            risk_puan -= 10  # Aile dengeli = daha az riskli
        
        # Açık tutarı
        fark = row.get('Fark Tutarı', 0)
        if fark < -500:
            risk_puan += 20
            risk_nedenler.append(f"Açık {fark:,.0f}")
        elif fark < -100:
            risk_puan += 10
        
        if risk_puan > 0:
            results.append({
                'Malzeme Kodu': kod,
                'Malzeme Adı': row.get('Malzeme Adı', row.get('Malzeme Tanımı', '')),
                'Ürün Grubu': row.get('Ürün Grubu', row.get('Mal Grubu Tanımı', '')),
                'Fark Miktarı': row.get('Fark Miktarı', 0),
                'Fark Tutarı': fark,
                'Fire Tutarı': row.get('Fire Tutarı', 0),
                'Risk Puan': risk_puan,
                'Risk Nedenleri': ' | '.join(risk_nedenler)
            })
    
    result_df = pd.DataFrame(results)
    if len(result_df) > 0:
        result_df = result_df.sort_values('Risk Puan', ascending=False).head(20)
    
    return result_df
