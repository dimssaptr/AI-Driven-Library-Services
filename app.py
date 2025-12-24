import streamlit as st
import pandas as pd
import json
import os
import re
import requests
from datetime import datetime

# --- KONFIGURASI HALAMAN (RAMAH SISWA) ---
st.set_page_config(
    page_title="Sobat Pustaka - Smart School Library",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- FILE PENYIMPANAN DATA ---
DB_FILE = 'school_library_data.json'

# --- DATA AWAL (KOLEKSI PERPUSTAKAAN SEKOLAH) ---
# Disesuaikan untuk Siswa SD/SMP/SMA
DEFAULT_DATA = [
    {"judul": "Laskar Pelangi", "penulis": "Andrea Hirata", "tags": "motivasi, sekolah, perjuangan, mimpi", "kategori": "Fiksi", "rak": "A-01", "p5": "Mandiri"},
    {"judul": "Dunia Sophie (Filsafat untuk Remaja)", "penulis": "Jostein Gaarder", "tags": "misteri, berpikir, sejarah, logika", "kategori": "Novel Edukasi", "rak": "B-03", "p5": "Bernalar Kritis"},
    {"judul": "Ensiklopedia Sains: Alam Semesta", "penulis": "Tim National Geographic", "tags": "sains, antariksa, ipa, fakta", "kategori": "Ensiklopedia", "rak": "C-12", "p5": "Bernalar Kritis"},
    {"judul": "Cara Jago Coding Tanpa Pusing", "penulis": "Budi Raharjo", "tags": "komputer, coding, game, teknologi", "kategori": "Keterampilan", "rak": "D-05", "p5": "Kreatif"},
    {"judul": "Laut Bercerita", "penulis": "Leila S. Chudori", "tags": "sejarah, persahabatan, sosial, sedih", "kategori": "Fiksi Sejarah", "rak": "A-02", "p5": "Berkebinekaan Global"},
    {"judul": "Atomic Habits (Versi Remaja)", "penulis": "James Clear", "tags": "psikologi, kebiasaan, disiplin, mental", "kategori": "Pengembangan Diri", "rak": "E-01", "p5": "Mandiri"},
]

# --- FUNGSI MANAJEMEN DATA ---
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

# --- FUNGSI PENCARIAN INTERNET (SUMBER BELAJAR) ---
@st.cache_data(show_spinner=False)
def search_learning_resources(keywords):
    """
    Mencari sumber belajar dari Crossref, disesuaikan agar relevan dengan kebutuhan sekolah.
    """
    results = []
    try:
        # Kita filter tipe konten agar lebih relevan (book-chapter, reference-entry, article)
        url = f"https://api.crossref.org/works?query={keywords}&rows=3&select=title,author,type,container-title,URL"
        response = requests.get(url, timeout=3)
        
        if response.status_code == 200:
            data = response.json()
            items = data.get('message', {}).get('items', [])
            
            for item in items:
                judul = item.get('title', ['No Title'])[0]
                
                penulis = "Tim Penulis"
                if 'author' in item and len(item['author']) > 0:
                    fam = item['author'][0].get('family', '')
                    given = item['author'][0].get('given', '')
                    penulis = f"{given} {fam}".strip()
                
                sumber = item.get('container-title', ['Jurnal/Database Global'])[0]
                link = item.get('URL', '#')
                
                results.append({
                    "judul": judul,
                    "penulis": penulis,
                    "kategori": "Sumber Digital (Global)",
                    "rak": "Internet",
                    "p5": "Bernalar Kritis",
                    "link": link
                })
    except:
        pass
    return results

# --- LOGIKA PRIVASI (PRIVACY SHIELD - SCHOOL EDITION) ---
def privacy_shield_check(text):
    warnings = []
    score = 100
    
    # 1. Deteksi Data Pribadi (Bahasa Edukatif)
    if re.search(r'[\w\.-]+@[\w\.-]+', text):
        warnings.append("🛡️ **Ups, ada Email!** Sebaiknya jangan posting alamat email sembarangan ya.")
        score -= 20
    if re.search(r'(\+62|08)\d{8,}', text):
        warnings.append("🛡️ **Bahaya:** Ada nomor HP/WA terdeteksi. Jangan disebar ya, nanti banyak spam/penipuan.")
        score -= 30
    if re.search(r'(Jl\.|Jalan|Rumah|Komplek)\s\w+', text, re.IGNORECASE):
        warnings.append("🛡️ **Jaga Privasi:** Jangan tulis alamat rumah detail di internet.")
        score -= 20
        
    # 2. Deteksi Cyberbullying/Toxic (Bahasa Sekolah)
    toxic_words = ['bodoh', 'tolol', 'jelek', 'mati', 'benci', 'sampah', 'gila']
    found_toxic = [word for word in toxic_words if word in text.lower()]
    if found_toxic:
        warnings.append(f"🤝 **Etika Digital:** Yuk ganti kata **'{', '.join(found_toxic)}'** dengan kata yang lebih baik. Jadilah netizen bijak!")
        score -= 25

    # 3. Analisis Sentimen Sederhana (Deteksi Kecemasan/Curhat)
    anxiety_words = ['takut', 'cemas', 'bingung', 'sedih', 'stres', 'capek']
    found_anxiety = [word for word in anxiety_words if word in text.lower()]
    
    return score, warnings, found_anxiety

def get_recommendations(text, df_local, use_internet=False):
    text_lower = text.lower()
    local_results = []
    
    # Pencarian Lokal (Matching Minat)
    for index, row in df_local.iterrows():
        tags = [t.strip().lower() for t in row['tags'].split(',')]
        # Cek relevansi tag
        relevance = sum(1 for tag in tags if tag in text_lower)
        
        # Logika tambahan: Jika user curhat (deteksi kata sedih/takut), sarankan buku motivasi
        if any(x in text_lower for x in ['sedih', 'takut', 'galau']) and row['kategori'] == 'Pengembangan Diri':
            relevance += 2
            
        if relevance > 0:
            local_results.append(row)
    
    # Pencarian Internet
    internet_results = []
    if use_internet:
        words = sorted(text.split(), key=len, reverse=True)[:3]
        query = " ".join(words)
        if len(query) > 3:
            internet_results = search_learning_resources(query)
    
    return local_results + internet_results

# --- HALAMAN USER (SISWA) ---
def student_page():
    st.markdown("## 🎓 Sobat Pustaka")
    st.markdown("##### *Teman Cerita & Belajar Kamu yang Aman*")
    
    # Layout Input
    with st.container():
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.info("💡 **Tips:** Bingung mau nulis caption IG/TikTok? Atau lagi cari bahan tugas? Tulis aja di sini, AI akan bantuin kamu cek keamanannya & cari buku yang pas!")
            
            input_text = st.text_area(
                "Apa yang lagi kamu pikirkan/kerjakan?", 
                height=120, 
                placeholder="Contoh: Aku lagi suka banget main game tapi takut nilai turun. Ada saran buku gak?"
            )
            
            col_act1, col_act2 = st.columns(2)
            with col_act1:
                use_internet = st.checkbox("🌍 Cari info tambahan dari internet", value=True)
            with col_act2:
                analyze = st.button("✨ Cek Tulisan & Cari Buku", use_container_width=True, type="primary")

        with col2:
            st.image("https://img.freepik.com/free-vector/flat-design-library-concept_23-2149117865.jpg?w=740", caption="Perpustakaan Digital Sekolah")

    st.divider()

    if analyze and input_text:
        df = load_data()
        
        # Proses Cepat
        with st.status("🤖 AI sedang bekerja...", expanded=True) as status:
            st.write("🛡️ Memeriksa keamanan privasi...")
            score, warnings, anxiety = privacy_shield_check(input_text)
            
            st.write("📚 Mengubungkan minatmu dengan buku di rak...")
            recs = get_recommendations(input_text, df, use_internet)
            
            status.update(label="Selesai!", state="complete", expanded=False)

        col_res1, col_res2 = st.columns([1, 1])

        # BAGIAN 1: PRIVACY SHIELD (EDUKASI)
        with col_res1:
            st.subheader("🛡️ Hasil Cek Keamanan")
            
            # Tampilan Skor ala Game
            if score >= 90:
                st.success(f"**Skor Keamanan: {score}/100 (SANGAT BAGUS)**")
                st.markdown("✅ Tulisan kamu aman! Siap diposting tanpa takut data bocor.")
            elif score >= 60:
                st.warning(f"**Skor Keamanan: {score}/100 (HATI-HATI)**")
                st.markdown("🤔 Hmm, ada beberapa hal yang perlu kamu perbaiki:")
                for w in warnings:
                    st.write(w)
            else:
                st.error(f"**Skor Keamanan: {score}/100 (BERISIKO)**")
                st.markdown("⛔ **Stop!** Jangan diposting dulu. Ini berbahaya buat kamu:")
                for w in warnings:
                    st.write(w)
            
            # Respon Empati (Jika terdeteksi cemas)
            if anxiety:
                st.info(f"💙 Sepertinya kamu lagi merasa **{', '.join(anxiety)}**. Gapapa kok merasa begitu. Coba baca buku rekomendasi di samping buat nemenin kamu ya.")

        # BAGIAN 2: REKOMENDASI BUKU (KURASI)
        with col_res2:
            st.subheader("📚 Rekomendasi Buat Kamu")
            if recs:
                st.write(f"Ada **{len(recs)}** bahan bacaan yang cocok sama cerita kamu:")
                for item in recs:
                    with st.expander(f"📖 {item['judul']}"):
                        st.write(f"**Penulis:** {item['penulis']}")
                        st.write(f"**Kategori:** {item['kategori']}")
                        
                        # Badge P5
                        if 'p5' in item:
                            st.caption(f"🏅 **Dimensi P5:** {item['p5']}")
                        
                        if item['rak'] == "Internet":
                            st.markdown(f"[Klik untuk baca sumber asli]({item.get('link', '#')})")
                        else:
                            st.markdown(f"📍 **Lokasi:** Rak {item['rak']} (Perpustakaan Sekolah)")
            else:
                st.warning("Belum nemu yang pas nih. Coba cerita lebih detail, misalnya tentang 'hobi', 'cita-cita', atau 'pelajaran kesukaan'.")

# --- HALAMAN ADMIN (PUSTAKAWAN) ---
def librarian_page():
    st.markdown("## 👩‍🏫 Dashboard Pustakawan")
    st.info("Mode Admin: Kelola Koleksi Buku & Data Peminjaman")
    
    df = load_data()
    tab1, tab2 = st.tabs(["📦 Katalog Buku", "➕ Tambah Buku Baru"])
    
    with tab1:
        st.dataframe(df, use_container_width=True)
        
    with tab2:
        with st.form("add_book_form"):
            col_a, col_b = st.columns(2)
            with col_a:
                new_judul = st.text_input("Judul Buku")
                new_penulis = st.text_input("Penulis")
                new_rak = st.text_input("Lokasi Rak", placeholder="Contoh: A-01")
            with col_b:
                new_tags = st.text_input("Kata Kunci (Tags)", placeholder="hobi, pelajaran, emosi")
                new_kategori = st.selectbox("Kategori", ["Fiksi", "Ensiklopedia", "Buku Paket", "Pengembangan Diri", "Komik Edukasi"])
                new_p5 = st.selectbox("Dimensi P5", ["Beriman & Bertakwa", "Berkebinekaan Global", "Gotong Royong", "Mandiri", "Bernalar Kritis", "Kreatif"])
            
            submitted = st.form_submit_button("Simpan ke Database")
            
            if submitted:
                new_data = {
                    "judul": new_judul,
                    "penulis": new_penulis,
                    "tags": new_tags,
                    "kategori": new_kategori,
                    "rak": new_rak,
                    "p5": new_p5
                }
                new_row = pd.DataFrame([new_data])
                df = pd.concat([df, new_row], ignore_index=True)
                save_data(df)
                st.success("Buku berhasil ditambahkan!")
                st.rerun()

# --- NAVIGASI UTAMA ---
def main():
    st.sidebar.title("Navigasi Sekolah")
    
    # Menu Navigasi yang lebih sederhana
    menu = st.sidebar.radio("Pilih Peran:", ["👦 Mode Siswa", "👩‍🏫 Mode Pustakawan"])
    
    st.sidebar.divider()
    
    if menu == "👦 Mode Siswa":
        st.sidebar.info("**Profil Siswa**\n\nNama: Budi (Kelas 11)\nStatus: Aktif Membaca")
        student_page()
    else:
        librarian_page()

if __name__ == "__main__":
    main()
