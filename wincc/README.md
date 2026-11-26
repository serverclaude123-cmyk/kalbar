# SCADA KALBAR – WinCC RT Professional (TIA Portal V19)

SCADA utama panel KALBAR dibangun di **WinCC RT Professional V19**. Project-nya adalah TIA `Project2` dengan perangkat `SCADAPC [WinCC RT Professional]`, yang jalan di PC SCADAPC (192.168.1.64). Folder `scada/` (FUXA) hanya untuk uji dan cadangan.

## Isi folder

| File | Fungsi |
|---|---|
| `make_tags_xlsx.ps1` | Membuat `KALBAR_tags.xlsx` dari `../plc/KB_HMI_tags.csv`. Isinya 80 HMI tag di tabel `KALBAR`, koneksi `Connection_1`, dengan linear scaling 0–10000 → 0–100 untuk satuan x0,01. |
| `make_alarms_xlsx.ps1` | Membuat `KALBAR_alarms.xlsx` dari `../plc/KB_HMI_alarms.csv`. Isinya 20 discrete alarm (kelas Errors) dengan trigger `ALMW0`/`ALMW1` (= `%MW200`/`%MW201`, cermin `%M200..231`). |
| `KALBAR_tags.xlsx`, `KALBAR_alarms.xlsx` | File impor yang sudah dibuat dari script di atas. |
| `HMITags_sample.xlsx`, `HMIAlarms.xlsx` | Template hasil export TIA V19, dipakai oleh kedua generator. |
| `read_xlsx.ps1` | Menampilkan isi xlsx tanpa perlu Excel, berguna untuk mengecek hasil generator. |

Generate ulang kedua file setiap kali daftar tag atau alarm PLC berubah:

```powershell
.\make_tags_xlsx.ps1
.\make_alarms_xlsx.ps1
```

## Koneksi PLC

Connection_1 memakai driver **Modicon Modbus TCP/IP** dengan setelan berikut:

- CPU type: *Unity, PL7, Premium, Micro, Quantum, M340*
- Alamat: 192.168.1.113, port 502
- Remote slave address: 255
- *Change word order*: dicentang

Pemetaan alamat ke Modbus:

- `%Mn` → coil n
- `%MWn` → holding register n

## Impor ke TIA

1. Buka **HMI tags → Show all tags**, lalu klik Import dan pilih `KALBAR_tags.xlsx`. Tombol Import tidak berfungsi kalau dijalankan dari editor tabel tag tunggal.
2. Buka **HMI alarms → Discrete alarms**, lalu klik Import dan pilih `KALBAR_alarms.xlsx`.
3. Pastikan tag `ALMW0` dan `ALMW1` bertipe HMI **UInt**, karena trigger discrete alarm tidak menerima Int.

## Layar Overview (Screen_1, 1024×768)

- Empat kartu: pH #1, pH #2, sisa klor, turbidity. Masing-masing berisi nilai, bar meter, dan input batas rendah/tinggi (`P_PH_L/H`, `P_CL_L/H`, `P_TU_M/H`).
- Tombol **ACK / Silence**: SetBit `HMI_ACK`, untuk mematikan buzzer di PLC. Alarm di Alarm view tetap harus di-acknowledge dari Alarm view.
- Tombol **Pause pH #1 / pH #2 / klorin**: InvertBit `MAN_PAUSE_*`.
- Lampu Aliran (`FLOW_STAB`), Kualitas (`QUALITY_OK`), Alarm (`ANY_ALARM`), dan PLC heartbeat (`HEARTBEAT`).
- Alarm view.

Layar dibuat langsung di editor TIA. TIA Openness V19 tidak bisa mengakses perangkat WinCC RT Professional, jadi layar ini tidak di-generate dari script.

## Runtime di SCADAPC

- Shortcut Desktop *Start WinCC RT - Project2* menjalankan `CCStartStop.exe` untuk `Project2\IM\HMI\R\1\D\HMI_NGXZ\HMI_NGXZ.mcp`, yaitu folder runtime internal TIA.
- Compile (Ctrl+B) **tidak** memperbarui database runtime tersebut. Untuk memasukkan perubahan, jalankan **Online → Simulation → Start**, lalu hentikan dengan shortcut *Stop WinCC RT*.
- Selama runtime aktif, TIA tertahan di "Save project". Jalankan *Stop WinCC RT* (`CCStartStop.exe /D /C`) sebelum menyimpan.

## Uji tanpa PLC

1. Jalankan simulator: `node ../scada/sim_m221.js` (port 5020, menjawab semua unit ID).
2. Ubah Connection_1 sementara ke 127.0.0.1 port 5020, lalu jalankan simulasi runtime.
3. Setelah selesai, kembalikan alamat ke PLC asli.

## Belum dikerjakan

- Layar Trend dan I/O & status.
- Kosmetik: beberapa label terpotong, dan kolom teks Alarm view masih sempit.
- Pastikan IP M221 di lapangan (project memakai 192.168.1.113, README utama menyebut default 192.168.1.10).
