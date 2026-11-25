# -*- coding: utf-8 -*-
"""Symbol table - KALBAR PDAM panel monitoring kualitas air (M221).
name -> (address, comment, hmi) ; hmi: None / 'R' / 'RW' / 'CMD' / 'TGL' / 'ALM'
PLC: TM221CE16R + TM3AI4 (modul 1). HMI/SCADA lewat Modbus TCP.
"""
SYM = {}
ORDER = []

def d(name, addr, comment, hmi=None, default=None, unit=""):
    assert name not in SYM, name
    SYM[name] = dict(addr=addr, comment=comment, hmi=hmi, default=default, unit=unit)
    ORDER.append(name)

# ---------------- DIGITAL INPUTS (TM221CE16R onboard, 9 DI %I0.0-0.8, 24 VDC sink) ----------------
d("FS_SAMPLE", "%I0.0", "Reed switch BAMa (terminal 2-3): 1 = aliran sampel ada", "R")
d("PH1_OK",    "%I0.1", "D1Cb pH #1 relai alarm XR3: 1 = normal (wiring fail-safe)", "R")
d("PH2_OK",    "%I0.2", "D1Cb pH #2 relai alarm XR3: 1 = normal", "R")
d("CL_OK",     "%I0.3", "D1Cb klorin relai alarm XR3: 1 = normal", "R")
d("TU_A1_OK",  "%I0.4", "TUC 5 Alarm 1 (turbidity tinggi): 1 = normal", "R")
d("TU_A2_OK",  "%I0.5", "TUC 5 Alarm 2 (fault alat): 1 = normal", "R")
d("PB_RESET",  "%I0.6", "Tombol ACK/RESET di pintu panel (NO)", "R")

# ---------------- DIGITAL OUTPUTS (CE16R: 7 relay %Q0.0-0.6, kontak kering) ----------------
d("Q_PAUSE_PH1", "%Q0.0", "PAUSE dosing D1Cb pH #1 -> X6 pin 3/4 (tutup = pause)")
d("Q_PAUSE_PH2", "%Q0.1", "PAUSE dosing D1Cb pH #2 -> X6 pin 3/4 (tutup = pause)")
d("Q_PAUSE_CL",  "%Q0.2", "PAUSE dosing D1Cb klorin -> X6 pin 3/4 (tutup = pause)")
d("Q_HL_ALM",    "%Q0.3", "Lampu ALARM merah (kedip = belum di-ACK)")
d("Q_BUZZER",    "%Q0.4", "Buzzer alarm")
d("Q_HL_OK",     "%Q0.5", "Lampu hijau: tetap = kualitas normal, kedip = aliran sampel hilang / dosing pause")
d("Q_ALM_REMOTE","%Q0.6", "Alarm umum ke SCADA/remote (ON = SEHAT, fail-safe)")

# ---------------- ANALOG INPUTS (TM3AI4 modul 1, 4-20 mA, skala custom) ----------------
d("AI_PH1", "%IW1.0", "pH #1 dari D1Cb X6: skala 0-1400 = pH 0,00-14,00")
d("AI_PH2", "%IW1.1", "pH #2 dari D1Cb X6: skala 0-1400 = pH 0,00-14,00")
d("AI_CL",  "%IW1.2", "Klorin bebas dari D1Cb X6: skala 0-500 = 0,00-5,00 mg/L (samakan range D1Cb)")
d("AI_TU",  "%IW1.3", "Turbidity TUC 5: skala 0-1000 = 0,00-10,00 NTU (samakan 4/20 mA TUC)")
d("ST_PH1", "%IWS1.0", "Status kanal pH #1 (0 = OK)")
d("ST_PH2", "%IWS1.1", "Status kanal pH #2")
d("ST_CL",  "%IWS1.2", "Status kanal klorin")
d("ST_TU",  "%IWS1.3", "Status kanal turbidity")

# ---------------- SYSTEM BITS ----------------
d("S_1S",  "%S6", "Basis waktu 1 detik (kedip)")

# ---------------- PARAMETERS %MW0-%MW59 (HMI R/W, retentive) ----------------
P = [
 ("P_T_FLOW_ON",  0, 60,   "s",       "Aliran sampel harus stabil selama ini sebelum pengukuran pH/Cl dianggap valid dan pause dilepas"),
 ("P_T_FLOW_OFF", 1, 10,   "s",       "Tunda alarm aliran sampel hilang"),
 ("P_T_ALM",      2, 60,   "s",       "Tunda alarm kualitas air (hindari alarm sesaat)"),
 ("P_PH_L",       3, 650,  "x0,01",   "Batas pH rendah (Permenkes 2/2023: 6,5)"),
 ("P_PH_H",       4, 850,  "x0,01",   "Batas pH tinggi (Permenkes 2/2023: 8,5)"),
 ("P_CL_L",       5, 20,   "x0,01 mg/L","Batas sisa klor rendah"),
 ("P_CL_H",       6, 100,  "x0,01 mg/L","Batas sisa klor tinggi"),
 ("P_TU_H",       7, 300,  "x0,01 NTU","Batas turbidity tinggi (Permenkes 2/2023: < 3 NTU)"),
 ("P_PH_DIFF",    8, 0,    "x0,01",   "Alarm selisih pH #1 vs pH #2 (0 = mati; pakai bila kedua sensor di titik yang sama)"),
 ("P_TU_SRC",     9, 0,    "",        "Sumber turbidity: 0 = 4-20 mA (%IW1.3), 1 = Modbus RTU SL1"),
 ("P_T_STARTUP", 10, 30,   "s",       "Tunda setelah PLC RUN sebelum alarm kualitas aktif"),
 ("P_TU_M",      11, 100,  "x0,01 NTU","Batas turbidity menengah (indikasi zona, di bawah = rendah/baik)"),
]
for name, mw, dflt, unit, cmt in P:
    d(name, f"%MW{mw}", cmt, "RW", dflt, unit)
d("SIGNATURE", "%MW60", "Tanda data parameter sudah diinisialisasi (12345)")

# ---------------- PROCESS VALUES %MW100.. (HMI read) ----------------
d("PH1_PV",   "%MW100", "pH #1 (x0,01)", "R", unit="x0,01")
d("PH2_PV",   "%MW101", "pH #2 (x0,01)", "R", unit="x0,01")
d("CL_PV",    "%MW102", "Sisa klor bebas (x0,01 mg/L)", "R", unit="x0,01 mg/L")
d("TU_PV",    "%MW103", "Turbidity terpakai (x0,01 NTU) - sesuai P_TU_SRC", "R", unit="x0,01 NTU")
d("TU_MA_PV", "%MW104", "Turbidity dari 4-20 mA (x0,01 NTU)", "R", unit="x0,01 NTU")
d("TU_MB_PV", "%MW105", "Turbidity dari Modbus (x0,01 NTU)", "R", unit="x0,01 NTU")
d("PH_DIFF",  "%MW106", "Selisih absolut pH #1 - pH #2 (x0,01)", "R")
for _i, (_n, _t) in enumerate([("PH1", "pH #1"), ("PH2", "pH #2"), ("CL", "klorin"), ("TU", "turbidity")]):
    d(f"{_n}_ZONE", f"%MW{130+_i}", f"Zona {_t}: 0 tidak valid, 1 rendah, 2 menengah, 3 tinggi (tanpa tunda)", "R")
d("TU_STATUS","%MW107", "TUC 5 reading status (reg 30010): 1 baik, 2 over, 3 under, 6 error", "R")
d("TU_ERRW",  "%MW108", "TUC 5 error bit (reg 30012): 0x01 desiccant, 0x02 loop mA, 0x04 kalibrasi, 0x40 lampu, 0x80 ultrasonik", "R")
d("MB_STEP",  "%MW109", "Langkah polling Modbus TUC 5 (0 = baca, 1 = tunggu)")
d("MB_ERR_TU","%MW110", "Counter error komunikasi TUC 5", "R")
d("IO_DI0",   "%MW120", "Cermin %I0.0-%I0.8 untuk HMI (bit n = %I0.n)", "R")
d("IO_DO0",   "%MW121", "Cermin %Q0.0-%Q0.6 untuk HMI (bit n = %Q0.n)", "R")
for k in range(2):
    d(f"ALMW{k}", f"%MW{200+k}", f"Word alarm {k} (= %M{200+16*k}..%M{215+16*k})", "R")
for k in range(2):
    d(f"ALMPREV{k}", f"%MW{204+k}", f"Word alarm {k} scan sebelumnya")
d("ALMTMP", "%MW208", "Word bantu deteksi alarm baru")
# Modbus buffer TUC 5: input register 30001.. (FC04, 12 word) -> %MW300..%MW311
d("TU_MB_F",   "%MF300", "TUC 5 reg 30001-30002 float NTU (word rendah dulu = urutan %MF M221)")
d("TU_MB_STAT","%MW309", "TUC 5 reg 30010 reading status (buffer)")
d("TU_MB_ERR", "%MW311", "TUC 5 reg 30012 error bit (buffer)")
d("TU_MB_X100","%MF320", "Bantu: NTU x 100 (float)")

# ---------------- INTERNAL BITS ----------------
d("STARTUP_DONE","%M1", "Tunda start-up selesai", "R")
d("FLOW_STAB",   "%M2", "Aliran sampel stabil > P_T_FLOW_ON", "R")
d("VALID_PH1",   "%M3", "Nilai pH #1 valid (aliran stabil, sinyal OK, tidak pause manual)", "R")
d("VALID_PH2",   "%M4", "Nilai pH #2 valid", "R")
d("VALID_CL",    "%M5", "Nilai klorin valid", "R")
d("VALID_TU",    "%M6", "Nilai turbidity valid", "R")
d("RESET_CMD",   "%M7", "Perintah ACK/reset (tombol panel tepi naik / HMI), 1 scan")
d("PB_RST_PREV", "%M8", "Memori tepi tombol reset")
d("HEARTBEAT",   "%M9", "Heartbeat 1 s untuk HMI/SCADA", "R")
d("ANY_ALARM",   "%M10","Ada alarm aktif", "R")
d("BUZZ_LATCH",  "%M11","Alarm baru belum di-ACK", "R")
d("QUALITY_OK",  "%M12","Semua nilai valid dan di dalam batas", "R")
d("PH1_OOR",     "%M13","pH #1 di luar batas (sebelum tunda)")
d("PH2_OOR",     "%M14","pH #2 di luar batas (sebelum tunda)")
d("CL_OOR",      "%M15","Klorin di luar batas (sebelum tunda)")
d("TU_OOR",      "%M16","Turbidity di atas batas (sebelum tunda)")
d("PHD_OOR",     "%M17","Selisih pH di atas batas (sebelum tunda)")
d("PAUSE_ANY",   "%M19","Ada dosing yang di-PAUSE (aliran hilang / manual)", "R")
d("POLL_PULSE",  "%M18","Pulsa polling Modbus")
# Cermin bit I/O fisik untuk SCADA (Modbus TCP coil): DI -> %M40.., DO -> %M50..
DI_NAMES = [n for n in ORDER if SYM[n]["addr"].startswith("%I0.")]
DO_NAMES = [n for n in ORDER if SYM[n]["addr"].startswith("%Q0.")]
for i, n in enumerate(DI_NAMES):
    d("X_" + n, f"%M{40+i}", f"Cermin {SYM[n]['addr']} {n}", "R")
for i, n in enumerate(DO_NAMES):
    d("X_" + n, f"%M{50+i}", f"Cermin {SYM[n]['addr']} {n}", "R")

# ---------------- ALARMS %M200-%M231 ----------------
ALARMS = [
 ("A_NOFLOW",    "Aliran sampel BAMa tidak ada - dosing pH/klorin di-PAUSE", False),
 ("A_PH1_DEV",   "D1Cb pH #1 alarm (relai XR3)", False),
 ("A_PH2_DEV",   "D1Cb pH #2 alarm (relai XR3)", False),
 ("A_CL_DEV",    "D1Cb klorin alarm (relai XR3)", False),
 ("A_TU_A1",     "TUC 5 alarm 1 - turbidity tinggi (relai alat)", False),
 ("A_TU_A2",     "TUC 5 alarm 2 - fault alat", False),
 ("A_PH1_L",     "pH #1 rendah", False),
 ("A_PH1_H",     "pH #1 tinggi", False),
 ("A_PH2_L",     "pH #2 rendah", False),
 ("A_PH2_H",     "pH #2 tinggi", False),
 ("A_CL_L",      "Sisa klor rendah", False),
 ("A_CL_H",      "Sisa klor tinggi", False),
 ("A_TU_H",      "Turbidity tinggi", False),
 ("A_PH_DIFF",   "Selisih pH #1 dan pH #2 terlalu besar - cek kalibrasi", False),
 ("A_PH1_SIG",   "Sinyal 4-20 mA pH #1 putus / di luar range", False),
 ("A_PH2_SIG",   "Sinyal 4-20 mA pH #2 putus / di luar range", False),
 ("A_CL_SIG",    "Sinyal 4-20 mA klorin putus / di luar range", False),
 ("A_TU_SIG",    "Sinyal 4-20 mA turbidity putus / fault (ERLV 2 mA)", False),
 ("A_TU_COMM",   "Komunikasi Modbus TUC 5 putus", False),
 ("A_TU_MBERR",  "TUC 5 melaporkan error (lihat TU_ERRW)", False),
]
assert len(ALARMS) <= 32, len(ALARMS)
for i, (n, txt, latch) in enumerate(ALARMS):
    d(n, f"%M{200+i}", txt + (" [LATCH]" if latch else ""), "ALM")

# ---------------- HMI COMMANDS (Set ON by HMI, reset by PLC) ----------------
CMDS = [
 ("HMI_ACK", 300, "Tombol HMI: ACK / silence buzzer"),
]
for n, m, c in CMDS:
    d(n, f"%M{m}", c, "CMD")
TGLS = [
 ("MAN_PAUSE_PH1", 310, "Toggle HMI: PAUSE dosing pH #1 (kalibrasi/perawatan)"),
 ("MAN_PAUSE_PH2", 311, "Toggle HMI: PAUSE dosing pH #2"),
 ("MAN_PAUSE_CL",  312, "Toggle HMI: PAUSE dosing klorin"),
 ("MAINT_TU",      313, "Toggle HMI: TUC 5 MAINTENANCE (alarm turbidity dimatikan)"),
]
for n, m, c in TGLS:
    d(n, f"%M{m}", c, "TGL")

# ---------------- TIMERS (auto-numbered) ----------------
TIMERS = []  # (name, base, preset_src, comment)
def t(name, base, preset, comment):
    idx = len(TIMERS)
    TIMERS.append((name, base, preset, comment))
    d(name, f"%TM{idx}", comment)

t("TM_STARTUP", "1 s", "P_T_STARTUP", "Tunda start-up")
t("TM_FLOW_ON", "1 s", "P_T_FLOW_ON", "Aliran sampel stabil")
t("TM_FLOW_OFF","1 s", "P_T_FLOW_OFF","Tunda alarm aliran hilang")
t("TM_PH1",     "1 s", "P_T_ALM",     "Tunda alarm pH #1")
t("TM_PH2",     "1 s", "P_T_ALM",     "Tunda alarm pH #2")
t("TM_CL",      "1 s", "P_T_ALM",     "Tunda alarm klorin")
t("TM_TU",      "1 s", "P_T_ALM",     "Tunda alarm turbidity")
t("TM_PHD",     "1 s", "P_T_ALM",     "Tunda alarm selisih pH")
t("TM_POLL",    "100 ms", 10,         "Interval polling Modbus TUC 5 (1 s)")

# READ_VAR block
d("RV_TU", "%READ_VAR0", "Baca TUC 5: SL1, ID 1, %IW (FC04), reg 0, qty 12 -> %MW300")
