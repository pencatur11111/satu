import streamlit as st
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor
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

# --- FUNGSI INTI TRANSLATE (MODIFIKASI: AMBIL ALTERNATIF KE-2) ---
def translate_core(text, target, source='id'):
    """Request ke Google API gtx, ambil alternatif ke-2 jika tersedia."""
    if not text or str(text).strip().lower() in ["nan", "none", ""]:
        return ""

    headers = {"User-Agent": random.choice(USER_AGENTS)}
    base_url = "https://translate.googleapis.com/translate_a/single"

    # Bangun URL manual agar dt=t dan dt=at pasti terkirim
    query_params = {
        "client": "gtx",
        "sl": source,
        "tl": target,
        "q": str(text).strip()
    }
    url = f"{base_url}?{urllib.parse.urlencode(query_params)}&dt=t&dt=at"

    try:
        response = requests.get(url, headers=headers, timeout=12)
        if response.status_code == 200:
            result_json = response.json()

            # Cari alternatif ke-2 (index 1 dari list alternatif)
            alternatives = result_json[1] if len(result_json) > 1 else []
            if len(alternatives) >= 2:
                return alternatives[1][0]   # <-- INI ALTERNATIF KE-2

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
