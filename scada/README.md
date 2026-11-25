# SCADA FUXA – KALBAR PDAM Kualitas Air

Project FUXA untuk panel M221 (TM221CE16R + TM3AI4). Semua alamat Modbus diambil langsung dari tabel simbol PLC (`../plc/generator/symbols.py`), jadi SCADA selalu cocok dengan program ladder.

## Isi folder

| File | Fungsi |
|---|---|
| `KB_FUXA_project.json` | Project FUXA siap impor (PLC default `192.168.1.10:502`) |
| `KB_FUXA_tags.csv` | Daftar 71 tag: simbol PLC, coil/holding register, alamat FUXA |
| `build_fuxa.py` | Generator project. Jalankan ulang bila program PLC berubah |
| `sim_m221.js` | Simulator memori M221 (Modbus TCP) untuk uji SCADA tanpa PLC |

## Layar

1. **Overview**: kartu pH #1, pH #2, sisa klor, turbidity (nilai besar, valid, alarm rendah/tinggi, sinyal 4-20 mA, batas). Panel aliran sampel BAMa dan status PAUSE tiap D1Cb dengan tombol pause manual. Ringkasan alarm dengan tombol **ACK / Silence**. Lampu heartbeat PLC di header.
2. **Trend**: grafik realtime pH #1/#2 dan klor + turbidity (2 sumbu Y). Nilai pH, klor dan turbidity disimpan DAQ tiap 60 s untuk riwayat.
3. **Setpoint**: semua parameter `%MW0–%MW10`, input dalam satuan teknik (mis. 6.5 untuk pH, ditulis ke PLC sebagai 650).
4. **I/O & status**: semua DI/DO fisik (lewat cermin %M40–56), bit status internal, diagnosa TUC 5 (mA vs Modbus, status, error bit).

Ada 20 alarm FUXA (satu per bit alarm PLC %M200–219), dikelompokkan *Kualitas air*, *Instrumen*, *Aliran sampel*. Alarm tampil di ikon lonceng di header dan riwayatnya tersimpan.

## Instalasi di PC SCADA

1. Install Node.js 18 atau 20 LTS.
2. Install dan jalankan FUXA:
   ```powershell
   npm install -g --unsafe-perm @frangoteam/fuxa
   fuxa
   ```
   Buka `http://localhost:1881`.
3. **Install plugin Modbus**: Editor (ikon ⚙ / tombol biru) → *Settings* → *Plugins* → install **modbus-serial**. Tanpa plugin ini device PLC tidak terhubung (log: *plugin is missing*).
4. **Impor project**: Editor → menu ☰ → *Open Project* → pilih `KB_FUXA_project.json` → *Save Project*.
5. **Set IP PLC**: Editor → *Connections* → `PLC_M221` → ubah alamat ke IP M221 di lapangan (port 502). Untuk port lain tulis `ip:port`. Atau buat ulang file dengan IP yang benar:
   ```powershell
   $env:KB_PLC_IP="192.168.10.20"; python build_fuxa.py
   ```

## Setting M221

- Machine Expert Basic → *Ethernet*: set IP statis, centang **Modbus TCP server**.
- FUXA membaca `%M` sebagai coil (FC01/05) dan `%MW` sebagai holding register (FC03/06). Unit ID 1 (M221 menerima 255 atau 1).
- Alamat FUXA 1-based: `%M200` = coil address 201, `%MW100` = holding register 101 (lihat `KB_FUXA_tags.csv`).

## Uji tanpa PLC (simulator)

```powershell
npm install modbus-serial
node sim_m221.js 5020
```

Lalu ubah alamat device `PLC_M221` ke `127.0.0.1:5020`. Simulator menggerakkan nilai pH/klor/turbidity, sesekali mematikan aliran sampel dan menaikkan turbidity di atas batas, jadi alarm, pause dan ACK bisa dicoba.

Sudah diuji dengan FUXA 1.3.6 + simulator: nilai terbaca dengan skala benar, toggle pause, ACK dan penulisan setpoint (2.5 NTU → `%MW7` = 250) sampai ke PLC, trend jalan, alarm muncul di header. **Belum diuji dengan M221 asli.**
