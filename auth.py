# ==================== AUTH.PY ====================
# Giriş sistemi ve kullanıcı yönetimi

import streamlit as st

def get_users():
    """Kullanıcıları st.secrets'tan al"""
    try:
        if "users" in st.secrets:
            return dict(st.secrets["users"])
    except:
        pass
    return {}

USERS = get_users()

def login():
    """Login sayfası ve doğrulama"""
    if "user" not in st.session_state:
        st.session_state.user = None
    
    if st.session_state.user is None:
        st.markdown("""
        <div style="max-width: 400px; margin: 100px auto; padding: 40px; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    border-radius: 15px; text-align: center;">
            <h1 style="color: white;">📊 Envanter Risk Analizi</h1>
            <p style="color: #eee;">Mağaza Detay Analizi</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.markdown("### 🔐 Giriş Yap")
            username = st.text_input("Kullanıcı Adı", key="login_user")
            password = st.text_input("Şifre", type="password", key="login_pass")
            
            if st.button("Giriş", use_container_width=True):
                if username.lower() in USERS and USERS[username.lower()] == password:
                    st.session_state.user = username.lower()
                    st.rerun()
                else:
                    st.error("❌ Hatalı kullanıcı adı veya şifre!")
        
        return False
    
    return True

def logout():
    """Çıkış yap"""
    st.session_state.user = None
    st.rerun()

def get_current_user():
    """Mevcut kullanıcıyı döndür"""
    return st.session_state.get("user", None)

def is_admin(user):
    """Admin kontrolü"""
    return user in ['ziya', 'admin']
