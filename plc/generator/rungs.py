# -*- coding: utf-8 -*-
"""Rungs - KALBAR PDAM panel monitoring kualitas air (M221)."""
from dsl import C, N, Cmp, Ser, Par, Rung, ST, STN, SET, RST, OP
from symbols import SYM, TIMERS, P as PARAMS, CMDS

SECTIONS = []   # (code, title, intro, [rungs])
def sec(code, title, intro):
    SECTIONS.append((code, title, intro, []))
def R(title, cond, outs, comment="", timer=None, block=None):
    SECTIONS[-1][3].append(Rung(title, cond, outs, comment, timer, block))

# (tag, PV, AI, status, valid, OOR, timer, low alm, high alm, sig alm, P_L, P_H, man pause, dosing out)
MEAS = [
 ("pH #1", "PH1_PV", "AI_PH1", "ST_PH1", "VALID_PH1", "PH1_OOR", "TM_PH1", "A_PH1_L", "A_PH1_H", "A_PH1_SIG", "P_PH_L", "P_PH_H", "MAN_PAUSE_PH1", "Q_PAUSE_PH1"),
 ("pH #2", "PH2_PV", "AI_PH2", "ST_PH2", "VALID_PH2", "PH2_OOR", "TM_PH2", "A_PH2_L", "A_PH2_H", "A_PH2_SIG", "P_PH_L", "P_PH_H", "MAN_PAUSE_PH2", "Q_PAUSE_PH2"),
 ("klorin", "CL_PV", "AI_CL",  "ST_CL",  "VALID_CL",  "CL_OOR",  "TM_CL",  "A_CL_L",  "A_CL_H",  "A_CL_SIG",  "P_CL_L", "P_CL_H", "MAN_PAUSE_CL",  "Q_PAUSE_CL"),
]

# =====================================================================
sec("POU0", "Inisialisasi & perintah",
    "Isi default parameter sekali, muat preset timer dari parameter HMI, tunda start-up, dan perintah ACK.")
R("Default parameter (sekali saat memori kosong)",
  Cmp("{SIGNATURE} <> 12345"),
  [OP(f"{{{n}}} := {dflt}") for n, mw, dflt, u, c in PARAMS] + [OP("{SIGNATURE} := 12345")],
  "Bila %MW60 belum 12345 (PLC baru / memori hilang) semua setpoint diisi nilai contoh. Setelah itu nilai hanya diubah dari HMI.")
R("Muat preset timer dari parameter", None,
  [OP(f"{{{tn}}}.P := {{{pre}}}") for tn, base, pre, c in TIMERS if isinstance(pre, str)],
  "Preset timer diambil dari %MW parameter tiap scan. Timer dengan preset tetap diisi di konfigurasi.")
R("Tunda start-up", Cmp("{SIGNATURE} = 12345"), [ST("STARTUP_DONE")],
  "Setelah PLC RUN, alarm kualitas menunggu P_T_STARTUP agar sinyal analog dan instrumen stabil.", timer="TM_STARTUP")
R("Perintah ACK (tombol panel tepi naik / HMI)",
  Par(Ser(C("PB_RESET"), N("PB_RST_PREV")), C("HMI_ACK")), [ST("RESET_CMD")])
R("Memori tepi tombol reset", C("PB_RESET"), [ST("PB_RST_PREV")])
R("Heartbeat untuk HMI/SCADA", C("S_1S"), [ST("HEARTBEAT")])

# =====================================================================
sec("POU1", "Nilai analog",
    "TM3AI4 diskalakan di konfigurasi modul (4-20 mA, skala custom) sehingga %IW langsung bernilai teknik. "
    "Range harus sama dengan setting mA output di D1Cb (menu 10.6) dan TUC 5 (menu 6.5.1).")
R("Salin nilai analog", None,
  [OP("{PH1_PV} := {AI_PH1}"), OP("{PH2_PV} := {AI_PH2}"), OP("{CL_PV} := {AI_CL}"), OP("{TU_MA_PV} := {AI_TU}")])
R("Selisih pH #1 - pH #2", None, [OP("{PH_DIFF} := {PH1_PV} - {PH2_PV}")])
R("  nilai absolut", Cmp("{PH_DIFF} < 0"), [OP("{PH_DIFF} := 0 - {PH_DIFF}")])
R("Turbidity dari 4-20 mA", Cmp("{P_TU_SRC} = 0"), [OP("{TU_PV} := {TU_MA_PV}")])
R("Turbidity dari Modbus", Cmp("{P_TU_SRC} = 1"), [OP("{TU_PV} := {TU_MB_PV}")],
  "TUC 5 hanya bisa memilih SATU output: 4-20 mA atau RS-485 (menu output). Samakan dengan P_TU_SRC.")
for tag, pv, ai, st, valid, oor, tm, al, ah, asig, pl, ph, mp, q in MEAS:
    R(f"Gangguan sinyal {tag}", Cmp(f"{{{st}}} <> 0"), [ST(asig)],
      "Status kanal TM3 bukan 0 = under/over range atau kabel putus (D1Cb fault = 3,6 mA)." if tag == "pH #1" else "")
R("Gangguan sinyal turbidity", Ser(Cmp("{P_TU_SRC} = 0"), N("MAINT_TU"), Cmp("{ST_TU} <> 0")), [ST("A_TU_SIG")],
  "Set ERLV TUC 5 = 2 mA: fault alat muncul sebagai under-range.")
R("Cermin status I/O fisik untuk HMI", None, [OP("{IO_DI0} := %I0.0:9"), OP("{IO_DO0} := %Q0.0:7")])

# =====================================================================
sec("POU2", "Aliran sampel & PAUSE dosing",
    "Reed switch BAMa menandakan aliran sampel. Tanpa aliran, nilai pH/klorin tidak mewakili air proses sehingga "
    "dosing D1Cb di-PAUSE lewat input pause X6 pin 3/4. Pause juga bisa dipaksa dari HMI saat kalibrasi.")
R("Aliran sampel stabil", C("FS_SAMPLE"), [ST("FLOW_STAB")], timer="TM_FLOW_ON")
R("Alarm aliran sampel hilang", Ser(N("FS_SAMPLE"), C("STARTUP_DONE")), [ST("A_NOFLOW")], timer="TM_FLOW_OFF")
for tag, pv, ai, st, valid, oor, tm, al, ah, asig, pl, ph, mp, q in MEAS:
    R(f"PAUSE dosing {tag}", Par(N("FLOW_STAB"), C(mp)), [ST(q)],
      "Relai ON = pause. Set input pause D1Cb ke 'aktif saat kontak tertutup'. Bila PLC mati, dosing tetap jalan (tidak berhenti mendadak)." if tag == "pH #1" else "")
    R(f"Nilai {tag} valid", Ser(C("FLOW_STAB"), C("STARTUP_DONE"), N(asig), N(mp)), [ST(valid)])
R("Nilai turbidity valid",
  Ser(C("STARTUP_DONE"), N("MAINT_TU"),
      Par(Ser(Cmp("{P_TU_SRC} = 0"), N("A_TU_SIG")), Ser(Cmp("{P_TU_SRC} = 1"), N("A_TU_COMM"), N("A_TU_MBERR")))),
  [ST("VALID_TU")], "TUC 5 punya flow cell sendiri, tidak tergantung aliran BAMa.")

# =====================================================================
sec("POU3", "Alarm kualitas air",
    "Nilai di luar batas selama P_T_ALM menjadi alarm. Batas default mengikuti Permenkes 2/2023 dan harus dikonfirmasi PDAM.")
for tag, pv, ai, st, valid, oor, tm, al, ah, asig, pl, ph, mp, q in MEAS:
    R(f"{tag} di luar batas", Ser(C(valid), Par(Cmp(f"{{{pv}}} < {{{pl}}}"), Cmp(f"{{{pv}}} > {{{ph}}}"))), [ST(oor)])
    R(f"  tunda alarm {tag}", C(oor), [], timer=tm)
    R(f"  {tag} rendah", Ser(C(tm), Cmp(f"{{{pv}}} < {{{pl}}}")), [ST(al)])
    R(f"  {tag} tinggi", Ser(C(tm), Cmp(f"{{{pv}}} > {{{ph}}}")), [ST(ah)])
R("Turbidity di atas batas", Ser(C("VALID_TU"), Cmp("{TU_PV} > {P_TU_H}")), [ST("TU_OOR")])
R("  tunda alarm turbidity", C("TU_OOR"), [ST("A_TU_H")], timer="TM_TU")
R("Selisih pH di atas batas", Ser(Cmp("{P_PH_DIFF} > 0"), C("VALID_PH1"), C("VALID_PH2"), Cmp("{PH_DIFF} > {P_PH_DIFF}")),
  [ST("PHD_OOR")], "Aktifkan (P_PH_DIFF > 0) hanya bila kedua elektroda mengukur air yang sama.")
R("  tunda alarm selisih pH", C("PHD_OOR"), [ST("A_PH_DIFF")], timer="TM_PHD")
R("Kualitas air normal",
  Ser(C("VALID_PH1"), C("VALID_PH2"), C("VALID_CL"), C("VALID_TU"),
      N("PH1_OOR"), N("PH2_OOR"), N("CL_OOR"), N("TU_OOR")),
  [ST("QUALITY_OK")])

# =====================================================================
sec("POU4", "Alarm dari instrumen",
    "Kontak alarm D1Cb (XR3) dan TUC 5 (Alarm 1/2) dibaca fail-safe: 1 = normal. Pilih kontak NC/NO di instrumen sehingga kabel putus = alarm.")
R("D1Cb pH #1 alarm", Ser(N("PH1_OK"), C("STARTUP_DONE")), [ST("A_PH1_DEV")])
R("D1Cb pH #2 alarm", Ser(N("PH2_OK"), C("STARTUP_DONE")), [ST("A_PH2_DEV")])
R("D1Cb klorin alarm", Ser(N("CL_OK"), C("STARTUP_DONE")), [ST("A_CL_DEV")])
R("TUC 5 alarm 1 (turbidity tinggi)", Ser(N("TU_A1_OK"), C("STARTUP_DONE"), N("MAINT_TU")), [ST("A_TU_A1")])
R("TUC 5 alarm 2 (fault)", Ser(N("TU_A2_OK"), C("STARTUP_DONE"), N("MAINT_TU")), [ST("A_TU_A2")])

# =====================================================================
sec("POU5", "Modbus RTU SL1 - TUC 5 (opsional)",
    "Aktif bila P_TU_SRC = 1. Satu READ_VAR membaca input register 30001-30012 (FC04, alamat 0, 12 word) ke %MW300-%MW311. "
    "Float NTU di 30001-30002 dengan word rendah dulu, sama dengan urutan %MF300 di M221. Peta register dari manual HF Micro TOL 19777 - verifikasi dengan uji baca.")
R("Pulsa polling 1 s", Ser(Cmp("{P_TU_SRC} = 1"), N("POLL_PULSE")), [ST("POLL_PULSE")], timer="TM_POLL")
R("Eksekusi READ_VAR TUC 5", Ser(Cmp("{MB_STEP} = 0"), C("POLL_PULSE")), [], block="RV_TU")
R("  mulai tunggu jawaban", Ser(Cmp("{MB_STEP} = 0"), C("POLL_PULSE")), [OP("{MB_STEP} := 1")])
R("  selesai OK: ambil data", Ser(Cmp("{MB_STEP} = 1"), C("%READ_VAR0.D")),
  [OP("{TU_MB_X100} := {TU_MB_F} * 100.0"), OP("{TU_MB_PV} := REAL_TO_INT({TU_MB_X100})"),
   OP("{TU_STATUS} := {TU_MB_STAT}"), OP("{TU_ERRW} := {TU_MB_ERR}"),
   OP("{MB_ERR_TU} := 0"), OP("{MB_STEP} := 0")],
  "Bila nilai tidak masuk akal (mis. 1E-38), word order terbalik: tukar %MW300/%MW301 sebelum konversi.")
R("  error komunikasi", Ser(Cmp("{MB_STEP} = 1"), C("%READ_VAR0.E")),
  [OP("{MB_ERR_TU} := {MB_ERR_TU} + 1"), OP("{MB_STEP} := 0")])
R("Batasi langkah polling", Par(Cmp("{MB_STEP} > 1"), Cmp("{P_TU_SRC} <> 1")), [OP("{MB_STEP} := 0")])
R("Batasi counter error", Cmp("{MB_ERR_TU} > 100"), [OP("{MB_ERR_TU} := 100")])
R("Komunikasi TUC 5 putus", Ser(Cmp("{P_TU_SRC} = 1"), N("MAINT_TU"), Cmp("{MB_ERR_TU} >= 3")), [ST("A_TU_COMM")])
R("TUC 5 melaporkan error",
  Ser(Cmp("{P_TU_SRC} = 1"), N("MAINT_TU"), N("A_TU_COMM"), Par(Cmp("{TU_STATUS} = 6"), Cmp("{TU_ERRW} <> 0"))),
  [ST("A_TU_MBERR")], "Reg 30010 = 6 (error) atau bit error reg 30012 (desiccant, lampu, ultrasonik, kalibrasi).")

# =====================================================================
sec("POU6", "Alarm, buzzer & lampu",
    "Alarm %M200-%M231 dipak ke %MW200-%MW201. Alarm baru menyalakan buzzer sampai ACK. Lampu alarm kedip selama belum ACK, menyala tetap selama alarm masih aktif.")
R("Pak bit alarm ke word", None, [OP(f"{{ALMW{k}}} := %M{200+16*k}:16") for k in range(2)])
for k in range(2):
    R(f"Deteksi alarm baru word {k}", None, [OP(f"{{ALMTMP}} := NOT {{ALMPREV{k}}}"), OP(f"{{ALMTMP}} := {{ALMW{k}}} AND {{ALMTMP}}")])
    R(f"  alarm baru word {k} -> buzzer", Cmp("{ALMTMP} <> 0"), [SET("BUZZ_LATCH")])
R("Simpan word alarm", None, [OP(f"{{ALMPREV{k}}} := {{ALMW{k}}}") for k in range(2)])
R("Ada alarm aktif", Par(*[Cmp(f"{{ALMW{k}}} <> 0") for k in range(2)]), [ST("ANY_ALARM")])
R("ACK: matikan buzzer", C("RESET_CMD"), [RST("BUZZ_LATCH")])
R("Buzzer", C("BUZZ_LATCH"), [ST("Q_BUZZER")])
R("Lampu alarm (kedip bila belum ACK)", Par(Ser(C("BUZZ_LATCH"), C("S_1S")), Ser(C("ANY_ALARM"), N("BUZZ_LATCH"))), [ST("Q_HL_ALM")])
R("Ada dosing di-PAUSE", Par(N("FLOW_STAB"), C("MAN_PAUSE_PH1"), C("MAN_PAUSE_PH2"), C("MAN_PAUSE_CL")), [ST("PAUSE_ANY")])
R("Lampu hijau (tetap = normal, kedip = pause)", Par(Ser(C("PAUSE_ANY"), C("S_1S")), Ser(N("PAUSE_ANY"), C("QUALITY_OK"), N("ANY_ALARM"))), [ST("Q_HL_OK")],
  "CE16R hanya 7 relay, jadi lampu kuning digabung: lampu hijau berkedip saat dosing di-PAUSE.")
R("Alarm umum ke remote (fail-safe)", N("ANY_ALARM"), [ST("Q_ALM_REMOTE")],
  "Relai ON = sehat. PLC mati / kabel putus terbaca sebagai alarm di SCADA.")

# =====================================================================
sec("POU7", "Reset tombol HMI",
    "Tombol HMI memakai mode 'Set ON'. PLC mengembalikan bit ke 0 setelah diproses.")
for n, m, c in CMDS:
    R(f"Reset {n}", C(n), [RST(n)])
