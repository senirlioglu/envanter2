# ==================== CONFIG.PY ====================
# Tüm sabitler, ayarlar ve konfigürasyonlar

import json
import os

# ==================== GOOGLE SHEETS ====================
IPTAL_SHEETS_ID = '1F4Th-xZ2n0jDyayy5vayIN2j-EGUzqw5Akd8mXQVh4o'
IPTAL_SHEET_NAME = 'IptalVerisi'

# ==================== CACHE SÜRELERİ ====================
CACHE_TTL_SHORT = 300      # 5 dakika
CACHE_TTL_MEDIUM = 900     # 15 dakika
CACHE_TTL_LONG = 3600      # 1 saat

# ==================== ANALİZ EŞİKLERİ ====================
KRONIK_THRESHOLD = 3           # Kaç dönem üst üste açık verirse kronik
FIRE_THRESHOLD = 500           # TL - Fire manipülasyon eşiği
CIGARETTE_KEYWORDS = ['SİGARA', 'SIGARA', 'MARLBORO', 'PARLIAMENT', 'KENT', 'CAMEL', 'WINSTON', 'MURATTI', 'CHESTERFIELD', 'LM', 'TEKEL']
FAMILY_TOLERANCE = 0.30        # Aile analizi miktar toleransı

# ==================== SEGMENT MAPPING ====================
SEGMENT_MAPPING = {
    'L': ['L', 'LA', 'LAB', 'LABC', 'LABCD'],
    'A': ['A', 'LA', 'LAB', 'LABC', 'LABCD'],
    'B': ['B', 'LAB', 'LABC', 'LABCD'],
    'C': ['C', 'LABC', 'LABCD'],
    'D': ['D', 'LABCD']
}

# ==================== HARIÇ NİTELİKLER ====================
HARIC_NITELIKLER = ['Geçici Delist', 'Bölgesel', 'Delist']

# ==================== RİSK AĞIRLIKLARI ====================
def load_risk_weights():
    """Risk ağırlıklarını config dosyasından yükle"""
    config_paths = [
        os.path.join(os.path.dirname(__file__), 'weights.json'),
        '/mount/src/envanter-risk-analizi/weights.json',
        'weights.json'
    ]
    
    for config_path in config_paths:
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            continue
    
    # Varsayılan değerler
    return {
        "risk_weights": {
            "toplam_oran": {"high": {"threshold": 2.0, "points": 40}, "medium": {"threshold": 1.5, "points": 25}, "low": {"threshold": 1.0, "points": 15}},
            "ic_hirsizlik": {"high": {"threshold": 50, "points": 30}, "medium": {"threshold": 30, "points": 20}, "low": {"threshold": 15, "points": 10}},
            "sigara": {"high": {"threshold": 5, "points": 35}, "low": {"threshold": 0, "points": 20}},
            "kronik": {"high": {"threshold": 100, "points": 15}, "low": {"threshold": 50, "points": 10}},
            "fire_manipulasyon": {"high": {"threshold": 10, "points": 20}, "low": {"threshold": 5, "points": 10}},
            "kasa_10tl": {"high": {"threshold": 20, "points": 15}, "low": {"threshold": 10, "points": 10}}
        },
        "risk_levels": {"kritik": 60, "riskli": 40, "dikkat": 20},
        "max_risk_score": 100
    }

RISK_CONFIG = load_risk_weights()

# ==================== JSON VERİ YÜKLEME ====================
def load_json_data(filename):
    """JSON dosyasından veri yükle"""
    paths = [
        os.path.join(os.path.dirname(__file__), filename),
        os.path.join('/mount/src/envanter-risk-analizi', filename),
        filename
    ]
    for path in paths:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            continue
    return {}

# Verileri yükle
SM_BS_MAGAZA = load_json_data('sm_bs_magaza.json')
SEGMENT_URUN = load_json_data('segment_urun.json')
