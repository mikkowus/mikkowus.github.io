const SESSION_DAYS = 30;
const LOGIN_ATTEMPT_WINDOW_MINUTES = 15;
const MAX_FAILED_ATTEMPTS_PER_NAME = 5;
const MAX_FAILED_ATTEMPTS_PER_IP = 20;

function corsHeaders(request, env) {
  const allowed = (env.ALLOWED_ORIGINS || '').split(',').map((s) => s.trim()).filter(Boolean);
  const origin = request.headers.get('Origin');
  const headers = {
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  };
  if (origin && allowed.includes(origin)) {
    headers['Access-Control-Allow-Origin'] = origin;
  }
  return headers;
}

function json(data, status, extraHeaders) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', ...extraHeaders },
  });
}

async function sha256Hex(input) {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(input));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

function timingSafeEqual(a, b) {
  if (a.length !== b.length) return false;
  let mismatch = 0;
  for (let i = 0; i < a.length; i++) {
    mismatch |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return mismatch === 0;
}

async function authenticate(request, env) {
  const auth = request.headers.get('Authorization') || '';
  if (!auth.startsWith('Bearer ')) return null;
  const token = auth.slice('Bearer '.length).trim();
  if (!token) return null;
  const row = await env.DB.prepare(
    `SELECT c.id, c.name, c.role FROM sessions s
     JOIN contributors c ON c.id = s.contributor_id
     WHERE s.token = ? AND s.expires_at > CURRENT_TIMESTAMP`
  ).bind(token).first();
  return row || null;
}

function submissionToFeature(row) {
  return {
    type: 'Feature',
    geometry: { type: 'Point', coordinates: [row.lon, row.lat] },
    properties: {
      id: `submission-${row.id}`,
      name: row.name,
      description: row.description || '',
      region: row.region || '',
      water_body_name: row.water_body_name || '',
      water_body_type: row.water_body_type || '',
      access_type: row.access_type || '',
      parking_notes: row.parking_notes || '',
      tags: row.tags ? JSON.parse(row.tags) : [],
      nearest_gauge_site_no: row.nearest_gauge_site_no || '',
      source_url: row.source_url || '',
      photos: [],
      tracks: [],
    },
  };
}

async function handleLogin(request, env) {
  const body = await request.json().catch(() => null);
  if (!body || !body.name || !body.code) return json({ error: 'name and code are required' }, 400);

  const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
  const window = `datetime('now', '-${LOGIN_ATTEMPT_WINDOW_MINUTES} minutes')`;
  const [byName, byIp] = await Promise.all([
    env.DB.prepare(`SELECT COUNT(*) AS count FROM login_attempts WHERE name = ? AND success = 0 AND attempted_at > ${window}`)
      .bind(body.name).first(),
    env.DB.prepare(`SELECT COUNT(*) AS count FROM login_attempts WHERE ip = ? AND success = 0 AND attempted_at > ${window}`)
      .bind(ip).first(),
  ]);
  if ((byName?.count || 0) >= MAX_FAILED_ATTEMPTS_PER_NAME || (byIp?.count || 0) >= MAX_FAILED_ATTEMPTS_PER_IP) {
    return json({ error: 'Too many attempts. Try again later.' }, 429);
  }

  const contributor = await env.DB.prepare('SELECT * FROM contributors WHERE name = ?').bind(body.name).first();
  const hash = await sha256Hex(`${body.name}:${body.code}`);
  const ok = !!contributor && timingSafeEqual(hash, contributor.access_code_hash);

  await env.DB.prepare('INSERT INTO login_attempts (name, ip, success) VALUES (?, ?, ?)')
    .bind(body.name, ip, ok ? 1 : 0).run();

  if (!ok) return json({ error: 'Invalid name or code' }, 401);

  const token = crypto.randomUUID();
  const expiresAt = new Date(Date.now() + SESSION_DAYS * 24 * 60 * 60 * 1000).toISOString();
  await env.DB.prepare('INSERT INTO sessions (token, contributor_id, expires_at) VALUES (?, ?, ?)')
    .bind(token, contributor.id, expiresAt).run();

  return json({ token, expiresAt, name: contributor.name, role: contributor.role }, 200);
}

async function handleCreateSubmission(request, env, contributor) {
  const body = await request.json().catch(() => null);
  if (!body || !body.name || typeof body.lat !== 'number' || typeof body.lon !== 'number') {
    return json({ error: 'name, lat, and lon are required' }, 400);
  }

  const result = await env.DB.prepare(
    `INSERT INTO submissions
      (name, description, region, water_body_name, water_body_type, access_type,
       parking_notes, tags, nearest_gauge_site_no, source_url, lat, lon, submitted_by, source)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
  ).bind(
    body.name,
    body.description || null,
    body.region || null,
    body.water_body_name || null,
    body.water_body_type || null,
    body.access_type || null,
    body.parking_notes || null,
    JSON.stringify(body.tags || []),
    body.nearest_gauge_site_no || null,
    body.source_url || null,
    body.lat,
    body.lon,
    contributor.id,
    body.source === 'bulk-import' ? 'bulk-import' : 'mobile'
  ).run();

  return json({ id: result.meta.last_row_id }, 201);
}

async function handleGeocode(request, env, contributor) {
  if (contributor.role !== 'owner') return json({ error: 'Owner role required' }, 403);
  if (!env.GOOGLE_MAPS_API_KEY) return json({ error: 'GOOGLE_MAPS_API_KEY not configured' }, 500);

  const body = await request.json().catch(() => null);
  const query = (body?.query || '').trim();
  if (!query) return json({ error: 'query is required' }, 400);

  const url = new URL('https://maps.googleapis.com/maps/api/place/findplacefromtext/json');
  url.searchParams.set('input', query);
  url.searchParams.set('inputtype', 'textquery');
  url.searchParams.set('fields', 'place_id,geometry,formatted_address,name');
  url.searchParams.set('key', env.GOOGLE_MAPS_API_KEY);

  const res = await fetch(url);
  if (!res.ok) return json({ error: `Places API responded ${res.status}` }, 502);
  const data = await res.json();

  if (data.status !== 'OK' || !data.candidates?.length) {
    return json({ error: data.status || 'No match found' }, 404);
  }

  const c = data.candidates[0];
  return json({
    lat: c.geometry.location.lat,
    lng: c.geometry.location.lng,
    formatted_address: c.formatted_address || '',
    place_id: c.place_id || '',
    matched_name: c.name || '',
  }, 200);
}

async function handleListSubmissions(request, env, contributor, status) {
  if (contributor.role !== 'owner') return json({ error: 'Owner role required' }, 403);
  const rows = await env.DB.prepare('SELECT * FROM submissions WHERE status = ? ORDER BY submitted_at DESC')
    .bind(status).all();

  if (status === 'approved' && new URL(request.url).searchParams.get('format') === 'geojson') {
    return json({ type: 'FeatureCollection', features: rows.results.map(submissionToFeature) }, 200);
  }
  return json(rows.results, 200);
}

async function handleReview(request, env, contributor, id, action) {
  if (contributor.role !== 'owner') return json({ error: 'Owner role required' }, 403);
  const body = await request.json().catch(() => ({}));
  const status = action === 'approve' ? 'approved' : 'rejected';

  const result = await env.DB.prepare(
    `UPDATE submissions SET status = ?, reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP, reviewer_notes = ?
     WHERE id = ? AND status = 'pending'`
  ).bind(status, contributor.id, body.reviewer_notes || null, id).run();

  if (result.meta.changes === 0) return json({ error: 'Submission not found or already reviewed' }, 404);
  return json({ ok: true }, 200);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const headers = corsHeaders(request, env);

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers });
    }

    try {
      let response;

      if (request.method === 'POST' && url.pathname === '/api/login') {
        response = await handleLogin(request, env);
      } else if (url.pathname === '/api/import/geocode' && request.method === 'POST') {
        const contributor = await authenticate(request, env);
        if (!contributor) return json({ error: 'Unauthorized' }, 401, headers);
        response = await handleGeocode(request, env, contributor);
      } else if (url.pathname === '/api/submissions' && request.method === 'POST') {
        const contributor = await authenticate(request, env);
        if (!contributor) return json({ error: 'Unauthorized' }, 401, headers);
        response = await handleCreateSubmission(request, env, contributor);
      } else if (url.pathname === '/api/submissions' && request.method === 'GET') {
        const contributor = await authenticate(request, env);
        if (!contributor) return json({ error: 'Unauthorized' }, 401, headers);
        const status = url.searchParams.get('status') || 'pending';
        response = await handleListSubmissions(request, env, contributor, status);
      } else {
        const reviewMatch = url.pathname.match(/^\/api\/submissions\/(\d+)\/(approve|reject)$/);
        if (reviewMatch && request.method === 'POST') {
          const contributor = await authenticate(request, env);
          if (!contributor) return json({ error: 'Unauthorized' }, 401, headers);
          response = await handleReview(request, env, contributor, Number(reviewMatch[1]), reviewMatch[2]);
        } else {
          response = json({ error: 'Not found' }, 404);
        }
      }

      const merged = new Headers(response.headers);
      Object.entries(headers).forEach(([k, v]) => merged.set(k, v));
      return new Response(response.body, { status: response.status, headers: merged });
    } catch (err) {
      console.error(err);
      return json({ error: 'Internal error' }, 500, headers);
    }
  },
};
