# Screener Teknikal Saham IDX

Screener statis (GitHub Pages) dengan data harian otomatis (GitHub Actions).

## Struktur
- `index.html` — screener (semua indikator dihitung di browser)
- `universe.csv` — daftar saham, sektor, keanggotaan indeks (edit di sini)
- `scripts/fetch_data.py` — ambil OHLCV, market cap, hitung beta vs IHSG
- `.github/workflows/update-data.yml` — jadwal harian 17.30 WIB
- `data/screener.json` — dibuat otomatis oleh workflow
- `custom-indicators.json` — indikator kustom bersama (opsional)

## Pasang
1. Buat repo GitHub, unggah semua file ini (pertahankan struktur folder, termasuk `.github`).
2. Settings → Pages → Deploy from a branch → `main` / root.
3. Settings → Actions → General → Workflow permissions → **Read and write**.
4. Tab Actions → *Update data screener* → **Run workflow** (sekali, untuk membuat `data/screener.json`).
5. Buka `https://<username>.github.io/<repo>/`.

## Perlu diverifikasi
Sektor dan keanggotaan indeks di `universe.csv` adalah estimasi awal. Samakan dengan pengumuman resmi BEI, lalu perbarui setiap ada evaluasi indeks.

## Indikator TradingView
Buka **Indikator kustom** di halaman → Tambah → pilih contoh. Kode Pine bisa diterjemahkan ke JavaScript memakai fungsi `ta.*`.
Agar tampil untuk semua pengunjung: Ekspor JSON → unggah sebagai `custom-indicators.json` di root repo.
