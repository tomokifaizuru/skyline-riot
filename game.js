/* Skyline Riot v0.1 — original concept prototype
   Air Gear vibes × Jet Set Radio energy — original IP only */
(function () {
  'use strict';

  const VERSION = '0.1';
  const RUN_TIME = 90;
  const TAG_COUNT = 6;
  const GRAVITY = 28;
  const ACCEL = 38;
  const MAX_SPEED = 22;
  const AIR_CTRL = 0.45;
  const JUMP_V = 11.5;
  const JUMP_HOLD_EXTRA = 7;
  const BOOST_SPEED = 34;
  const BOOST_COST = 0.35;
  const FRICTION = 8;
  const GRIND_SPEED = 18;
  const WALL_SPEED = 14;

  // ---------- DOM ----------
  const canvas = document.getElementById('game');
  const overlay = document.getElementById('overlay');
  const menuPanel = document.getElementById('menuPanel');
  const howPanel = document.getElementById('howPanel');
  const pausePanel = document.getElementById('pausePanel');
  const endPanel = document.getElementById('endPanel');
  const scoreVal = document.getElementById('scoreVal');
  const comboVal = document.getElementById('comboVal');
  const timeVal = document.getElementById('timeVal');
  const tagVal = document.getElementById('tagVal');
  const boostFill = document.getElementById('boostFill');
  const comboFlash = document.getElementById('comboFlash');
  const arrowHint = document.getElementById('arrowHint');
  const tagToast = document.getElementById('tagToast');
  const stickEl = document.getElementById('stick');
  const stickKnob = document.getElementById('stickKnob');

  // ---------- STATE ----------
  let mode = 'menu'; // menu | how | play | pause | end
  let score = 0, combo = 0, comboTimer = 0, boost = 0.2;
  let timeLeft = RUN_TIME, tagsDone = 0;
  let keys = Object.create(null);
  let stick = { x: 0, y: 0 };
  let jumpHeld = false, jumpWas = false, jumpBuffered = 0;
  let wantBoost = false, wantTag = false, wantTrick = false;
  let lastT = 0;
  let autoDemo = false; // Playwright can set window.__SR_AUTO = true

  // ---------- AUDIO ----------
  let audioCtx = null, masterGain = null, musicNodes = null, muted = false;
  function ensureAudio() {
    if (audioCtx) return;
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    audioCtx = new AC();
    masterGain = audioCtx.createGain();
    masterGain.gain.value = 0.35;
    masterGain.connect(audioCtx.destination);
  }
  function beep(freq, dur, type, vol) {
    if (!audioCtx || muted) return;
    const o = audioCtx.createOscillator();
    const g = audioCtx.createGain();
    o.type = type || 'square';
    o.frequency.value = freq;
    g.gain.value = vol || 0.08;
    o.connect(g); g.connect(masterGain);
    const t = audioCtx.currentTime;
    g.gain.setValueAtTime(vol || 0.08, t);
    g.gain.exponentialRampToValueAtTime(0.001, t + dur);
    o.start(t); o.stop(t + dur + 0.02);
  }
  function sfxJump() { beep(220, 0.08, 'triangle', 0.1); beep(440, 0.12, 'square', 0.06); }
  function sfxLand() { beep(90, 0.08, 'sawtooth', 0.05); }
  function sfxGrind() { beep(160 + Math.random() * 40, 0.05, 'sawtooth', 0.035); }
  function sfxTag() { beep(523, 0.1, 'square', 0.1); beep(784, 0.15, 'triangle', 0.08); }
  function sfxTrick() { beep(660, 0.06, 'square', 0.07); beep(990, 0.08, 'triangle', 0.05); }
  function sfxBoost() { beep(110, 0.2, 'sawtooth', 0.09); beep(220, 0.25, 'triangle', 0.06); }
  function sfxWin() { [523,659,784,1046].forEach((f,i)=>setTimeout(()=>beep(f,0.15,'square',0.08), i*90)); }
  function sfxLose() { [392,330,262].forEach((f,i)=>setTimeout(()=>beep(f,0.18,'sawtooth',0.07), i*120)); }

  function startMusic() {
    ensureAudio();
    if (!audioCtx || musicNodes) return;
    const tempo = 112;
    const beat = 60 / tempo;
    const now = audioCtx.currentTime + 0.05;
    const bass = audioCtx.createOscillator();
    const bassG = audioCtx.createGain();
    bass.type = 'triangle';
    bassG.gain.value = 0.04;
    bass.connect(bassG); bassG.connect(masterGain);
    const lead = audioCtx.createOscillator();
    const leadG = audioCtx.createGain();
    lead.type = 'square';
    leadG.gain.value = 0.02;
    lead.connect(leadG); leadG.connect(masterGain);
    const notes = [110, 138.59, 164.81, 146.83, 110, 123.47, 146.83, 164.81];
    const leadNotes = [329.63, 392, 440, 392, 349.23, 329.63, 293.66, 329.63];
    let step = 0;
    function schedule() {
      if (!musicNodes) return;
      const t0 = audioCtx.currentTime;
      for (let i = 0; i < 8; i++) {
        const t = t0 + i * beat * 0.5;
        const n = notes[(step + i) % notes.length];
        const ln = leadNotes[(step + i) % leadNotes.length];
        bass.frequency.setValueAtTime(n, t);
        lead.frequency.setValueAtTime(ln, t);
        leadG.gain.setValueAtTime(0.001, t);
        leadG.gain.linearRampToValueAtTime(0.025, t + 0.02);
        leadG.gain.exponentialRampToValueAtTime(0.001, t + beat * 0.45);
      }
      step = (step + 8) % notes.length;
      musicNodes.timer = setTimeout(schedule, beat * 8 * 500);
    }
    bass.start(now); lead.start(now);
    musicNodes = { bass, lead, bassG, leadG, timer: null };
    schedule();
  }
  function stopMusic() {
    if (!musicNodes) return;
    clearTimeout(musicNodes.timer);
    try { musicNodes.bass.stop(); musicNodes.lead.stop(); } catch (e) {}
    musicNodes = null;
  }

  // ---------- THREE ----------
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor(0x1a2340, 1);
  renderer.shadowMap.enabled = false;

  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0x1a2340, 40, 120);

  const camera = new THREE.PerspectiveCamera(55, 1, 0.1, 200);
  camera.position.set(0, 12, 18);

  // Cel gradient maps
  function makeToonGradient(steps) {
    const c = document.createElement('canvas');
    c.width = steps; c.height = 1;
    const ctx = c.getContext('2d');
    for (let i = 0; i < steps; i++) {
      const v = Math.floor((i / (steps - 1)) * 255);
      ctx.fillStyle = `rgb(${v},${v},${v})`;
      ctx.fillRect(i, 0, 1, 1);
    }
    const tex = new THREE.CanvasTexture(c);
    tex.minFilter = THREE.NearestFilter;
    tex.magFilter = THREE.NearestFilter;
    return tex;
  }
  const toonGrad = makeToonGradient(4);

  function toonMat(color, emissive) {
    const m = new THREE.MeshToonMaterial({
      color: new THREE.Color(color),
      gradientMap: toonGrad,
      emissive: new THREE.Color(emissive || 0x000000),
      emissiveIntensity: emissive ? 0.55 : 0
    });
    return m;
  }

  function addOutline(mesh, color, scale) {
    const geo = mesh.geometry;
    const mat = new THREE.MeshBasicMaterial({
      color: color || 0x0a0e1a,
      side: THREE.BackSide
    });
    const outline = new THREE.Mesh(geo, mat);
    outline.scale.multiplyScalar(scale || 1.045);
    mesh.add(outline);
    return outline;
  }

  // Lights
  scene.add(new THREE.AmbientLight(0x6a7ab0, 0.55));
  const sun = new THREE.DirectionalLight(0xffe8c8, 0.85);
  sun.position.set(20, 40, 10);
  scene.add(sun);
  const fill = new THREE.DirectionalLight(0x66ccff, 0.35);
  fill.position.set(-15, 10, -10);
  scene.add(fill);
  const neon = new THREE.PointLight(0xff3eb5, 0.8, 40);
  neon.position.set(0, 8, 0);
  scene.add(neon);

  // ---------- WORLD ----------
  const world = new THREE.Group();
  scene.add(world);
  const solids = []; // {box: Box3, mesh, type: 'ground'|'ramp'|'roof'|'wall'}
  const rails = [];  // {a: Vector3, b: Vector3, mesh}
  const walls = [];  // wall ride planes {normal, point, minY, maxY, minAlong, maxAlong, along}
  const tagSpots = [];

  function addSolid(mesh, type) {
    mesh.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(mesh);
    solids.push({ box, mesh, type: type || 'ground' });
    world.add(mesh);
  }

  function boxMesh(w, h, d, color, y) {
    const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), toonMat(color));
    m.position.y = y !== undefined ? y : h / 2;
    addOutline(m, 0x0a0e1a, 1.03);
    return m;
  }

  // Sky dome (simple)
  const sky = new THREE.Mesh(
    new THREE.SphereGeometry(150, 24, 16),
    new THREE.MeshBasicMaterial({ color: 0x152048, side: THREE.BackSide })
  );
  scene.add(sky);

  // Stars
  (function makeStars() {
    const g = new THREE.BufferGeometry();
    const n = 200;
    const pos = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const th = Math.random() * Math.PI * 2;
      const ph = Math.random() * Math.PI * 0.45;
      const r = 80 + Math.random() * 40;
      pos[i*3] = Math.sin(ph) * Math.cos(th) * r;
      pos[i*3+1] = Math.cos(ph) * r * 0.6 + 20;
      pos[i*3+2] = Math.sin(ph) * Math.sin(th) * r;
    }
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    scene.add(new THREE.Points(g, new THREE.PointsMaterial({ color: 0xffffff, size: 0.35 })));
  })();

  // Moon
  const moon = new THREE.Mesh(new THREE.SphereGeometry(3.5, 16, 16), toonMat(0xfff2c8, 0x554422));
  moon.position.set(-35, 40, -50);
  scene.add(moon);

  function buildCity() {
    // Ground plaza
    const ground = boxMesh(80, 1, 80, 0x2a3358, -0.5);
    addSolid(ground, 'ground');

    // Street strips
    const road = new THREE.Mesh(new THREE.BoxGeometry(12, 0.05, 70), toonMat(0x1c2238));
    road.position.set(0, 0.02, 0);
    world.add(road);
    const road2 = new THREE.Mesh(new THREE.BoxGeometry(70, 0.05, 12), toonMat(0x1c2238));
    road2.position.set(0, 0.025, 0);
    world.add(road2);

    // Sidewalks / plaza color accents
    [[-18, 0, 18, 0x31406e], [18, 0, 18, 0x31406e], [-18, 0, -18, 0x31406e], [18, 0, -18, 0x31406e]].forEach(([x,y,z,c]) => {
      const p = boxMesh(14, 0.2, 14, c, 0.1);
      p.position.x = x; p.position.z = z;
      addSolid(p, 'ground');
    });

    // Buildings (rooftops)
    const bdefs = [
      { x: -22, z: -22, w: 14, d: 14, h: 10, c: 0x3a4a7a },
      { x: 22, z: -20, w: 16, d: 12, h: 14, c: 0x44558a },
      { x: -20, z: 22, w: 12, d: 16, h: 12, c: 0x3d5080 },
      { x: 24, z: 22, w: 14, d: 14, h: 18, c: 0x4a5c94 },
      { x: 0, z: -28, w: 18, d: 10, h: 8, c: 0x364878 },
      { x: -30, z: 0, w: 10, d: 18, h: 11, c: 0x405086 },
      { x: 30, z: 2, w: 10, d: 16, h: 9, c: 0x3c4c82 }
    ];
    bdefs.forEach(b => {
      const m = boxMesh(b.w, b.h, b.d, b.c, b.h / 2);
      m.position.x = b.x; m.position.z = b.z;
      addSolid(m, 'roof');
      // neon trim
      const trim = new THREE.Mesh(
        new THREE.BoxGeometry(b.w + 0.2, 0.25, b.d + 0.2),
        toonMat(Math.random() > 0.5 ? 0xff3eb5 : 0x3ef0ff, Math.random() > 0.5 ? 0xff3eb5 : 0x3ef0ff)
      );
      trim.position.set(b.x, b.h + 0.05, b.z);
      world.add(trim);
      // wall faces for wall-ride (outward normals on long sides)
      const halfW = b.w / 2, halfD = b.d / 2;
      walls.push({
        normal: new THREE.Vector3(1, 0, 0), point: new THREE.Vector3(b.x + halfW, 0, b.z),
        minY: 0.5, maxY: b.h - 0.5, cx: b.x, cz: b.z, halfAlong: halfD, alongAxis: 'z'
      });
      walls.push({
        normal: new THREE.Vector3(-1, 0, 0), point: new THREE.Vector3(b.x - halfW, 0, b.z),
        minY: 0.5, maxY: b.h - 0.5, cx: b.x, cz: b.z, halfAlong: halfD, alongAxis: 'z'
      });
      walls.push({
        normal: new THREE.Vector3(0, 0, 1), point: new THREE.Vector3(b.x, 0, b.z + halfD),
        minY: 0.5, maxY: b.h - 0.5, cx: b.x, cz: b.z, halfAlong: halfW, alongAxis: 'x'
      });
      walls.push({
        normal: new THREE.Vector3(0, 0, -1), point: new THREE.Vector3(b.x, 0, b.z - halfD),
        minY: 0.5, maxY: b.h - 0.5, cx: b.x, cz: b.z, halfAlong: halfW, alongAxis: 'x'
      });
    });

    // Ramps onto rooftops
    function addRamp(x, z, rotY, len, rise, width) {
      const geo = new THREE.BoxGeometry(width, 0.4, len);
      const m = new THREE.Mesh(geo, toonMat(0x5dff9a));
      addOutline(m, 0x0a0e1a, 1.04);
      const ang = Math.atan2(rise, len);
      m.rotation.x = -ang;
      m.rotation.order = 'YXZ';
      m.rotation.y = rotY;
      m.position.set(x, rise / 2, z);
      // Approximate solid as thin box following ramp
      addSolid(m, 'ramp');
      // invisible collision slabs
      const steps = 6;
      for (let i = 0; i < steps; i++) {
        const t = (i + 0.5) / steps;
        const localZ = -len / 2 + t * len;
        const hx = Math.sin(rotY) * localZ;
        const hz = Math.cos(rotY) * localZ;
        const hy = t * rise;
        const slab = new THREE.Mesh(new THREE.BoxGeometry(width, 0.5, len / steps), new THREE.MeshBasicMaterial({ visible: false }));
        slab.position.set(x + hx, hy, z + hz);
        addSolid(slab, 'ramp');
      }
    }
    addRamp(-22, -12, 0, 10, 10, 4);
    addRamp(22, -11, 0, 12, 14, 4);
    addRamp(-20, 12, Math.PI, 12, 12, 4);
    addRamp(24, 12, Math.PI, 14, 18, 4);
    addRamp(-8, -28, Math.PI / 2, 10, 8, 4);
    addRamp(-22, 0, Math.PI / 2, 10, 11, 3.5);

    // Rails
    function addRail(x1, y1, z1, x2, y2, z2) {
      const a = new THREE.Vector3(x1, y1, z1);
      const b = new THREE.Vector3(x2, y2, z2);
      const dir = new THREE.Vector3().subVectors(b, a);
      const len = dir.length();
      const mid = new THREE.Vector3().addVectors(a, b).multiplyScalar(0.5);
      const rail = new THREE.Mesh(
        new THREE.CylinderGeometry(0.12, 0.12, len, 8),
        toonMat(0x3ef0ff, 0x1a8899)
      );
      rail.position.copy(mid);
      rail.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().normalize());
      world.add(rail);
      const glow = new THREE.Mesh(
        new THREE.CylinderGeometry(0.2, 0.2, len, 8),
        new THREE.MeshBasicMaterial({ color: 0x3ef0ff, transparent: true, opacity: 0.18 })
      );
      glow.position.copy(mid);
      glow.quaternion.copy(rail.quaternion);
      world.add(glow);
      rails.push({ a, b, dir: dir.normalize(), len, mesh: rail });
    }
    addRail(-8, 0.6, -6, 8, 0.6, -6);
    addRail(-6, 0.6, 8, 6, 0.6, 14);
    addRail(-22, 10.3, -14, -22, 10.3, -8);
    addRail(22, 14.3, -14, 16, 14.3, -20);
    addRail(-14, 12.3, 22, -8, 8.2, 10);
    addRail(10, 0.6, -2, 18, 0.6, 6);
    addRail(0, 8.3, -28, 8, 8.3, -28);

    // Tag spots
    const tagPositions = [
      [0, 0.1, 0],
      [-22, 10.15, -22],
      [22, 14.15, -20],
      [-20, 12.15, 22],
      [24, 18.15, 22],
      [0, 8.15, -28]
    ];
    tagPositions.forEach((p, i) => {
      const marker = new THREE.Mesh(
        new THREE.CylinderGeometry(1.2, 1.2, 0.15, 20),
        toonMat(0xffe566, 0xaa8833)
      );
      marker.position.set(p[0], p[1] + 0.08, p[2]);
      world.add(marker);
      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(1.4, 0.08, 8, 24),
        new THREE.MeshBasicMaterial({ color: 0xff3eb5 })
      );
      ring.rotation.x = Math.PI / 2;
      ring.position.copy(marker.position);
      ring.position.y += 0.2;
      world.add(ring);
      const decal = new THREE.Mesh(
        new THREE.PlaneGeometry(2.2, 2.2),
        new THREE.MeshBasicMaterial({ color: 0xff3eb5, transparent: true, opacity: 0, side: THREE.DoubleSide })
      );
      decal.rotation.x = -Math.PI / 2;
      decal.position.set(p[0], p[1] + 0.12, p[2]);
      world.add(decal);
      tagSpots.push({ pos: new THREE.Vector3(p[0], p[1], p[2]), marker, ring, decal, tagged: false, idx: i });
    });

    // Props: cones, neon signs
    for (let i = 0; i < 8; i++) {
      const cone = new THREE.Mesh(new THREE.ConeGeometry(0.35, 0.9, 8), toonMat(0xff7a3e));
      cone.position.set((Math.random() - 0.5) * 40, 0.45, (Math.random() - 0.5) * 40);
      if (Math.abs(cone.position.x) < 4 && Math.abs(cone.position.z) < 4) cone.position.x += 8;
      addOutline(cone);
      world.add(cone);
    }
  }
  buildCity();

  // ---------- PLAYER ----------
  const player = {
    pos: new THREE.Vector3(0, 1.2, 8),
    vel: new THREE.Vector3(),
    yaw: Math.PI,
    state: 'ground', // ground | air | grind | wall
    grindRail: null, grindT: 0, grindBal: 0,
    wall: null, wallTime: 0,
    jumpTime: 0, canCoyote: 0,
    trickSpin: 0, trickFlip: 0, airTricks: 0,
    mesh: null, skates: null
  };

  function buildSkater() {
    const g = new THREE.Group();
    // body
    const torso = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.85, 0.45), toonMat(0x3ef0ff));
    torso.position.y = 1.15;
    addOutline(torso);
    g.add(torso);
    // hoodie accent
    const hood = new THREE.Mesh(new THREE.BoxGeometry(0.75, 0.35, 0.5), toonMat(0xff3eb5));
    hood.position.y = 1.45;
    addOutline(hood);
    g.add(hood);
    // head
    const head = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.5, 0.5), toonMat(0xffe0c2));
    head.position.y = 1.85;
    addOutline(head);
    g.add(head);
    // hair
    const hair = new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.25, 0.55), toonMat(0x1a1a28));
    hair.position.y = 2.1;
    g.add(hair);
    // legs
    const legL = new THREE.Mesh(new THREE.BoxGeometry(0.25, 0.7, 0.3), toonMat(0x243056));
    legL.position.set(-0.18, 0.55, 0);
    g.add(legL);
    const legR = legL.clone();
    legR.position.x = 0.18;
    g.add(legR);
    // skates
    const skateGeo = new THREE.BoxGeometry(0.35, 0.18, 0.9);
    const skateMat = toonMat(0xffe566, 0x665522);
    const sL = new THREE.Mesh(skateGeo, skateMat);
    sL.position.set(-0.18, 0.12, 0.1);
    const sR = new THREE.Mesh(skateGeo, skateMat);
    sR.position.set(0.18, 0.12, 0.1);
    // thruster glow
    const thr = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.12, 0.25, 8), toonMat(0x3ef0ff, 0x3ef0ff));
    thr.rotation.x = Math.PI / 2;
    thr.position.set(0, 0, -0.5);
    sL.add(thr.clone()); sR.add(thr);
    g.add(sL); g.add(sR);
    // arms
    const armL = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.65, 0.22), toonMat(0x3ef0ff));
    armL.position.set(-0.5, 1.15, 0);
    g.add(armL);
    const armR = armL.clone();
    armR.position.x = 0.5;
    g.add(armR);

    g.scale.setScalar(0.95);
    scene.add(g);
    player.mesh = g;
    player.skates = [sL, sR];
  }
  buildSkater();

  // Camera follow
  const camTarget = new THREE.Vector3();
  const camPos = new THREE.Vector3(0, 10, 16);

  // ---------- PHYSICS HELPERS ----------
  function groundHeightAt(x, z) {
    let best = 0;
    const probe = new THREE.Vector3(x, 50, z);
    for (const s of solids) {
      if (x < s.box.min.x - 0.05 || x > s.box.max.x + 0.05) continue;
      if (z < s.box.min.z - 0.05 || z > s.box.max.z + 0.05) continue;
      const top = s.box.max.y;
      if (top > best && top < probe.y) best = top;
    }
    return best;
  }

  function nearestRail(pos, maxDist) {
    let best = null, bestD = maxDist, bestT = 0;
    for (const r of rails) {
      const ab = new THREE.Vector3().subVectors(r.b, r.a);
      const ap = new THREE.Vector3().subVectors(pos, r.a);
      const t = Math.max(0, Math.min(1, ap.dot(ab) / ab.lengthSq()));
      const closest = new THREE.Vector3().copy(r.a).addScaledVector(ab, t);
      const d = closest.distanceTo(pos);
      if (d < bestD) { bestD = d; best = r; bestT = t; }
    }
    return best ? { rail: best, t: bestT, dist: bestD } : null;
  }

  function findWallRide(pos, vel) {
    const speed = vel.length();
    if (speed < 6) return null;
    for (const w of walls) {
      const toWall = new THREE.Vector3().subVectors(pos, w.point);
      const dist = toWall.dot(w.normal);
      if (dist < 0.2 || dist > 1.4) continue;
      if (pos.y < w.minY || pos.y > w.maxY) continue;
      const along = w.alongAxis === 'z' ? pos.z - w.cz : pos.x - w.cx;
      if (Math.abs(along) > w.halfAlong - 0.3) continue;
      // moving mostly parallel / into wall
      const into = -vel.clone().normalize().dot(w.normal);
      if (into < 0.15) continue;
      return w;
    }
    return null;
  }

  // ---------- GAME FLOW ----------
  function showOverlay(which) {
    overlay.classList.add('visible');
    menuPanel.style.display = which === 'menu' ? '' : 'none';
    howPanel.style.display = which === 'how' ? '' : 'none';
    pausePanel.style.display = which === 'pause' ? '' : 'none';
    endPanel.style.display = which === 'end' ? '' : 'none';
  }
  function hideOverlay() { overlay.classList.remove('visible'); }

  function resetRun() {
    score = 0; combo = 0; comboTimer = 0; boost = 0.25;
    timeLeft = RUN_TIME; tagsDone = 0;
    player.pos.set(0, 1.2, 8);
    player.vel.set(0, 0, 0);
    player.yaw = Math.PI;
    player.state = 'ground';
    player.grindRail = null; player.wall = null;
    player.trickSpin = 0; player.trickFlip = 0; player.airTricks = 0;
    tagSpots.forEach(t => {
      t.tagged = false;
      t.decal.material.opacity = 0;
      t.marker.material.emissiveIntensity = 0.55;
      t.ring.visible = true;
    });
    updateHUD();
  }

  function startRun() {
    ensureAudio();
    if (audioCtx && audioCtx.state === 'suspended') audioCtx.resume();
    startMusic();
    resetRun();
    mode = 'play';
    hideOverlay();
    canvas.focus();
  }

  function endRun(win) {
    mode = 'end';
    stopMusic();
    if (win) sfxWin(); else sfxLose();
    document.getElementById('endTitle').textContent = win ? 'DISTRICT CLEARED!' : 'TIME UP';
    document.getElementById('endTitle').className = 'resultBig ' + (win ? 'win' : 'lose');
    document.getElementById('endMsg').textContent = win
      ? 'You tagged every spot. Harbor Heights is yours.'
      : 'The crew will remember this. Try again.';
    document.getElementById('endScore').textContent = String(score);
    showOverlay('end');
  }

  function addScore(pts, label) {
    const mult = Math.max(1, combo);
    const gained = Math.floor(pts * mult);
    score += gained;
    combo += 1;
    comboTimer = 2.2;
    boost = Math.min(1, boost + 0.08 + pts * 0.002);
    if (combo >= 2) {
      comboFlash.textContent = (label ? label + ' ' : '') + 'COMBO x' + combo;
      comboFlash.classList.add('show');
      clearTimeout(comboFlash._t);
      comboFlash._t = setTimeout(() => comboFlash.classList.remove('show'), 500);
    }
    updateHUD();
  }

  function updateHUD() {
    scoreVal.textContent = String(score);
    comboVal.textContent = 'x' + combo;
    const m = Math.floor(timeLeft / 60);
    const s = Math.floor(timeLeft % 60);
    timeVal.textContent = m + ':' + String(s).padStart(2, '0');
    tagVal.textContent = tagsDone + '/' + TAG_COUNT;
    boostFill.style.width = Math.floor(boost * 100) + '%';
  }

  function nearestUntagged() {
    let best = null, bestD = 1e9;
    for (const t of tagSpots) {
      if (t.tagged) continue;
      const d = t.pos.distanceTo(player.pos);
      if (d < bestD) { bestD = d; best = t; }
    }
    return best;
  }

  // ---------- INPUT ----------
  function isTouchDevice() {
    return matchMedia('(pointer: coarse)').matches || 'ontouchstart' in window;
  }
  if (isTouchDevice()) document.body.classList.add('touch');

  window.addEventListener('keydown', (e) => {
    keys[e.code] = true;
    if (['Space', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.code)) e.preventDefault();
    if (e.code === 'Space') jumpBuffered = 0.15;
    if (e.code === 'KeyF') wantTag = true;
    if (e.code === 'ShiftLeft' || e.code === 'ShiftRight') wantBoost = true;
    if (e.code === 'KeyQ' || e.code === 'KeyE') wantTrick = true;
    if (e.code === 'Escape' || e.code === 'KeyP') {
      if (mode === 'play') { mode = 'pause'; stopMusic(); showOverlay('pause'); }
      else if (mode === 'pause') { mode = 'play'; startMusic(); hideOverlay(); }
    }
  });
  window.addEventListener('keyup', (e) => { keys[e.code] = false; });

  // Virtual stick
  let stickTouchId = null;
  function setStickFromEvent(clientX, clientY) {
    const r = stickEl.getBoundingClientRect();
    const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    let dx = (clientX - cx) / (r.width / 2);
    let dy = (clientY - cy) / (r.height / 2);
    const mag = Math.hypot(dx, dy) || 1;
    if (mag > 1) { dx /= mag; dy /= mag; }
    stick.x = dx; stick.y = dy;
    stickKnob.style.transform = `translate(calc(-50% + ${dx * 28}px), calc(-50% + ${dy * 28}px))`;
  }
  stickEl.addEventListener('pointerdown', (e) => {
    stickTouchId = e.pointerId;
    stickEl.setPointerCapture(e.pointerId);
    setStickFromEvent(e.clientX, e.clientY);
  });
  stickEl.addEventListener('pointermove', (e) => {
    if (e.pointerId !== stickTouchId) return;
    setStickFromEvent(e.clientX, e.clientY);
  });
  function clearStick() {
    stickTouchId = null; stick.x = 0; stick.y = 0;
    stickKnob.style.transform = 'translate(-50%, -50%)';
  }
  stickEl.addEventListener('pointerup', clearStick);
  stickEl.addEventListener('pointercancel', clearStick);

  function bindHold(btn, on, off) {
    const down = (e) => { e.preventDefault(); on(); };
    const up = (e) => { e.preventDefault(); off(); };
    btn.addEventListener('pointerdown', down);
    btn.addEventListener('pointerup', up);
    btn.addEventListener('pointerleave', up);
    btn.addEventListener('pointercancel', up);
  }
  bindHold(document.getElementById('btnJump'), () => { jumpHeld = true; jumpBuffered = 0.15; }, () => { jumpHeld = false; });
  bindHold(document.getElementById('btnBoost'), () => { wantBoost = true; }, () => { wantBoost = false; });
  bindHold(document.getElementById('btnTag'), () => { wantTag = true; }, () => {});

  document.getElementById('btnStart').onclick = () => startRun();
  document.getElementById('btnHow').onclick = () => { mode = 'how'; showOverlay('how'); };
  document.getElementById('btnHowBack').onclick = () => { mode = 'menu'; showOverlay('menu'); };
  document.getElementById('pauseBtn').onclick = () => {
    if (mode === 'play') { mode = 'pause'; stopMusic(); showOverlay('pause'); }
  };
  document.getElementById('btnResume').onclick = () => { mode = 'play'; startMusic(); hideOverlay(); };
  document.getElementById('btnToMenu').onclick = () => { mode = 'menu'; stopMusic(); showOverlay('menu'); };
  document.getElementById('btnRetry').onclick = () => startRun();
  document.getElementById('btnEndMenu').onclick = () => { mode = 'menu'; showOverlay('menu'); };

  // ---------- UPDATE ----------
  function getMoveInput() {
    let x = stick.x;
    let z = stick.y;
    if (keys['KeyA'] || keys['ArrowLeft']) x -= 1;
    if (keys['KeyD'] || keys['ArrowRight']) x += 1;
    if (keys['KeyW'] || keys['ArrowUp']) z -= 1;
    if (keys['KeyS'] || keys['ArrowDown']) z += 1;
    // auto demo for Playwright
    if (window.__SR_AUTO && mode === 'play') {
      const n = nearestUntagged();
      if (n) {
        const to = new THREE.Vector3().subVectors(n.pos, player.pos);
        // camera-relative-ish: world XZ
        x = Math.max(-1, Math.min(1, to.x * 0.15));
        z = Math.max(-1, Math.min(1, to.z * 0.15));
        if (player.state === 'ground' && to.y > 1.5) jumpBuffered = 0.1;
        if (player.state === 'air' && player.airTricks < 2) wantTrick = true;
        if (boost > 0.4 && to.length() > 12) wantBoost = true;
        if (to.length() < 2.2) wantTag = true;
      }
    }
    const len = Math.hypot(x, z);
    if (len > 1) { x /= len; z /= len; }
    return { x, z };
  }

  function tryJump(dt) {
    const want = jumpBuffered > 0 || (keys['Space'] && !jumpWas) || jumpHeld && jumpBuffered > 0;
    jumpBuffered = Math.max(0, jumpBuffered - dt);
    if (!want) return;
    if (player.state === 'ground' || player.canCoyote > 0 || player.state === 'grind' || player.state === 'wall') {
      player.vel.y = JUMP_V;
      player.state = 'air';
      player.grindRail = null;
      player.wall = null;
      player.jumpTime = 0;
      player.canCoyote = 0;
      player.airTricks = 0;
      jumpBuffered = 0;
      sfxJump();
      addScore(25, 'JUMP');
    } else if (player.state === 'air') {
      // trick
      doTrick();
      jumpBuffered = 0;
    }
  }

  function doTrick() {
    if (player.state !== 'air') return;
    player.airTricks += 1;
    player.trickSpin += Math.PI * (Math.random() > 0.5 ? 1 : -1);
    player.trickFlip += Math.PI * 0.5;
    sfxTrick();
    addScore(80 + player.airTricks * 20, 'TRICK');
    wantTrick = false;
  }

  function updatePlayer(dt) {
    const input = getMoveInput();
    // camera-relative movement
    const camYaw = Math.atan2(camera.position.x - player.pos.x, camera.position.z - player.pos.z);
    const forward = new THREE.Vector3(-Math.sin(camYaw), 0, -Math.cos(camYaw));
    // Actually third-person: stick forward goes away from camera look-at
    // Use player yaw based: easier — stick relative to camera behind player
    const lookYaw = player.yaw;
    // Better: move relative to camera view
    const viewForward = new THREE.Vector3();
    camera.getWorldDirection(viewForward);
    viewForward.y = 0; viewForward.normalize();
    const viewRight = new THREE.Vector3().crossVectors(viewForward, new THREE.Vector3(0, 1, 0)).normalize();
    // stick.y negative is forward on screen
    const wish = new THREE.Vector3()
      .addScaledVector(viewRight, input.x)
      .addScaledVector(viewForward, -input.z);
    if (wish.lengthSq() > 0.001) {
      wish.normalize();
      player.yaw = Math.atan2(wish.x, wish.z);
    }

    const boosting = (wantBoost || keys['ShiftLeft'] || keys['ShiftRight']) && boost > 0.05;
    if (boosting && player.state !== 'grind') {
      boost = Math.max(0, boost - BOOST_COST * dt);
      if (!player._boosting) { sfxBoost(); player._boosting = true; }
    } else player._boosting = false;
    wantBoost = false;

    const maxSp = boosting ? BOOST_SPEED : MAX_SPEED;

    if (player.state === 'grind' && player.grindRail) {
      const r = player.grindRail;
      player.grindT += (GRIND_SPEED * dt) / r.len;
      // balance
      const balIn = (keys['KeyA'] || keys['ArrowLeft'] ? -1 : 0) + (keys['KeyD'] || keys['ArrowRight'] ? 1 : 0) + stick.x;
      player.grindBal += balIn * dt * 2;
      player.grindBal *= (1 - dt * 0.5);
      if (Math.abs(player.grindBal) > 1.4 || player.grindT < 0 || player.grindT > 1) {
        // fall off
        player.state = 'air';
        player.vel.set(r.dir.x * GRIND_SPEED, 2, r.dir.z * GRIND_SPEED);
        player.grindRail = null;
      } else {
        const ab = new THREE.Vector3().subVectors(r.b, r.a);
        player.pos.copy(r.a).addScaledVector(ab, player.grindT);
        player.pos.y += 0.55;
        player.vel.set(r.dir.x * GRIND_SPEED, 0, r.dir.z * GRIND_SPEED);
        player.yaw = Math.atan2(r.dir.x, r.dir.z);
        if (Math.random() < dt * 8) sfxGrind();
        addScore(2, null);
        boost = Math.min(1, boost + dt * 0.12);
      }
      tryJump(dt);
    } else if (player.state === 'wall' && player.wall) {
      const w = player.wall;
      player.wallTime += dt;
      const alongDir = w.alongAxis === 'z' ? new THREE.Vector3(0, 0, 1) : new THREE.Vector3(1, 0, 0);
      // keep speed along wall
      const alongVel = player.vel.dot(alongDir) || (wish.dot(alongDir) * WALL_SPEED);
      const spd = Math.sign(alongVel || 1) * Math.min(WALL_SPEED, Math.abs(alongVel) + 4 * dt);
      player.vel.copy(alongDir).multiplyScalar(spd);
      player.vel.y = Math.max(player.vel.y - GRAVITY * 0.35 * dt, -2);
      player.pos.addScaledVector(player.vel, dt);
      player.pos.addScaledVector(w.normal, 0.55 - /* stick to wall */ 0);
      // snap distance to wall
      const toWall = new THREE.Vector3().subVectors(player.pos, w.point);
      const dist = toWall.dot(w.normal);
      player.pos.addScaledVector(w.normal, 0.55 - dist);
      const along = w.alongAxis === 'z' ? player.pos.z - w.cz : player.pos.x - w.cx;
      if (player.pos.y < w.minY || player.pos.y > w.maxY || Math.abs(along) > w.halfAlong || player.wallTime > 2.2) {
        player.state = 'air';
        player.wall = null;
        player.vel.addScaledVector(w.normal, 4);
      } else {
        addScore(3, null);
        boost = Math.min(1, boost + dt * 0.1);
      }
      tryJump(dt);
    } else {
      // ground / air
      const ctrl = player.state === 'air' ? AIR_CTRL : 1;
      if (wish.lengthSq() > 0.001) {
        player.vel.x += wish.x * ACCEL * ctrl * dt;
        player.vel.z += wish.z * ACCEL * ctrl * dt;
      } else if (player.state === 'ground') {
        player.vel.x *= Math.max(0, 1 - FRICTION * dt);
        player.vel.z *= Math.max(0, 1 - FRICTION * dt);
      }
      // clamp horizontal
      const hsp = Math.hypot(player.vel.x, player.vel.z);
      if (hsp > maxSp) {
        player.vel.x *= maxSp / hsp;
        player.vel.z *= maxSp / hsp;
      }

      // jump hold
      if (player.state === 'air') {
        player.jumpTime += dt;
        if ((jumpHeld || keys['Space']) && player.jumpTime < 0.28 && player.vel.y > 0) {
          player.vel.y += JUMP_HOLD_EXTRA * dt;
        }
        if (wantTrick || keys['KeyQ'] || keys['KeyE']) doTrick();
      }

      player.vel.y -= GRAVITY * dt;
      player.pos.x += player.vel.x * dt;
      player.pos.y += player.vel.y * dt;
      player.pos.z += player.vel.z * dt;

      // bounds
      player.pos.x = Math.max(-38, Math.min(38, player.pos.x));
      player.pos.z = Math.max(-38, Math.min(38, player.pos.z));

      const gh = groundHeightAt(player.pos.x, player.pos.z);
      const foot = 0.95;
      if (player.pos.y <= gh + foot && player.vel.y <= 0) {
        player.pos.y = gh + foot;
        if (player.state === 'air') {
          sfxLand();
          if (player.airTricks > 0) addScore(50 * player.airTricks, 'LAND');
        }
        player.vel.y = 0;
        player.state = 'ground';
        player.canCoyote = 0.12;
        player.trickSpin *= 0.5;
        player.trickFlip *= 0.5;
        // auto grind snap
        const nr = nearestRail(player.pos, 1.35);
        if (nr && hsp > 4) {
          player.state = 'grind';
          player.grindRail = nr.rail;
          player.grindT = nr.t;
          player.grindBal = 0;
          addScore(100, 'GRIND');
          sfxGrind();
        }
      } else {
        if (player.state === 'ground') {
          player.canCoyote -= dt;
          if (player.canCoyote <= 0) player.state = 'air';
        }
        // wall ride check
        if (player.state === 'air' && player.vel.y < 4) {
          const w = findWallRide(player.pos, player.vel);
          if (w) {
            player.state = 'wall';
            player.wall = w;
            player.wallTime = 0;
            addScore(120, 'WALL');
          }
        }
      }
      tryJump(dt);
    }

    // Tag
    if (wantTag || keys['KeyF']) {
      wantTag = false;
      for (const t of tagSpots) {
        if (t.tagged) continue;
        if (player.pos.distanceTo(t.pos) < 2.5 && Math.abs(player.pos.y - t.pos.y) < 3) {
          t.tagged = true;
          tagsDone += 1;
          t.decal.material.opacity = 0.95;
          t.decal.material.color.setHex([0xff3eb5, 0x3ef0ff, 0xffe566, 0x5dff9a][t.idx % 4]);
          t.ring.visible = false;
          t.marker.material.emissiveIntensity = 0.15;
          sfxTag();
          addScore(500, 'TAG');
          tagToast.textContent = 'TAGGED! ' + tagsDone + '/' + TAG_COUNT;
          tagToast.classList.add('show');
          clearTimeout(tagToast._t);
          tagToast._t = setTimeout(() => tagToast.classList.remove('show'), 900);
          if (tagsDone >= TAG_COUNT) endRun(true);
          break;
        }
      }
    }

    jumpWas = !!(keys['Space'] || jumpHeld);

    // animate mesh
    player.mesh.position.copy(player.pos);
    player.mesh.position.y -= 0.95;
    player.mesh.rotation.y = player.yaw;
    if (player.state === 'air') {
      player.mesh.rotation.y += player.trickSpin;
      player.mesh.rotation.x = player.trickFlip * 0.35;
      player.trickSpin *= 1 - dt * 1.5;
      player.trickFlip *= 1 - dt * 1.5;
    } else if (player.state === 'wall' && player.wall) {
      player.mesh.rotation.z = player.wall.normal.x !== 0 ? -player.wall.normal.x * 0.6 : -player.wall.normal.z * 0.6;
    } else {
      player.mesh.rotation.x *= 1 - dt * 8;
      player.mesh.rotation.z *= 1 - dt * 8;
      // skate lean
      const lean = Math.max(-0.35, Math.min(0.35, -stick.x * 0.3));
      player.mesh.rotation.z = lean;
    }
    // thruster flicker when boosting
    player.skates.forEach(s => {
      s.children.forEach(c => {
        if (c.material && c.material.emissive) c.material.emissiveIntensity = boosting ? 1.2 : 0.4;
      });
    });
  }

  function updateCamera(dt) {
    const behind = new THREE.Vector3(Math.sin(player.yaw), 0, Math.cos(player.yaw));
    const desired = new THREE.Vector3().copy(player.pos)
      .addScaledVector(behind, 10)
      .add(new THREE.Vector3(0, 6.5, 0));
    camPos.lerp(desired, 1 - Math.pow(0.001, dt));
    camTarget.lerp(player.pos.clone().add(new THREE.Vector3(0, 1.4, 0)), 1 - Math.pow(0.0001, dt));
    camera.position.copy(camPos);
    camera.lookAt(camTarget);
  }

  function updateArrow() {
    const n = nearestUntagged();
    if (!n || mode !== 'play') { arrowHint.style.opacity = '0'; return; }
    arrowHint.style.opacity = '1';
    // project direction onto screen
    const dir = new THREE.Vector3().subVectors(n.pos, player.pos);
    const local = dir.clone().applyAxisAngle(new THREE.Vector3(0, 1, 0), -player.yaw);
    const ang = Math.atan2(local.x, -local.z);
    arrowHint.style.transform = `translateY(-50%) rotate(${ang}rad)`;
  }

  function animateTagRings(t) {
    tagSpots.forEach((spot, i) => {
      if (spot.tagged) return;
      spot.ring.rotation.z = t * 2 + i;
      spot.marker.position.y = spot.pos.y + 0.08 + Math.sin(t * 3 + i) * 0.08;
    });
  }

  // ---------- RESIZE ----------
  function resize() {
    const w = canvas.clientWidth || window.innerWidth;
    const h = canvas.clientHeight || window.innerHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / Math.max(1, h);
    camera.updateProjectionMatrix();
  }
  window.addEventListener('resize', resize);
  resize();

  // ---------- LOGO ----------
  (function drawLogo() {
    const c = document.getElementById('logoCanvas');
    const ctx = c.getContext('2d');
    ctx.fillStyle = '#0b1020';
    ctx.fillRect(0, 0, c.width, c.height);
    // skyline silhouette
    ctx.fillStyle = '#1a2748';
    const buildings = [[20,120,50,180],[70,90,40,180],[120,60,55,180],[185,100,45,180],[240,40,60,180],[310,80,50,180],[370,110,40,180],[420,70,55,180],[490,95,40,180]];
    buildings.forEach(([x,y,w,base]) => ctx.fillRect(x, y, w, base - y));
    // neon lines
    ctx.strokeStyle = '#3ef0ff'; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(30, 150); ctx.lineTo(200, 80); ctx.lineTo(360, 130); ctx.lineTo(530, 70); ctx.stroke();
    ctx.strokeStyle = '#ff3eb5'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(40, 160); ctx.lineTo(220, 95); ctx.lineTo(400, 140); ctx.stroke();
    // title text baked lightly
    ctx.font = '900 52px Segoe UI, system-ui, sans-serif';
    ctx.fillStyle = '#3ef0ff';
    ctx.fillText('SKYLINE', 40, 70);
    ctx.fillStyle = '#ff3eb5';
    ctx.fillText('RIOT', 300, 70);
  })();

  // ---------- LOOP ----------
  function frame(t) {
    const dt = Math.min(0.05, (t - lastT) / 1000 || 0.016);
    lastT = t;

    if (mode === 'play') {
      timeLeft -= dt;
      if (timeLeft <= 0) { timeLeft = 0; endRun(false); }
      if (comboTimer > 0) {
        comboTimer -= dt;
        if (comboTimer <= 0) combo = 0;
      }
      updatePlayer(dt);
      updateCamera(dt);
      updateArrow();
      updateHUD();
      neon.position.set(player.pos.x, player.pos.y + 2, player.pos.z);
    } else {
      // idle orbit camera on menu
      const ang = t * 0.00025;
      camera.position.set(Math.sin(ang) * 28, 16, Math.cos(ang) * 28);
      camera.lookAt(0, 4, 0);
    }
    animateTagRings(t * 0.001);
    renderer.render(scene, camera);
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  // ---------- TEST HOOKS ----------
  window.__SR = {
    version: VERSION,
    start: startRun,
    getState: () => ({ mode, score, combo, boost, timeLeft, tagsDone, playerState: player.state,
      pos: player.pos.toArray(), vel: player.vel.toArray() }),
    setAuto: (v) => { window.__SR_AUTO = !!v; },
    tagNearest: () => { wantTag = true; },
    jump: () => { jumpBuffered = 0.2; jumpHeld = true; setTimeout(() => { jumpHeld = false; }, 200); },
    boost: () => { wantBoost = true; boost = 1; },
    teleport: (x, y, z) => {
      player.pos.set(x, y, z);
      player.vel.set(0, 0, 0);
      player.state = 'ground';
      player.grindRail = null;
      player.wall = null;
    },
    snapGrind: () => {
      const nr = nearestRail(player.pos, 80);
      if (!nr) return false;
      player.state = 'grind';
      player.grindRail = nr.rail;
      player.grindT = Math.max(0.05, Math.min(0.95, nr.t));
      player.grindBal = 0;
      player.vel.set(nr.rail.dir.x * GRIND_SPEED, 0, nr.rail.dir.z * GRIND_SPEED);
      const ab = new THREE.Vector3().subVectors(nr.rail.b, nr.rail.a);
      player.pos.copy(nr.rail.a).addScaledVector(ab, player.grindT);
      player.pos.y += 0.55;
      return true;
    },
    forceTag: (idx) => {
      const t = tagSpots[idx || 0];
      if (!t || t.tagged) return false;
      player.pos.set(t.pos.x, t.pos.y + 1.2, t.pos.z);
      wantTag = true;
      return true;
    },
    launchAir: () => {
      player.state = 'air';
      player.pos.y = Math.max(player.pos.y, 6) + 4;
      player.vel.set(10, 16, -8);
      doTrick();
    }
  };

  console.log('Skyline Riot v' + VERSION + ' ready');
})();
