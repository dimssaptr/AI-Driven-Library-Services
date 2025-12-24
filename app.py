import streamlit as st
import pandas as pd
import json
import os
import re
import requests
import hashlib # Untuk simulasi keamanan password sederhana

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Sobat Pustaka - Smart School Library",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- FILE PENYIMPANAN DATA ---
BOOK_DB_FILE = 'school_library_data.json'
USER_DB_FILE = 'users.json'

# --- 1. MANAJEMEN DATA BUKU ---
DEFAULT_BOOKS = [
    {"judul": "Laskar Pelangi", "penulis": "Andrea Hirata", "tags": "motivasi, sekolah, perjuangan, mimpi", "kategori": "Fiksi", "rak": "A-01", "p5": "Mandiri"},
    {"judul": "Dunia Sophie", "penulis": "Jostein Gaarder", "tags": "misteri, berpikir, sejarah, logika", "kategori": "Novel Edukasi", "rak": "B-03", "p5": "Bernalar Kritis"},
    {"judul": "Ensiklopedia Sains", "penulis": "Tim NatGeo", "tags": "sains, antariksa, ipa, fakta", "kategori": "Ensiklopedia", "rak": "C-12", "p5": "Bernalar Kritis"},
    {"judul": "Atomic Habits (Remaja)", "penulis": "James Clear", "tags": "psikologi, kebiasaan, disiplin", "kategori": "Pengembangan Diri", "rak": "E-01", "p5": "Mandiri"},
]

@st.cache_data
def load_books():
    if not os.path.exists(BOOK_DB_FILE):
        with open(BOOK_DB_FILE, 'w') as f:
            json.dump(DEFAULT_BOOKS, f)
        return pd.DataFrame(DEFAULT_BOOKS)
    try:
        with open(BOOK_DB_FILE, 'r') as f:
            data = json.load(f)
        return pd.DataFrame(data)
    except:
        return pd.DataFrame(DEFAULT_BOOKS)

# --- 2. MANAJEMEN USER (LOGIN/REGISTER) ---
def load_users():
    if not os.path.exists(USER_DB_FILE):
        return []
    try:
        with open(USER_DB_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_user(new_user):
    users = load_users()
    users.append(new_user)
    with open(USER_DB_FILE, 'w') as f:
        json.dump(users, f)

def check_login(username, password):
    users = load_users()
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    for user in users:
        if user['username'] == username and user['password'] == hashed_pw:
            return user
    return None

def check_user_exists(username):
    users = load_users()
    for user in users:
        if user['username'] == username:
            return True
    return False

# --- 3. FITUR INTI (AI & PENCARIAN) ---
def privacy_shield_check(text):
    warnings = []
    score = 100
    if re.search(r'[\w\.-]+@[\w\.-]+', text):
        warnings.append("🛡️ **Ups, ada Email!** Jangan posting email sembarangan ya.")
        score -= 20
    if re.search(r'(\+62|08)\d{8,}', text):
        warnings.append("🛡️ **Bahaya:** Ada nomor HP terdeteksi. Jangan disebar.")
        score -= 30
    toxic_words = ['bodoh', 'tolol', 'jelek', 'mati', 'benci']
    found_toxic = [word for word in toxic_words if word in text.lower()]
    if found_toxic:
        warnings.append(f"🤝 **Etika:** Yuk ganti kata kasar **'{', '.join(found_toxic)}** dengan yang lebih sopan.")
        score -= 25
    anxiety_words = ['takut', 'cemas', 'bingung', 'sedih']
    found_anxiety = [word for word in anxiety_words if word in text.lower()]
    return score, warnings, found_anxiety

def get_recommendations(text, df_local, user_interest=None):
    text_lower = text.lower()
    local_results = []
    
    for index, row in df_local.iterrows():
        tags = [t.strip().lower() for t in row['tags'].split(',')]
        relevance = sum(1 for tag in tags if tag in text_lower)
        
        # --- ALGORITMA PERSONALISASI (Hanya untuk User Login) ---
        # Jika user punya minat (misal: 'sains') dan buku ini sesuai, tambah poin relevansi
        if user_interest:
            interest_list = [i.strip().lower() for i in user_interest.split(',')]
            for interest in interest_list:
                if interest in row['tags'].lower() or interest in row['kategori'].lower():
                    relevance += 2 # Boost skor rekomendasi
        
        if relevance > 0:
            row['score'] = relevance # Simpan skor untuk sorting
            local_results.append(row)
    
    # Sort hasil berdasarkan relevansi tertinggi
    local_results = sorted(local_results, key=lambda x: x['score'], reverse=True)
    return local_results

# --- 4. HALAMAN AUTHENTICATION (LOGIN/SIGNUP) ---
def auth_page():
    st.markdown("<h1 style='text-align: center;'>🎓 Sobat Pustaka</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Portal Literasi Digital & Keamanan Siswa</p>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["🔑 Masuk (Sign In)", "📝 Daftar (Sign Up)", "👀 Tamu (Guest)"])
    
    # --- TAB SIGN IN ---
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit_login = st.form_submit_button("Masuk")
            
            if submit_login:
                user = check_login(username, password)
                if user:
                    st.session_state['logged_in'] = True
                    st.session_state['user'] = user
                    st.session_state['role'] = 'student'
                    st.success(f"Selamat datang kembali, {user['name']}!")
                    st.rerun()
                else:
                    st.error("Username atau Password salah.")

    # --- TAB SIGN UP ---
    with tab2:
        st.info("Belum punya akun? Isi data diri kamu di sini untuk mendapatkan rekomendasi buku yang lebih personal!")
        with st.form("signup_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_name = st.text_input("Nama Lengkap")
                new_user = st.text_input("Buat Username")
                new_pass = st.text_input("Buat Password", type="password")
            with col2:
                new_grade = st.selectbox("Kelas", ["7", "8", "9", "10", "11", "12"])
                new_interest = st.text_input("Minat/Hobi (Penting untuk Algoritma!)", placeholder="Contoh: Sains, Sejarah, Coding")
            
            submit_reg = st.form_submit_button("Daftar Sekarang")
            
            if submit_reg:
                if new_name and new_user and new_pass:
                    if check_user_exists(new_user):
                        st.warning("Username sudah dipakai, cari yang lain ya.")
                    else:
                        hashed_pw = hashlib.sha256(new_pass.encode()).hexdigest()
                        user_data = {
                            "name": new_name,
                            "username": new_user,
                            "password": hashed_pw,
                            "grade": new_grade,
                            "interest": new_interest
                        }
                        save_user(user_data)
                        st.success("Akun berhasil dibuat! Silakan login di tab sebelah.")
                else:
                    st.warning("Mohon lengkapi semua data.")

    # --- TAB GUEST ---
    with tab3:
        st.write("Masuk sebagai tamu? Kamu tetap bisa cari buku dan cek keamanan tulisan, tapi **rekomendasi tidak akan disesuaikan dengan minatmu**.")
        if st.button("Masuk sebagai Tamu 🚀"):
            st.session_state['logged_in'] = True
            st.session_state['user'] = {"name": "Tamu", "interest": None} # Interest None = Tidak ada personalisasi
            st.session_state['role'] = 'guest'
            st.rerun()

# --- 5. HALAMAN UTAMA (DASHBOARD) ---
def main_app():
    user = st.session_state['user']
    role = st.session_state['role']
    
    # --- SIDEBAR (PROFIL) ---
    with st.sidebar:
        if role == 'guest':
            st.image("https://cdn-icons-png.flaticon.com/512/847/847969.png", width=80)
            st.title("Mode Tamu")
            st.info("⚠ Fitur Personalisasi Nonaktif")
            st.write("Silakan Login untuk menyimpan riwayat dan mendapat rekomendasi sesuai hobi.")
        else:
            st.image("https://cdn-icons-png.flaticon.com/512/1999/1999625.png", width=80)
            st.title(f"Halo, {user['name']}")
            st.caption(f"Kelas {user['grade']}")
            st.markdown("---")
            st.write("**Minat Terdaftar:**")
            st.success(f"🎯 {user['interest']}")
            st.caption("*Algoritma AI akan memprioritaskan buku sesuai minat di atas.*")
        
        st.markdown("---")
        if st.button("Keluar / Log Out"):
            st.session_state.clear()
            st.rerun()

    # --- KONTEN UTAMA ---
    st.markdown(f"## 📚 Perpustakaan Digital (User: {user['name']})")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.write("Apa yang sedang kamu pikirkan? (Tugas, Curhat, Caption Medsos)")
        input_text = st.text_area("Ketik di sini...", height=100)
        analyze = st.button("🔍 Analisis & Cari Referensi", type="primary")

    with col2:
        if role == 'guest':
            st.warning("💡 **Tips Tamu:** Hasil pencarianmu bersifat umum. Login untuk hasil yang lebih spesifik!")
        else:
            st.info(f"💡 **AI Personal:** Sistem akan mencari buku yang berhubungan dengan teks kamu DAN hobimu ({user['interest']}).")

    if analyze and input_text:
        df = load_books()
        
        # Privacy Check
        score, warnings, anxiety = privacy_shield_check(input_text)
        
        # Recommendation Logic
        # Jika Guest, user['interest'] adalah None, jadi algoritma personalisasi mati.
        recs = get_recommendations(input_text, df, user_interest=user.get('interest'))

        # TAMPILAN HASIL
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("🛡️ Keamanan & Etika")
            if score >= 90:
                st.success(f"Skor: {score} (Aman)")
            else:
                st.warning(f"Skor: {score} (Perlu Perbaikan)")
                for w in warnings: st.write(w)
            
            if anxiety:
                st.info(f"Terdeteksi perasaan: {', '.join(anxiety)}. Semangat ya! Buku di samping mungkin bisa nemenin kamu.")

        with c2:
            st.subheader("📖 Rekomendasi Buku")
            if recs:
                for item in recs:
                    # Menandai jika buku ini direkomendasikan karena minat user
                    is_personalized = False
                    if role != 'guest' and user['interest']:
                        user_interests = [i.strip().lower() for i in user['interest'].split(',')]
                        if any(i in item['tags'].lower() for i in user_interests):
                            is_personalized = True
                    
                    with st.expander(f"{'⭐ ' if is_personalized else ''}{item['judul']}"):
                        st.write(f"**Penulis:** {item['penulis']}")
                        st.write(f"**Rak:** {item['rak']}")
                        if is_personalized:
                            st.caption("✨ *Disarankan karena sesuai profil minatmu.*")
                        st.caption(f"Tags: {item['tags']}")
            else:
                st.write("Belum ada buku yang cocok.")

# --- MAIN FLOW CONTROL ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    auth_page()
else:
    main_app()
