# Screener Teknikal Saham IDX

Screener statis (GitHub Pages) dengan data harian otomatis (GitHub Actions).

## Struktur
- `index.html` — screener (indikator dihitung di browser)
- `universe.csv` — daftar saham, sektor, keanggotaan indeks
- `scripts/fetch_data.py` — ambil OHLCV, market cap, beta vs IHSG
- `.github/workflows/update-data.yml` — jadwal harian 17.30 WIB
- `data/screener.json` — dibuat otomatis oleh workflow
- `custom-indicators.json` — indikator kustom bersama (opsional)

## Pasang
1. Pastikan file screener tersedia di root repo.
2. Settings → Pages → Deploy from a branch → `main` / root.
3. Settings → Actions → General → Workflow permissions → **Read and write**.
4. Actions → **Update data screener** → **Run workflow** sekali.

## Catatan data
OHLCV berasal dari Yahoo Finance melalui yfinance. Beta dihitung terhadap IHSG (`^JKSE`) dari return harian 252 observasi terakhir yang tersedia. Market cap diambil dari Yahoo Finance jika tersedia. Universe dan keanggotaan indeks mengikuti `universe.csv` dan tetap perlu diverifikasi terhadap sumber resmi BEI.
