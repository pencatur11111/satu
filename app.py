import streamlit as st
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
import time
import random
import urllib.parse
from openpyxl.styles import PatternFill

# =============================================
# ARSENAL MAHRUS (TANPA DELAY, RETRY HANYA SAAT LIMIT)
# =============================================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
]

MAX_RETRIES = 3
INITIAL_BACKOFF = 2.0    # detik (hanya dipakai kalau kena 429)
BACKOFF_FACTOR = 2.0

def translate_core(text, target, source='id'):
    """
    Request cepat ke Google Translate, ambil alternatif ke-2.
    Tidak ada delay buatan, hanya retry jika kena limit/error.
    """
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

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, headers=headers, timeout=12)
            if response.status_code == 200:
                result_json = response.json()
                # Alternatif ke-2
                alternatives = result_json[1] if len(result_json) > 1 else []
                if len(alternatives) >= 2:
                    return alternatives[1][0]
                # Fallback ke terjemahan utama
                if isinstance(result_json[0], list):
                    translated_parts = [part[0] for part in result_json[0] if part[0]]
                    return "".join(translated_parts)
                return ""
            elif response.status_code == 429:
                # Kena limit, baru tidur sebentar sebelum coba lagi
                if attempt < MAX_RETRIES:
                    sleep_time = INITIAL_BACKOFF * (BACKOFF_FACTOR ** (attempt - 1))
                    sleep_time += random.uniform(0, 1)
                    time.sleep(sleep_time)
                    continue
                else:
                    return "ERR_LIMIT"
            else:
                if attempt < MAX_RETRIES:
                    time.sleep(INITIAL_BACKOFF * attempt)
                    continue
                else:
                    return None
        except Exception:
            if attempt < MAX_RETRIES:
                time.sleep(INITIAL_BACKOFF * attempt)
                continue
            else:
                return None
    return None

def translate_smart(text, target):
    """Pecah teks panjang >4000 karakter, lalu gabung."""
    text_str = str(text).strip()
    if len(text_str) <= 4000:
        return translate_core(text_str, target)
    chunks = [text_str[i:i+3800] for i in range(0, len(text_str), 3800)]
    results = []
    for chunk in chunks:
        res = translate_core(chunk, target)
        if res is None or res == "ERR_LIMIT":
            return res
        results.append(res)
    return " ".join(results)

# =============================================
# TAMPILAN STREAMLIT
# =============================================
st.set_page_config(page_title="Mahrus Super Cepat", page_icon="🧞‍♂️", layout="wide")

# --- SIDEBAR ---
st.sidebar.markdown("<h1 style='text-align: center; color: gold;'>🧞‍♂️ KLAIM MAHRUS</h1>", unsafe_allow_html=True)
if st.sidebar.button("✨ Klik ✨"):
    st.balloons()
    st.sidebar.success("MAHRUS SUDAH DIRESTUI! GOOGLE TRANSLATE NURUT, LIMIT MENJAUH!")
    st.sidebar.markdown("> *\"UWU, HALO SAYANG....!\"*")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Pengaturan")
target_lang = st.sidebar.text_input("Kode Bahasa Tujuan", value="en", help="Contoh: en, ja, fi, ko, ar")
max_workers = st.sidebar.slider("Jumlah Worker (Pasukan Mahrus)", 1, 10, 8, help="8 itu paling jos, tapi kalau merah turunkan ke 6.")
st.sidebar.markdown("---")
st.sidebar.info("💡 **Tips Cepat:**\n"
                "- Tanpa delay buatan, langsung gas.\n"
                "- Kalau mulai banyak merah, kurangi worker.\n"
                "- Jangan tutup browser, biarkan menyala.")

# --- BADAN UTAMA ---
st.title("🧞‍♂️ Mahrus Super Cepat — Translator Tanpa Jeda")
st.markdown(
    "Upload file Excel, **kolom B** akan diterjemahkan dengan **alternatif ke‑2** ala Google Translate. "
    "**Tanpa delay**, hanya pakai retry saat kena limit. Langsung tancap gas!"
)

uploaded_file = st.file_uploader("📂 Upload file Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        total_rows = len(df)
        st.success(f"✅ File '{uploaded_file.name}' terdeteksi: **{total_rows} baris**.")

        if st.button("🚀 MULAI TERJEMAHKAN (GAS POLL)"):
            if df.shape[1] < 2:
                st.error("Kolom B tidak ditemukan. Harap letakkan teks di kolom kedua (B).")
            else:
                texts = df.iloc[:, 1].astype(str).tolist()
                results = [None] * total_rows

                progress_bar = st.progress(0)
                status_text = st.empty()
                time_text = st.empty()
                start_time = time.time()

                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_idx = {
                        executor.submit(translate_smart, texts[i], target_lang): i
                        for i in range(total_rows)
                    }
                    completed = 0
                    last_update = 0
                    for future in as_completed(future_to_idx):
                        idx = future_to_idx[future]
                        try:
                            results[idx] = future.result()
                        except:
                            results[idx] = None
                        completed += 1

                        if completed - last_update >= 50 or completed == total_rows:
                            last_update = completed
                            elapsed = time.time() - start_time
                            if completed > 0:
                                eta = (elapsed / completed) * (total_rows - completed)
                                eta_min = int(eta // 60)
                                eta_sec = int(eta % 60)
                                progress_bar.progress(completed / total_rows)
                                status_text.write(f"⏳ {completed}/{total_rows} baris selesai")
                                time_text.markdown(f"⏱️ Sisa: **{eta_min} mnt {eta_sec} dtk** | "
                                                   f"Kecepatan: **{completed/(elapsed/60):.1f} baris/menit**")

                df['Hasil Translate'] = results

                st.subheader("📋 Cuplikan Hasil (5 Baris Pertama)")
                st.dataframe(df[['Hasil Translate']].head(5))

                nama_bersih = uploaded_file.name.rsplit('.', 1)[0]
                nama_output = f"{nama_bersih}_MahrusSuperCepat_{target_lang}.xlsx"
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Sheet1')
                    workbook = writer.book
                    sheet = writer.sheets['Sheet1']
                    merah = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
                    hijau = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")

                    for row_idx, hasil in enumerate(results, start=2):
                        if hasil is None or hasil == "ERR_LIMIT" or hasil == "":
                            for col in range(1, df.shape[1] + 1):
                                sheet.cell(row=row_idx, column=col).fill = merah
                        else:
                            sheet.cell(row=row_idx, column=df.shape[1]).fill = hijau

                st.success(f"✅ Selesai! Nama file: **{nama_output}**")
                st.download_button(
                    label="📥 Download Hasil Terjemahan",
                    data=output.getvalue(),
                    file_name=nama_output,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    except Exception as e:
        st.error(f"❌ Error: {e}")
        st.info("Coba kurangi worker, periksa file, atau istirahat sebentar.")
