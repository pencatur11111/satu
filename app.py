import streamlit as st
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
import time
import random
import urllib.parse
from openpyxl.styles import PatternFill

# --- KONFIGURASI USER-AGENT ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0"
]

# --- FUNGSI INTI TRANSLATE (DENGAN RETRY & RATE LIMIT) ---
def translate_core(text, target, source='id', retries=3):
    """Request ke Google API dengan timeout dan retry. Ambil alternatif ke-2 jika ada."""
    if not text or str(text).strip().lower() in ["nan", "none", ""]:
        return ""

    # Delay acak biar tidak dianggap bot
    time.sleep(random.uniform(0.3, 0.8))

    headers = {"User-Agent": random.choice(USER_AGENTS)}
    base = "https://translate.googleapis.com/translate_a/single"

    # Susun URL manual agar dt=t&dt=at pasti terkirim
    query = urllib.parse.urlencode({
        "client": "gtx",
        "sl": source,
        "tl": target,
        "q": str(text).strip()
    })
    url = f"{base}?{query}&dt=t&dt=at"

    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                result = response.json()

                # Ambil alternatif ke-2 jika tersedia
                if len(result) > 1 and len(result[1]) >= 2:
                    return result[1][1][0]  # alternatif ke-2

                # Fallback ke terjemahan utama
                if isinstance(result[0], list):
                    parts = [p[0] for p in result[0] if p[0]]
                    return "".join(parts)
                return ""

            elif response.status_code == 429:
                # Kena limit, tunggu lebih lama lalu ulangi
                wait = (attempt + 1) * 3
                time.sleep(wait)
                continue
            else:
                # Error lain, ulangi
                time.sleep(1)
                continue

        except Exception:
            time.sleep(1)
            continue

    # Jika sudah retry maksimal masih gagal, kembalikan teks asli agar tidak kosong total
    return f"[ERR] {text[:80]}"

def translate_smart(text, target):
    """Chunking teks besar (>4500 karakter) biar aman."""
    text_str = str(text).strip()
    if len(text_str) <= 4500:
        return translate_core(text_str, target)

    # Pecah per 4000 char
    chunks = [text_str[i:i+4000] for i in range(0, len(text_str), 4000)]
    hasil = []
    for chunk in chunks:
        res = translate_core(chunk, target)
        if res and not res.startswith("[ERR]"):
            hasil.append(res)
        else:
            return res  # hentikan jika gagal
    return " ".join(hasil)

# --- TAMPILAN STREAMLIT ---
st.set_page_config(page_title="Translator 26K - v3", page_icon="💎", layout="wide")
st.title("🐓 Turbo Excel Translator (Versi 26K Baris)")
st.markdown("Alat terjemahan massal anti limit. Kode bahasa tujuan isi di sidebar kiri.")

# --- SIDEBAR ---
st.sidebar.header("⚙️ Konfigurasi")
target_lang = st.sidebar.text_input("Kode Bahasa Tujuan", value="en", help="contoh: en, ja, ko")
workers = st.sidebar.slider("Jumlah Worker (disarankan 3-5)", 1, 5, 3,
                            help="Makin sedikit makin aman, makin banyak risiko limit.")
st.sidebar.info("📌 Untuk 26.000+ baris, disarankan **worker = 3** dan bersabar. Proses bisa memakan waktu 2-6 jam di lokal.")

# --- UPLOAD FILE ---
uploaded = st.file_uploader("Upload file Excel (.xlsx)", type=["xlsx"])
if uploaded:
    df = pd.read_excel(uploaded)
    st.success(f"File dimuat: {uploaded.name} | Total baris: {len(df)}")

    if st.button("🚀 Mulai Terjemahkan (Semua Baris)"):
        if df.shape[1] < 2:
            st.error("Minimal ada 2 kolom (kolom B akan diterjemahkan).")
        else:
            teks = df.iloc[:, 1].astype(str).tolist()
            total = len(teks)
            hasil = [None] * total

            progress = st.progress(0)
            status_teks = st.empty()
            waktu_teks = st.empty()
            start = time.time()

            # Eksekusi paralel dengan worker terbatas
            with ThreadPoolExecutor(max_workers=workers) as executor:
                # Kirim tugas
                future_map = {executor.submit(translate_smart, teks[i], target_lang): i for i in range(total)}
                selesai = 0
                for future in as_completed(future_map):
                    idx = future_map[future]
                    try:
                        hasil[idx] = future.result()
                    except:
                        hasil[idx] = "[ERR] Exception"
                    selesai += 1

                    # Perkiraan sisa waktu
                    elapsed = time.time() - start
                    rata = elapsed / selesai
                    eta = int(rata * (total - selesai))
                    progress.progress(selesai / total)
                    status_teks.write(f"⏳ Selesai {selesai}/{total} baris")
                    waktu_teks.markdown(f"⏱️ Perkiraan sisa: **{eta//60} menit {eta%60} detik**")

            # Tambahkan kolom hasil
            df['Hasil Translate'] = hasil

            # Preview
            st.subheader("📋 Cuplikan Hasil (5 Baris Pertama)")
            st.dataframe(df[['Hasil Translate']].head())

            # Siapkan file unduh
            nama_file = uploaded.name.rsplit('.', 1)[0]
            file_hasil = f"{nama_file} ({target_lang}).xlsx"
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Sheet1')
                workbook = writer.book
                sheet = writer.sheets['Sheet1']
                red = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
                # Warnai merah jika error atau kosong
                for baris, val in enumerate(hasil, start=2):
                    if val is None or val == "" or val.startswith("[ERR]"):
                        for kol in range(1, df.shape[1]+1):
                            sheet.cell(row=baris, column=kol).fill = red

            st.success(f"✅ Selesai! Nama file: {file_hasil}")
            st.download_button("📥 Unduh Hasil", data=output.getvalue(),
                               file_name=file_hasil,
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=12)
        if response.status_code == 200:
            result_json = response.json()
            
            # Cek apakah ada alternatif (index 1) dan minimal 2 item
            alternatives = result_json[1] if len(result_json) > 1 else []
            if len(alternatives) >= 2:
                # Ambil teks alternatif ke-2 (index 1)
                return alternatives[1][0]
            
            # Fallback: gabung terjemahan utama seperti biasa
            if isinstance(result_json[0], list):
                translated_parts = [part[0] for part in result_json[0] if part[0]]
                return "".join(translated_parts)
            return ""
        elif response.status_code == 429:
            return "ERR_LIMIT"
    except Exception:
        pass
    return None

def translate_smart(text, target):
    """Logika Chunking: Memecah teks raksasa (>4500 karakter)."""
    text_str = str(text).strip()
    
    if len(text_str) <= 4500:
        return translate_core(text_str, target)
    
    # Pecah per 4000 karakter agar aman dari limit URL
    chunks = [text_str[i:i+4000] for i in range(0, len(text_str), 4000)]
    translated_results = []
    
    for c in chunks:
        res = translate_core(c, target)
        if res and res != "ERR_LIMIT":
            translated_results.append(res)
        else:
            return "ERR_LIMIT" if res == "ERR_LIMIT" else None
            
    return " ".join(translated_results)

# --- ANTARMUKA STREAMLIT ---
st.set_page_config(page_title="Turbo Translator Pro v2", page_icon="⚡", layout="wide")

st.title("⚡ Turbo Excel Translator")
st.markdown("Alat translasi otomatis untuk file Excel buatan fadhil ganteng kece keren hebat slebew.  kalo gatau kodenya tanya gugel nulisnya gini 639-1 kode bahasa ..... bahasa mu ketiken. JANGAN LUPA DIKASIH LETI 1 BARIS DIATAS NYA")
st.markdown("PAKAILAH 1 TAB AJA JANGAN MULTI TAB WOYYYY RUSAK HOST E, NDAK TAK HOST NO MANEH WM")
# --- SIDEBAR ---
st.sidebar.header("⚙️ Pengaturan")
target_lang = st.sidebar.text_input("Kode Bahasa Tujuan", value="en", help="Contoh: en, ja, fi, ko, ar")
max_workers = st.sidebar.slider("Kecepatan (Workers)", 1, 15, 5, help="Disarankan 5-10 agar aman.")

st.sidebar.markdown("---")
st.sidebar.info("📌 **Catatan:**\nJika hasil download berwarna merah, artinya IP kamu terkena limit sementara. Kurangi Workers atau ganti koneksi internet. pesan untuk mahrus UWES RUS NEK GA KUAT 10 AE GAUSA MEKSO DIULEK ULEK KODENE SAMPE DADI 100!!!")

# --- PROSES UTAMA ---
uploaded_file = st.file_uploader("Upload file Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        st.success(f"File dimuat: '{uploaded_file.name}' | Total: {len(df)} baris.")

        if st.button("🚀 Mulai Terjemahkan"):
            if df.shape[1] < 2:
                st.error("Kolom B (Kolom ke-2) tidak ditemukan!")
            else:
                texts_to_process = df.iloc[:, 1].tolist()
                total_rows = len(texts_to_process)
                results = [None] * total_rows
                
                # UI Progress
                progress_bar = st.progress(0)
                status_placeholder = st.empty()
                time_placeholder = st.empty()
                
                start_time = time.time()

                # --- MULTITHREADING ---
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_idx = {executor.submit(translate_smart, texts_to_process[i], target_lang): i for i in range(total_rows)}
                    
                    completed = 0
                    for future in future_to_idx:
                        idx = future_to_idx[future]
                        try:
                            results[idx] = future.result()
                        except:
                            results[idx] = None
                        
                        completed += 1
                        
                        # Hitung Estimasi Waktu
                        elapsed = time.time() - start_time
                        avg_time = elapsed / completed
                        eta = int(avg_time * (total_rows - completed))
                        
                        # Update Progress UI
                        progress_bar.progress(completed / total_rows)
                        status_placeholder.write(f"⏳ Memproses: {completed}/{total_rows} baris")
                        time_placeholder.markdown(f"⏱️ Sisa waktu: **{eta} detik**")

                df['Hasil Translate'] = results
                
                # --- PREVIEW ---
                st.subheader("📋 Preview Hasil (5 Baris Pertama)")
                st.dataframe(df[['Hasil Translate']].head(5))

                # --- GENERASI FILE DENGAN WARNA & NAMA DINAMIS ---
                nama_file_murni = uploaded_file.name.rsplit('.', 1)[0]
                nama_file_baru = f"{nama_file_murni} ({target_lang}).xlsx"

                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Sheet1')
                    
                    workbook = writer.book
                    worksheet = writer.sheets['Sheet1']
                    red_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
                    
                    # Cek error untuk diwarnai merah
                    for row_num, val in enumerate(results, start=2):
                        if val is None or val == "ERR_LIMIT" or val == "":
                            for col_num in range(1, df.shape[1] + 1):
                                worksheet.cell(row=row_num, column=col_num).fill = red_fill

                st.success(f"✅ Selesai! Nama file: {nama_file_baru}")
                
                st.download_button(
                    label="📥 Download Hasil Terjemahan",
                    data=output.getvalue(),
                    file_name=nama_file_baru,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
