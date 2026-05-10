import streamlit as st
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import time
import random
import urllib.parse
import re
from openpyxl.styles import PatternFill

# --- KONFIGURASI USER-AGENT ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0"
]

# --- FUNGSI INTI TRANSLATE (ALTERNATIF KE-2) ---
def translate_core(text, target, source='id'):
    if not text or str(text).strip().lower() in ["nan", "none", ""]:
        return ""

    headers = {"User-Agent": random.choice(USER_AGENTS)}
    base_url = "https://translate.googleapis.com/translate_a/single"
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
            try:
                result_json = response.json()
            except:
                return None

            # Alternatif ke-2 jika ada
            alternatives = None
            if isinstance(result_json, list) and len(result_json) > 1:
                second_elem = result_json[1]
                if isinstance(second_elem, list) and len(second_elem) > 0:
                    alternatives = second_elem
            if alternatives and len(alternatives) >= 2:
                if isinstance(alternatives[1], list) and len(alternatives[1]) > 0:
                    return str(alternatives[1][0])

            # Fallback utama
            if isinstance(result_json, list) and len(result_json) > 0:
                main_data = result_json[0]
                if isinstance(main_data, list):
                    translated_parts = [str(part[0]) for part in main_data if isinstance(part, list) and len(part) > 0]
                    if translated_parts:
                        return "".join(translated_parts)
            return ""
        elif response.status_code == 429:
            return "ERR_LIMIT"
        else:
            return None
    except:
        return None

# --- PEMBERSIH INGGRIS DI HASIL AKHIR ---
def clean_english(text, target_lang):
    """
    Cari kata/kalimat berbahasa Inggris dalam hasil terjemahan,
    lalu terjemahkan ke target_lang dan ganti. Kembalikan teks bersih.
    """
    if not text or not isinstance(text, str):
        return text

    # Pola: karakter alfabet + spasi yang mungkin membentuk kata/frasa Inggris
    # Menangkap minimal 2 huruf biar tidak tertukar singkatan
    pattern = r'[A-Za-z]{2,}'
    matches = re.findall(pattern, text)
    if not matches:
        return text

    # Ganti setiap kata/kalimat Inggris unik agar tidak dobel request
    unique_words = list(set(matches))
    for word in unique_words:
        # Terjemahkan dari Inggris ke target
        translated = translate_core(word, target_lang, source='en')
        if translated and translated != "ERR_LIMIT" and translated != "":
            text = text.replace(word, translated)
    return text

# --- TRANSLATE TANPA CHUNKING (SIMPEL) ---
def translate_smart(text, target):
    """
    Terjemahkan seluruh teks, ambil alternatif ke-2,
    lalu bersihkan sisa kata Inggris.
    """
    result = translate_core(text, target, source='id')
    if result and result != "ERR_LIMIT":
        result = clean_english(result, target)
    return result

# --- ANTARMUKA STREAMLIT ---
st.set_page_config(page_title="Turbo Translator Pro v2", page_icon="⚡", layout="wide")

st.title("⚡ Turbo Excel Translator")
st.markdown("Alat translasi otomatis untuk file Excel buatan fadhil ganteng kece keren hebat slebew.  kalo gatau kodenya tanya gugel nulisnya gini 639-1 kode bahasa ..... bahasa mu ketiken. JANGAN LUPA DIKASIH LETI 1 BARIS DIATAS NYA")
st.markdown("PAKAILAH 1 TAB AJA JANGAN MULTI TAB WOYYYY RUSAK HOST E, NDAK TAK HOST NO MANEH WM")

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
                        elapsed = time.time() - start_time
                        avg_time = elapsed / completed
                        eta = int(avg_time * (total_rows - completed))

                        progress_bar.progress(completed / total_rows)
                        status_placeholder.write(f"⏳ Memproses: {completed}/{total_rows} baris")
                        time_placeholder.markdown(f"⏱️ Sisa waktu: **{eta} detik**")

                # Cleaning tahap akhir (memastikan bersih dari Inggris)
                # Ini sudah dilakukan di translate_smart, jadi aman
                df['Hasil Translate'] = results

                st.subheader("📋 Preview Hasil (5 Baris Pertama)")
                st.dataframe(df[['Hasil Translate']].head(5))

                nama_file_murni = uploaded_file.name.rsplit('.', 1)[0]
                nama_file_baru = f"{nama_file_murni} ({target_lang}).xlsx"

                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Sheet1')

                    workbook = writer.book
                    worksheet = writer.sheets['Sheet1']
                    red_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")

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
