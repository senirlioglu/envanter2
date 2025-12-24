# 📊 Envanter Risk Analizi v2.0

A101 mağazaları için modüler envanter risk analizi sistemi.

## 🚀 Kurulum

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 📁 Modül Yapısı

```
envanter-risk-analizi/
├── app.py                 # Ana uygulama
├── config.py              # Ayarlar ve sabitler
├── auth.py                # Giriş sistemi
├── database/              # Supabase işlemleri
├── analysis/              # Analiz modülleri
├── camera/                # Kamera entegrasyonu
├── excel/                 # Excel raporları
├── ui/                    # UI bileşenleri
└── utils/                 # Yardımcı fonksiyonlar
```

## ⚙️ Streamlit Cloud Secrets

```toml
SUPABASE_URL = "your-supabase-url"
SUPABASE_KEY = "your-supabase-key"

[users]
ziya = "password"
```

## 📊 Özellikler

- Parçalı Envanter Analizi
- Sürekli Envanter Takibi
- SM/BS/GM Dashboard
- İç Hırsızlık Tespiti
- Kamera Entegrasyonu
- Risk Skorlama
- Excel Raporları
