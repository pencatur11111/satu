import streamlit as st
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
import time
import random
import urllib.parse
from openpyxl.styles import PatternFill, Font, Alignment

# =============================================
# KONFIGURASI MAHRUS - AGAR TIDAK MUDAH LIMIT
# =============================================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
]

MAX_RETRIES = 3          # kalau gagal/timeout, ulangi sampai 3x
BACKOFF_FACTOR = 2       # jeda makin panjang tiap retry
INITIAL_BACKOFF = 1.5    # detik

# =============================================
# FUNGSI ANTI LIMIT & ALTERNATIF 2 (MAHRUS MODE)
# =============================================
def translate_core(text, target, source='id', retries=MAX_RETRIES):
    """Request ke Google Translate, pilih alternatif ke-2 jika tersedia,
       dilengkapi mekanisme retry & backoff untuk hadapi limit."""
    if not text or str(text).strip().lower() in ["nan", "none", ""]:
        return ""

    headers = {"User-Agent": random.choice(USER_AGENTS)}
    base_url = "https://translate.googleapis.com/translate_a/single"

    # Bangun URL manual agar dt=t dan dt=at PASTI terkirim
    query_params = {
        "client": "gtx",
        "sl": source,
        "tl": target,
        "q": str(text).strip()
    }
    url = f"{base_url}?{urllib.parse.urlencode(query_params)}&dt=t&dt=at"

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                result_json = response.json()
                # Cari alternatif ke-2 (index 1 di list alternatif)
                alternatives = result_json[1] if len(result_json) > 1 else []
                if len(alternatives) >= 2:
                    return alternatives[1][0]   # INI ALTERNATIF KE-2, SESUAI PERMINTAAN

                # Fallback ke terjemahan utama jika alternatif tidak cukup
                if isinstance(result_json[0], list):
                    translated_parts = [part[0] for part in result_json[0] if part[0]]
                    return "".join(translated_parts)
                return ""

            elif response.status_code == 429:
                if attempt == retries:
                    return "ERR_LIMIT"   # sudah mentok, kasih kode error
                else:
                    sleep_time = INITIAL_BACKOFF * (BACKOFF_FACTOR ** (attempt - 1))
                    time.sleep(sleep_time)
                    continue
            else:
                # error lain (500, 403, dll)
                if attempt == retries:
                    return None
                else:
                    time.sleep(INITIAL_BACKOFF * attempt)
                    continue

        except Exception:
            if attempt == retries:
                return None
            else:
                time.sleep(INITIAL_BACKOFF * attempt)
                continue

    return None

def translate_smart(text, target):
    """Pintar: jika teks super panjang (>4000 karakter), pecah jadi beberapa
       bagian lalu gabung lagi, biar tidak ditolak Google karena URL kepanjangan."""
    text_str = str(text).strip()
    if len(text_str) <= 4000:
        return translate_core(text_str, target)

    # Pecah per 3800 karakter (aman dari batas URL)
    chunks = [text_str[i:i+3800] for i in range(0, len(text_str), 3800)]
    translated_chunks = []
    for chunk in chunks:
        res = translate_core(chunk, target)
        if res is None or res == "ERR_LIMIT":
            return res   # hentikan jika ada error
        translated_chunks.append(res)
    return " ".join(translated_chunks)

# =============================================
# TAMPILAN STREAMLIT - EDISI KLAIM MAHRUS
# =============================================
st.set_page_config(page_title="Translator Sakti Mahrus", page_icon="🧞‍♂️", layout="wide")

# --- KLAIM MAHRUS DI SIDEBAR ---
st.sidebar.markdown("<h1 style='text-align: center; color: gold;'>🧞‍♂️ KLAIM MAHRUS</h1>", unsafe_allow_html=True)
if st.sidebar.button("✨ Klik untuk Klaim Mahrus ✨"):
    st.balloons()
    st.sidebar.success("MAHRUS SUDAH DIRESTUI! GOOGLE TRANSLATE NURUT, LIMIT MENJAUH, HASIL MANTAP!")
    st.sidebar.markdown("> *\"Wleeeee...\"* — Mahrus")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Setelan Dewa")
target_lang = st.sidebar.text_input("Kode Bahasa Tujuan", value="en", help="Contoh: en, ja, fi, ko, ar. Lihat kode ISO 639-1.")
max_workers = st.sidebar.slider("Jumlah Worker (Pasukan Mahrus)", 1, 10, 5,
                                help="MAHRUS bilang: 5-8 aja, jangan serakah. 10 maksimal.")

st.sidebar.markdown("---")
st.sidebar.info("💡 **Kutipan Mahrus:**\n"
                "- *\"Baris merah? Turunin worker, sholat dulu.*\"\n"
                "- *\"Klaim dulu biar jos, jangan lupa baca bismillah.*\"\n"
                "- *\"Alternatif ke-2 itu bukti kemewahan, hasilnya lebih dalem.*\"")

# --- JUDUL UTAMA ---
st.title("🧞‍♂️ Translator Excel Super Mahrus — Edisi Canggih Anti Limit")
st.markdown(
    "Masukkan file Excel, **kolom B** akan diterjemahkan pakai **alternatif ke-2** ala Google Translate. "
    "Cocok buat 26.000 baris teks panjang, asal klaim Mahrus dulu ya 😎"
)

# --- UPLOAD FILE ---
uploaded_file = st.file_uploader("📂 Upload file Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        st.success(f"✅ File '{uploaded_file.name}' siap digempur! Total {len(df)} baris.")

        if st.button("🚀 MULAI TERJEMAHKAN (INI PERJUANGAN MAHRUS)"):
            if df.shape[1] < 2:
                st.error("Kolom B (kolom kedua) tidak ditemukan. Pastikan data ada di kolom B ya.")
            else:
                texts = df.iloc[:, 1].astype(str).tolist()
                total = len(texts)
                results = [None] * total

                # Progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                time_text = st.empty()
                start_time = time.time()

                # Thread pool dengan max_workers dari slider
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_idx = {executor.submit(translate_smart, texts[i], target_lang): i for i in range(total)}
                    completed = 0
                    for future in as_completed(future_to_idx):
                        idx = future_to_idx[future]
                        try:
                            results[idx] = future.result()
                        except:
                            results[idx] = None
                        completed += 1

                        # Update progress & estimasi
                        elapsed = time.time() - start_time
                        if completed > 0:
                            eta = (elapsed / completed) * (total - completed)
                            status_text.write(f"⏳ {completed}/{total} baris selesai")
                            time_text.markdown(f"⏱️ Estimasi sisa: **{int(eta//60)} menit {int(eta%60)} detik**")
                        progress_bar.progress(completed / total)

                # Tambahkan kolom hasil
                df['Hasil Translate'] = results

                # --- PREVIEW 5 BARIS PERTAMA ---
                st.subheader("📋 Cuplikan Hasil (5 Baris Pertama)")
                st.dataframe(df[['Hasil Translate']].head(5))

                # --- GENERASI FILE DENGAN WARNA KREASI MAHRUS ---
                nama_bersih = uploaded_file.name.rsplit('.', 1)[0]
                nama_output = f"{nama_bersih}_Mahrus_{target_lang}.xlsx"

                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Sheet1')
                    workbook = writer.book
                    sheet = writer.sheets['Sheet1']

                    # Warna merah muda untuk error
                    merah_mahrus = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
                    # Warna emas kehijauan untuk sukses (biar tambah canggih)
                    emas_mahrus = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")

                    for row_idx, hasil in enumerate(results, start=2):
                        if hasil is None or hasil == "ERR_LIMIT" or hasil == "":
                            # baris error -> merah di semua kolom
                            for col in range(1, df.shape[1] + 1):
                                sheet.cell(row=row_idx, column=col).fill = merah_mahrus
                        else:
                            # baris sukses -> emas kehijauan biar sumringah
                            sheet.cell(row=row_idx, column=df.shape[1]).fill = emas_mahrus

                st.success(f"✅ Perjuangan selesai! Nama file: **{nama_output}**")
                st.download_button(
                    label="📥 Download Hasil Terjemahan",
                    data=output.getvalue(),
                    file_name=nama_output,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    except Exception as e:
        st.error(f"❌ Ada kesalahan teknis: {e}")
        st.info("Coba:\n- Pastikan file tidak corrupt\n- Kurangi worker\n- Istirahat sejenak (biar IP gak diblokir)")
