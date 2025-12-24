import streamlit as st
import pandas as pd
import json
import os
import re
import requests
import hashlib
import random
import time

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Sobat Pustaka AI",
    page_icon="🤖",
    layout="wide"
)

# --- DATABASE FILES ---
BOOK_DB_FILE = 'school_library_data.json'
USER_DB_FILE = 'users.json'

# --- DATA BUKU SEKOLAH DEFAULT ---
DEFAULT_BOOKS = [
    {"judul": "Laskar Pelangi", "penulis": "Andrea Hirata", "tags": "motivasi sekolah perjuangan mimpi", "kategori": "Fiksi", "rak": "A-01"},
    {"judul": "Dunia Sophie", "penulis": "Jostein Gaarder", "tags": "filsafat misteri berpikir sejarah", "kategori": "Novel Edukasi", "rak": "B-03"},
    {"judul": "Ensiklopedia Sains: Antariksa", "penulis": "Tim NatGeo", "tags": "sains ipa planet bintang", "kategori": "Ensiklopedia", "rak": "C-12"},
    {"judul": "Atomic Habits (Remaja)", "penulis": "James Clear", "tags": "psikologi disiplin malas rajin", "kategori": "Pengembangan Diri", "rak": "E-01"},
    {"judul": "Si Juki: Lika Liku Anak Kos", "penulis": "Faza Meonk", "tags": "komik lucu hiburan santai", "kategori": "Komik", "rak": "F-05"},
    {"judul": "Sejarah Indonesia Modern", "penulis": "M.C. Ricklefs", "tags": "sejarah pahlawan merdeka ips", "kategori": "Sejarah", "rak": "G-02"},
]

# --- 1. FUNGSI DATABASE & AUTH ---
@st.cache_data
def load_books():
    if not os.path.exists(BOOK_DB_FILE):
        with open(BOOK_DB_FILE, 'w') as f:
            json.dump(DEFAULT_BOOKS, f)
        return pd.DataFrame(DEFAULT_BOOKS)
    try:
        with open(BOOK_DB_FILE, 'r') as f:
            return pd.DataFrame(json.load(f))
    except:
        return pd.DataFrame(DEFAULT_BOOKS)

def load_users():
    if not os.path.exists(USER_DB_FILE): return []
    try:
        with open(USER_DB_FILE, 'r') as f: return json.load(f)
    except: return []

def save_user(new_user):
    users = load_users()
    users.append(new_user)
    with open(USER_DB_FILE, 'w') as f: json.dump(users, f)

def check_login(username, password):
    users = load_users()
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    for user in users:
        if user['username'] == username and user['password'] == hashed_pw:
            return user
    return None

# --- 2. FITUR PENCARIAN INTERNET (RESTORED) ---
def search_internet_resources(keywords):
    """Mencari sumber dari Crossref (Database Jurnal Terbuka)"""
    results = []
    # Ambil 3 kata kunci terpanjang dari input user untuk pencarian lebih akurat
    clean_words = re.sub(r'[^\w\s]', '', keywords).split()
    top_keywords = sorted(clean_words, key=len, reverse=True)[:3]
    query = "+".join(top_keywords)
    
    try:
        url = f"https://api.crossref.org/works?query={query}&rows=3&select=title,author,URL,container-title"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            items = response.json().get('message', {}).get('items', [])
            for item in items:
                title = item.get('title', ['Tanpa Judul'])[0]
                url_link = item.get('URL', '#')
                journal = item.get('container-title', ['Jurnal Ilmiah'])[0]
                results.append({
                    "judul": title,
                    "penulis": journal,
                    "kategori": "Sumber Internet (Jurnal)",
                    "rak": "Digital / Link",
                    "link": url_link
                })
    except:
        pass # Jika internet mati, kembalikan list kosong
    return results

# --- 3. FITUR LOGIKA AI (SIMULASI GENERATIVE) ---
def analyze_content(text):
    """Menganalisis sentimen dan keamanan privasi"""
    warnings = []
    score = 100
    
    # Deteksi Privasi
    if re.search(r'[\w\.-]+@[\w\.-]+', text):
        warnings.append("Hati-hati, ada alamat email disitu.")
        score -= 20
    if re.search(r'(\+62|08)\d{8,}', text):
        warnings.append("Jangan sebarkan nomor HP di ranah publik.")
        score -= 30
    
    # Deteksi Emosi (Simple Keyword Matching)
    text_lower = text.lower()
    mood = "netral"
    if any(x in text_lower for x in ['sedih', 'nangis', 'takut', 'capek', 'stres']):
        mood = "negatif"
    elif any(x in text_lower for x in ['senang', 'bahagia', 'semangat', 'seru']):
        mood = "positif"
    elif any(x in text_lower for x in ['tugas', 'pr', 'ujian', 'belajar']):
        mood = "akademis"

    return score, warnings, mood

def get_smart_recommendations(text, df_local, user_interest):
    """Pencarian Fuzzy: Mencocokkan kata apa saja yang ada"""
    local_recs = []
    text_words = set(re.sub(r'[^\w\s]', '', text.lower()).split())
    
    # 1. Cari di Database Sekolah
    for idx, row in df_local.iterrows():
        book_tags = set(row['tags'].lower().split())
        # Hitung irisan kata (seberapa banyak kata user cocok dengan tag buku)
        match_count = len(text_words.intersection(book_tags))
        
        # Boost jika sesuai minat user (hanya untuk Member)
        if user_interest:
            user_hobbies = set(user_interest.lower().split(','))
            if len(user_hobbies.intersection(book_tags)) > 0:
                match_count += 3 # Prioritas tinggi
        
        if match_count > 0:
            row['score'] = match_count
            local_recs.append(row)
            
    # Sort berdasarkan skor relevansi
    local_recs = sorted(local_recs, key=lambda x: x['score'], reverse=True)
    
    # 2. Jika hasil lokal sedikit (< 2), cari di Internet
    internet_recs = []
    if len(local_recs) < 2:
        internet_recs = search_internet_resources(text)
        
    return local_recs[:3] + internet_recs

def generate_ai_response(user_name, text, score, warnings, mood, recs):
    """
    Fungsi ini mensimulasikan gaya bicara AI Generative (ChatGPT) 
    menggunakan template dinamis agar terasa natural.
    """
    # 1. Pembuka (Empati)
    greetings = [f"Halo {user_name}!", f"Hai {user_name}, terima kasih sudah bercerita.", f"Halo {user_name}, AI di sini siap bantu."]
    
    if mood == "negatif":
        empathy = "Aku mendeteksi nada kecemasan atau kesedihan dalam tulisanmu. Gapapa kok merasa begitu, tarik napas dulu ya. 💙"
    elif mood == "positif":
        empathy = "Wah, tulisanmu penuh energi positif! Keren banget semangatnya! 🔥"
    elif mood == "akademis":
        empathy = "Kelihatannya kamu lagi fokus mengerjakan tugas sekolah ya. Semangat belajarnya! 📚"
    else:
        empathy = "Aku sudah membaca tulisanmu dengan seksama."
        
    # 2. Feedback Keamanan (Privacy)
    if score == 100:
        security = "✅ **Kabar baik:** Tulisanmu aman dari data pribadi sensitif. Siap diposting!"
    else:
        security = f"⚠️ **Saran Perbaikan:** Skor keamananmu {score}/100. " + " ".join(warnings) + " Sebaiknya disensor dulu ya sebelum posting."
        
    # 3. Pengantar Rekomendasi
    if recs:
        rec_intro = "Untuk membantumu, aku sudah memilihkan beberapa referensi yang relevan:"
    else:
        rec_intro = "Aku belum menemukan buku yang pas di rak sekolah, mungkin kamu bisa coba cari dengan kata kunci lain?"

    # Gabungkan semua
    full_response = f"""
    {random.choice(greetings)}
    
    {empathy}
    
    ---
    **Analisis Keamanan:**
    {security}
    
    ---
    **Rekomendasi Pustaka:**
    {rec_intro}
    """
    return full_response

# --- 4. UI HALAMAN UTAMA ---
def main_app():
    user = st.session_state['user']
    role = st.session_state['role']
    
    # Sidebar
    with st.sidebar:
        st.title(f"Profil: {user['name']}")
        if role == 'student':
            st.caption(f"Minat: {user['interest']}")
        else:
            st.caption("Mode Tamu (Tanpa Personalisasi)")
        
        if st.button("Keluar"):
            st.session_state.clear()
            st.rerun()

    # Chat Interface
    st.header("🤖 AI Library Assistant")
    st.info("Fitur Baru: Tanyakan apa saja, AI akan merespon dengan bahasa manusia, mengecek keamanan, dan mencarikan buku sekaligus (termasuk dari internet).")

    # Inisialisasi Chat History
    if "messages" not in st.session_state:
        st.session_state.messages = []
        # Pesan pembuka dari AI
        welcome_msg = f"Halo {user['name']}! Apa yang bisa kubantu? Mau curhat, cari bahan tugas, atau cek caption medsos?"
        st.session_state.messages.append({"role": "assistant", "content": welcome_msg, "recs": []})

    # Tampilkan Chat History
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            # Jika ada rekomendasi buku tersimpan di history
            if "recs" in message and message["recs"]:
                for book in message["recs"]:
                    with st.expander(f"📖 {book['judul']}"):
                        st.write(f"**Penulis:** {book['penulis']}")
                        st.caption(f"Kategori: {book['kategori']}")
                        if "link" in book:
                            st.markdown(f"[🔗 Baca Sumber Internet]({book['link']})")
                        else:
                            st.write(f"📍 **Rak:** {book['rak']}")

    # Input User
    if prompt := st.chat_input("Ketik sesuatu di sini..."):
        # 1. Tampilkan pesan user
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # 2. Proses AI
        with st.spinner("AI sedang berpikir & mencari buku..."):
            df_books = load_books()
            
            # Analisis
            score, warnings, mood = analyze_content(prompt)
            
            # Cari Rekomendasi (Lokal + Internet)
            interest = user.get('interest') if role == 'student' else None
            recommendations = get_smart_recommendations(prompt, df_books, interest)
            
            # Generate Jawaban Naratif
            ai_text = generate_ai_response(user['name'], prompt, score, warnings, mood, recommendations)
            
            # Simulasi mengetik (biar keren)
            time.sleep(1) 

        # 3. Tampilkan Balasan AI
        with st.chat_message("assistant"):
            st.markdown(ai_text)
            if recommendations:
                for book in recommendations:
                    with st.expander(f"📖 {book['judul']}"):
                        st.write(f"**Penulis:** {book['penulis']}")
                        st.caption(f"Kategori: {book['kategori']}")
                        if "link" in book:
                            st.markdown(f"[🔗 Baca Sumber Internet]({book['link']})")
                        else:
                            st.write(f"📍 **Rak:** {book['rak']}")
        
        # Simpan ke history
        st.session_state.messages.append({
            "role": "assistant", 
            "content": ai_text, 
            "recs": recommendations
        })

# --- 5. HALAMAN LOGIN/SIGNUP ---
def auth_page():
    st.title("🎓 Sobat Pustaka AI")
    tab1, tab2, tab3 = st.tabs(["Masuk", "Daftar", "Tamu"])

    with tab1: # Login
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Masuk"):
                user = check_login(u, p)
                if user:
                    st.session_state['logged_in'] = True
                    st.session_state['user'] = user
                    st.session_state['role'] = 'student'
                    st.rerun()
                else: st.error("Gagal masuk.")

    with tab2: # Daftar
        with st.form("signup"):
            nama = st.text_input("Nama Panggilan")
            user_new = st.text_input("Buat Username")
            pass_new = st.text_input("Buat Password", type="password")
            minat = st.text_input("Hobi/Minat (Penting untuk AI)", placeholder="Cth: Coding, Masak, Sejarah")
            if st.form_submit_button("Daftar"):
                if user_new and pass_new:
                    hashed = hashlib.sha256(pass_new.encode()).hexdigest()
                    save_user({"name": nama, "username": user_new, "password": hashed, "interest": minat})
                    st.success("Berhasil! Silakan login.")
                else: st.warning("Isi semua data.")

    with tab3: # Guest
        st.write("Masuk tanpa login (Fitur personalisasi non-aktif).")
        if st.button("Masuk sebagai Tamu"):
            st.session_state['logged_in'] = True
            st.session_state['user'] = {"name": "Tamu", "interest": None}
            st.session_state['role'] = 'guest'
            st.rerun()

# --- MAIN ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if st.session_state['logged_in']: main_app()
else: auth_page()
