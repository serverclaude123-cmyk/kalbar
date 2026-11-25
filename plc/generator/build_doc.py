# -*- coding: utf-8 -*-
# KALBAR documentation section - executed from build.py (shares its namespace)

ARCH = f"""
<div class="grid2">
 <div class="card"><h4>PLC &amp; modul</h4><ul>
  <li><b>TM221CE24R</b>: 14 DI, 10 DO relay, Ethernet (Modbus TCP server ke HMI/SCADA), SL1 RS-485 (Modbus RTU master, opsional untuk TUC 5).</li>
  <li><b>TM3AI4</b> (modul 1): 4 kanal 4–20 mA → <code>%IW1.0–1.3</code>, status <code>%IWS1.x</code>.</li>
  <li>Analog onboard CE24R hanya 0–10 V, jadi tidak dipakai untuk sinyal 4–20 mA.</li>
 </ul></div>
 <div class="card"><h4>Instrumen</h4><ul>
  <li><b>BAMa</b> bypass fitting, 2 slot PG13.5 untuk elektroda pH, reed switch aliran sampel (maks. 42 V / 0,25 A).</li>
  <li><b>D1Cb ×3</b> (pH #1, pH #2, klorin): X6 1(−)/2(+) adalah mA output <b>aktif</b> (maks. 450 Ω), X6 3/4 input pause (kontak kering), XR3 relai alarm.</li>
  <li><b>TUC 5</b> turbidity (OEM HF Micro TOL): 4–20 mA <b>aktif</b> (maks. 1000 Ω) <i>atau</i> RS-485 Modbus, dan 2 relai alarm form C.</li>
 </ul></div>
 <div class="card"><h4>HMI / SCADA</h4><ul>
  <li>Modbus TCP port 502. Bit <code>%Mn</code> = <code>0x n</code>, word <code>%MWn</code> = <code>4x n</code> (zero-based).</li>
  <li>Bila driver memakai alamat 1-based, tambahkan +1.</li>
  <li>Nilai proses <code>%MW100–110</code>, alarm <code>%M200–219</code>, setpoint <code>%MW0–10</code>.</li>
 </ul></div>
 <div class="card"><h4>Wiring penting</h4><ul>
  <li>Semua mA output instrumen <b>aktif</b>: kanal TM3AI4 tanpa suplai loop 24 V.</li>
  <li>Input pause D1Cb diberi tegangan internal ±6 V. Hanya sambung ke kontak relai PLC, <b>jangan diberi 24 V</b>.</li>
  <li>Relai TUC 5 dan D1Cb ke DI 24 VDC PLC. Jangan campur 230 VAC dan SELV di terminal relai yang sama.</li>
  <li>Kabel coax elektroda pH langsung ke XE1 D1Cb, pisahkan dari kabel daya.</li>
 </ul></div>
</div>"""

FLAGS = """
<div class="flag crit"><b>Konfirmasi sebelum dipakai.</b> Model PLC (TM221CE24R + TM3AI4) dan fungsi kedua pH controller (dua titik berbeda atau redundan) adalah asumsi. Ident code kedua D1Cb pH belum dicek: harus versi mV (P 5) dengan mA output (kode 1).</div>
<div class="flag"><b>Perlu diverifikasi di Machine Expert Basic:</b> sintaks status kanal TM3 <code>%IWS1.x</code>, bit string <code>%I0.0:14</code>, pin <code>.D</code>/<code>.E</code> READ_VAR, operasi float <code>%MF300</code> dan <code>REAL_TO_INT</code>. Peta register TUC 5 berasal dari manual HF Micro TOL 19777 (2004), jadi cocokkan dengan uji baca.</div>
"""

ASSUME = tbl(["Topik", "Asumsi di program"], [
 ("Pause dosing", "Relai PLC ON = pause. Bila PLC mati, dosing tetap berjalan (klorinasi PDAM tidak berhenti mendadak). Set input pause D1Cb aktif saat kontak tertutup."),
 ("Aliran sampel", "Reed switch BAMa ke PLC. Pengukuran pH/klorin valid setelah aliran stabil <code>P_T_FLOW_ON</code>. TUC 5 punya flow cell sendiri."),
 ("Sumber turbidity", "<code>P_TU_SRC</code> 0 = 4–20 mA (default), 1 = Modbus. TUC 5 hanya bisa mengaktifkan satu output."),
 ("Batas mutu", "Default mengikuti Permenkes 2/2023: pH 6,5–8,5, kekeruhan &lt; 3 NTU, sisa klor 0,2–1,0 mg/L (contoh). Konfirmasi dengan PDAM."),
 ("Skala analog", "pH 0–14, klorin 0–5 mg/L, turbidity 0–10 NTU. Harus sama dengan setting mA output tiap instrumen."),
 ("Alarm", "Semua alarm tidak di-latch. ACK hanya mematikan buzzer dan menghentikan kedip lampu."),
])

html_doc = f"""<title>Ladder M221 KALBAR</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>{CSS}</style>
<div class="wrap">
<div class="titleblock">
 <div style="display:grid;gap:6px">
  <span class="eyebrow">Program PLC · Draft untuk review</span>
  <h1>Ladder M221 KALBAR PDAM</h1>
  <p>Monitoring kualitas air: pH ×2, sisa klor, turbidity. Pause dosing saat aliran sampel hilang, alarm mutu, dan data ke HMI/SCADA lewat Modbus TCP.</p>
 </div>
 <div class="tb-meta">
  <span>PLC</span><b>TM221CE24R + TM3AI4</b>
  <span>Instrumen</span><b>BAMa, D1Cb ×3, TUC 5</b>
  <span>Jumlah rung</span><b>{TOTAL_RUNGS}</b>
  <span>Tanggal</span><b>25/11/2026</b>
 </div>
</div>
<nav class="toc">
 <a href="#arsitektur">Arsitektur</a><a href="#io">I/O</a><a href="#konfig">Parameter &amp; timer</a><a href="#program">Program</a><a href="#hmi">HMI/SCADA</a><a href="#memori">Memori internal</a><a href="#komisioning">Komisioning</a>
</nav>

<section class="block" id="arsitektur"><h2>Arsitektur &amp; asumsi</h2>
{ARCH}
{FLAGS}
{ASSUME}
<h3>Konfigurasi READ_VAR (SL1, hanya bila P_TU_SRC = 1)</h3>
{tbl(["Blok","Slave ID","ObjType","FirstObj","Quantity","IndexData","Isi"], [
 (code("%READ_VAR0"),"1 (= alamat TUC 5)","%IW (FC04)","0","12",code("%MW300"),"TUC 5 reg 30001–30012"),
])}
{tbl(["Buffer","Register TUC 5","Isi"], [
 (code("%MW300–301 (%MF300)"),"30001–30002","Turbidity float, word rendah dulu"),
 (code("%MW302–303"),"30003–30004","Turbidity raw float"),
 (code("%MW309"),"30010","Reading status: 1 baik, 2 over, 3 under, 6 error"),
 (code("%MW310"),"30011","Ringkasan: bit0 error, bit1 alarm 1, bit2 alarm 2, bit3 kalibrasi"),
 (code("%MW311"),"30012","Error: 0x01 desiccant, 0x02 loop mA, 0x04 kalibrasi, 0x10 over-range, 0x40 lampu, 0x80 ultrasonik"),
])}
<p class="intro">SL1: Modbus RTU master, 9600 bps, 8 data, parity None, 1 stop. Samakan dengan TUC 5 (menu 485: baud, address, RTU). Terminasi 120 Ω di ujung bus.</p>
</section>

<section class="block" id="io"><h2>Daftar I/O</h2>
<h3>Digital input ({len(di)})</h3>
{tbl(["Alamat","Simbol","Keterangan"], di)}
<p class="intro">Sinyal alarm instrumen memakai wiring fail-safe: 1 = normal, 0 = alarm atau kabel putus.</p>
<h3>Digital output ({len(do)})</h3>
{tbl(["Alamat","Simbol","Keterangan"], do)}
<h3>Analog input ({len(ai)})</h3>
{tbl(["Alamat","Simbol","Keterangan / skala"], ai)}
<p class="intro">Konfigurasi TM3AI4: tipe 4–20 mA, skala <i>Customized</i> sesuai kolom keterangan, filter 1–2 detik.</p>
</section>

<section class="block" id="konfig"><h2>Parameter (setpoint HMI) &amp; timer</h2>
{tbl(["Alamat","Simbol","Default","Satuan","Keterangan"], par_rows)}
<h3>Timer</h3>
{tbl(["Timer","Simbol","Tipe","Basis waktu","Preset","Fungsi"], tm_rows)}
</section>

<section class="block" id="program"><h2>Program ladder</h2>
<div class="legend">
 <span><span class="sw" style="background:var(--cmp)"></span>Blok pembanding</span>
 <span><span class="sw" style="background:var(--op)"></span>Blok operasi</span>
 <span><span class="sw" style="background:var(--tm)"></span>Timer TON / READ_VAR</span>
 <span>( ) coil · (S) set · (R) reset · kontak dengan garis miring = NC</span>
</div>
<p class="intro">Setiap rung dapat diketik di Machine Expert Basic dalam mode IL (buka &quot;IL&quot; di bawah rung) lalu diubah ke tampilan Ladder. Ikuti urutan nomor rung.</p>
<nav class="toc">{"".join(toc)}</nav>
{"".join(prog)}
</section>

<section class="block" id="hmi"><h2>HMI / SCADA</h2>
<h3>Tombol perintah (HMI → PLC)</h3>
{tbl(["PLC","Modbus","Simbol","Mode switch","Fungsi"], cmd_rows)}
<p class="intro">Tombol ACK memakai mode <b>Set ON</b> dan PLC me-reset bitnya. Toggle pause/maintenance bertahan sampai dimatikan.</p>
<h3>Nilai proses &amp; status word (baca)</h3>
{tbl(["PLC","Modbus","Simbol","Keterangan"], pv_rows)}
<h3>Bit status (baca)</h3>
{tbl(["PLC","Modbus","Simbol","Keterangan"], st_rows)}
<h3>Daftar alarm</h3>
{tbl(["PLC","Modbus","Simbol","Teks alarm","Latch"], alm_rows)}
</section>

<section class="block" id="memori"><h2>Memori internal (tidak untuk HMI)</h2>
{tbl(["Alamat","Simbol","Keterangan"], int_rows)}
</section>

<section class="block" id="komisioning"><h2>Checklist komisioning</h2>
<div class="grid2">
 <div class="card"><h4>Instrumen</h4><ul>
  <li>D1Cb menu 10.6: mA output 4–20 mA = pH 0–14 / klorin 0–5 mg/L, sama dengan skala TM3AI4.</li>
  <li>D1Cb: input pause aktif saat kontak tertutup. Uji dengan relai %Q0.0–0.2.</li>
  <li>TUC 5 menu 6.5.1: 4 mA = 0, 20 mA = 10 NTU. Menu 6.5.2: ERLV = 2 mA.</li>
  <li>Cek kontak reed BAMa: kontak yang tertutup saat aliran ada masuk ke %I0.0.</li>
 </ul></div>
 <div class="card"><h4>Uji fungsi</h4><ul>
  <li>Tutup valve sampel BAMa: setelah P_T_FLOW_OFF muncul alarm aliran dan ketiga D1Cb pause.</li>
  <li>Lepas kabel mA tiap kanal: alarm sinyal muncul dan nilai tidak lagi valid.</li>
  <li>Simulasikan nilai di luar batas (kalibrator mA): alarm setelah P_T_ALM.</li>
  <li>Bila Modbus dipakai: bandingkan %MW105 dengan display TUC 5, baca reg 30008 (model).</li>
  <li>Matikan PLC: relai remote %Q0.7 jatuh dan SCADA menerima alarm.</li>
 </ul></div>
</div>
</section>
</div>
"""
open(os.path.join(OUT, "KB_M221_Ladder.html"), "w", encoding="utf-8").write(html_doc)
print("rungs", TOTAL_RUNGS, "html bytes", len(html_doc))
