# ==================== CAMERA / IPTAL INTEGRATION ====================
# Google Sheets iptal verisi ve kamera entegrasyonu

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Google Sheets ayarları
IPTAL_SHEETS_ID = '1F4Th-xZ2n0jDyayy5vayIN2j-EGUzqw5Akd8mXQVh4o'
IPTAL_SHEET_NAME = 'IptalVerisi'


@st.cache_data(ttl=300)
def get_iptal_verisi_from_sheets():
    """Google Sheets'ten iptal verisini çeker"""
    try:
        csv_url = f'https://docs.google.com/spreadsheets/d/{IPTAL_SHEETS_ID}/gviz/tq?tqx=out:csv&sheet={IPTAL_SHEET_NAME}'
        df = pd.read_csv(csv_url, encoding='utf-8')
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        return pd.DataFrame()


def get_iptal_timestamps_for_magaza(magaza_kodu, malzeme_kodlari):
    """Belirli mağaza ve ürünler için iptal timestamp bilgilerini döner"""
    df_iptal = get_iptal_verisi_from_sheets()
    
    if df_iptal.empty:
        return {}
    
    df_iptal = df_iptal.copy()
    
    # Kolon isimleri
    col_magaza = 'Mağaza - Anahtar'
    col_malzeme = 'Malzeme - Anahtar'
    col_tarih = 'Tarih - Anahtar'
    col_saat = 'Fiş Saati'
    col_miktar = 'Miktar'
    col_islem_no = 'İşlem Numarası'
    col_kasa = 'Kasa numarası'
    
    cols = df_iptal.columns.tolist()
    if col_magaza not in cols and len(cols) > 7:
        col_magaza = cols[7]
    if col_malzeme not in cols and len(cols) > 17:
        col_malzeme = cols[17]
    if col_tarih not in cols and len(cols) > 3:
        col_tarih = cols[3]
    if col_saat not in cols and len(cols) > 31:
        col_saat = cols[31]
    if col_islem_no not in cols and len(cols) > 36:
        col_islem_no = cols[36]
    if col_kasa not in cols and len(cols) > 20:
        col_kasa = cols[20]
    
    def clean_code(x):
        return str(x).strip().replace('.0', '')
    
    df_iptal[col_magaza] = df_iptal[col_magaza].apply(clean_code)
    df_iptal[col_malzeme] = df_iptal[col_malzeme].apply(clean_code)
    
    magaza_str = clean_code(magaza_kodu)
    df_mag = df_iptal[df_iptal[col_magaza] == magaza_str]
    
    if df_mag.empty:
        return {}
    
    malzeme_set = set(clean_code(m) for m in malzeme_kodlari)
    
    result = {}
    
    for _, row in df_mag.iterrows():
        malzeme = clean_code(row[col_malzeme])
        
        if malzeme not in malzeme_set:
            continue
        
        tarih = row.get(col_tarih, '')
        saat = row.get(col_saat, '')
        miktar = row.get(col_miktar, 0)
        islem_no = row.get(col_islem_no, '')
        kasa_no = row.get(col_kasa, '')
        
        if malzeme not in result:
            result[malzeme] = []
        
        result[malzeme].append({
            'tarih': tarih,
            'saat': saat,
            'miktar': miktar,
            'islem_no': islem_no,
            'kasa_no': kasa_no
        })
    
    return result


def _get_price_col(df):
    """Fiyat kolonunu bul"""
    if 'Satış Fiyatı' in df.columns:
        return pd.to_numeric(df['Satış Fiyatı'], errors='coerce').fillna(0)
    if 'Birim Fiyat' in df.columns:
        return pd.to_numeric(df['Birim Fiyat'], errors='coerce').fillna(0)
    return pd.Series(0, index=df.index, dtype=float)


def enrich_internal_theft_with_camera(internal_df, magaza_kodu, envanter_tarihi, full_df=None):
    """İç hırsızlık tablosuna kamera kontrol bilgisi ekler"""
    if internal_df.empty:
        return internal_df
    
    df = internal_df.copy()
    
    if isinstance(envanter_tarihi, str):
        try:
            envanter_tarihi = datetime.strptime(envanter_tarihi, '%Y-%m-%d')
        except:
            try:
                envanter_tarihi = datetime.strptime(envanter_tarihi, '%d.%m.%Y')
            except:
                envanter_tarihi = datetime.now()
    elif hasattr(envanter_tarihi, 'to_pydatetime'):
        envanter_tarihi = envanter_tarihi.to_pydatetime()
    
    kamera_limit = envanter_tarihi - timedelta(days=15)
    
    malzeme_kodlari = df['Malzeme Kodu'].astype(str).tolist()
    
    kategori_col = None
    for col in ['Mal Grubu Tanımı', 'Ürün Grubu', 'Ana Grup']:
        if col in df.columns:
            kategori_col = col
            break
    
    kategori_urunleri = {}
    if kategori_col and full_df is not None:
        for _, row in df.iterrows():
            kategori = row.get(kategori_col, '')
            if kategori and kategori not in kategori_urunleri:
                if kategori_col in full_df.columns:
                    price = _get_price_col(full_df)
                    kat_mask = (full_df[kategori_col] == kategori) & (price >= 100)
                    kat_urunler = full_df.loc[kat_mask, 'Malzeme Kodu'].astype(str).unique().tolist()
                    kategori_urunleri[kategori] = kat_urunler
    
    tum_kategori_kodlari = set()
    for kodlar in kategori_urunleri.values():
        tum_kategori_kodlari.update(kodlar)
    
    tum_kodlar = list(set(malzeme_kodlari) | tum_kategori_kodlari)
    iptal_data = get_iptal_timestamps_for_magaza(magaza_kodu, tum_kodlar)
    
    kamera_kontrol = []
    
    for _, row in df.iterrows():
        malzeme_kodu = str(row['Malzeme Kodu']).strip()
        kategori = row.get(kategori_col, '') if kategori_col else ''
        
        sonuc = _ara_iptal_kaydi(malzeme_kodu, iptal_data, kamera_limit)
        
        if sonuc['bulundu']:
            kamera_kontrol.append(sonuc['detay'])
        else:
            alternatif_bulundu = False
            alternatif_detay = ""
            
            if kategori and kategori in kategori_urunleri:
                for alt_kod in kategori_urunleri[kategori]:
                    if alt_kod != malzeme_kodu:
                        alt_sonuc = _ara_iptal_kaydi(alt_kod, iptal_data, kamera_limit)
                        if alt_sonuc['bulundu']:
                            alternatif_bulundu = True
                            alt_ad = ""
                            if full_df is not None:
                                alt_rows = full_df[full_df['Malzeme Kodu'].astype(str) == alt_kod]
                                if len(alt_rows) > 0:
                                    alt_ad = alt_rows['Malzeme Tanımı'].iloc[0] if 'Malzeme Tanımı' in alt_rows.columns else alt_kod
                            
                            alternatif_detay = f"🔄 KATEGORİ: {alt_ad[:30] if alt_ad else alt_kod} → {alt_sonuc['detay']}"
                            break
            
            if alternatif_bulundu:
                kamera_kontrol.append(alternatif_detay)
            else:
                kamera_kontrol.append(f"❌ {kategori} kategorisinde 100+ TL iptal yok" if kategori else "❌ İptal kaydı yok")
    
    df['KAMERA KONTROL DETAY'] = kamera_kontrol
    
    return df


def _ara_iptal_kaydi(malzeme_kodu, iptal_data, kamera_limit):
    """Bir ürün için iptal kaydı ara ve formatla"""
    if malzeme_kodu not in iptal_data:
        return {'bulundu': False, 'detay': ''}
    
    iptaller = iptal_data[malzeme_kodu]
    son_15_gun = []
    
    for iptal in iptaller:
        tarih_str = str(iptal['tarih'])
        
        try:
            for fmt in ['%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y']:
                try:
                    tarih = datetime.strptime(tarih_str.split()[0], fmt)
                    break
                except:
                    continue
            else:
                continue
            
            if tarih >= kamera_limit:
                son_15_gun.append({**iptal, 'tarih_dt': tarih})
        except:
            pass
    
    if not son_15_gun:
        return {'bulundu': False, 'detay': ''}
    
    son_15_gun_sorted = sorted(son_15_gun, key=lambda x: x['tarih_dt'], reverse=True)
    
    detaylar = []
    for iptal in son_15_gun_sorted[:3]:
        tarih = iptal['tarih_dt'].strftime('%d.%m.%Y')
        saat = str(iptal.get('saat', ''))[:8]
        
        kasa_no = str(iptal.get('kasa_no', '')).strip()
        if kasa_no and kasa_no != 'nan' and kasa_no != '':
            kasa_no = kasa_no.replace('.0', '')
            kasa_str = f"K{kasa_no}"
        else:
            kasa_str = ""
        
        detaylar.append(f"{tarih} {saat} {kasa_str}".strip())
    
    return {
        'bulundu': True,
        'detay': "✅ KAMERA BAK " + " | ".join(detaylar)
    }
