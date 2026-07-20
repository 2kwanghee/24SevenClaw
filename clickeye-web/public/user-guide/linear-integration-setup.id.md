---
title: Konfigurasi Integrasi Linear
description: Panduan langkah demi langkah mulai dari pendaftaran kunci API Linear, konfigurasi Webhook, hingga alur DayQueued.
order: 5
---

# Konfigurasi Integrasi Linear

Atur keseluruhan alur ini: AI Team ClickEye mendaftarkan sub-task yang dihasilkannya sebagai isu Linear secara otomatis, dan ketika status isu berubah menjadi `Queued`, Claude Code lokal secara otomatis memulai pengembangan.

---

## Alur Keseluruhan

```
[ClickEye AI Team] Buat draf AI
         │ → Daftarkan isu Linear secara otomatis
         ▼
[Linear] Status isu → diubah ke Queued
         │
         ▼
[PC Lokal] Webhook diterima atau polling
         │
         ▼
[Claude Code] Jalankan pipeline pengembangan otomatis
```

---

## Step 1 — Menerbitkan Kunci API Linear

1. Akses [https://linear.app/settings/api](https://linear.app/settings/api)
2. Klik **Personal API keys → Create key**
3. Masukkan nama (mis. `ClickEye`)
4. Izin: **Full access** atau minimal `issues:write`
5. Salin kunci yang diterbitkan (`lin_api_...`)

---

## Step 2 — Memeriksa Team ID Linear

Anda memerlukan **Team ID** Linear. Periksa dengan salah satu cara berikut:

- Aplikasi Linear → klik kanan nama tim pada bilah sisi kiri → **Copy Team ID**
- Atau periksa di URL: `https://linear.app/{workspace}/team/{TEAM_ID}/issues`

---

## Step 3 — Menyimpan di Halaman Pengaturan ClickEye

1. Akses [Pengaturan ClickEye → Linear](https://app.24sevenclaw.com/settings/linear)
2. Masukkan item berikut:

| Field | Keterangan | Wajib |
|------|------|------|
| Linear API Key | Format `lin_api_...` | ✅ |
| Team ID | UUID tim tempat isu akan dibuat | ✅ |
| Webhook Secret | String acak untuk verifikasi tanda tangan HMAC | ⬜ |
| Tunnel URL | URL publik server webhook lokal | ⬜ |

3. Klik **Simpan**

> **Tips keamanan**: Untuk Webhook Secret, gunakan string acak yang kuat yang dihasilkan dengan `openssl rand -hex 32`.

> **Saat menyimpan Tunnel URL**: Server akan secara otomatis mendaftarkan Webhook ke workspace Linear Anda.

---

## Step 4 — Menyertakan Skill Linear di Proyek

Jika proyek yang dikirim dari konsol delivery menyertakan skill **Linear**, skrip integrasi Linear akan disediakan bersamanya.

Nilai-nilai berikut diperlukan dalam berkas `.env` proyek:

```bash
LINEAR_API_KEY=lin_api_xxxxxxxxxxxx
LINEAR_TEAM_ID=your-team-uuid
WEBHOOK_SECRET=your-webhook-secret
TUNNEL_PROVIDER=cloudflare   # cloudflare | ngrok | polling
```

---

## Step 5 — Memilih Metode Pelacakan Real-Time

### Metode A: Cloudflare Tunnel (Direkomendasikan)

Gratis dan menyediakan URL statis.

```bash
bash scripts/setup-tunnel.sh
```

Saat skrip dijalankan:
1. `cloudflared` terinstal secara otomatis (Homebrew / apt / snap)
2. Tunnel diaktifkan dan URL `https://xxxx.trycloudflare.com` diterbitkan
3. `WEBHOOK_PUBLIC_URL` pada `.env` diperbarui secara otomatis

Simpan URL yang diterbitkan ke field **Tunnel URL** pada [halaman pengaturan ClickEye](https://app.24sevenclaw.com/settings/linear).

> ⚠️ Jika Anda menutup jendela terminal ini, tunnel akan berhenti. Untuk menjalankannya di latar belakang: `nohup bash scripts/setup-tunnel.sh &`

### Metode B: ngrok

```bash
TUNNEL_PROVIDER=ngrok bash scripts/setup-tunnel.sh
```

- Paket gratis: URL berubah setiap kali dimulai ulang. Saat URL berubah, perlu disimpan ulang di halaman pengaturan
- URL tetap berbayar: Jika Anda mengatur `NGROK_AUTH_TOKEN` pada `.env`, autentikasi dilakukan otomatis

### Metode C: Polling 30 detik (Tanpa Tunnel)

Melakukan polling ke Linear setiap 30 detik tanpa Webhook. Cocok untuk lingkungan yang sulit menyiapkan tunnel.

```bash
python scripts/linear_watcher.py
```

Menjalankan di latar belakang:

```bash
python scripts/linear_watcher.py &
```

---

## Step 6 — Mengaktifkan Server Webhook Lokal (Metode Cloudflare/ngrok)

Jalankan di terminal baru:

```bash
bash scripts/start-webhook.sh
```

Pemeriksaan kesehatan (health check):

```bash
curl http://localhost:9876/health
# {"status":"ok","port":9876}
```

---

## Step 7 — Memverifikasi Alur DayQueued

Setelah semua konfigurasi selesai, pengembangan otomatis akan terpicu dengan alur berikut:

1. ClickEye AI Team → klik **Hasilkan Draf AI**
2. Isu didaftarkan secara otomatis ke Linear (mis. `24S-123`)
3. Di Linear, ubah status isu menjadi **Queued** (atau `DayQueued`, `NightQueued`)
4. Di lingkungan lokal, pipeline berjalan secara otomatis:

   - **Mode Webhook**: Periksa di terminal `start-webhook.sh`
     ```
     [ClickEye] Linear webhook diterima: isu 24S-123 → Queued
     [ClickEye] Pipeline pengembangan otomatis dipicu
     ```
   - **Mode Polling**: Periksa di terminal `linear_watcher.py`
     ```
     [watcher] Isu ditemukan: 24S-123 (Queued) → menjalankan pipeline
     ```

---

## Pemecahan Masalah

| Gejala | Penyebab | Cara Mengatasi |
|------|------|----------|
| Banner "Kredensial Linear tidak ada" | Kunci API belum disimpan | Simpan kunci API di halaman pengaturan |
| Pembuatan isu Linear gagal | Kunci API kedaluwarsa atau izin kurang | Terbitkan kunci baru lalu simpan ulang |
| Tidak ada penerimaan Webhook | Tunnel URL tidak cocok | Simpan ulang Tunnel URL saat ini di halaman pengaturan |
| Verifikasi tanda tangan gagal (401) | Webhook Secret tidak cocok | Pastikan Secret pada `.env` dan halaman pengaturan sama |
| Instalasi `cloudflared` gagal | Masalah koneksi internet atau izin | [Panduan instalasi manual](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) |
| URL ngrok berubah | Mulai ulang paket gratis | Simpan ulang URL baru di halaman pengaturan atau gunakan paket berbayar |
| Polling tidak mendeteksi isu | Galat `LINEAR_TEAM_ID` | Pastikan TEAM_ID pada `.env` benar dengan memeriksanya di Linear |

---

## Daftar Periksa Keamanan

- [ ] Apakah kunci API Linear hanya ada di `.env` dan tidak ter-commit ke Git? (periksa `.gitignore`)
- [ ] Apakah Webhook Secret cukup kuat? (`openssl rand -hex 32` direkomendasikan)
- [ ] Apakah `start-webhook.sh` hanya menerima dari localhost? (port 9876 tidak perlu diekspos ke luar)
- [ ] Apakah tunnel Cloudflare/ngrok hanya mengekspos port 9876?

---

## Panduan Terkait

- [Memulai](/guide/getting-started) — Alur dasar konsol delivery ClickEye
- [Pengelolaan AI Team](/guide/ai-team-management) — Menghasilkan draf AI dan memeriksa isu Linear
