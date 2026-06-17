---
title: Penggunaan CLI
description: Panduan instalasi dan perintah utama alat ClickEye CLI.
order: 4
---

# Penggunaan CLI

ClickEye CLI adalah antarmuka baris perintah untuk pengguna tingkat lanjut. Alat ini berbagi mesin pembuatan yang sama dengan dasbor web.

## Instalasi

```bash
npm install -g @clickeye/cli
```

## Perintah Dasar

```bash
# Periksa versi
clickeye --version

# Bantuan
clickeye --help

# Masuk
clickeye login

# Buat solusi
clickeye create

# Daftar solusi
clickeye list
```

## Membuat Solusi

```bash
# Buat solusi dalam mode interaktif
clickeye create

# Tentukan opsi
clickeye create --platform claude-code --stack nextjs
```

## Berkas Konfigurasi

Konfigurasi CLI disimpan di `~/.clickeye/config.json`.

```json
{
  "apiUrl": "https://api.clickeye.io",
  "token": "your-api-token"
}
```

> Detail lebih lanjut akan diperbarui kemudian (24S-186).
