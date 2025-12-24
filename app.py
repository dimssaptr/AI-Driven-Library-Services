import streamlit as st
import pandas as pd
import json
import os
import re
import requests  # Library untuk koneksi internet
from datetime import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="AI-Driven Library Services",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- FILE PENYIMPANAN DATA (JSON) ---
DB_FILE = 'library_data.json'

# Data Awal (Default)
DEFAULT_DATA = [
    {"judul": "Personal Branding di Era Digital", "penulis": "Prof. Dr. Deni Darmawan", "tags": "branding, sosmed, digital", "jenis": "Buku", "sumber": "Perpus UPI"},
    {"judul": "Psikologi Komunikasi Gen Z", "penulis": "Dr. Hana Silvana", "tags": "psikologi, komunikasi, mental, cemas", "jenis": "Jurnal", "sumber": "Perpus UPI"},
    {"judul": "Etika Digital & UU ITE", "penulis": "Tim Hukum", "tags": "hukum, privasi, ite, pidana", "jenis": "E-Book", "sumber": "Perpus UPI"},
]

# --- FUNGSI MANAJEMEN DATA (CACHE) ---
@st.cache_data
def load_data():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w') as f:
            json.dump(DEFAULT_DATA, f)
        return pd.DataFrame(DEFAULT_DATA)
    try:
        with open(DB_FILE, 'r') as f:
            data = json.load(f)
        return pd.DataFrame(data)
    except:
        return pd.DataFrame(DEFAULT_DATA)

def save_data(df):
    data_list = df.to_dict('records')
    with open(DB_FILE, 'w') as f:
        json.dump(data_list, f)
    st.cache_data.clear()

# --- FUNGSI PENCARIAN INTERNET ASLI (CROSSREF API) ---
# Menggunakan cache agar pencarian yang sama tidak perlu loading ulang
@st.cache_data(show_spinner=False) 
def search_real_internet(keywords):
    """
    Mencari data ASLI ke database Crossref (Database Jurnal Internasional).
    Ini butuh koneksi internet, tapi jauh lebih cepat dari Google Scholar.
    """
    results = []
    try:
        # Request ke API Crossref (Publik & Legal)
        url = f"https://api.crossref.org/works?query={keywords}&rows=3&select=title,author,type,container-title"
        response = requests.get(url, timeout=3) # Timeout 3 detik agar tidak hang
        
        if response.status_code == 200:
            data = response.json()
            items = data.get('message', {}).get('items', [])
            
            for item in items:
                # Membersihkan data dari JSON
                judul = item.get('title', ['No Title'])[0]
                
                # Ambil nama penulis pertama
                penulis = "Unknown Author"
                if 'author' in item and len(item['author']) > 0:
                    fam = item['author'][0].get('family', '')
                    given = item['author'][0].get('given', '')
                    penulis = f"{given} {fam}".strip()
                
                jenis = item.get('type', 'Journal Article').replace('-', ' ').title()
                sumber = item.get('container-title', ['International Database'])[0]
                
                results.append({
                    "judul": judul,
                    "penulis": penulis,
                    "tags": keywords, # Tagging otomatis sesuai keyword
                    "jenis": jenis,
                    "sumber": f"🌐 {sumber}" # Tandai ini dari internet
                })
    except Exception as e:
        # Jika internet mati/error, kembalikan list kosong (jangan crash)
        pass
        
    return results

# --- LOGIKA PRIVASI ---
def privacy_shield_check(text):
    warnings = []
    score = 100
    
    # 1. Deteksi Data Pribadi
    if re.search(r'[\w\.-]+@[\w\.-]+', text):
        warnings.append("⚠️ **Bahaya Privasi:** Terdeteksi ALAMAT EMAIL.")
        score -= 20
    if re.search(r'(\+62|08)\d{8,}', text):
        warnings.append("⚠️ **Bahaya Privasi:** Terdeteksi NOMOR TELEPON/WA.")
        score -= 30
    if re.search(r'\b\d{16}\b', text):
        warnings.append("⚠️ **Bahaya Fatal:** Terdeteksi deretan angka mirip NIK/Kartu Kredit.")
        score -= 50

    # 2. Deteksi Kata Kasar
    toxic_words = ['bodoh', 'tolol', 'anjing', 'benci', 'mati', 'sampah', 'jual', 'slot']
    found_toxic = [word for word in toxic_words if word in text.lower()]
    if found_toxic:
        warnings.append(f"⚠️ **Etika Digital:** Terdeteksi kata sensitif: {', '.join(found_toxic)}.")
        score -= 25

    return score, warnings

def get_recommendations(text, df_local, use_internet=False):
    text_lower = text.lower()
    
    # 1. Cari di Lokal (Database Perpus UPI)
    local_results = []
    for index, row in df_local.iterrows():
        tags = [t.strip().lower() for t in row['tags'].split(',')]
        relevance = sum(1 for tag in tags if tag in text_lower)
        if relevance > 0:
            local_results.append(row)
    
    # 2. Cari di Internet (Real Time)
    internet_results = []
    if use_internet:
        # Ambil keyword utama dari teks user (3 kata terpanjang)
        words = sorted(text.split(), key=len, reverse=True)[:3]
        query = " ".join(words)
        
        if len(query) > 3:
            internet_results = search_real_internet(query)
    
    return local_results + internet_results

# --- USER INTERFACE ---
def user_page():
    st.markdown("## 📚 AI-Driven Library Services")
    st.caption("Real-time Connection | Privacy Shield | Content Validator")
    
    if 'history' not in st.session_state:
        st.session_state.history = []

    with st.container():
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📝 Lab Pembuatan Konten")
            default_text = "Saya ingin riset tentang dampak kecerdasan buatan (AI) dalam pendidikan."
            input_text = st.text_area("Draf Caption / Ide Konten:", height=150, value="", placeholder=f"Contoh: {default_text}")
            
            col_act1, col_act2 = st.columns(2)
            with col_act1:
                use_internet = st.checkbox("🌐 Cari Data Global (Real-Time Internet)", value=True)
            with col_act2:
                analyze = st.button("🚀 Analisis & Validasi", use_container_width=True, type="primary")

        with col2:
            st.info("💡 **Live Connection:**\nSistem terhubung ke API Crossref (Database Jurnal Global). Pastikan laptop terkoneksi internet.")

    st.divider()

    if analyze and input_text:
        df = load_data()
        
        # Proses Cepat
        with st.status("Sedang memproses...", expanded=True) as status:
            st.write("🔍 Mengecek keamanan privasi...")
            score, warnings = privacy_shield_check(input_text)
            
            st.write("🌍 Mengambil referensi dari Database Lokal & Global...")
            recs = get_recommendations(input_text, df, use_internet)
            
            status.update(label="Selesai!", state="complete", expanded=False)
            
        # Simpan History
        st.session_state.history.append({"time": datetime.now().strftime("%H:%M:%S"), "text": input_text[:30]+"..."})

        col_res1, col_res2 = st.columns(2)

        with col_res1:
            st.subheader("🛡️ Privacy Shield")
            if score >= 80:
                st.success(f"**Keamanan: {score}/100 (AMAN)**")
                st.markdown("✅ Konten bersih dari data sensitif.")
            elif score >= 50:
                st.warning(f"**Keamanan: {score}/100 (WASPADA)**")
                for w in warnings:
                    st.write(w)
            else:
                st.error(f"**Keamanan: {score}/100 (BERBAHAYA)**")
                for w in warnings:
                    st.write(w)

        with col_res2:
            st.subheader("📖 Referensi Tervalidasi")
            if recs:
                st.write(f"Menemukan **{len(recs)}** referensi:")
                for item in recs:
                    with st.expander(f"{item['judul']}"):
                        st.write(f"**Penulis:** {item['penulis']}")
                        st.write(f"**Jenis:** {item['jenis']}")
                        if "🌐" in item['sumber']:
                            st.caption(f"Sumber: {item['sumber']} (Live Internet)")
                        else:
                            st.caption(f"Sumber: {item['sumber']} (Koleksi Kampus)")
            else:
                st.warning("Belum menemukan referensi. Coba gunakan kata kunci bahasa Inggris untuk hasil global yang lebih banyak.")

# --- ADMIN PAGE ---
def admin_page():
    st.markdown("## 🛠️ Admin Pustakawan")
    st.info("Mode Admin (Bypass Login)")
    
    df = load_data()
    tab1, tab2 = st.tabs(["📚 Data Buku", "➕ Input Cepat"])
    
    with tab1:
        st.dataframe(df, use_container_width=True)
        
    with tab2:
        with st.form("add_book_form"):
            col_a, col_b = st.columns(2)
            with col_a:
                new_judul = st.text_input("Judul")
                new_penulis = st.text_input("Penulis")
            with col_b:
                new_tags = st.text_input("Tags", placeholder="keyword1, keyword2")
                new_jenis = st.selectbox("Jenis", ["Buku", "Jurnal", "E-Book"])
            
            submitted = st.form_submit_button("Simpan Data")
            
            if submitted:
                new_data = {
                    "judul": new_judul,
                    "penulis": new_penulis,
                    "tags": new_tags,
                    "jenis": new_jenis,
                    "sumber": "Perpus UPI (Manual)"
                }
                new_row = pd.DataFrame([new_data])
                df = pd.concat([df, new_row], ignore_index=True)
                save_data(df)
                st.success("Tersimpan!")
                st.rerun()

def main():
    st.sidebar.title("Navigasi")
    menu = st.sidebar.radio("Pilih Mode:", ["👤 Mode Mahasiswa", "⚙️ Mode Admin"])
    
    if menu == "👤 Mode Mahasiswa":
        st.sidebar.divider()
        st.sidebar.subheader("Riwayat")
        if 'history' in st.session_state and st.session_state.history:
            for h in reversed(st.session_state.history[-3:]):
                st.sidebar.caption(f"🕒 {h['time']} - {h['text']}")
            
        user_page()
    else:
        admin_page()

if __name__ == "__main__":
    main()