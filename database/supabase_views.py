# ==================== SUPABASE VIEWS ====================
# Materialized view sorguları

import streamlit as st
import pandas as pd
from .supabase_client import supabase


@st.cache_data(ttl=300)
def get_sm_summary_from_view(satis_muduru=None, donemler=None, tarih_baslangic=None, tarih_bitis=None):
    """
    SM/GM Özet ekranı için Supabase MATERIALIZED VIEW'den veri çek
    mv_magaza_ozet kullanır - önceden hesaplanmış, çok hızlı
    """
    try:
        query = supabase.table('mv_magaza_ozet').select('*')
        
        if satis_muduru:
            query = query.eq('satis_muduru', satis_muduru)
        
        if donemler and len(donemler) > 0:
            query = query.in_('envanter_donemi', donemler)
        
        if tarih_baslangic:
            query = query.gte('max_envanter_tarihi', tarih_baslangic.strftime('%Y-%m-%d'))
        if tarih_bitis:
            query = query.lte('min_envanter_tarihi', tarih_bitis.strftime('%Y-%m-%d'))
        
        result = query.execute()
        
        if not result.data:
            return pd.DataFrame()
        
        df = pd.DataFrame(result.data)
        
        # Kolon isimlerini düzenle
        column_mapping = {
            'magaza_kodu': 'Mağaza Kodu',
            'magaza_tanim': 'Mağaza Adı',
            'satis_muduru': 'Satış Müdürü',
            'bolge_sorumlusu': 'Bölge Sorumlusu',
            'envanter_donemi': 'Envanter Dönemi',
            'min_envanter_tarihi': 'Envanter Tarihi',
            'max_envanter_tarihi': 'Envanter Tarihi Son',
            'envanter_baslangic_tarihi': 'Envanter Başlangıç Tarihi',
            'fark_tutari': 'Fark Tutarı',
            'kismi_tutari': 'Kısmi Tutarı',
            'fire_tutari': 'Fire Tutarı',
            'satis': 'Satış',
            'fark_miktari': 'Fark Miktarı',
            'kismi_miktari': 'Kısmi Miktarı',
            'onceki_fark_miktari': 'Önceki Fark Miktarı',
            'sigara_net': 'Sigara Net',
            'ic_hirsizlik': 'İç Hırs.',
            'kronik_acik': 'Kronik',
            'kronik_fire': 'Kronik Fire',
            'kasa_adet': 'Kasa Adet',
            'kasa_tutar': 'Kasa Tutar',
        }
        df = df.rename(columns=column_mapping)
        
        # Hesaplamalar
        df['Fark'] = df['Fark Tutarı'].fillna(0) + df['Kısmi Tutarı'].fillna(0)
        df['Fire'] = df['Fire Tutarı'].fillna(0)
        df['Toplam Açık'] = df['Fark'] + df['Fire']
        
        # Oranlar
        df['Fark %'] = (abs(df['Fark']) / df['Satış'] * 100).fillna(0)
        df['Fire %'] = (abs(df['Fire']) / df['Satış'] * 100).fillna(0)
        df['Toplam %'] = (abs(df['Toplam Açık']) / df['Satış'] * 100).fillna(0)
        
        # Gün hesabı
        try:
            df['Gün'] = (pd.to_datetime(df['Envanter Tarihi']) - 
                        pd.to_datetime(df['Envanter Başlangıç Tarihi'])).dt.days
            df['Gün'] = df['Gün'].apply(lambda x: max(1, abs(x)) if pd.notna(x) else 1)
        except:
            df['Gün'] = 1
        
        df['Günlük Fark'] = df['Fark'] / df['Gün']
        df['Günlük Fire'] = df['Fire'] / df['Gün']
        
        # Sigara açığı
        df['Sigara'] = df['Sigara Net'].apply(lambda x: abs(x) if x < 0 else 0)
        
        # Risk puanı hesapla
        def calc_risk_score(row):
            score = 0
            reasons = []
            
            kayip = row['Toplam %']
            if kayip > 2.0:
                score += 40
                reasons.append(f"Kayıp %{kayip:.1f}")
            elif kayip > 1.5:
                score += 25
                reasons.append(f"Kayıp %{kayip:.1f}")
            elif kayip > 1.0:
                score += 15
            
            ic = row['İç Hırs.']
            if ic > 50:
                score += 30
                reasons.append(f"İç Hırs. {ic:.0f}")
            elif ic > 30:
                score += 20
            elif ic > 15:
                score += 10
            
            sig = row['Sigara']
            if sig > 5:
                score += 35
                reasons.append(f"Sigara {sig:.0f}")
            elif sig > 0:
                score += 20
                reasons.append(f"Sigara {sig:.0f}")
            
            kr = row['Kronik']
            if kr > 100:
                score += 15
                reasons.append(f"Kronik {kr:.0f}")
            elif kr > 50:
                score += 10
            
            kasa = abs(row.get('Kasa Tutar', 0) or 0)
            if kasa > 5000:
                score += 20
                reasons.append(f"Kasa {kasa:,.0f}")
            elif kasa > 2000:
                score += 10
            
            return score, ', '.join(reasons) if reasons else '-'
        
        df[['Risk Puan', 'Risk Nedenleri']] = df.apply(
            lambda row: pd.Series(calc_risk_score(row)), axis=1
        )
        
        # Risk seviyesi
        def get_risk_level(score):
            if score >= 70:
                return '🔴 KRİTİK'
            elif score >= 50:
                return '🟠 RİSKLİ'
            elif score >= 30:
                return '🟡 DİKKAT'
            else:
                return '🟢 TEMİZ'
        
        df['Risk'] = df['Risk Puan'].apply(get_risk_level)
        df['BS'] = df['Bölge Sorumlusu']
        
        return df
        
    except Exception as e:
        st.error(f"VIEW hatası: {e}")
        return pd.DataFrame()
