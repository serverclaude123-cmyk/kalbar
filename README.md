# KALBAR PDAM – ProMinent water-quality instruments → PLC interfacing

Notes for wiring the ProMinent analysers to the PLC. Manuals are in [`manuals/`](manuals/), label photos in [`photos/`](photos/).

## Equipment

| Unit | Type / ident code | Serial | What it is |
|---|---|---|---|
| Bypass fitting | ProMinent **BAMa** `BAMAEU222XXXF01X000000EN` | 2025338669 | Flow cell for 2 × PG13.5 sensors (pH), float flow meter + reed switch |
| Controller ×2 | ProMinent **DULCOMETER D1Cb** (pH) | – (labels not yet checked) | pH controller, mV input via coax XE1 |
| Controller ×1 | ProMinent **DULCOMETER D1Cb** `D1CBW00601000VC1211M22ENWS` | 2025242888 | Free-chlorine controller, 4–20 mA sensor input |
| Turbidimeter | ProMinent **DULCO turb C TUC 5**, part 1115440 (type `TUC5WSWD`) | 2026020349 | Turbidity, ISO 7027 IR, ultrasonic cleaning. OEM of **HF scientific Micro TOL** |

### BAMa ident code `BAMA EU 2 2 2 X X X F 0 1 X 00 00 00 EN`
| Code | Meaning |
|---|---|
| EU | Europe |
| 2 | 20–60 l/h, max 60 °C / 3.5 bar |
| 2 | Float flow meter + scale + **reed switch** |
| 2 | **2 modules PG13.5** (pH / ORP / conductivity) |
| X | 0 modules G1" (amperometric e.g. chlorine) – **none** |
| X | 0 modules G3/4" |
| X | No metering module |
| F | Filter 300 µm stainless |
| 0 | No sensor cleaning |
| 1 | Hose 8x5 + 12x6 mm |
| X | No status light |
| 00/00/00 | PM logo / no accessories / no approvals |
| EN | English manual |

⚠️ BAMa has no G1" slot → chlorine sensor needs a separate holder/module.

### D1Cb chlorine ident code `D1CB W 00 6 01 0 0 0 V C 1 2 1 1 M 2 2 EN WS`
| Code | Meaning |
|---|---|
| W | Wall-mount, IP65 |
| 00 | LCD + keypad, PM logo |
| 6 | 90–253 VAC |
| 01 | Certification (likely CE) |
| 0 0 0 | No HW extension / no RC circuit / no external connection |
| V C | Software preset, **chlorine** |
| 1 | **mA input** (sensor 4–20 mA) |
| 2 | Pt100/Pt1000 temperature input |
| 1 | **Pause input** |
| 1 | **mA output 0/4–20 mA** |
| M | Alarm + 2 solenoid-valve relays |
| 2 | 2 pump pulse outputs |
| 2 | PID |
| EN | English |
| WS | Not in manual table – ask ProMinent |

## Terminal / signal data

### BAMa reed switch (manual Tab. 3/4)
- Terminal 1 = NC, 2 = Common, 3 = NO. Potential-free.
- Max **42 V SELV, 0.25 A, 3 W** → 24 VDC to PLC DI OK, never 230 VAC.
- Cable Ø4 mm via M12 gland, ferrules ≤0.5 mm². Factory switch point 30 % ≈ 25 l/h.
- Check with multimeter which contact is closed with flow; use the closed-in-normal contact (fail-safe).

### D1Cb (manual 986362, Fig. 12 p.35 + board label)
| Terminal | Function |
|---|---|
| XE1 (coax) | mV input pH/ORP |
| XE2 | Liquid potential |
| XE3 | Pt100/Pt1000 |
| XE4 (1 NC, 2 −, 4 +) | 4–20 mA sensor input (chlorine) |
| XA5 | Pump P1 / P2 pulse outputs (OptoMOS, max 50 V / 50 mA) |
| **X6 1(−) / 2(+)** | **mA output → PLC AI** |
| X6 3(−) / 4(+) | Pause digital input – **dry contact only, do not apply voltage** (≈6 V internal) |
| XR1 / XR2 | Relay 1/2 (solenoid valve), 5 A |
| **XR3 (1-2-3)** | **Alarm relay, changeover, 5 A → PLC DI** |
| XP1 | Mains N / L |

mA output: 0/3.8–23 mA, fault 3.6 or 21.5 mA, **active**, max 450 Ω @ 20.5 mA, 18 V max, isolated 500 V, ±0.25 %. Configure in menu 10.6 "Set mA output".
Do not mix SELV and mains on XR1–XR3/XP.

### TUC 5 turbidimeter (manual BA DT 070 01/22)
- Terminal strip P1 in terminal box: alarms top row; RS-485 bottom-left; 4–20 mA bottom-right.
- **4–20 mA: active (24 V internal), isolated, max 1000 Ω.** Menu 6.5.1: 4 mA / 20 mA NTU values (e.g. 0–10 NTU). Menu 6.5.2: ERLV fault current → set **2 mA**.
- **Alarm 1/2: form C relays 120–240 VAC 2 A** (NO/C/NC).
- **RS-485 Modbus RTU/ASCII**, address 1–255, 1200–19200 baud, default 8N1, 120 Ω termination on last node, ≤900 m.
- Range 0–100 NTU (0–10 / 0–1000 via USB stick). Sample 0.1–1.5 l/min, inlet ≤7 bar.

## TUC 5 Modbus map (from HF scientific Micro TOL Modbus manual 19777 Rev 1.4)

> ProMinent says Modbus info "on request". The TUC 5 is an HF Micro TOL OEM; map below is from the 2004 HF manual – **verify with a test read** (read 30008 model no. and compare 30001 with display).

Float = 2 registers, **first register = low word** (word swap / CDAB). Each word MSB first.

### Input registers (FC 04)
| Reg | PLC offset | Type | Content |
|---|---|---|---|
| **30001–30002** | 0 | Float | **Turbidity reading (NTU/FNU)** |
| 30003–30004 | 2 | Float | Raw reading |
| 30005/6/7 | 4/5/6 | Int | SW version major/minor/rev |
| 30008 | 7 | Int | Model number |
| 30009 | 8 | Int | Model suffix |
| **30010** | 9 | Int | Status: 1 good, 2 over, 3 under, 6 error |
| **30011** | 10 | Bits | b0 error, b1 alarm1, b2 alarm2, b3 cal error |
| **30012** | 11 | Bits | 0x01 desiccant, 0x02 mA loop break, 0x04 cal, 0x10 over-range, 0x20 flow, 0x40 lamp, 0x80 ultrasonic, 0x100/0x200 general |
| 30013 | 12 | Int | PCB revision |

Holding 40031–40043 duplicate 30001–30013 (FC 03).

### Discrete inputs (FC 02)
10001 instrument error · 10002 alarm 1 · 10003 alarm 2 · 10004 cal error · 10005 desiccant error

### Coils (FC 01/05)
00001 offset · 00002 flow alarm · 00003 access code · 00004 ultrasonic cleaning · 00005 desiccant as error

### Holding registers (FC 03/06/16) – settings (table in PDF is misaligned, verify)
40001–02 offset (F) · 40003 decimals · 40004 response time · 40005 units 0 NTU/1 FNU · 40006 backlight · 40008 output 0 off/1 mA/2 485 · 40009–10 NTU @4 mA (F) · 40011–12 NTU @20 mA (F) · 40013 baud 0=1200…3=9600,4=19200 · 40014 data bits · 40015 parity · 40016 stop · 40017 address · 40018 0 RTU/1 ASCII · 40020 alarm1 func 0 off/1 low/2 high · 40021–22 alarm1 SP (F) · 40023/24 alarm1 delay on/off · 40026 alarm2 func · 40027–28 alarm2 SP (F) · 40029/30 alarm2 delay on/off

## PLC I/O list (draft)

| # | Signal | Source | Type |
|---|---|---|---|
| AI1 | pH #1 | D1Cb pH #1 X6 1/2 | 4–20 mA active → passive AI |
| AI2 | pH #2 | D1Cb pH #2 X6 1/2 | 4–20 mA active → passive AI |
| AI3 | Free chlorine | D1Cb Cl X6 1/2 | 4–20 mA active → passive AI |
| AI4 | Turbidity | TUC 5 mA terminal | 4–20 mA active → passive AI (or Modbus) |
| DI1–3 | D1Cb alarms | XR3 each | Dry contact |
| DI4–5 | Turbidity alarm 1/2 | TUC 5 relays | Dry contact |
| DI6 | Sample flow OK | BAMa reed sw. 2/3 | Dry contact 24 VDC |
| DO (opt.) | Pause dosing | PLC relay → D1Cb X6 3/4 | Dry contact only |

**All 4 analog sources are active (self-powered) – do not loop-power from PLC.**

## PLC program (Schneider M221)

Folder [`plc/`](plc/) – draft program for **TM221CE16R (relay version) + TM3AI4** (70 rungs, Indonesian comments). I/O: 7 of 9 DI, all 7 relay DO used (green lamp blinks = dosing paused):

| File | Content |
|---|---|
| `KB_M221_Ladder.html` | Full documentation: I/O, parameters, timers, every rung as ladder + IL, HMI/SCADA map, commissioning checklist (open in browser) |
| `KB_M221_program_IL.txt` | IL program, type/paste per rung in Machine Expert Basic then switch view to Ladder |
| `KB_M221_symbols.csv` | Symbol table (import into Machine Expert Basic) |
| `KB_HMI_tags.csv`, `KB_HMI_alarms.csv` | Modbus TCP tags and alarm list for HMI/SCADA |
| `generator/` | Python source – edit `symbols.py` / `rungs.py`, run `python build.py ..` from `plc/generator` |

Functions: sample-flow detection (BAMa reed) → pause D1Cb dosing via X6 3/4, pH/Cl/turbidity limit alarms with delay, 4-20 mA signal-fault alarms, instrument relay alarms, optional TUC 5 Modbus RTU (P_TU_SRC = 1), alarm lamp/buzzer/ACK, fail-safe remote alarm relay.

## SCADA (WinCC RT Professional)

The main SCADA is **WinCC RT Professional V19** (TIA Portal `Project2`, runtime PC SCADAPC). Folder [`wincc/`](wincc/) holds the tag and alarm import generators (80 tags, 20 discrete alarms), the generated xlsx files, and notes on the Overview screen and runtime. See [wincc/README.md](wincc/README.md).

## SCADA (FUXA, test/backup)

Folder [`scada/`](scada/) – FUXA project generated from the PLC symbol table: Overview, Trend, Setpoint, I/O & status screens, 20 alarms, DAQ history. Import `scada/KB_FUXA_project.json`, install the **modbus-serial** plugin, set the PLC IP. See [scada/README.md](scada/README.md). `scada/sim_m221.js` simulates the M221 for testing without hardware.

## Open items
- [ ] Photos/ident codes of the 2 pH D1Cb (confirm mV version `P 5`)
- [ ] Chlorine sensor type and where it mounts (BAMa has no G1" slot)
- [ ] D1Cb code suffix `WS` meaning
- [ ] Confirm TUC 5 Modbus map with test read / ProMinent
- [ ] PLC brand/model → wiring diagram + scaling table

## Sources
- BAMa manual BA DTZ 013 09/22 (indufarm copy)
- D1Cb/D1Cc manual 986362 BA DM 197 12/13 – prominent.fr
- DULCO turb C TUC 5/6 BA DT 070 01/22 – prominent.de
- HF scientific Micro TOL Modbus manual 19777 & owner's manual 24034 – watts.com
