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

# --- PEMBERSIH INGGRIS OTOMATIS (RINGAN) ---
def clean_english_light(text, target_lang):
    """
    Cari kata bahasa Inggris (alfabet murni, >=3 huruf) di hasil,
    maksimal 5 kata unik per sel. Terjemahkan & ganti.
    """
    if not text or not isinstance(text, str):
        return text

    # Cari semua kata dengan huruf alfabet saja (termasuk apostrof internal)
    matches = re.findall(r'\b[A-Za-z]{3,}\b', text)
    if not matches:
        return text

    # Ambil maksimal 5 kata unik (diurutkan agar stabil)
    unique_words = list(dict.fromkeys(matches))[:5]

    for word in unique_words:
        translated = translate_core(word, target_lang, source='en')
        if translated and translated != "ERR_LIMIT" and translated != "":
            # Ganti hanya kata utuh (pakai word boundary)
            text = re.sub(r'\b' + re.escape(word) + r'\b', translated, text, count=1)
    return text

# --- TRANSLATE TANPA CHUNKING (SIMPEL + BERSIH OTOMATIS) ---
def translate_smart(text, target):
    result = translate_core(text, target, source='id')
    if result and result != "ERR_LIMIT":
        result = clean_english_light(result, target)   # selalu aktif
    return result

# --- ANTARMUKA STREAMLIT ---
st.set_page_config(page_title="Turbo Translator Pro v2", page_icon="⚡", layout="wide")

st.title("⚡ Turbo Excel Translator (Otomatis Bersih Inggris)")
st.markdown("Alat translasi otomatis untuk file Excel buatan fadhil ganteng kece keren hebat slebew.  kalo gatau kodenya tanya gugel nulisnya gini 639-1 kode bahasa ..... bahasa mu ketiken. JANGAN LUPA DIKASIH LETI 1 BARIS DIATAS NYA")
st.markdown("PAKAILAH 1 TAB AJA JANGAN MULTI TAB WOYYYY RUSAK HOST E, NDAK TAK HOST NO MANEH WM")

st.sidebar.header("⚙️ Pengaturan")
target_lang = st.sidebar.text_input("Kode Bahasa Tujuan", value="en", help="Contoh: en, ja, fi, ko, ar")
max_workers = st.sidebar.slider("Kecepatan (Workers)", 1, 15, 5, help="Disarankan 5-10 agar aman.")

st.sidebar.markdown("---")
st.sidebar.info("📌 **Catatan:**\nHasil sekarang otomatis bersih dari sisa kata Inggris seperti 'has been told'. "
                "Maksimal 5 kata unik dibersihkan per sel agar tetap cepat. "
                "Jika masih ada yang merah, kurangi Workers atau istirahat dulu.\n\n"
                "pesan untuk mahrus UWES RUS NEK GA KUAT 10 AE GAUSA MEKSO DIULEK ULEK KODENE SAMPE DADI 100!!!")

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
