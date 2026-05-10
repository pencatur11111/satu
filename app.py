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
# ARSENAL MAHRUS - BIAR GOOGLE TIDAK MARAH
# =============================================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
]

# Pengaturan backoff
MAX_RETRIES = 4
INITIAL_BACKOFF = 1.0        # detik
BACKOFF_FACTOR = 2.0

# =============================================
# FUNGSI INTI - DENGAN DELAY ACAK & RETRY
# =============================================
def translate_core(text, target, source='id', min_delay=0.1, max_delay=0.5):
    """
    Terjemahkan teks via Google Translate, ambil alternatif ke-2.
    """
    if not text or str(text).strip().lower() in ["nan", "none", ""]:
        return ""

    # Delay acak dulu (anti-burst)
    time.sleep(random.uniform(min_delay, max_delay))

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
                # Alternatif ke-2 (index 1 di list alternatif)
                alternatives = result_json[1] if len(result_json) > 1 else []
                if len(alternatives) >= 2:
                    return alternatives[1][0]
                # Fallback ke terjemahan utama
                if isinstance(result_json[0], list):
                    translated_parts = [part[0] for part in result_json[0] if part[0]]
                    return "".join(translated_parts)
                return ""
            elif response.status_code == 429:
                if attempt == MAX_RETRIES:
                    return "ERR_LIMIT"
                else:
                    # Exponential backoff dengan jitter
                    sleep_time = INITIAL_BACKOFF * (BACKOFF_FACTOR ** (attempt - 1))
                    sleep_time += random.uniform(0, 0.5)
                    time.sleep(sleep_time)
                    continue
            else:
                if attempt == MAX_RETRIES:
                    return None
                else:
                    time.sleep(INITIAL_BACKOFF * attempt)
                    continue
        except Exception:
            if attempt == MAX_RETRIES:
                return None
            else:
                time.sleep(INITIAL_BACKOFF * attempt)
                continue
    return None

def translate_smart(text, target, min_delay, max_delay):
    """Pecah teks panjang >4000 karakter menjadi chunk, lalu gabungkan."""
    text_str = str(text).strip()
    if len(text_str) <= 4000:
        return translate_core(text_str, target, min_delay, max_delay)

    chunks = [text_str[i:i+3800] for i in range(0, len(text_str), 3800)]
    results = []
    for chunk in chunks:
        res = translate_core(chunk, target, min_delay, max_delay)
        if res is None or res == "ERR_LIMIT":
            return res
        results.append(res)
    return " ".join(results)

# =============================================
# STREAMLIT UI – MAHRUS TURBO
# =============================================
st.set_page_config(page_title="Mahrus Turbo Translator", page_icon="🧞‍♂️", layout="wide")

# --- SIDEBAR DENGAN KLAIM MAHRUS ---
st.sidebar.markdown("<h1 style='text-align: center; color: gold;'>🧞‍♂️ KLAIM MAHRUS</h1>", unsafe_allow_html=True)
if st.sidebar.button("✨ Klik ✨"):
    st.balloons()
    st.sidebar.success("MAHRUS SUDAH DIRESTUI! GOOGLE TRANSLATE NURUT, LIMIT MENJAUH!")
    st.sidebar.markdown("> *\"UWU, HALO SAYANG....!\"*")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Pengaturan Kecepatan")
target_lang = st.sidebar.text_input("Kode Bahasa Tujuan", value="en", help="Contoh: en, ja, fi, ko, ar")

# Mode kecepatan (pilih worker + delay)
speed_mode = st.sidebar.selectbox("Pilih Mode Kecepatan", ["Aman (Anti Limit)", "Seimbang (Rekomendasi)", "Ngebut (Mahrus)"],
                                  index=1)
if speed_mode == "Aman (Anti Limit)":
    workers = 3
    min_d = 0.3
    max_d = 0.8
    st.sidebar.caption("Worker: 3 | Delay: 0.3–0.8 detik. Aman banget, lambat tapi pasti.")
elif speed_mode == "Seimbang (Rekomendasi)":
    workers = 6
    min_d = 0.1
    max_d = 0.4
    st.sidebar.caption("Worker: 6 | Delay: 0.1–0.4 detik. Cukup ngebut, relatif aman.")
else:
    workers = 8
    min_d = 0.05
    max_d = 0.2
    st.sidebar.caption("Worker: 8 | Delay: 0.05–0.2 detik. Ngebut! Hati-hati, bisa kena limit kalau Google galak.")

st.sidebar.markdown("---")
st.sidebar.warning("💡 **Pesan Mahrus:**\n"
                   "- Kalau banyak merah, ganti ke mode 'Aman'.\n"
                   "- Jangan tutup browser, biarkan bekerja.\n"
                   "- Laptop tetap dicolok charger, jangan tidur.\n"
                   "- Kalau 26rb baris, bisa 1-3 jam. Sabar ya ges.")

# --- BADAN UTAMA ---
st.title("🧞‍♂️ Mahrus Turbo Translator — Edisi Perang 26.000 Baris")
st.markdown(
    "Upload file Excel, **kolom B** akan diterjemahkan dengan **alternatif ke-2** ala Google Translate. "
    "Sudah dilengkapi delay acak & retry, cocok buat data banyak. Jangan lupa klaim dulu biar jos!"
)

uploaded_file = st.file_uploader("📂 Upload file Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        total_rows = len(df)
        st.success(f"✅ File '{uploaded_file.name}' terdeteksi: **{total_rows} baris**.")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Mode", speed_mode)
        with col2:
            estimasi_waktu_per_baris = min_d + (max_d - min_d)/2 + 0.5  # asumsi waktu request
            total_seconds = total_rows * estimasi_waktu_per_baris / workers
            jam = int(total_seconds // 3600)
            menit = int((total_seconds % 3600) // 60)
            st.metric("Estimasi Waktu", f"{jam} jam {menit} mnt" if jam > 0 else f"{menit} menit")

        if st.button("🚀 MULAI TERJEMAHKAN (TIDURKAN LAPTOP JANGAN)"):
            if df.shape[1] < 2:
                st.error("Kolom B tidak ditemukan. Harap letakkan teks di kolom kedua (B).")
            else:
                texts = df.iloc[:, 1].astype(str).tolist()
                results = [None] * total_rows

                progress_bar = st.progress(0)
                status_text = st.empty()
                time_text = st.empty()
                start_time = time.time()

                # Eksekusi multithread
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    future_to_idx = {
                        executor.submit(translate_smart, texts[i], target_lang, min_d, max_d): i
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

                        # Update UI tiap 50 baris agar tidak berat
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

                # Tambahkan kolom hasil
                df['Hasil Translate'] = results

                # Preview
                st.subheader("📋 Cuplikan Hasil (5 Baris Pertama)")
                st.dataframe(df[['Hasil Translate']].head(5))

                # Siapkan file unduh dengan pewarnaan Mahrus
                nama_bersih = uploaded_file.name.rsplit('.', 1)[0]
                nama_output = f"{nama_bersih}_MahrusTurbo_{target_lang}.xlsx"
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Sheet1')
                    workbook = writer.book
                    sheet = writer.sheets['Sheet1']
                    # Warna
                    merah_mahrus = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
                    hijau_mahrus = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")

                    for row_idx, hasil in enumerate(results, start=2):
                        if hasil is None or hasil == "ERR_LIMIT" or hasil == "":
                            for col in range(1, df.shape[1] + 1):
                                sheet.cell(row=row_idx, column=col).fill = merah_mahrus
                        else:
                            sheet.cell(row=row_idx, column=df.shape[1]).fill = hijau_mahrus

                st.success(f"✅ Perjuangan selesai! Nama file: **{nama_output}**")
                st.download_button(
                    label="📥 Download Hasil Terjemahan",
                    data=output.getvalue(),
                    file_name=nama_output,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    except Exception as e:
        st.error(f"❌ Error: {e}")
        st.info("Coba perkecil worker (mode Aman), periksa file Excel, atau istirahat sebentar.")
