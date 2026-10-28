/* Skyline Riot — Sky Trek skater (concept sheet) + Miles Morales / Spider-Verse look
   Procedural Three.js character. Shared by character.html viewer and game.js. */
(function (root) {
  'use strict';

  const COL = {
    hair: 0x0c1220,
    hairHi: 0x1a2740,
    skin: 0xf0c4a0,
    skinShade: 0xd4a07a,
    jacket: 0x0a0a0e,
    jacketHi: 0x1a1a22,
    lining: 0xff5a12,
    liningHi: 0xff7a3a,
    piping: 0xf2f2f5,
    tee: 0xf7f7f7,
    pants: 0x0c0c12,
    stripe: 0xf0f0f4,
    glove: 0x111118,
    skate: 0x101018,
    wheel: 0xc8d0dc,
    crest: 0xe02028,
    crestWing: 0xd8dde8,
    eye: 0x1a1010,
    buckle: 0xb8c0cc,
    strap: 0x1a2848
  };

  function makeToonGrad(THREE, steps) {
    const c = document.createElement('canvas');
    c.width = steps; c.height = 1;
    const ctx = c.getContext('2d');
    for (let i = 0; i < steps; i++) {
      const v = Math.floor((i / Math.max(1, steps - 1)) * 255);
      ctx.fillStyle = `rgb(${v},${v},${v})`;
      ctx.fillRect(i, 0, 1, 1);
    }
    const tex = new THREE.CanvasTexture(c);
    tex.minFilter = THREE.NearestFilter;
    tex.magFilter = THREE.NearestFilter;
    return tex;
  }

  function toonMat(THREE, color, emissive, grad) {
    return new THREE.MeshToonMaterial({
      color: new THREE.Color(color),
      gradientMap: grad,
      emissive: new THREE.Color(emissive || 0x000000),
      emissiveIntensity: emissive ? 0.45 : 0
    });
  }

  function outlineMat(THREE, color) {
    return new THREE.MeshBasicMaterial({
      color: color || 0x050508,
      side: THREE.BackSide
    });
  }

  function addOutline(THREE, mesh, scale, oMat) {
    if (!mesh.geometry) return null;
    const o = new THREE.Mesh(mesh.geometry, oMat || outlineMat(THREE));
    o.scale.multiplyScalar(scale || 1.055);
    o.userData.isOutline = true;
    mesh.add(o);
    return o;
  }

  function box(THREE, w, h, d, mat, oMat, outlineScale) {
    const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
    if (oMat !== false) addOutline(THREE, m, outlineScale || 1.055, oMat);
    return m;
  }

  function cyl(THREE, rTop, rBot, h, segs, mat, oMat) {
    const m = new THREE.Mesh(new THREE.CylinderGeometry(rTop, rBot, h, segs || 8), mat);
    if (oMat !== false) addOutline(THREE, m, 1.06, oMat);
    return m;
  }

  function sphere(THREE, r, segs, mat, oMat) {
    const m = new THREE.Mesh(new THREE.SphereGeometry(r, segs || 10, segs || 8), mat);
    if (oMat !== false) addOutline(THREE, m, 1.05, oMat);
    return m;
  }

  /** Build the Sky Trek skater from the concept sheet. */
  function createSkater(THREE, opts) {
    opts = opts || {};
    const grad = opts.gradientMap || makeToonGrad(THREE, 4);
    const oMat = outlineMat(THREE, 0x050508);
    const M = (c, e) => toonMat(THREE, c, e, grad);

    const root = new THREE.Group();
    root.name = 'SkyTrekSkater';

    // Hierarchy pivots
    const hips = new THREE.Group(); hips.name = 'hips'; hips.position.y = 0.92;
    root.add(hips);

    const torsoG = new THREE.Group(); torsoG.name = 'torso'; torsoG.position.y = 0.18;
    hips.add(torsoG);

    const headG = new THREE.Group(); headG.name = 'head'; headG.position.y = 0.72;
    torsoG.add(headG);

    const armLG = new THREE.Group(); armLG.name = 'armL'; armLG.position.set(-0.42, 0.52, 0);
    torsoG.add(armLG);
    const armRG = new THREE.Group(); armRG.name = 'armR'; armRG.position.set(0.42, 0.52, 0);
    torsoG.add(armRG);

    const legLG = new THREE.Group(); legLG.name = 'legL'; legLG.position.set(-0.16, 0, 0);
    hips.add(legLG);
    const legRG = new THREE.Group(); legRG.name = 'legR'; legRG.position.set(0.16, 0, 0);
    hips.add(legRG);

    // ---- TORSO: black jacket + white tee peek ----
    const jacket = box(THREE, 0.62, 0.78, 0.38, M(COL.jacket), oMat, 1.05);
    jacket.position.y = 0.28;
    torsoG.add(jacket);

    // Orange lining visible at open front (two panels)
    const liningL = box(THREE, 0.06, 0.68, 0.02, M(COL.lining), oMat, 1.04);
    liningL.position.set(-0.12, 0.26, 0.195);
    torsoG.add(liningL);
    const liningR = liningL.clone();
    liningR.position.x = 0.12;
    torsoG.add(liningR);

    // White tee hem below jacket
    const tee = box(THREE, 0.55, 0.22, 0.34, M(COL.tee), oMat, 1.04);
    tee.position.y = -0.18;
    torsoG.add(tee);

    // High collar
    const collar = box(THREE, 0.48, 0.22, 0.36, M(COL.jacket), oMat, 1.06);
    collar.position.set(0, 0.72, -0.02);
    torsoG.add(collar);
    // Orange inside collar
    const collarIn = box(THREE, 0.42, 0.18, 0.02, M(COL.lining), false);
    collarIn.position.set(0, 0.72, 0.16);
    torsoG.add(collarIn);

    // White piping on sleeves (will also appear on arm pieces)
    const pipeL = box(THREE, 0.04, 0.55, 0.04, M(COL.piping), false);
    pipeL.position.set(-0.33, 0.35, 0.1);
    torsoG.add(pipeL);
    const pipeR = pipeL.clone();
    pipeR.position.x = 0.33;
    torsoG.add(pipeR);

    // Back crest emblem (red circle + silver wings)
    const crest = cyl(THREE, 0.12, 0.12, 0.04, 12, M(COL.crest, 0x440000), oMat);
    crest.rotation.x = Math.PI / 2;
    crest.position.set(0, 0.38, -0.2);
    torsoG.add(crest);
    // Wing L
    const wingL = box(THREE, 0.22, 0.06, 0.03, M(COL.crestWing), oMat, 1.04);
    wingL.position.set(-0.2, 0.4, -0.2);
    wingL.rotation.z = 0.35;
    torsoG.add(wingL);
    const wingR = wingL.clone();
    wingR.position.x = 0.2;
    wingR.rotation.z = -0.35;
    torsoG.add(wingR);
    // Inner crest detail
    const crestIn = cyl(THREE, 0.06, 0.06, 0.045, 8, M(COL.piping), false);
    crestIn.rotation.x = Math.PI / 2;
    crestIn.position.set(0, 0.38, -0.21);
    torsoG.add(crestIn);

    // Belt
    const belt = box(THREE, 0.58, 0.08, 0.36, M(COL.jacket), oMat, 1.04);
    belt.position.y = -0.28;
    torsoG.add(belt);
    const buckle = box(THREE, 0.1, 0.07, 0.04, M(COL.buckle), false);
    buckle.position.set(0, -0.28, 0.19);
    torsoG.add(buckle);
    // Hanging strap (left hip)
    const strap = box(THREE, 0.05, 0.55, 0.03, M(COL.strap), oMat, 1.04);
    strap.position.set(-0.28, -0.5, 0.05);
    strap.rotation.z = 0.15;
    torsoG.add(strap);
    const strapTip = box(THREE, 0.06, 0.08, 0.035, M(COL.piping), false);
    strapTip.position.set(-0.32, -0.78, 0.05);
    torsoG.add(strapTip);

    // ---- HEAD + SPIKY HAIR ----
    const head = box(THREE, 0.38, 0.42, 0.36, M(COL.skin), oMat, 1.06);
    head.position.y = 0.12;
    headG.add(head);

    // Eyes (simple anime)
    const eyeL = box(THREE, 0.07, 0.05, 0.02, M(COL.eye), false);
    eyeL.position.set(-0.09, 0.14, 0.18);
    headG.add(eyeL);
    const eyeR = eyeL.clone();
    eyeR.position.x = 0.09;
    headG.add(eyeR);
    // Brows
    const browL = box(THREE, 0.09, 0.02, 0.02, M(COL.hair), false);
    browL.position.set(-0.09, 0.2, 0.18);
    browL.rotation.z = 0.15;
    headG.add(browL);
    const browR = browL.clone();
    browR.position.x = 0.09;
    browR.rotation.z = -0.15;
    headG.add(browR);

    // Neck
    const neck = cyl(THREE, 0.1, 0.12, 0.12, 8, M(COL.skin), oMat);
    neck.position.y = -0.12;
    headG.add(neck);

    // Spiky hair — multiple cones/boxes in wild directions
    const hairRoot = new THREE.Group();
    hairRoot.name = 'hair';
    hairRoot.position.y = 0.28;
    headG.add(hairRoot);

    function spike(x, y, z, sx, sy, sz, rx, ry, rz, col) {
      const s = box(THREE, sx, sy, sz, M(col || COL.hair), oMat, 1.07);
      s.position.set(x, y, z);
      s.rotation.set(rx || 0, ry || 0, rz || 0);
      hairRoot.add(s);
      return s;
    }
    // Cap base
    const hairCap = sphere(THREE, 0.24, 10, M(COL.hair), oMat);
    hairCap.scale.set(1.05, 0.7, 1.05);
    hairCap.position.y = 0.02;
    hairRoot.add(hairCap);

    // Spikes matching the messy blue-black look
    spike(0.0, 0.28, -0.05, 0.14, 0.42, 0.12, 0.2, 0, 0);
    spike(-0.12, 0.22, 0.0, 0.12, 0.38, 0.1, 0.15, 0, 0.45);
    spike(0.12, 0.22, 0.0, 0.12, 0.38, 0.1, 0.15, 0, -0.45);
    spike(-0.18, 0.12, 0.05, 0.1, 0.32, 0.1, 0.4, 0, 0.7);
    spike(0.18, 0.12, 0.05, 0.1, 0.32, 0.1, 0.4, 0, -0.7);
    spike(0.0, 0.18, 0.16, 0.14, 0.28, 0.1, -0.55, 0, 0);
    spike(-0.08, 0.1, -0.16, 0.1, 0.26, 0.1, 0.6, 0.2, 0.2);
    spike(0.08, 0.1, -0.16, 0.1, 0.26, 0.1, 0.6, -0.2, -0.2);
    spike(-0.22, 0.05, -0.05, 0.1, 0.22, 0.09, 0.3, 0, 1.0);
    spike(0.22, 0.05, -0.05, 0.1, 0.22, 0.09, 0.3, 0, -1.0);
    spike(0.0, 0.32, 0.08, 0.1, 0.3, 0.09, -0.2, 0, 0, COL.hairHi);
    spike(-0.05, 0.26, -0.12, 0.09, 0.24, 0.08, 0.5, 0, 0.1);

    // ---- ARMS + FINGERLESS GLOVES ----
    function buildArm(side) {
      const g = side < 0 ? armLG : armRG;
      const sx = side;
      // Upper arm (jacket sleeve)
      const upper = box(THREE, 0.18, 0.38, 0.2, M(COL.jacket), oMat, 1.05);
      upper.position.set(0, -0.12, 0);
      g.add(upper);
      // Forearm
      const fore = box(THREE, 0.16, 0.36, 0.18, M(COL.jacket), oMat, 1.05);
      fore.position.set(0, -0.48, 0);
      g.add(fore);
      // Rolled orange cuff
      const cuff = box(THREE, 0.2, 0.1, 0.22, M(COL.lining), oMat, 1.05);
      cuff.position.set(0, -0.66, 0);
      g.add(cuff);
      // White piping stripe on sleeve
      const pipe = box(THREE, 0.03, 0.5, 0.03, M(COL.piping), false);
      pipe.position.set(sx * 0.08, -0.25, 0.08);
      g.add(pipe);
      // Fingerless glove
      const glove = box(THREE, 0.15, 0.16, 0.17, M(COL.glove), oMat, 1.05);
      glove.position.set(0, -0.78, 0);
      g.add(glove);
      // Fingers stubs
      for (let i = 0; i < 3; i++) {
        const f = box(THREE, 0.035, 0.08, 0.04, M(COL.skin), false);
        f.position.set((i - 1) * 0.04, -0.9, 0.04);
        g.add(f);
      }
      // Wrist strap
      const wstrap = box(THREE, 0.17, 0.04, 0.18, M(COL.buckle), false);
      wstrap.position.set(0, -0.7, 0);
      g.add(wstrap);
      return { upper, fore, cuff, glove };
    }
    const armPartsL = buildArm(-1);
    const armPartsR = buildArm(1);

    // ---- LEGS + ORANGE CUFFS + SIDE STRIPE ----
    function buildLeg(side) {
      const g = side < 0 ? legLG : legRG;
      // Thigh
      const thigh = box(THREE, 0.22, 0.42, 0.26, M(COL.pants), oMat, 1.05);
      thigh.position.y = -0.22;
      g.add(thigh);
      // Shin
      const shin = box(THREE, 0.2, 0.4, 0.24, M(COL.pants), oMat, 1.05);
      shin.position.y = -0.62;
      g.add(shin);
      // White side stripe
      const stripe = box(THREE, 0.035, 0.75, 0.03, M(COL.stripe), false);
      stripe.position.set(side * 0.11, -0.42, 0);
      g.add(stripe);
      // Orange rolled cuff
      const cuff = box(THREE, 0.24, 0.1, 0.28, M(COL.lining), oMat, 1.05);
      cuff.position.y = -0.84;
      g.add(cuff);
      // Ankle skin peek
      const ankle = cyl(THREE, 0.06, 0.07, 0.08, 8, M(COL.skin), false);
      ankle.position.y = -0.92;
      g.add(ankle);

      // ---- INLINE SKATE ----
      const skateG = new THREE.Group();
      skateG.name = side < 0 ? 'skateL' : 'skateR';
      skateG.position.y = -1.02;
      g.add(skateG);

      const boot = box(THREE, 0.26, 0.26, 0.58, M(COL.skate), oMat, 1.07);
      boot.position.set(0, 0.04, 0.08);
      skateG.add(boot);
      // Toe
      const toe = box(THREE, 0.24, 0.16, 0.2, M(COL.skate), oMat, 1.06);
      toe.position.set(0, -0.01, 0.32);
      skateG.add(toe);
      // Cuff / buckle
      const skBuckle = box(THREE, 0.28, 0.07, 0.16, M(COL.buckle), false);
      skBuckle.position.set(0, 0.16, 0.0);
      skateG.add(skBuckle);
      // Lace strip
      const lace = box(THREE, 0.08, 0.14, 0.02, M(COL.piping), false);
      lace.position.set(0, 0.06, 0.22);
      skateG.add(lace);
      // Frame
      const frame = box(THREE, 0.1, 0.07, 0.55, M(COL.buckle), false);
      frame.position.set(0, -0.12, 0.04);
      skateG.add(frame);
      // Wheels (4 silver) — larger & spaced
      const wheels = [];
      for (let i = 0; i < 4; i++) {
        const wh = cyl(THREE, 0.085, 0.085, 0.08, 10, M(COL.wheel), oMat);
        wh.rotation.z = Math.PI / 2;
        wh.position.set(0, -0.2, -0.18 + i * 0.14);
        skateG.add(wh);
        wheels.push(wh);
      }
      // Thruster glow (Sky Trek motor)
      const thr = cyl(THREE, 0.05, 0.08, 0.14, 8, M(0x3ef0ff, 0x3ef0ff), false);
      thr.rotation.x = Math.PI / 2;
      thr.position.set(0, -0.05, -0.28);
      skateG.add(thr);

      return { thigh, shin, cuff, skateG, wheels, thr };
    }
    const legPartsL = buildLeg(-1);
    const legPartsR = buildLeg(1);

    // Lift so wheel bottoms sit near local y=0 (built with hips at 0.92 → lowest ~-0.35)
    const BASE_HIPS_Y = 0.92 + 0.36;
    hips.position.y = BASE_HIPS_Y;
    root.scale.setScalar(1.0);

    // Animation state
    const anim = {
      name: 'idle',
      t: 0,
      speed: 0,
      baseHipsY: BASE_HIPS_Y,
      parts: {
        hips, torsoG, headG, armLG, armRG, legLG, legRG,
        skateL: legPartsL.skateG, skateR: legPartsR.skateG,
        wheelsL: legPartsL.wheels, wheelsR: legPartsR.wheels,
        thrL: legPartsL.thr, thrR: legPartsR.thr,
        hair: hairRoot
      }
    };

    function setAnim(name) {
      anim.name = name || 'idle';
    }

    function update(dt, info) {
      info = info || {};
      anim.t += dt;
      const t = anim.t;
      const spd = info.speed != null ? info.speed : anim.speed;
      anim.speed = spd;
      const state = info.state || anim.name;
      if (info.state) anim.name = info.state;

      // Reset lean bases
      const breath = Math.sin(t * 2.2) * 0.015;

      if (state === 'idle' || (state === 'ground' && spd < 0.5)) {
        hips.position.y = anim.baseHipsY + breath;
        torsoG.rotation.x = breath * 0.5;
        headG.rotation.y = Math.sin(t * 0.7) * 0.08;
        armLG.rotation.z = 0.15 + Math.sin(t * 1.5) * 0.04;
        armRG.rotation.z = -0.15 - Math.sin(t * 1.5) * 0.04;
        armLG.rotation.x = 0.05;
        armRG.rotation.x = 0.05;
        legLG.rotation.x = 0;
        legRG.rotation.x = 0;
        hairRoot.rotation.z = Math.sin(t * 1.2) * 0.02;
      } else if (state === 'grind') {
        hips.position.y = anim.baseHipsY - 0.10;
        torsoG.rotation.x = 0.25;
        headG.rotation.x = -0.1;
        armLG.rotation.z = 0.85;
        armRG.rotation.z = -0.85;
        armLG.rotation.x = -0.3;
        armRG.rotation.x = -0.3;
        legLG.rotation.x = -0.15;
        legRG.rotation.x = 0.35;
        legLG.rotation.z = 0.1;
        legRG.rotation.z = -0.05;
        // spin wheels
        const spin = t * 18;
        legPartsL.wheels.forEach(w => { w.rotation.x = spin; });
        legPartsR.wheels.forEach(w => { w.rotation.x = spin; });
      } else if (state === 'air') {
        hips.position.y = anim.baseHipsY;
        torsoG.rotation.x = -0.15;
        armLG.rotation.z = 0.6;
        armRG.rotation.z = -0.6;
        armLG.rotation.x = -0.4;
        armRG.rotation.x = 0.5;
        legLG.rotation.x = 0.4;
        legRG.rotation.x = -0.5;
        hairRoot.rotation.x = -0.1;
      } else if (state === 'wall') {
        hips.position.y = anim.baseHipsY - 0.02;
        torsoG.rotation.x = 0.1;
        armLG.rotation.z = 0.4;
        armRG.rotation.z = -1.0;
        legLG.rotation.x = 0.2;
        legRG.rotation.x = -0.1;
      } else {
        // skate / ground moving — stride
        const cadence = Math.min(14, 6 + spd * 0.55);
        const swing = Math.sin(t * cadence) * Math.min(0.7, 0.25 + spd * 0.03);
        hips.position.y = anim.baseHipsY - 0.02 + Math.abs(Math.sin(t * cadence)) * 0.04;
        torsoG.rotation.x = 0.12 + breath;
        torsoG.rotation.z = -swing * 0.08;
        headG.rotation.y = swing * 0.1;
        armLG.rotation.x = -swing * 0.7;
        armRG.rotation.x = swing * 0.7;
        armLG.rotation.z = 0.25;
        armRG.rotation.z = -0.25;
        legLG.rotation.x = swing * 0.85;
        legRG.rotation.x = -swing * 0.85;
        hairRoot.rotation.z = swing * 0.05;
        const spin = t * (8 + spd * 1.5);
        legPartsL.wheels.forEach(w => { w.rotation.x = spin; });
        legPartsR.wheels.forEach(w => { w.rotation.x = spin; });
      }

      // Thruster intensity
      const boost = !!info.boosting;
      [legPartsL.thr, legPartsR.thr].forEach(thr => {
        if (thr.material) {
          thr.material.emissiveIntensity = boost ? 1.4 : (spd > 2 ? 0.55 : 0.25);
        }
      });
    }

    root.userData.skater = {
      setAnim,
      update,
      anim,
      skates: [legPartsL.skateG, legPartsR.skateG],
      thrusters: [legPartsL.thr, legPartsR.thr],
      parts: anim.parts
    };

    return root;
  }

  /** Spider-Verse post-process: halftone shadows + CMYK edge offset. Returns {composer-like render}. */
  function createVersePass(THREE, renderer, scene, camera) {
    // Fullscreen quad with custom shader reading a render target
    const rt = new THREE.WebGLRenderTarget(
      Math.floor(renderer.domElement.width) || 512,
      Math.floor(renderer.domElement.height) || 512,
      { minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, format: THREE.RGBAFormat }
    );

    const uniforms = {
      tDiffuse: { value: rt.texture },
      resolution: { value: new THREE.Vector2(rt.width, rt.height) },
      time: { value: 0 },
      halftoneScale: { value: 2.8 },
      chromaStrength: { value: 0.0016 },
      inkBoost: { value: 1.15 }
    };

    const mat = new THREE.ShaderMaterial({
      uniforms,
      vertexShader: [
        'varying vec2 vUv;',
        'void main(){',
        '  vUv = uv;',
        '  gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0);',
        '}'
      ].join('\n'),
      fragmentShader: [
        'uniform sampler2D tDiffuse;',
        'uniform vec2 resolution;',
        'uniform float time;',
        'uniform float halftoneScale;',
        'uniform float chromaStrength;',
        'uniform float inkBoost;',
        'varying vec2 vUv;',
        // Rotated halftone dots
        'float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7))) * 43758.5453); }',
        'float luma(vec3 c){ return dot(c, vec3(0.299,0.587,0.114)); }',
        'void main(){',
        '  vec2 uv = vUv;',
        '  vec2 px = 1.0 / resolution;',
        // CMYK-ish chromatic print offset
        '  float ang = 0.35;',
        '  vec2 dirR = vec2(cos(ang), sin(ang)) * chromaStrength;',
        '  vec2 dirB = vec2(cos(ang+2.1), sin(ang+2.1)) * chromaStrength;',
        '  float r = texture2D(tDiffuse, uv + dirR).r;',
        '  float g = texture2D(tDiffuse, uv).g;',
        '  float b = texture2D(tDiffuse, uv + dirB).b;',
        '  vec3 col = vec3(r,g,b);',
        // Halftone in darker regions
        '  float L = luma(col);',
        '  vec2 htUV = uv * resolution / (halftoneScale * 6.0);',
        '  vec2 cell = fract(htUV) - 0.5;',
        '  float dist = length(cell);',
        '  float threshold = 0.45;',
        '  float dots = smoothstep(threshold, threshold - 0.12, dist + (1.0 - L) * 0.35);',
        '  float shade = mix(1.0, 0.55, dots * (1.0 - smoothstep(0.35, 0.75, L)));',
        '  col *= shade;',
        // Slight ink boost / posterize toward comic flats
        '  col = pow(col, vec3(0.95)) * inkBoost;',
        '  col = floor(col * 7.0 + 0.5) / 7.0 * 0.55 + col * 0.45;',
        // Soft vignette paper edge
        '  float vig = smoothstep(1.15, 0.35, length(uv - 0.5) * 1.15);',
        '  col *= 0.88 + 0.12 * vig;',
        '  gl_FragColor = vec4(col, 1.0);',
        '}'
      ].join('\n')
    });

    const cam2 = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    const quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), mat);
    const scene2 = new THREE.Scene();
    scene2.add(quad);

    function setSize(w, h) {
      const pr = renderer.getPixelRatio ? renderer.getPixelRatio() : 1;
      rt.setSize(Math.max(1, Math.floor(w * pr)), Math.max(1, Math.floor(h * pr)));
      uniforms.resolution.value.set(rt.width, rt.height);
    }

    function render(t) {
      uniforms.time.value = t || 0;
      renderer.setRenderTarget(rt);
      renderer.render(scene, camera);
      renderer.setRenderTarget(null);
      renderer.render(scene2, cam2);
    }

    return { render, setSize, uniforms, dispose: () => rt.dispose() };
  }

  root.SkylineCharacter = {
    createSkater,
    createVersePass,
    makeToonGrad,
    COLORS: COL
  };
})(typeof window !== 'undefined' ? window : globalThis);
