const ICONS = {
  check: '<path d="M20 6 9 17l-5-5"/>',
  camera: '<path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3z"/><circle cx="12" cy="13" r="3"/>',
  upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>',
  lock: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
  arrow: '<path d="M5 12h14M12 5l7 7-7 7"/>',
  back: '<path d="M19 12H5M12 19l-7-7 7-7"/>',
  cloud: '<path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/>',
  close: '<path d="M18 6 6 18M6 6l12 12"/>',
  refresh: '<path d="M3 12a9 9 0 0 1 15-6.7L21 8M21 3v5h-5M21 12a9 9 0 0 1-15 6.7L3 16M3 21v-5h5"/>',
  wifioff: '<path d="M12 20h.01M8.5 16.4a5 5 0 0 1 7 0M2 8.8a15 15 0 0 1 4.2-2.6M22 8.8a15 15 0 0 0-10-3.3M5 12.9a10 10 0 0 1 5.2-2.7M19 12.9a10 10 0 0 0-2.7-1.9M2 2l20 20"/>',
  badge: '<rect x="3" y="3" width="18" height="18" rx="4" stroke-dasharray="3 2.5"/><path d="M12 7l5 5-5 5-5-5z"/>', // placeholder slot for your custom symbols
  dots: '<circle cx="12" cy="12" r="8" stroke-dasharray="2 3"/>',
  scan: '<path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2M7 12h10"/>',
  notebook: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 7h6M9 11h6M3 8h2M3 12h2M3 16h2"/>',
  compass: '<circle cx="12" cy="12" r="9"/><path d="m15.5 8.5-2 5-5 2 2-5z"/>',
  bulb: '<path d="M9 18h6M10 22h4M12 2a7 7 0 0 0-4 12.7c.7.6 1 1.3 1 2.3h6c0-1 .3-1.7 1-2.3A7 7 0 0 0 12 2z"/>',
  // ---- mistake-type symbols: 24x24, one stroke colour (currentColor), so they follow the theme
  t_arithmetic_slip: '<path d="M12 3l7.8 4.5v9L12 21l-7.8-4.5v-9z"/><path d="M9.2 10.6h5.6M9.2 13.4h5.6"/>',   // hexagon (your notebook)
  t_sign_slip: '<path d="M12 4.5v8M8 8.5h8M8 18.5h8"/>',                                                    // ±
  t_both_sides: '<circle cx="12" cy="6.5" r="1.4" fill="currentColor"/><circle cx="6.5" cy="16.5" r="1.4" fill="currentColor"/><circle cx="17.5" cy="16.5" r="1.4" fill="currentColor"/>', // ∴
  t_wrong_operation: '<path d="M4 8h13M13.5 4.5 17 8l-3.5 3.5M20 16H7M10.5 12.5 7 16l3.5 3.5"/>',          // two different moves
  t_distribution: '<path d="M14 5c-2.2 3-2.2 11 0 14M20 5c2.2 3 2.2 11 0 14M3.5 12h7M7.8 9.4 10.5 12l-2.7 2.6"/>',
  t_unlike_terms: '<circle cx="7" cy="12" r="3.4"/><rect x="14" y="8.6" width="6.8" height="6.8" rx="1.4"/><path d="M10.4 12h3.6"/>',
  t_dropped_term: '<path d="M6 13.5 12 7l6 6.5"/><path d="M5 18.5h3M10.5 18.5h3M16 18.5h3"/>',            // ^ with dashes (your notebook)
  t_copy_error: '<rect x="4.5" y="5.5" width="15" height="13" rx="3" stroke-dasharray="3 3"/>',             // dotted box (your notebook)
  t_inequality_flip: '<path d="M10 6.5 4.5 12l5.5 5.5M14 6.5l5.5 5.5-5.5 5.5"/>',
  t_order_of_ops: '<path d="M4 18.5h4.5V14H13V9.5h4.5V5.5"/>',
  t_equals_sign: '<path d="M4.5 9.5h9M4.5 14.5h9M17 8.5 20 12l-3 3.5"/>',
  t_unit_mistake: '<rect x="3" y="8" width="18" height="8" rx="1.8"/><path d="M6.5 8v3M10 8v4.5M13.5 8v3M17 8v4.5"/>',
  t_messy_layout: '<path d="M4 7h10M7 12h13M4 17h9"/>',
  t_unclear_char: '<circle cx="12" cy="12" r="8" stroke-dasharray="2 3"/>',                                  // dotted circle (your notebook)
  t_skipped_step: '<path d="M5 6h14M5 18h14"/><circle cx="12" cy="10" r="1" fill="currentColor"/><circle cx="12" cy="14" r="1" fill="currentColor"/>',
  t_check: '<path d="M12 4l8 8-8 8-8-8z"/>',
  screen: '<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>',
};
const tic = t => ic(ICONS['t_' + t] ? 't_' + t : 't_check'); // icon for a mistake type
const ic = n => `<svg class="i" viewBox="0 0 24 24" aria-hidden="true">${ICONS[n]}</svg>`;
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const $ = s => document.querySelector(s);

async function api(path, body, opts = {}) {
  const isForm = body instanceof FormData;
  const r = await fetch(path, {
    method: body === undefined ? 'GET' : 'POST', signal: opts.signal, headers: { ...(opts.headers || {}), ...(body !== undefined && !isForm ? { 'Content-Type': 'application/json' } : {}) },
    body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
  });
  if (!r.ok) {
    let m = 'Something went wrong. Please try again.';
    try { const d = await r.json(); if (typeof d.detail === 'string') m = d.detail; } catch (_) {}
    throw Object.assign(new Error(m), { status: r.status });
  }
  return r.json();
}

function setTheme(t) { // t = 'light' | 'dark' | null (follow the device)
  if (t) document.documentElement.dataset.theme = t; else delete document.documentElement.dataset.theme;
  try { t ? localStorage.setItem('compass.theme', t) : localStorage.removeItem('compass.theme'); } catch (_) {}
}
try { const t = localStorage.getItem('compass.theme'); if (t) document.documentElement.dataset.theme = t; } catch (_) {}
