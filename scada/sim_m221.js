// Simulator memori M221 (Modbus TCP server) untuk uji SCADA FUXA tanpa PLC.
// Pakai: npm install modbus-serial   lalu   node sim_m221.js [port]   (default 5020)
// Di FUXA ubah alamat device PLC_M221 ke 127.0.0.1 port 5020.
const ModbusRTU = require("modbus-serial");
const port = parseInt(process.argv[2] || "5020", 10);

const coils = new Array(400).fill(false);   // %M0..%M399
const hreg = new Array(400).fill(0);        // %MW0..%MW399

// parameter default (sama dengan PLC rung 001)
Object.assign(hreg, { 0: 60, 1: 10, 2: 60, 3: 650, 4: 850, 5: 20, 6: 100, 7: 300, 8: 0, 9: 0, 10: 30, 11: 100, 60: 12345 });

let t = 0;
setInterval(() => {
  t++;
  const ph1 = Math.round(720 + 25 * Math.sin(t / 20));
  const ph2 = Math.round(705 + 20 * Math.sin(t / 25 + 1));
  const cl = Math.round(55 + 45 * Math.sin(t / 30));   // kadang < 0,20 mg/L
  const tu = Math.round(80 + 40 * Math.sin(t / 15)) + (t % 120 > 100 ? 300 : 0); // sesekali > 3 NTU
  const flow = (t % 90) < 80;                                                       // sesekali aliran hilang
  hreg[100] = ph1; hreg[101] = ph2; hreg[102] = cl; hreg[103] = tu; hreg[104] = tu; hreg[106] = Math.abs(ph1 - ph2);
  hreg[107] = 1;
  const zone = (v, lo, hi, ok) => !ok ? 0 : v < lo ? 1 : v > hi ? 3 : 2;
  hreg[130] = zone(ph1, hreg[3], hreg[4], coils[3]);
  hreg[131] = zone(ph2, hreg[3], hreg[4], coils[4]);
  hreg[132] = zone(cl, hreg[5], hreg[6], coils[5]);
  hreg[133] = tu > hreg[7] ? 3 : tu > hreg[11] ? 2 : 1;
  coils[1] = t > 5;                    // STARTUP_DONE
  coils[2] = flow && (t % 90) > 3;     // FLOW_STAB
  coils[3] = coils[4] = coils[5] = coils[2] && !coils[310];
  coils[6] = true;                     // VALID_TU
  coils[9] = t % 2 === 0;              // HEARTBEAT
  coils[200] = !flow && t > 5;         // A_NOFLOW
  coils[212] = tu > hreg[7];           // A_TU_H
  coils[12] = coils[2] && !coils[212]; // QUALITY_OK
  coils[16] = tu > hreg[7];
  coils[19] = !coils[2] || coils[310] || coils[311] || coils[312]; // PAUSE_ANY
  // cermin I/O
  coils[40] = flow; coils[41] = coils[42] = coils[43] = coils[44] = coils[45] = true;
  coils[50] = coils[51] = coils[52] = !coils[2];
  if (coils[310]) coils[50] = true; if (coils[311]) coils[51] = true; if (coils[312]) coils[52] = true;
  const anyAlm = coils.slice(200, 232).some(Boolean);
  if (anyAlm && !coils[10]) coils[11] = true;  // alarm baru -> BUZZ_LATCH
  coils[10] = anyAlm;
  if (coils[300]) { coils[11] = false; coils[300] = false; }  // HMI_ACK
  coils[53] = coils[10]; coils[54] = coils[11]; coils[55] = coils[12]; coils[56] = !coils[10];
}, 1000);

const vector = {
  getCoil: (a) => coils[a] || false,
  setCoil: (a, v) => { coils[a] = !!v; },
  getDiscreteInput: (a) => false,
  getHoldingRegister: (a) => hreg[a] || 0,
  setRegister: (a, v) => { hreg[a] = v; },
  getInputRegister: (a) => 0,
};
new ModbusRTU.ServerTCP(vector, { host: "0.0.0.0", port, unitID: 1, debug: false });
console.log("Simulator M221 Modbus TCP di port", port);
