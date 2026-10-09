const S = { view: 'join', code: '', session: '', lesson: null, result: null, photo: null, workFile: null, taskFile: null,
  wantTask: false, skipTask: false, ctrl: null, error: '' };
try { const j = JSON.parse(sessionStorage.getItem('compass.s') || 'null'); if (j && j.session) Object.assign(S, j, { view: 'home' }); } catch (_) {}
const save = () => { try { sessionStorage.setItem('compass.s', JSON.stringify({ code: S.code, session: S.session, lesson: S.lesson })); } catch (_) {} };
const getQ = () => { try { return JSON.parse(localStorage.getItem('compass.q') || '[]'); } catch (_) { return []; } };
const setQ = q => { try { localStorage.setItem('compass.q', JSON.stringify(q)); } catch (_) {} };
const WORDS = ['No', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine'];

// ---------------------------------------------------------------- pieces
const head = back => `<header class="top">${back ? `<button class="sq" data-act="home" aria-label="Back">${ic('back')}</button>` : `<div class="sq">${ic('compass')}</div>`}
  <div class="ttl"><b>Compass</b><span>${S.lesson ? esc(S.lesson.subject) + ' • ' + esc(S.lesson.room) : 'Join your class'}</span></div>
  <button class="round" data-act="help" aria-label="Guide to the marks">?</button></header>`;
const foot = `<footer class="priv">${ic('lock')} Only you see your work.</footer>`;
const page = (back, body) => head(back) + `<main>${body}</main>` + foot;

const VIEWS = {
  join: () => head(false) + `<main><div class="hero">${ic('compass')}</div><h1 tabindex="-1">A little help,<br>a step at a time.</h1>
    <p>Join your classroom. Ask for help quietly, whenever you need it.</p>
    <div><label for="code">Class code</label><input id="code" type="text" autocapitalize="characters" autocomplete="off" value="${esc(S.code)}" placeholder="MAPLE8"><div class="hint">Your teacher will share this.</div></div>
    <div><label for="sc">Student code · optional</label><input id="sc" type="text" autocomplete="off" placeholder="Enter your code"><div class="hint">Only if your teacher gave you one.</div></div>
    ${S.error ? `<p role="alert" style="color:var(--amber-ink)">${esc(S.error)}</p>` : ''}
    <button class="btn pri" data-act="join">${ic('arrow')} Join class</button></main>` + foot,

  home: () => page(false, `<span class="pill">${esc(S.lesson.label)} · ${esc(S.lesson.title)}</span><h1 tabindex="-1">How’s it going?</h1>
    <p>A quick signal helps your teacher find the right pace. No one else sees your tap.</p>
    <button class="big lost" data-act="pulse" data-kind="lost">${ic('cloud')}<div><b>I'm lost</b><span>A little more explanation, please.</span></div></button>
    <button class="big got" data-act="pulse" data-kind="got_it">${ic('check')}<div><b>Got it</b><span>Ready for the next step.</span></div></button>
    <div class="card"><b>Want a fresh look at your steps?</b><button class="btn" data-act="photo">${ic('camera')} Check my work</button><p>Take a photo or upload one.</p></div>`),

  photo: () => page(true, `<div class="circle">${ic('notebook')}</div><h1 tabindex="-1">Start with a photo</h1>
    <p>Nothing here yet, and that’s okay. Photograph a few steps whenever you’d like a second look.</p>
    <button class="btn pri" data-act="cam">${ic('camera')} Take a photo</button><button class="btn" data-act="up">${ic('upload')} Upload a photo</button>
    <p>Just your work is enough. Keep your name and classmates out of the photo.</p>`),

  checking: () => page(false, `<div class="circle">${ic('scan')}</div><h1 tabindex="-1">Looking at each step…</h1>
    <p>This may take a moment. We’re checking the maths, not judging you.</p><div class="bar"><i id="bar" style="width:33%"></i></div>
    <p id="stage">Reading your photo · 1 of 3</p><p>Your photo stays private. You can stop the check at any time.</p>
    <button class="btn" data-act="stop">Stop checking</button>`),

  unreadable: () => page(true, `<div class="circle">${ic('scan')}</div><h1 tabindex="-1">${esc(S.error ? 'I couldn’t check this photo' : 'I couldn’t read this photo')}</h1>
    <p>${esc(S.error || 'The writing is a little too soft to check. Nothing you did wrong—let’s try with more light.')}</p>
    <p style="color:var(--ink);font-weight:600">Keep the page flat and fit all your steps inside the photo.</p>
    <button class="btn pri" data-act="cam">${ic('camera')} Retake photo</button><button class="btn" data-act="up">${ic('upload')} Choose another photo</button>
    <p>No result was shared. Your work is still private.</p>`),

  offline: () => { const n = getQ().length; return page(true, `<div class="circle">${ic('wifioff')}</div><h1 tabindex="-1">You’re offline for now</h1>
    <p>Your signal hasn’t reached your teacher. It’s saved on this device, not sent.</p>
    <div class="card"><span class="chip a" style="align-self:flex-start">Not sent · ${n} signal${n === 1 ? '' : 's'}</span><p>Reconnect, then tap below to send it privately.</p>${S.error ? `<p role="alert">${esc(S.error)}</p>` : ''}</div>
    <button class="btn pri" data-act="resend">${ic('refresh')} Reconnect &amp; send</button><button class="btn" data-act="discard">Discard saved signal</button>
    <p>Need help now? You can always ask your teacher directly.</p>`); },

  task: () => page(true, `<h1 tabindex="-1">One more piece</h1><span class="chip g" style="align-self:flex-start">Your work photo is ready</span>
    ${photoBlock(true)}
    <div class="card amber">${ic('camera')}<h2>Take a photo of the task so I can check the idea too.</h2><p>Include the question and any diagram. You don’t need to show your name.</p>
    <button class="btn pri" data-act="task-cam">${ic('camera')} Take task photo</button></div>
    <button class="btn" data-act="task-up">${ic('upload')} Upload task photo</button><button class="btn link" data-act="skip-task">See my steps first</button>`),

  result: () => { const r = S.result, bad = r.steps.filter(s => s.status === 'check').length;
    return page(true, `<h1 tabindex="-1">Let’s look together</h1>
    <p>${bad ? `${WORDS[bad] || bad} step${bad === 1 ? '' : 's'} to revisit. Your thinking is still a useful place to start.` : 'Every step follows from the one before it. Nicely done.'}</p>
    ${r.demo ? '<span class="demo">Demo data: no AI key is set, so this is a fixed example.</span>' : ''}
    ${photoBlock(false)}
    <div class="chips">${bad ? `<span class="chip a">${r.steps.find(s => s.status === 'check').index} · Check this step</span>` : ''}${r.steps.some(s => s.status === 'ok') ? `<span class="chip g">${ic('check')} Correct</span>` : ''}</div>
    <p>Tap an amber step for a hint. Checks follow your previous line.</p>`); },
};

function marker(s) {
  if (s.status === 'ok') return `<span class="mk ok" title="Correct">${ic('check')}</span>`;
  if (s.status === 'check') return `<button class="mk amber" data-act="hint" data-i="${s.index}" aria-label="Step ${s.index}: check this step">${s.index}</button>`;
  return `<span class="mk">${s.index}</span>`;
}

function photoBlock(compact) {
  const r = S.result, withBox = S.photo && r.steps.some(s => s.line_box);
  if (!withBox) { // no photo or no positions: show the lines we read, with the same marks
    return `<div class="rows">${r.steps.map(s => `<div class="row ${s.status}">${marker(s)}<code>${esc(s.text)}</code>${s.mistake ? `<span class="tile" title="${esc(s.mistake.name)}">${tic(s.mistake.type)}</span>` : ''}${altChip(s, false)}</div>`).join('')}</div>`;
  }
  const items = r.steps.filter(s => s.line_box).filter((s, i) => !compact || i < 3).map(s => {
    const [x, y, w, h] = s.line_box, cy = ((y + h / 2) * 100).toFixed(2);
    const m = s.mistake;
    return `<div style="position:absolute;left:0;right:0;top:${cy}%">${marker(s)}${m ? `<span class="badge" title="${esc(m.name)}">${tic(m.type)}</span>` : ''}${altChip(s, true, ((x + w) * 100).toFixed(1))}</div>` +
      (s.status === 'check' ? `<div class="wave ${m && m.certainty === 'certain' ? 'sure' : ''}" style="left:${x * 100}%;width:${w * 100}%;top:${((y + h) * 100).toFixed(2)}%"></div>` : '');
  }).join('');
  return `<div class="photo"><img src="${S.photo}" alt="Your photographed work">${items}</div>`;
}

function altChip(s, abs, left) {
  if (!s.unreadable || !s.unreadable.length) return '';
  const u = s.unreadable[0];
  return `<button class="${abs ? 'alt' : 'chip'}" ${abs ? `style="left:${left}%"` : ''} data-act="unclear" data-i="${s.index}">${ic('dots')} ${u.alternatives.map(esc).join(' or ')}</button>`;
}

// ---------------------------------------------------------------- rendering
function view(name, err) {
  S.view = name; S.error = err || '';
  $('#app').innerHTML = VIEWS[name]();
  const h = $('#app h1'); if (h) h.focus({ preventScroll: true });
  window.scrollTo(0, 0);
}
function layer(html) { $('#layer').innerHTML = html ? `<div class="back" data-act="close"></div><div class="sheet" role="dialog" aria-modal="true">${html}</div>` : ''; }
function toast(msg, icon = 'lock') {
  const t = document.createElement('div'); t.className = 'toast'; t.setAttribute('role', 'status');
  t.innerHTML = `${ic(icon)} ${esc(msg)} ${ic('check')}`; document.body.append(t); setTimeout(() => t.remove(), 2600);
}
const closeBtn = `<button class="sq" data-act="close" aria-label="Close">${ic('close')}</button>`;

// ---------------------------------------------------------------- actions
function expired(e) { // server restarted or the lesson ended: the saved class code/session no longer works
  if (e.status !== 401 && e.status !== 404 && e.status !== 410) return false;
  sessionStorage.removeItem('compass.s'); S.session = ''; S.lesson = null;
  view('join', e.status === 410 ? e.message : 'This class is no longer running. Ask your teacher for the current class code, then join again.');
  return true;
}

async function sendPulse(kind) { await api('/api/pulse', { code: S.code, session: S.session, kind }); }

async function flush() {
  const q = getQ();
  for (let i = 0; i < q.length; i++) { await sendPulse(q[i].kind); setQ(q.slice(i + 1)); }
}

async function analyze() {
  S.ctrl = new AbortController(); view('checking');
  const fd = new FormData(); fd.append('code', S.code); fd.append('session', S.session); fd.append('photo', S.workFile);
  if (S.taskFile) fd.append('task_photo', S.taskFile);
  const stage = n => { const b = $('#bar'); if (b) { b.style.width = n * 33 + '%'; $('#stage').textContent = `Reading your photo · ${n} of 3`; } };
  try {
    stage(2);
    const r = await api('/api/analyze', fd, { signal: S.ctrl.signal }); stage(3);
    S.result = r;
    if (r.reading_quality === 'low' || !r.steps.length) return view('unreadable');
    view(r.needs_task_photo && !S.taskFile && !S.skipTask ? 'task' : 'result');
  } catch (e) {
    if (e.name === 'AbortError') return view('home');
    if (expired(e)) return;
    view('unreadable', e instanceof TypeError ? 'No connection, so your photo wasn’t sent. Check your Wi-Fi and try again.' : e.message);
  }
}

function onFile(f) {
  if (S.wantTask) { S.taskFile = f; S.wantTask = false; } else { S.workFile = f; S.taskFile = null; S.skipTask = false; if (S.photo) URL.revokeObjectURL(S.photo); S.photo = URL.createObjectURL(f); }
  analyze();
}

async function recheck(i, pos, ch) {
  const r = S.result, lines = r.task ? [{ text: r.task, box: null, unclear: [] }] : [];
  r.steps.forEach(s => {
    let t = s.text, u = s.unreadable || [];
    if (s.index === i) { t = t.slice(0, pos) + ch + t.slice(pos + 1); u = u.filter(x => x.pos !== pos); }
    lines.push({ text: t, box: s.line_box, unclear: u });
  });
  try {
    const out = await api('/api/check', { lines, code: S.code, session: S.session, result_id: r.result_id });
    out.demo = r.demo; S.result = out; layer(''); view('result');
  } catch (e) { layer(''); if (!expired(e)) toast(e.message, 'close'); }
}

const ACT = {
  async join() {
    S.code = $('#code').value.trim().toUpperCase(); const sc = $('#sc').value.trim();
    try {
      const r = await api('/api/join', { code: S.code, student_code: sc || null });
      Object.assign(S, { session: r.session, lesson: r.lesson }); save(); view('home');
    } catch (e) { view('join', e instanceof TypeError ? 'No connection. Check your Wi-Fi and try again.' : e.message); }
  },
  async pulse(d) {
    try { await flush(); await sendPulse(d.kind); toast('Sent privately'); }
    catch (e) {
      if (e instanceof TypeError) { setQ([...getQ(), { kind: d.kind, t: Date.now() }]); view('offline'); }
      else if (!expired(e)) toast(e.message, 'close');
    }
  },
  async resend() {
    try { await flush(); toast('Sent privately'); view('home'); } catch (e) { view('offline', e instanceof TypeError ? 'Still offline. Try again in a moment.' : e.message); }
  },
  discard() { setQ([]); view('home'); },
  home() { view('home'); }, photo() { view('photo'); }, stop() { S.ctrl && S.ctrl.abort(); },
  cam() { S.wantTask = false; $('#cam').click(); }, up() { S.wantTask = false; $('#up').click(); },
  'task-cam'() { S.wantTask = true; $('#cam').click(); }, 'task-up'() { S.wantTask = true; $('#up').click(); },
  'skip-task'() { S.skipTask = true; view('result'); },
  close() { layer(''); },
  hint(d) {
    const s = S.result.steps.find(x => x.index == d.i), m = s.mistake, sure = m.certainty === 'certain';
    layer(`<div class="hd"><h2>A hint for step ${s.index}</h2>${closeBtn}</div>
      <div class="chips"><span class="chip a">${tic(m.type)} ${esc(m.name)} · ${sure ? 'sure' : 'worth checking'}</span></div>
      <p style="color:var(--ink)">${esc(m.hint)}</p>
      ${m.also.some(a => a.type === 'skipped_step') ? '<p>You also did two moves at once. Writing the in-between line can show where it slipped.</p>' : ''}
      ${m.practice ? `<div class="try"><b>Try just this step</b><code>${esc(m.practice)}</code></div>` : ''}
      <button class="btn pri" data-act="close">Back to my work</button><button class="btn" data-act="dispute" data-i="${s.index}">This isn't right</button>`);
  },
  async dispute(d) {
    const s = S.result.steps.find(x => x.index == d.i);
    try { await api('/api/feedback', { code: S.code, session: S.session, step: s.index, mistake_type: s.mistake && s.mistake.type }); layer(''); toast('Thanks, noted privately'); }
    catch (e) { layer(''); toast(e.message, 'close'); }
  },
  unclear(d) {
    const s = S.result.steps.find(x => x.index == d.i), u = s.unreadable[0];
    layer(`<div class="hd"><h2>Which character is it?</h2>${closeBtn}</div><p>Line ${s.index}: <code>${esc(s.text)}</code>. Pick the one you wrote.</p>
      ${u.alternatives.map(a => `<button class="btn" data-act="pick" data-i="${s.index}" data-pos="${u.pos}" data-ch="${esc(a)}">${esc(a)}</button>`).join('')}`);
  },
  pick(d) { recheck(+d.i, +d.pos, d.ch); },
  async help() {
    let types = []; try { types = await api('/api/legend'); } catch (_) {}
    layer(`<div class="hd"><h2>A guide to the marks</h2>${closeBtn}</div><p>These are pointers, not grades. Your work is always yours to question.</p>
      <div class="leg"><span class="mk ok">${ic('check')}</span><div><b>Quiet check · correct</b><span>This step follows your previous line.</span></div></div>
      <div class="leg"><span class="mk amber">2</span><div><b>Amber marker · check this step</b><span>Tap for a small, helpful hint.</span></div></div>
      <div class="leg"><span class="mk amber"><span style="width:26px;height:6px;display:block;background:url('data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2212%22 height=%226%22%3E%3Cpath d=%22M0 3Q3 0 6 3T12 3%22 fill=%22none%22 stroke=%22%23B7791F%22 stroke-width=%221.5%22/%3E%3C/svg%3E') repeat-x"></span></span><div><b>Single wave · worth checking</b><span>A possible slip. You decide.</span></div></div>
      <div class="leg"><span class="mk amber"><span style="width:26px;height:11px;display:block;background:url('data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2212%22 height=%2211%22%3E%3Cpath d=%22M0 3Q3 0 6 3T12 3M0 8Q3 5 6 8T12 8%22 fill=%22none%22 stroke=%22%23B7791F%22 stroke-width=%221.5%22/%3E%3C/svg%3E') repeat-x"></span></span><div><b>Double wave · sure</b><span>A clearer reason to revisit the step.</span></div></div>
      <div class="leg"><span class="mk amber">${tic('sign_slip')}</span><div><b>Mistake-type symbol</b><span>Shows the kind of slip. Tap the step for a hint.</span></div></div>
      <div class="leg"><span class="mk amber">${ic('dots')}</span><div><b>Dotted circle · unreadable character</b><span>Confirm a character, like 1 or 7.</span></div></div>
      ${types.length ? `<h3 style="margin:8px 0 0">Kinds of pointers</h3>${types.map(t => `<div class="leg"><span class="mk amber">${tic(t.type)}</span><div><b>${esc(t.name)}</b><span>${esc(t.blurb)}</span></div></div>`).join('')}` : ''}
      <button class="btn pri" data-act="close">Back to my work</button>`);
  },
};

document.addEventListener('click', e => { const a = e.target.closest('[data-act]'); if (a && ACT[a.dataset.act]) ACT[a.dataset.act](a.dataset, a); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') layer(''); if (e.key === 'Enter' && e.target.id && /^(code|sc)$/.test(e.target.id)) ACT.join(); });
$('#cam').onchange = $('#up').onchange = e => { const f = e.target.files[0]; e.target.value = ''; if (f) onFile(f); };
addEventListener('online', () => { if (getQ().length && S.view === 'offline') ACT.resend(); });

const qc = new URLSearchParams(location.search).get('c'); if (qc && !S.session) S.code = qc.toUpperCase();
view(S.session && S.lesson ? 'home' : 'join');
