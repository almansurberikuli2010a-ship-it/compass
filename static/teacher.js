let T = null, ws = null, snap = null, closing = false;
try { T = JSON.parse(localStorage.getItem('compass.t') || 'null'); } catch (_) {}

const hdr = (right = '') => `<header><div class="sq" style="width:44px;height:44px">${ic('compass')}</div><b style="font-size:22px">Compass</b>
  <span class="nav">Live lesson</span><span class="sp"></span>${right}</header>`;
const themeBtn = () => `<button class="nav" style="border:0" data-act="theme">${document.documentElement.dataset.theme === 'dark' ? 'Dark mode' : 'Light mode'}</button><span class="sq" style="width:44px;height:44px;border-radius:50%;font-weight:700">T</span>`;

function startForm(note = '') {
  $("#root").innerHTML = hdr(themeBtn()) + `<div class="pc" style="max-width:520px;display:flex;flex-direction:column;gap:14px">
    <h1>Start a lesson</h1><p>Students join with the class code. Photos and names never reach this screen.</p>${note ? `<p role="alert" style="color:var(--amber-ink)">${esc(note)}</p>` : ''}
    <div><label for="f-title">Topic</label><input id="f-title" type="text" value="Equations, one step at a time"></div>
    <div><label for="f-subject">Subject</label><input id="f-subject" type="text" value="Maths"></div>
    <div><label for="f-room">Room</label><input id="f-room" type="text" value="Room 8"></div>
    <div><label for="f-label">Lesson label</label><input id="f-label" type="text" value="Lesson 04"></div>
    <div><label for="f-dur">Length in minutes</label><input id="f-dur" type="text" inputmode="numeric" value="45"></div>
    <button class="btn pri" data-act="start">Start lesson</button></div>`;
}

function connect() {
  closing = false; let got = false;
  ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/teacher/${T.code}?token=${encodeURIComponent(T.token)}`);
  ws.onmessage = e => { got = true; snap = JSON.parse(e.data); render(); };
  ws.onclose = () => {
    if (closing) return;
    if (!got) { localStorage.removeItem('compass.t'); T = null; return startForm('That lesson is no longer running. Start a new one.'); }
    const l = $('.live'); if (l) { l.classList.add('off'); l.textContent = 'Reconnecting…'; }
    setTimeout(connect, 2000);
  };
}

function heat(n, max) {
  const p = max ? Math.round(100 * n / max) : 0;
  return `background:color-mix(in srgb,#7A4A12 ${p}%,var(--chip));color:${p > 50 ? '#fff' : 'var(--ink)'}`;
}

function render() {
  const s = snap, L = s.lesson, r = s.room, max = Math.max(1, ...s.timeline.windows.map(w => w.lost));
  const segs = Math.min(Math.max(s.students, 1), 60), sc = s.students ? segs / s.students : 1;
  const lostN = Math.round(r.lost * sc), gotN = Math.round(r.got_it * sc);
  const seg = Array.from({ length: segs }, (_, i) => `<i class="${i < lostN ? 'l' : i < lostN + gotN ? 'g' : ''}"></i>`).join('');
  const pk = s.timeline.peak, W = s.timeline.windows;
  const hm = s.heatmap, hmax = Math.max(1, ...hm.rows.flatMap(x => x.cells));
  const tone = { hint: ic('badge'), check: ic('badge'), ok: ic('check') };
  const ins = s.insight
    ? `<div class="pc ins">${ic('bulb')} <b>A useful moment to revisit</b><h3>${esc(s.insight.headline)}</h3><p>${esc(s.insight.body)}</p><p style="margin-top:12px">Based on ${esc(s.insight.based_on)}</p></div>`
    : `<div class="pc ins">${ic('bulb')} <b>A useful moment to revisit</b><h3>Not enough signals yet</h3><p>When several students tap “I'm lost”, the moment and what followed it will show here.</p></div>`;
  $("#root").innerHTML = hdr(themeBtn()) + `
  <div style="display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;margin-bottom:18px"><div>
    <p>${esc(L.room.toUpperCase())} / ${esc(L.label.toUpperCase())}</p><h1>${esc(L.title)}</h1>
    <p>${s.students} students connected · Class code <b style="color:var(--ink)">${esc(L.code)}</b> · Minute ${L.minute} of ${L.duration}</p></div>
    <div style="display:flex;flex-direction:column;gap:10px;align-items:flex-end"><span class="live ${L.ended ? 'off' : ''}">${L.ended ? 'Lesson ended' : 'Live · updated just now'}</span>
    ${L.ended ? '' : '<button class="btn" style="width:auto;padding:0 28px;min-height:48px" data-act="end">End lesson</button>'}</div></div>
  <div class="grid">
    <div class="pc c4"><h2>How the room feels</h2><span class="chip">Last 2 minutes</span>
      <div style="margin-top:14px"><span class="num">${r.lost}</span> <span style="color:var(--mute)">of ${s.students} · I'm lost</span></div><div class="seg" aria-hidden="true">${seg}</div>
      <p>${ic('cloud')} ${r.lost} I'm lost</p><p>${ic('check')} ${r.got_it} Got it</p><p>${ic('dots')} ${r.quiet} no recent signal</p></div>
    <div class="pc c8"><div style="display:flex;justify-content:space-between"><div><h2>Where the pace changed</h2><p>Students feeling lost · 2-minute windows</p></div>${pk ? `<span class="chip a" style="height:fit-content">Peak · minute ${pk.minute}</span>` : ''}</div>
      <div class="chart" role="img" aria-label="Students feeling lost per 2-minute window">${W.map(w => `<i class="${pk && w.minute === pk.minute && pk.lost > 0 ? 'pk' : ''}" style="height:${Math.max(3, 100 * w.lost / max)}%">${pk && w.minute === pk.minute ? `<em>${w.lost}</em>` : ''}</i>`).join('')}</div>
      <div class="xs">${W.map((w, i) => `<span>${i % 4 === 0 ? w.minute : ''}</span>`).join('')}</div>
      <p style="margin-top:10px">The spike is a cue to pause—not a score for the class.</p></div>
    <div class="pc c7"><h2>Mistake-type heatmap</h2><p>Students with each pointer, by lesson interval. A student may appear in several types.</p>
      ${hm.rows.length ? `<table><tr><th></th>${hm.bins.map(b => `<th>${esc(b)}</th>`).join('')}</tr>${hm.rows.map(x => `<tr><td class="l">${tic(x.type)} ${esc(x.label)}</td>${x.cells.map(n => `<td class="h" style="${heat(n, hmax)}">${n}</td>`).join('')}</tr>`).join('')}</table>` : '<p style="margin:18px 0">No pointers yet. They appear as students check their work.</p>'}</div>
    <div class="c5" style="display:flex;flex-direction:column;gap:20px">${ins}
      <div class="pc plan"><h2>A 5-minute re-explanation</h2><b>${esc(s.plan.title)}</b><ul>${s.plan.steps.map(p => `<li><b>${p.min} min</b><span>${esc(p.text)}</span></li>`).join('')}</ul>
      <button class="btn pri" data-act="present">${ic('screen')} Use this explanation</button></div></div>
    <div class="pc c7"><h2>Class work · names hidden</h2><p>${s.work.photos} photos · ${s.work.checked} checked · ${s.work.clarify} need clarification</p>
      ${s.work.latest.map(w => `<div class="work"><span>Private work</span><span><b>${w.clock}</b> &nbsp;${esc(w.summary)}</span><span>${w.type ? tic(w.type) : ic('check')} ${esc(w.label)}</span></div>`).join('') || '<p style="margin:14px 0">Nothing yet.</p>'}</div>
  </div>
  <p style="margin-top:20px">${ic('lock')} Private signals. Shared understanding. Students’ names and original photos stay hidden here.</p>`;
}

const ACT = {
  async start() {
    const v = id => $('#' + id).value.trim();
    try {
      const r = await api('/api/lessons', { title: v('f-title') || 'Today’s lesson', subject: v('f-subject') || 'Maths', room: v('f-room') || 'Room 1', label: v('f-label') || 'Lesson 1', duration: Math.min(Math.max(parseInt(v('f-dur')) || 45, 5), 180) });
      T = { code: r.code, token: r.token }; localStorage.setItem('compass.t', JSON.stringify(T)); connect();
    } catch (e) { startForm(e.message); }
  },
  async end() {
    if (!confirm('End this lesson? Students will no longer be able to send signals.')) return;
    try { await api(`/api/lessons/${T.code}/end`, {}, { headers: { 'X-Teacher-Token': T.token } }); } catch (e) { alert(e.message); }
  },
  theme() { setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'); if (snap) render(); else startForm(); },
  present() {
    $('#ov').innerHTML = `<div class="over" role="dialog" aria-modal="true"><button class="btn" style="width:auto;padding:0 24px;float:right" data-act="closeov">Close</button>
      <h1>${esc(snap.plan.title)}</h1><ul style="padding:0">${snap.plan.steps.map(p => `<li><b>${p.min} min</b> &nbsp;${esc(p.text)}</li>`).join('')}</ul></div>`;
  },
  closeov() { $('#ov').innerHTML = ''; },
};
document.addEventListener('click', e => { const a = e.target.closest('[data-act]'); if (a && ACT[a.dataset.act]) ACT[a.dataset.act](); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') ACT.closeov(); });
addEventListener('beforeunload', () => { closing = true; });

if (T) connect(); else startForm();
