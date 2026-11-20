// Narrative Stickman Engine — runtime (Phase 1).
// Rig, damped springs and head follow-through adapted from the MIT stick-explainer
// demo (vendor/lemo-opuscar/styles/stick-explainer/demo), see NOTICE.
// Plan in → deterministic frame out: all randomness is seeded at build time,
// render(t) only interpolates a precomputed spring table (never depends on call order).
import { clamp, lerp, seg, ss, mulberry } from '/core/lib.js';

// ---------------- Skeleton (figure height = 1 unit; angle 0 points down, +pi/2 right) ----------------
const GEO = { thigh: .215, shin: .215, hipH: .42, spine: .285, sh: .065, upper: .18, fore: .155, headR: .112, stance: .09 };
const rest = () => ({ hx: 0, hy: 0, lean: 0, bend: 0, head: 0,
  la: -.56, lb: .24, ra: .56, rb: -.24, lfx: 0, lfy: 0, rfx: 0, rfy: 0, hdx: 0, hdy: 0 });
const KEYS = Object.keys(rest());
const dirv = a => [Math.sin(a), Math.cos(a)];

// One damped spring per parameter (w = angular frequency, z = damping ratio).
// Arms fast, head loosest → follow-through and overlap on a pose change.
const SPR = { hx: [20, .8], hy: [24, .62], lean: [13, .6], bend: [12, .55], head: [9, .42],
  la: [13, .58], ra: [13, .58], lb: [9.5, .46], rb: [9.5, .46],
  lfx: [30, .85], lfy: [30, .85], rfx: [30, .85], rfy: [30, .85] };
const HEADSPR = [16, .38];   // the head arrives a little after the body stops

// Two-segment IK: hip H, foot F, knee toward side (-1 left / +1 right)
function ik(H, F, L1, L2, side) {
  let dx = F[0] - H[0], dy = F[1] - H[1], d = Math.hypot(dx, dy); const m = (L1 + L2) * .9995;
  if (d > m) { F = [H[0] + dx / d * m, H[1] + dy / d * m]; dx = F[0] - H[0]; dy = F[1] - H[1]; d = m; }
  const a = (L1 * L1 - L2 * L2 + d * d) / (2 * d), h = Math.sqrt(Math.max(0, L1 * L1 - a * a));
  const px = H[0] + a * dx / d, py = H[1] + a * dy / d; let nx = -dy / d, ny = dx / d;
  if (nx * side < 0) { nx = -nx; ny = -ny; }
  return [[px + nx * h, py + ny * h], F];
}

// All joints of one figure in pixels. The head sits on the neck; its lag only rotates.
function joints(f, p) {
  const S = f.S, bx = f.x, gy = f.gy;
  const Hp = [bx + p.hx * S, gy - (GEO.hipH - p.hy) * S];
  const sd = dirv(Math.PI - p.lean);                    // lean > 0 leans right
  const N = [Hp[0] + sd[0] * GEO.spine * S, Hp[1] + sd[1] * GEO.spine * S];
  const mid = [(Hp[0] + N[0]) / 2, (Hp[1] + N[1]) / 2], perp = [-sd[1], sd[0]];
  const Cc = [mid[0] + perp[0] * p.bend * S, mid[1] + perp[1] * p.bend * S];
  const u = 1 - GEO.sh / GEO.spine;                     // shoulder point on the spine curve
  const Sh = [(1 - u) * (1 - u) * Hp[0] + 2 * (1 - u) * u * Cc[0] + u * u * N[0],
              (1 - u) * (1 - u) * Hp[1] + 2 * (1 - u) * u * Cc[1] + u * u * N[1]];
  const lag = clamp(p.hdx / GEO.headR * .9, -.35, .35);
  const hd = dirv(Math.PI - (p.lean + p.head + lag)), hr = GEO.headR * S;
  const Hd = [N[0] + hd[0] * hr, N[1] + hd[1] * hr];
  const arm = (a, b) => { const e = dirv(a), E = [Sh[0] + e[0] * GEO.upper * S, Sh[1] + e[1] * GEO.upper * S];
    const w = dirv(a + b); return [E, [E[0] + w[0] * GEO.fore * S, E[1] + w[1] * GEO.fore * S]]; };
  const footL = [bx + (-GEO.stance + p.lfx) * S, gy - p.lfy * S];
  const footR = [bx + (GEO.stance + p.rfx) * S, gy - p.rfy * S];
  return { Hp, N, Cc, Sh, Hd, aL: arm(p.la, p.lb), aR: arm(p.ra, p.rb),
    lL: ik(Hp, footL, GEO.thigh * S, GEO.shin * S, -1), lR: ik(Hp, footR, GEO.thigh * S, GEO.shin * S, 1) };
}

// ---------------- Target poses (mutate p; breathing runs first, poses override on top) ----------------
function idle(p, t, ph) {
  p.hx += .005 * Math.sin(t * 1.25 + ph);
  p.lean += .012 * Math.sin(t * 1.05 + ph * 1.3);
  p.hy += .004 * (.5 + .5 * Math.sin(t * 2.1 + ph));
  p.la -= .03 * Math.sin(t * 1.5 + ph);
  p.ra += .03 * Math.sin(t * 1.5 + ph + .7);
}
const POSES = {
  idle,
  // greeting wave: right arm up, forearm swinging
  wave(p, t, ph) {
    const w = Math.sin(2 * Math.PI * 1.7 * t + ph) * ss(seg(t, 0, .3));
    p.ra = 2.35; p.rb = .45 + .6 * w; p.lean += .02; p.head += .04;
  },
  // marching in place: feet alternate, arms swing against the legs
  walk(p, t, ph) {
    const w = t * 2 * Math.PI * 1.6 + ph, s = Math.sin(w), c = Math.cos(w);
    p.lfx = .07 * s; p.lfy = .05 * Math.max(0, s);
    p.rfx = -.07 * s; p.rfy = .05 * Math.max(0, -s);
    p.la += -.12 * s; p.ra += .12 * s;
    p.lean += .04; p.hy += .008 * Math.abs(c);
  },
};

// ---------------- Plan → scene ----------------
function validate(plan) {
  if (!plan || typeof plan !== 'object') throw new Error('plan must be an object');
  if (!(plan.duration > 0)) throw new Error('plan.duration must be a positive number of seconds');
  if (!Array.isArray(plan.actors) || !plan.actors.length) throw new Error('plan.actors must be a non-empty array');
  for (const a of plan.actors) {
    if (typeof a.x !== 'number') throw new Error(`actor ${a.id ?? '?'}: x must be a number (0..1 of width)`);
    let prev = -Infinity;
    for (const b of a.beats || []) {
      if (typeof b.t !== 'number') throw new Error(`actor ${a.id ?? '?'}: beat t must be a number`);
      if (b.t <= prev) throw new Error(`actor ${a.id ?? '?'}: beats must be strictly increasing in t`);
      if (b.pose && !(b.pose in POSES)) throw new Error(`actor ${a.id ?? '?'}: unknown pose "${b.pose}"`);
      if (b.x != null && typeof b.x !== 'number') throw new Error(`actor ${a.id ?? '?'}: beat x must be a number`);
      prev = b.t;
    }
  }
}

const activeBeat = (a, t) => { let b = null; for (const k of a.beats || []) { if (k.t <= t) b = k; else break; } return b; };

// target pose of one actor at time t (stepwise beats; the springs smooth the steps)
function target(a, t) {
  const p = rest();
  idle(p, t, a.phase);
  const b = activeBeat(a, t);
  if (b && b.pose && b.pose !== 'idle') POSES[b.pose](p, t, a.phase);
  return p;
}

// x keyframes: the actor's base x, overridden by any beat that carries x (smoothstep between keys)
function xTrack(a) {
  const keys = (a.beats || []).filter(b => b.x != null).map(b => [b.t, b.x]);
  if (!keys.length || keys[0][0] > 0) keys.unshift([0, a.x]);
  return t => {
    if (t <= keys[0][0]) return keys[0][1];
    for (let i = 0; i < keys.length - 1; i++) {
      if (t <= keys[i + 1][0]) return lerp(keys[i][1], keys[i + 1][1], ss(seg(t, keys[i][0], keys[i + 1][0])));
    }
    return keys[keys.length - 1][1];
  };
}

// Damped-spring simulation of one actor over [0, dur], recorded at 240 Hz (adapted from the demo).
// render(t) only reads this table → order-independent, byte-identical between runs.
function simulate(a, dur) {
  const dt = 1 / 1200, every = 5, frames = [];
  const p0 = target(a, 0), v = {}; for (const k of KEYS) v[k] = 0;
  const st = { p: p0, v, hp: null, hv: [0, 0] };
  let step = 0;
  for (let t = 0; t <= dur + 1e-9; t += dt, step++) {
    if (step % every === 0) frames.push({ ...st.p });
    const tg = target(a, t);
    for (const k in SPR) { const [w, z] = SPR[k]; const acc = w * w * (tg[k] - st.p[k]) - 2 * z * w * st.v[k]; st.v[k] += acc * dt; st.p[k] += st.v[k] * dt; }
    const R = [st.p.hx + Math.sin(st.p.lean) * GEO.spine + Math.sin(st.p.lean + st.p.head) * GEO.headR,
               GEO.hipH - st.p.hy + Math.cos(st.p.lean) * GEO.spine + Math.cos(st.p.lean + st.p.head) * GEO.headR];
    if (!st.hp) st.hp = [...R];
    const [w, z] = HEADSPR;
    for (let q = 0; q < 2; q++) { const acc = w * w * (R[q] - st.hp[q]) - 2 * z * w * st.hv[q]; st.hv[q] += acc * dt; st.hp[q] += st.hv[q] * dt; }
    st.p.hdx = clamp(st.hp[0] - R[0], -.03, .03);
    st.p.hdy = clamp(st.hp[1] - R[1], -.03, .03);
  }
  if (frames.length < 2) frames.push({ ...frames[0] });
  return {
    at(t) {
      const f = t * 240, i = clamp(Math.floor(f), 0, frames.length - 2), u = clamp(f - i);
      const A = frames[i], B = frames[i + 1], q = {};
      for (const k of KEYS) q[k] = lerp(A[k], B[k], u);
      return q;
    },
  };
}

// ---------------- Drawing (even-hose style: one quadratic curve per limb, one line weight) ----------------
function ctrl(A, B, E, k) { const m = [(A[0] + E[0]) / 2, (A[1] + E[1]) / 2]; return [B[0] + (B[0] - m[0]) * k, B[1] + (B[1] - m[1]) * k]; }

function drawFigure(g, f, p) {
  const S = f.S, j = joints(f, p), lw = 7 * clamp(Math.sqrt(S / 380), .6, 1.05), k = .8;
  g.save();
  g.lineCap = 'round'; g.lineJoin = 'round';
  g.strokeStyle = f.col;
  g.lineWidth = lw;
  g.beginPath();
  for (const [K, F] of [j.lL, j.lR]) { const Q = ctrl(j.Hp, K, F, k); g.moveTo(j.Hp[0], j.Hp[1]); g.quadraticCurveTo(Q[0], Q[1], F[0], F[1]); }
  g.moveTo(j.Hp[0], j.Hp[1]); g.quadraticCurveTo(j.Cc[0], j.Cc[1], j.N[0], j.N[1]);
  for (const [El, Hn] of [j.aL, j.aR]) { const Q = ctrl(j.Sh, El, Hn, k); g.moveTo(j.Sh[0], j.Sh[1]); g.quadraticCurveTo(Q[0], Q[1], Hn[0], Hn[1]); }
  g.stroke();
  g.fillStyle = f.fill;                                      // head disc covers the spine tip inside it
  g.beginPath(); g.arc(j.Hd[0], j.Hd[1], GEO.headR * S, 0, Math.PI * 2); g.fill();
  g.lineWidth = lw * .95; g.strokeStyle = f.col; g.stroke();
  g.restore();
}

// ---------------- Scene ----------------
export function buildScene(plan) {
  validate(plan);
  const rnd = mulberry((plan.seed | 0) || 1);
  const stage = plan.stage || {};
  const actors = plan.actors.map(a => ({
    ...a,
    phase: a.phase ?? rnd() * Math.PI * 2,
    scale: a.scale ?? 400,
    color: a.color ?? '#24242C',
    fill: a.fill ?? stage.bg ?? '#F3F0EA',
    sim: null,
    xAt: null,
  }));
  for (const a of actors) { a.sim = simulate(a, plan.duration); a.xAt = xTrack(a); }
  return { dur: plan.duration, stage, actors };
}

export function drawScene(g, scene, W, H, t) {
  const st = scene.stage;
  g.fillStyle = st.bg || '#F3F0EA';
  g.fillRect(0, 0, W, H);
  if (st.ground !== false) {                                // the system line every figure stands on
    const y = (st.ground_y ?? .82) * H;
    g.save(); g.lineCap = 'round'; g.strokeStyle = st.ground_color || '#E2DDD2'; g.lineWidth = 7;
    g.beginPath(); g.moveTo(0, y); g.lineTo(W, y); g.stroke(); g.restore();
  }
  const gy = (st.ground_y ?? .82) * H;
  for (const a of scene.actors) {
    drawFigure(g, { x: a.xAt(t) * W, gy, S: a.scale, col: a.color, fill: a.fill }, a.sim.at(t));
  }
}

// Standalone default for manual renders (node core/render/still.mjs engine-js 0).
export const DEFAULT_PLAN = {
  seed: 7,
  duration: 4,
  stage: { bg: '#F3F0EA', ground: true, ground_y: .82 },
  actors: [
    { id: 'narrator', x: .3, scale: 420, beats: [{ t: 0, pose: 'walk' }, { t: 1.6, pose: 'idle', x: .4 }, { t: 2.2, pose: 'wave' }] },
    { id: 'friend', x: .68, scale: 400, phase: 2.4, beats: [{ t: 0, pose: 'idle' }, { t: 2.4, pose: 'wave' }] },
  ],
};
