---
title: Wizard Solusi 7-Step
description: Panduan item input, contoh, dan kesalahan umum pada tiap langkah wizard 7-Step.
order: 3
---

# Cara Menggunakan Wizard Solusi 7-Step

Wizard ClickEye terdiri dari total 10 layar, dan 2 di antaranya diproses secara otomatis oleh AI. Layar yang Anda isi/pilih sendiri berjumlah 8.

---

## Alur Keseluruhan

```
Step 1. Masukkan informasi perusahaan
   ↓ (klik Berikutnya)
[AI Otomatis] Buat prototipe solusi (~30 dtk)
   ↓
Step 2. Pilih prototipe
   ↓ (klik Berikutnya)
[AI Otomatis] Analisis rekomendasi PM (~10 dtk)
   ↓
Step 3. Pilih PM
   ↓
Step 4. Tinjau konfigurasi PM
   ↓
Step 5. Konfigurasikan agen & skill
   ↓
Step 6. Pilih platform
   ↓
Step 7. Masukkan variabel lingkungan
   ↓
Step 8. Tinjauan akhir & pembuatan proyek
```

---

## Step 1 — Informasi Perusahaan & Kebutuhan Solusi

Pada tahap ini, AI memahami konteks perusahaan dan kebutuhan Anda untuk merancang solusi.

### Item Input

| Item | Wajib | Batas | Keterangan |
|------|------|------|------|
| Nama perusahaan | ✅ | 200 karakter | Nama perusahaan atau tim |
| Skala perusahaan | ✅ | pilihan | Startup (1–10 orang) / Usaha kecil (11–50 orang) / UKM (51–200 orang) / Perusahaan menengah (201–1.000 orang) / Perusahaan besar (1.000+ orang) |
| Industri | ✅ | pilihan | IT, Keuangan/Fintech, E-commerce, Kesehatan, Pendidikan, Manufaktur, Logistik, Pemasaran, Game, Lainnya |
| Tech stack | ⬜ | pilihan ganda | Python, TypeScript, React, Next.js, FastAPI, Docker, dll. (dapat dipilih lebih dari satu) |
| Produk/layanan utama | ✅ | 500 karakter | Produk atau layanan yang sedang dijual/dioperasikan perusahaan saat ini |
| Jenis bisnis | ✅ | pilihan | B2B / B2C / B2B2C / Alat internal |
| Deskripsi perusahaan | ⬜ | 1.000 karakter | Konteks tambahan seperti susunan tim, tingkat pengembangan, masalah saat ini |
| Deskripsi solusi yang dibutuhkan | ✅ | minimal 50 / maksimal 2.000 karakter | **Item yang paling utama dijadikan acuan oleh AI** |

### Contoh Penulisan

**Cara menulis deskripsi solusi yang dibutuhkan dengan baik:**

```
✅ Contoh yang baik:
Kami ingin mengotomatiskan pertanyaan pelanggan yang saat ini kami kelola di Excel.
Tim penjualan kami yang terdiri dari 8 orang menangani lebih dari 100 pertanyaan per hari. Kami ingin balasan otomatis untuk
pertanyaan yang berulang, dan notifikasi Slack untuk kasus mendesak.
Akan lebih baik lagi jika terintegrasi dengan CRM kami.

❌ Contoh yang buruk:
Kami membutuhkan otomatisasi AI.
```

### Kesalahan Umum

- **Menulis deskripsi solusi terlalu singkat**: Jika kurang dari minimal 50 karakter, tombol "Berikutnya" tidak akan aktif. Tuliskan alur kerja yang spesifik dan hasil yang Anda inginkan.
- **Tidak memilih tech stack**: Anda tetap bisa melanjutkan tanpa memilihnya, tetapi jika Anda memilih teknologi yang sedang digunakan tim Anda, AI akan merancang solusi yang lebih sesuai.
- **Mengabaikan deskripsi perusahaan**: Meskipun bukan item wajib, jika Anda menuliskan skala tim, tingkat teknis saat ini, dan kendala-kendala yang ada, prototipe yang dihasilkan akan jauh lebih akurat.

---

## [AI Otomatis] Pembuatan Prototipe Solusi

Saat Anda menekan tombol "Berikutnya", AI secara otomatis menghasilkan 3 prototipe solusi. Proses ini memakan waktu sekitar 30 detik. Pada layar ini, Anda tidak perlu memberikan input apa pun.

---

## Step 2 — Pemilihan Prototipe

Pilih satu dari 3 kandidat solusi yang dihasilkan AI yang paling cocok dengan arah proyek Anda.

### Cara Membaca Kartu

Setiap kartu prototipe menampilkan informasi berikut:

- **Nama**: Sebutan solusi
- **Tipe**: SaaS / REST API / Full-stack / Alat internal / MVP / Custom
- **Deskripsi**: Ikhtisar solusi

### Kesalahan Umum

- **Memilih "yang terlihat paling mahal"**: Solusi yang kompleks tidak selalu yang terbaik. Pilihlah yang sesuai dengan skala tim dan tingkat teknis Anda.
- **Jika tidak ada yang Anda sukai**: Kembalilah ke langkah sebelumnya, tuliskan kebutuhan solusi secara lebih spesifik, lalu hasilkan ulang.

---

## [AI Otomatis] Analisis Rekomendasi PM

Setelah Anda memilih prototipe, AI menganalisis daftar PM (Project Manager AI) yang dioptimalkan untuk solusi tersebut. Proses ini memakan waktu sekitar 10 detik.

---

## Step 3 — Pemilihan PM

Pilih PM AI yang akan memimpin proyek dari daftar PM yang direkomendasikan AI.

### Cara Membaca Kartu PM

| Item | Keterangan |
|------|------|
| Avatar & nama | Profil PM |
| Domain | Bidang yang menjadi keahlian PM |
| Tingkat kecocokan (%) | Kesesuaian dengan prototipe yang Anda pilih |
| Alasan rekomendasi | Dasar analisis AI |
| Tingkat keberhasilan / Proyek selesai / Rata-rata penilaian | Indikator kinerja |

### Kesalahan Umum

- **Memilih hanya berdasarkan tingkat kecocokan**: Periksa juga apakah domainnya sesuai dengan industri proyek Anda.
- **Melanjutkan tanpa memilih**: Pemilihan PM bersifat wajib. Jika tidak dipilih, tombol "Berikutnya" akan nonaktif.

---

## Step 4 — Verifikasi Konfigurasi PM

Tahap ini untuk memeriksa sub-agent dan skill apa saja yang menyusun PM yang Anda pilih. Anda boleh hanya memeriksanya tanpa perubahan, lalu melanjutkan ke langkah berikutnya.

---

## Step 5 — Pengaturan Agent & Skill

Agent dasar telah dipilih berdasarkan konfigurasi PM. Anda dapat menambah atau menghapusnya sesuai kebutuhan.

### Agent

Setiap AI agent menangani peran tertentu (penulisan kode, pengujian, dokumentasi, dll.). Disarankan untuk mempertahankan item yang dipilih secara default.

### Skill Integrasi (Opsional)

Skill adalah fitur integrasi dengan layanan eksternal.

| Skill | Keterangan | Perlu Konfigurasi Tambahan |
|------|------|--------------|
| linear | Integrasi pelacakan isu Linear | ✅ LINEAR_API_KEY, LINEAR_TEAM_ID |
| slack | Pengiriman notifikasi Slack | ✅ SLACK_WEBHOOK_URL |
| github | Pembuatan PR GitHub otomatis | ✅ GITHUB_TOKEN |

> **Saat memilih skill Linear**: Pada Step 7 (variabel lingkungan), `LINEAR_API_KEY` dan `LINEAR_TEAM_ID` akan ditambahkan sebagai item wajib. Lihat [Panduan Konfigurasi Integrasi Linear](/guide/linear-integration-setup).

### Kesalahan Umum

- **Menambahkan skill yang tidak diperlukan**: Jika Anda menambahkan skill, kunci API terkait juga wajib diisi. Jangan menambahkan skill untuk layanan yang tidak akan Anda gunakan.

---

## Step 6 — Pemilihan Platform

Pilih platform AI agent yang akan menjalankan ZIP yang telah diunduh.

| Platform | Direkomendasikan untuk | Catatan |
|--------|----------|------|
| **Claude Code** ⭐ | Sebagian besar pengguna | Agent koding AI dari Anthropic, paling baik didukung |
| Gemini CLI | Pengguna ekosistem Google | Berbasis Google Gemini |
| Cursor | Penggemar editor kode AI | Editor berbasis VS Code |
| Codex | Pengguna OpenAI | Berbasis OpenAI Codex |

### Kesalahan Umum

- **Memilih Claude Code tanpa memiliki ANTHROPIC_API_KEY**: Jika Anda memilih Claude Code, Anda wajib memasukkan kunci API Anthropic pada Step 7. Terbitkan terlebih dahulu di [console.anthropic.com](https://console.anthropic.com).

---

## Step 7 — Pengaturan Variabel Lingkungan

Masukkan kunci API dan variabel lingkungan yang diperlukan untuk menjalankan solusi. Nilai yang Anda masukkan di sini akan disimpan dalam berkas `.env` di dalam berkas ZIP.

### Kunci API Wajib

| Kunci | Status Wajib | Tempat Penerbitan |
|----|----------|-------|
| `ANTHROPIC_API_KEY` | Selalu wajib | [console.anthropic.com](https://console.anthropic.com) |
| `LINEAR_API_KEY` | Saat skill Linear dipilih | [linear.app/settings/api](https://linear.app/settings/api) |
| `LINEAR_TEAM_ID` | Saat skill Linear dipilih | Lihat di URL tim Linear |

### Saat Memilih Skill Linear — Metode Pelacakan Real-Time

| Metode | Biaya | Karakteristik | Direkomendasikan untuk |
|------|------|------|----------|
| **Cloudflare Tunnel** ⭐ | Gratis | URL statis, perlu menjaga terminal tetap berjalan | Sebagian besar pengguna |
| ngrok | Berbayar $8/bln (tetap) / Gratis (sementara) | URL berubah saat dimulai ulang (gratis) | Pemilik akun ngrok |
| Polling 30 detik | Gratis | Tidak perlu webhook, jeda maksimal 30 detik | Jika sulit menyiapkan tunnel |

### Cara Menambahkan Variabel Lingkungan

1. Pada bagian **Tambah Variabel Lingkungan** di bagian bawah layar, masukkan nama kunci (`KEY_NAME`) dan nilainya.
2. Klik tombol **+** atau tekan tombol Enter.
3. Jika Anda ingin mengisi nilainya nanti, ubah langsung berkas `.env` setelah mengekstrak ZIP.

### Kesalahan Umum

- **Melanjutkan tanpa mengisi `ANTHROPIC_API_KEY`**: Anda tetap dapat berpindah ke langkah berikutnya meskipun kunci wajib belum diatur, tetapi akan terjadi galat saat ZIP dijalankan. **Pastikan mengisinya sebelum melanjutkan.**
- **Membagikan berkas ZIP**: Berkas `.env` berisi kunci yang sebenarnya. Jangan membagikan berkas ZIP kepada orang lain.
- **Memilih metode Cloudflare dengan paket gratis ngrok**: URL akan berubah saat dimulai ulang sehingga webhook menjadi tidak valid. Anda harus menyimpan ulang URL di halaman pengaturan ClickEye.

---

## Step 8 — Verifikasi Akhir & Pembuatan Proyek

Menampilkan ringkasan dari semua konfigurasi yang telah Anda masukkan sejauh ini. Jika tidak ada masalah, klik tombol **Buat Proyek**.

### Item yang Diperiksa

- Nama perusahaan / Jenis bisnis / Produk utama
- Nama & tipe prototipe yang dipilih
- PM yang dipilih
- Daftar agent & skill
- Platform
- Jumlah variabel lingkungan yang diatur

### Setelah Membuat Proyek

1. Tombol unduh berkas ZIP akan ditampilkan.
2. Ekstrak ZIP dan jalankan platform yang Anda pilih (Claude Code, dll.).
3. Pengembangan AI pun dimulai.

---

## Pertanyaan yang Sering Diajukan

**T. Apakah AI akan menghasilkan ulang jika saya kembali ke langkah sebelumnya?**
J. Prototipe hanya dihasilkan ulang saat informasi perusahaan (Step 1) diubah. Langkah lainnya tidak akan menghasilkan ulang meskipun Anda kembali ke langkah sebelumnya.

**T. Apa yang terjadi jika saya menutup wizard di tengah jalan?**
J. Isian Anda tetap tersimpan selama sesi browser dipertahankan. Jika Anda menutup browser sepenuhnya, Anda harus memulai dari awal lagi.

**T. Berkas apa saja yang ada di dalam ZIP yang dihasilkan?**
J. ZIP berisi berkas konfigurasi yang sesuai dengan platform yang Anda pilih (`.claude/`, `.gemini/`, dll.), `.env`, `CLAUDE.md`, `README.md`, dan lainnya.
