# ==================== SUPABASE CLIENT ====================
# Supabase bağlantı yönetimi

import streamlit as st
from supabase import create_client, Client

# Credentials
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

@st.cache_resource
def get_supabase_client():
    """Supabase client oluştur (cached)"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("⚠️ Supabase credentials eksik! Secrets'a SUPABASE_URL ve SUPABASE_KEY ekleyin.")
        st.stop()
    
    from supabase import ClientOptions
    options = ClientOptions(
        postgrest_client_timeout=60,
    )
    return create_client(SUPABASE_URL, SUPABASE_KEY, options=options)

# Global client
supabase: Client = get_supabase_client()
