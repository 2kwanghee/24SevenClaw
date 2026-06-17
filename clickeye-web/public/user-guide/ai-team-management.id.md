---
title: Pengelolaan AI Team
description: Panduan cara meminta tugas, menghasilkan draf AI, dan menyinkronkan dengan Linear di dasbor AI Team.
order: 4
---

# Pengelolaan AI Team

Dasbor AI Team adalah sistem 3 lapis untuk mengorkestrasikan tim AI agent proyek Anda.

---

## Cara Mengakses Dasbor

1. Web ClickEye → pilih proyek dari daftar proyek
2. Halaman detail proyek → klik **AI Team** pada bilah sisi kiri atau tab bagian atas
3. URL: `/projects/{projectId}/ai-team`

---

## Memahami Struktur 3 Lapis

| Lapis | Penanggung Jawab | Peran |
|------|-------|------|
| **Lapis 1 — Manusia** | Pengguna | Permintaan tugas, persetujuan tahap, keputusan akhir |
| **Lapis 2 — PM AI** | AI | Penguraian tugas, pembuatan draf, koordinasi peninjauan, menjalankan pipeline 10 tahap |
| **Lapis 3 — AI Team** | Para AI agent | Eksekusi paralel sub-task |

---

## Meminta Tugas Pertama

Jika belum ada sesi, tombol **Minta Tugas Pertama** akan ditampilkan di tengah layar.

1. Klik **Minta Tugas Pertama** (atau **Permintaan Tugas Baru** di header)
2. Masukkan judul dan deskripsi tugas pada modal
3. Klik **Buat** → sesi dibuat dengan status `requested`

### Mengelola Beberapa Sesi

Anda dapat beralih antarsesi melalui tab di bagian atas. Setiap tab menampilkan judul sesi dan tahap saat ini.

---

## Alur Tahap (Phase)

| Tahap | Keterangan | Aksi Pengguna |
|------|------|-----------|
| requested | Tugas diminta | — |
| decomposed | Sub-task diuraikan | — |
| assigned | Ditugaskan ke PM | Klik tombol **Hasilkan Draf AI** |
| drafting | Draf AI sedang ditulis | — |
| reviewing | Sedang ditinjau | — |
| integrating | Sedang diintegrasikan | — |
| validating | Sedang divalidasi | Klik tombol **Setujui** |
| approved | Disetujui | — |
| transitioning | Sedang bertransisi | — |
| completed | Selesai | — |

---

## Menghasilkan Draf AI

Saat tahap sesi menjadi `assigned`, tombol **Hasilkan Draf AI** akan aktif.

1. Klik tombol **Hasilkan Draf AI**
2. AI secara otomatis menjalankan dua pekerjaan secara berurutan:
   - ① Pembuatan draf sub-task (menguraikan tugas menjadi satuan-satuan kecil)
   - ② Pendaftaran otomatis isu Linear (jika kredensial Linear telah disimpan)

### Layar Setelah Draf AI Dihasilkan

- **Ronde peninjauan**: Draf yang ditulis AI ditampilkan
- **Petunjuk sinkronisasi Linear**: Daftar isu Linear yang terdaftar ditampilkan

---

## Petunjuk Sinkronisasi Linear

Jika pembuatan draf AI berhasil, panel "Sinkronisasi Linear" akan muncul.

### Saat Pendaftaran Otomatis Isu Berhasil

```
✓ Isu Linear berhasil dibuat: 24S-123, 24S-124, 24S-125
```

Anda dapat memeriksa ID isu yang terdaftar (mis. `24S-123`) di Linear.

### Saat Kredensial Linear Belum Disimpan

```
Kredensial Linear tidak ditemukan. Simpan kunci API Anda di pengaturan →
```

Dalam hal ini, simpan terlebih dahulu kunci API Anda dengan merujuk pada [Panduan Konfigurasi Integrasi Linear](/guide/linear-integration-setup).

---

## Penugasan Peran (Pemeriksaan Sub-task)

Periksa setiap kartu sub-task di bagian AI Team (Lapis 3).

Setiap kartu sub-task menampilkan informasi berikut:

- **Peran**: Peran agent penanggung jawab (mis. backend, frontend, devops)
- **Judul**: Nama sub-task
- **Ringkasan draf**: Ikhtisar pekerjaan yang ditulis AI

Sub-task diperbarui secara otomatis setiap 30 detik.

---

## Persetujuan Akhir

Saat PM AI menyelesaikan pekerjaan dan mencapai tahap validasi (`validating`), tombol **Setujui** akan aktif.

1. Periksa isi draf AI pada ronde peninjauan.
2. Jika tidak ada masalah, klik tombol **Setujui**.
3. Sesi bertransisi secara berurutan dari `approved` → `completed`.

---

## Penanda Risiko

Jika terdeteksi potensi masalah pada sesi, penanda risiko akan ditampilkan di bagian atas.

| Penanda | Arti |
|-------|------|
| Kompleksitas tinggi | Cakupan pekerjaan terlalu luas |
| Konflik dependensi | Masalah relasi dependensi antar sub-task |
| Kunci belum diatur | Kunci API wajib tidak tersedia |

---

## Penyegaran dan Pembaruan Real-Time

- **Tombol Segarkan**: Memperbarui daftar sesi dan ringkasan sesi saat ini secara manual.
- **Bagian AI Team**: Diperbarui secara otomatis setiap 30 detik.

---

## Pertanyaan yang Sering Diajukan

**T. Apa yang terjadi jika saya mengeklik Hasilkan Draf AI beberapa kali?**
J. Jika draf sudah ada, draf tersebut tidak akan ditimpa. Tombol hanya aktif pada tahap `assigned`.

**T. Pendaftaran isu Linear gagal, bagaimana cara mencobanya lagi?**
J. Simpan kunci API Anda di [halaman pengaturan](/settings/linear), lalu segarkan halaman AI Team. Pendaftaran isu akan dicoba ulang saat draf AI dihasilkan.

**T. Bisakah saya menghapus sesi?**
J. Saat ini UI tidak menyediakan fitur penghapusan sesi. Anda dapat menambahkan sesi baru kapan saja.
