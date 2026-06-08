/* ============================================================================
   LMU App — overlay component generator
   Plain JS (window.LMU). Each render* fn returns an HTML string for one overlay.
   Markup is DIRECTION-AGNOSTIC: the look is themed by a `.dir-*` class on an
   ancestor (see overlays.css). One coherent race scenario feeds every widget:
   Le Mans 24h · Hypercar · car #50 "P. ROSSI" running P5.
   ============================================================================ */
(function () {
  // ---- shared race scenario -------------------------------------------------
  const DATA = {
    speed: { spd: 248, gear: 4, rpm: 0.72, rpmRed: 0.9 },
    inputs: { t: 0.86, b: 0.0, c: 0.0, steer: -0.28 }, // steer -1..1
    fuel: { fuel: 58.4, cap: 105, ve: 0.61 },
    tyres: [
      { pos: 'FL', temp: 88,  wear: 0.93 },
      { pos: 'FR', temp: 99,  wear: 0.90 },
      { pos: 'RL', temp: 74,  wear: 0.96 },
      { pos: 'RR', temp: 116, wear: 0.87 },
    ],
    standings: {
      header: ['GAP', 'INT', 'BEST', 'LAST'],
      groups: [
        {
          cls: 'HYP', clsName: 'HYPERCAR', color: '#CC0000', rows: [
            { p: 1, n: 'B. HARTLEY',    car: '7',  gap: '',      int: '',     best: '3:24.123', last: '3:25.660', tone: 'best',   badge: '' },
            { p: 2, n: 'K. ESTRE',      car: '6',  gap: '+1.2',  int: '+1.2', best: '3:24.401', last: '3:25.880', tone: '',       badge: 'PIT' },
            { p: 3, n: 'A. FUOCO',      car: '50', gap: '+4.8',  int: '+3.6', best: '3:24.560', last: '3:26.100', tone: '',       badge: '' },
            { sep: true },
            { p: 4, n: 'J. PIER GUIDI', car: '51', gap: '+18.4', int: '+13.6',best: '3:24.880', last: '3:26.300', tone: '',       badge: '' },
            { p: 5, n: 'P. ROSSI',      car: '2',  gap: '+21.0', int: '+2.6', best: '3:24.990', last: '3:25.990', tone: 'player', badge: '' },
            { p: 6, n: 'L. VANTHOOR',   car: '15', gap: '+24.4', int: '+3.4', best: '3:25.220', last: '3:26.700', tone: '',       badge: 'OUT' },
          ]
        },
        {
          cls: 'GT3', clsName: 'LMGT3', color: '#00A040', rows: [
            { p: 1, n: 'V. ROSSI',      car: '46', gap: '',      int: '',     best: '3:51.200', last: '3:52.640', tone: '',  badge: '' },
            { p: 2, n: 'N. AL HARTHY',  car: '95', gap: '+2.7',  int: '+2.7', best: '3:51.560', last: '3:53.010', tone: '',  badge: '' },
          ]
        }
      ]
    },
    relative: [
      { side: 'ahead',  cls: 'P2',  color: '#1050C8', p: 1, n: 'F. ALBUQUERQUE', gap: '-8.4', badge: '' },
      { side: 'ahead',  cls: 'GT3', color: '#00A040', p: 3, n: 'M. MALYKHIN',    gap: '-4.1', badge: '' },
      { side: 'ahead',  cls: 'HYP', color: '#CC0000', p: 2, n: 'K. ESTRE',       gap: '-1.6', badge: 'PIT' },
      { side: 'player', cls: 'HYP', color: '#CC0000', p: 5, n: 'P. ROSSI',       gap: '0.0',  badge: '' },
      { side: 'behind', cls: 'GT3', color: '#00A040', p: 5, n: 'D. SCHIAVONI',   gap: '+2.3', badge: '' },
      { side: 'behind', cls: 'P2',  color: '#1050C8', p: 2, n: 'O. COTTINGHAM',  gap: '+5.9', badge: '' },
      { side: 'behind', cls: 'HYP', color: '#CC0000', p: 6, n: 'L. VANTHOOR',    gap: '+9.2', badge: 'OUT' },
    ],
  };

  const DIRECTIONS = [
    { id: 'broadcast', name: 'Broadcast',  tag: 'WEC TV graphics · ambre · condensé' },
    { id: 'telemetry', name: 'Telemetry',  tag: 'MoTeC / data-logger · cyan · mono · LED' },
    { id: 'apex',      name: 'Apex',       tag: 'HUD jeu moderne · lime · chanfreins' },
    { id: 'graphite',  name: 'Graphite',   tag: 'Minimal · monochrome · hairline' },
  ];

  // ---- helpers --------------------------------------------------------------
  const esc = (s) => String(s);

  // Tyre temperature → color (mirrors the app's _temp_color logic)
  function tyreColor(t) {
    const cold = 60, optLo = 80, optHi = 100, hot = 120;
    if (t <= 0) return '#5a5a5a';
    if (t < cold) return '#508cff';
    if (t < optLo) { const f = (t - cold) / (optLo - cold); return rgb(80 - 80 * f, 140 + 80 * f, 255 - 175 * f); }
    if (t <= optHi) return '#3cdc50';
    if (t < hot) { const f = (t - optHi) / (hot - optHi); return rgb(60 + 195 * f, 220 - 160 * f, 80 - 60 * f); }
    return '#ff3c3c';
  }
  const rgb = (r, g, b) => `rgb(${r | 0},${g | 0},${b | 0})`;

  // segmented RPM / shift-light bar (used by all directions, themed by CSS)
  function rpmBar(ratio, n = 18) {
    const lit = Math.round(ratio * n);
    let out = '<div class="ov-rpm">';
    for (let i = 0; i < n; i++) {
      const f = i / (n - 1);
      const zone = f < 0.62 ? 'lo' : f < 0.85 ? 'mid' : 'hi';
      out += `<i class="ov-rpm__seg ${i < lit ? 'on' : ''} z-${zone}"></i>`;
    }
    return out + '</div>';
  }

  // ---- widgets --------------------------------------------------------------
  function renderSpeed(d = DATA.speed) {
    return `
    <div class="ov ov-speed">
      ${rpmBar(d.rpm)}
      <div class="ov-speed__row">
        <div class="ov-speed__spd">
          <b>${d.spd}</b><span class="ov-unit">KM/H</span>
        </div>
        <div class="ov-speed__gear">${d.gear}</div>
      </div>
    </div>`;
  }

  function renderInputs(d = DATA.inputs) {
    const bar = (lbl, val, kind) => `
      <div class="ov-ibar k-${kind}">
        <div class="ov-ibar__val">${Math.round(val * 100)}</div>
        <div class="ov-ibar__track"><i style="--p:${val}"></i></div>
        <div class="ov-ibar__lbl">${lbl}</div>
      </div>`;
    const deg = Math.round(d.steer * 270);
    return `
    <div class="ov ov-inputs">
      <div class="ov-inputs__bars">
        ${bar('T', d.t, 't')}${bar('B', d.b, 'b')}${bar('C', d.c, 'c')}
      </div>
      <div class="ov-inputs__wheel">
        <svg viewBox="0 0 100 100" class="ov-wheel" style="--deg:${deg}deg">
          <circle cx="50" cy="50" r="40" class="ov-wheel__rim"/>
          <line x1="50" y1="50" x2="87" y2="50" class="ov-wheel__spoke"/>
          <line x1="50" y1="50" x2="50" y2="87" class="ov-wheel__spoke"/>
          <line x1="50" y1="50" x2="13" y2="50" class="ov-wheel__spoke"/>
          <circle cx="50" cy="50" r="9" class="ov-wheel__hub"/>
        </svg>
        <div class="ov-inputs__deg">${deg >= 0 ? '+' : ''}${deg}°</div>
      </div>
    </div>`;
  }

  function renderFuel(d = DATA.fuel) {
    const rf = Math.max(0, Math.min(1, d.fuel / d.cap));
    const lvl = rf < 0.10 ? 'crit' : rf < 0.25 ? 'warn' : 'ok';
    return `
    <div class="ov ov-fuel">
      <div class="ov-fbar k-fuel lvl-${lvl}">
        <div class="ov-fbar__track"><i style="--p:${rf}"></i></div>
        <div class="ov-fbar__lbl">FUEL</div>
        <div class="ov-fbar__val">${d.fuel.toFixed(1)} <small>L</small></div>
      </div>
      <div class="ov-fbar k-ve">
        <div class="ov-fbar__track"><i style="--p:${d.ve}"></i></div>
        <div class="ov-fbar__lbl">VIRTUAL ENERGY</div>
        <div class="ov-fbar__val">${Math.round(d.ve * 100)}<small>%</small></div>
      </div>
    </div>`;
  }

  function renderTyres(d = DATA.tyres) {
    const cell = (t) => {
      const col = tyreColor(t.temp);
      const tempCls = t.temp >= 120 ? 's-hot' : t.temp < 80 ? 's-cold' : 's-opt';
      return `
      <div class="ov-tyre ${tempCls}">
        <div class="ov-tyre__corner">${t.pos}</div>
        <div class="ov-tyre__temp">${t.temp}°</div>
        <div class="ov-tyre__bar"><i style="--p:${t.wear};background:${col}"></i></div>
        <div class="ov-tyre__wear">${Math.round(t.wear * 100)}%</div>
      </div>`;
    };
    return `
    <div class="ov ov-tyres">
      <div class="ov-tyres__grid">
        ${cell(d[0])}${cell(d[1])}${cell(d[2])}${cell(d[3])}
      </div>
    </div>`;
  }

  function renderStandings(d = DATA.standings, opts = {}) {
    const cols = opts.cols || ['gap', 'int', 'best', 'last'];
    const head = `
      <div class="ov-strow ov-strow--head">
        <span class="c-pos"></span>
        <span class="c-name">DRIVER</span>
        ${cols.map((c) => `<span class="c-${c}">${c.toUpperCase()}</span>`).join('')}
      </div>`;
    let body = '';
    d.groups.forEach((g) => {
      body += `
        <div class="ov-clshdr">
          <span class="ov-clschip" style="--cc:${g.color}">${g.cls}</span>
          <span class="ov-clsname">${g.clsName}</span>
        </div>`;
      g.rows.forEach((r) => {
        if (r.sep) { body += `<div class="ov-stsep"></div>`; return; }
        const posCls = r.p === 1 ? 'p1' : r.p === 2 ? 'p2' : r.p === 3 ? 'p3' : '';
        const bestCls = r.tone === 'best' ? 'v-purple' : r.tone === 'player' ? 'v-green' : '';
        const badge = r.badge ? `<span class="ov-badge b-${r.badge.toLowerCase()}">${r.badge}</span>` : '';
        body += `
          <div class="ov-strow ${r.tone === 'player' ? 'is-player' : ''}">
            <span class="c-pos ${posCls}">${r.p}</span>
            <span class="c-name"><b>${r.n}</b>${badge}</span>
            <span class="c-gap">${r.gap}</span>
            <span class="c-int">${r.int}</span>
            <span class="c-best ${bestCls}">${r.best}</span>
            <span class="c-last">${r.last}</span>
          </div>`;
      });
    });
    return `<div class="ov ov-standings">${head}${body}</div>`;
  }

  function renderRelative(d = DATA.relative) {
    let rows = '';
    d.forEach((r) => {
      const gapCls = r.side === 'ahead' ? 'g-ahead' : r.side === 'behind' ? 'g-behind' : 'g-self';
      const badge = r.badge ? `<span class="ov-badge b-${r.badge.toLowerCase()}">${r.badge}</span>` : '';
      rows += `
        <div class="ov-relrow ${r.side === 'player' ? 'is-player' : ''}">
          <span class="c-chip" style="--cc:${r.color}">${r.p}</span>
          <span class="c-name"><b>${r.n}</b>${badge}</span>
          <span class="c-gap ${gapCls}">${r.gap}</span>
        </div>`;
    });
    return `<div class="ov ov-relative">${rows}</div>`;
  }

  // ---- fuel / VE calculators (fuel_calc.py / ve_calc.py) -------------------
  function calcTable(rows) {
    const head = `
      <div class="rl"></div>
      <div class="h">USAGE</div><div class="h">LAPS</div>
      <div class="h">REFUEL</div><div class="h">FINISH</div>`;
    const body = rows.map((r) => `
      <div class="rl">${r.lbl}</div>
      <div class="v">${r.usage}</div>
      <div class="v">${r.laps}</div>
      <div class="v ${r.refuel === 'OK' ? 'ok' : ''}">${r.refuel}</div>
      <div class="v">${r.finish}</div>`).join('');
    return `<div class="ov-calc__table">${head}${body}</div>`;
  }

  function renderFuelCalc() {
    return `
    <div class="ov ov-calc">
      <div class="ov-cbar k-fuel">
        <i style="--p:0.556"></i>
        <span class="ov-cbar__lbl">FUEL</span>
        <span class="ov-cbar__val">58.4 <small>L</small></span>
      </div>
      <div class="ov-calc__sep"></div>
      ${calcTable([
        { lbl: 'LAST',  usage: '3.2L', laps: '18.3', refuel: '+14L', finish: '2.1L' },
        { lbl: 'AVG 5', usage: '3.4L', laps: '17.2', refuel: '+18L', finish: '1.4L' },
      ])}
    </div>`;
  }

  function renderVeCalc() {
    return `
    <div class="ov ov-calc">
      <div class="ov-cbar k-ve">
        <i style="--p:0.61"></i>
        <span class="ov-cbar__lbl">VE</span>
        <span class="ov-cbar__val">61 <small>%</small></span>
      </div>
      <div class="ov-cbar k-fuel">
        <i style="--p:0.556"></i>
        <span class="ov-cbar__lbl">FUEL</span>
        <span class="ov-cbar__val">58.4 <small>L</small></span>
      </div>
      <div class="ov-calc__sep"></div>
      ${calcTable([
        { lbl: 'LAST',  usage: '5.4%', laps: '18.5', refuel: '+22%', finish: '3.1%' },
        { lbl: 'AVG 5', usage: '5.6%', laps: '17.9', refuel: '+25%', finish: '2.4%' },
      ])}
      <div class="ov-calc__ratio">
        <span class="rl">FUEL RATIO</span><span class="v">0.59</span>
      </div>
    </div>`;
  }

  // ---- control panel (the main window) -------------------------------------
  function renderControl() {
    const items = [
      ['Speed & Gear', true], ['Inputs', true], ['Fuel & Virtual Energy', true],
      ['Standings', true], ['Relative', false], ['Tyres', true],
    ];
    const rows = items.map(([name, on]) => `
      <div class="cw-row">
        <span class="cw-name">${name}</span>
        <button class="cw-gear" title="Configure">${gearSvg()}</button>
        <button class="cw-toggle ${on ? 'on' : 'off'}">${on ? 'ON' : 'OFF'}</button>
      </div>`).join('');
    return `
    <div class="cw">
      <div class="cw-titlebar">
        <span class="cw-dot"></span><span class="cw-title">LMU&nbsp;APP</span>
        <span class="cw-winbtns"><i></i><i></i><i class="x"></i></span>
      </div>
      <div class="cw-tabs">
        <button class="cw-tab active">Overlays</button>
        <button class="cw-tab">Class Colors</button>
      </div>
      <div class="cw-body">
        ${rows}
        <div class="cw-divider"></div>
        <label class="cw-check"><span class="cw-box checked"></span>Hide overlays in garage</label>
        <div class="cw-divider"></div>
        <div class="cw-lockrow">
          <span class="cw-lock free"><span class="cw-lockknob"></span></span>
          <span class="cw-lockcap">FREE — overlays draggable</span>
        </div>
      </div>
    </div>`;
  }

  function gearSvg() {
    return `<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" aria-hidden="true">
      <path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 0 0 .12-.61l-1.92-3.32a.49.49 0 0 0-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54a.48.48 0 0 0-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96a.48.48 0 0 0-.59.22L2.74 8.87a.49.49 0 0 0 .12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58a.49.49 0 0 0-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.04.24.23.41.47.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32a.49.49 0 0 0-.12-.61l-2.01-1.58zM12 15.6a3.6 3.6 0 1 1 0-7.2 3.6 3.6 0 0 1 0 7.2z"/>
    </svg>`;
  }

  window.LMU = {
    DATA, DIRECTIONS,
    renderSpeed, renderInputs, renderFuel, renderTyres,
    renderStandings, renderRelative, renderControl, tyreColor,
    renderFuelCalc, renderVeCalc,
  };
})();
