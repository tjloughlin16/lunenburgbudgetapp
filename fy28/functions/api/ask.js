/** The question inbox: a resident asks, we store it, TJ and I read it.
 *
 *  WHAT THIS DELIBERATELY DOES NOT DO: answer. No model is called here, and that is the
 *  main cost control rather than an omission. An endpoint that asks an LLM per submission
 *  can be spammed into a bill; an endpoint that writes a row cannot, because the storage
 *  behind it does not bill at all.
 *
 *  THE COST MODEL, stated plainly because it drove every choice below.
 *
 *  On the Workers Free plan D1 does not bill. It STOPS: 100,000 writes a day. The risk was
 *  therefore never a surprise invoice, it was AVAILABILITY -- and specifically the site's
 *  own daily database push, which writes ~70,000 rows in one go. If submissions shared that
 *  budget, a flood would mean the public data goes stale until tomorrow.
 *
 *  So submissions live in their OWN D1 database (`lunenburg-questions`). A spam burst can
 *  exhaust that database's budget and the only casualty is the form saying "try again
 *  tomorrow". The read API, the query endpoint and the nightly push are untouched.
 *
 *  FIVE GATES, cheapest first, so an abusive request is refused before it costs anything:
 *
 *    1. Method and size      -- a body over the cap is rejected before it is parsed
 *    2. Shape                -- required field present, within length, not obviously junk
 *    3. Turnstile            -- Cloudflare's bot check. Free, no billing, and it fails
 *                               CLOSED here: no secret configured means no writes, ever
 *    4. Per-source rate      -- N per source per hour, counted in the same database
 *    5. Global daily cap     -- a hard ceiling on accepted rows per day. This is the one
 *                               that makes the exposure bounded rather than merely small,
 *                               because it holds even if every gate above is bypassed
 *
 *  Gates 4 and 5 each cost ONE indexed read before any write. That is the price of the
 *  ceiling and it is worth it.
 *
 *  ON THE SOURCE HASH. We keep a truncated SHA-256 of the caller's address plus a salt,
 *  never the address. Enough to notice one source flooding; not enough to recover who it
 *  was. A public budget site collecting residents' IP addresses would be a poor trade for
 *  a rate limit, and the lossy version does the same job.
 */

const MAX_BODY_BYTES = 8 * 1024;   // the whole request
const MAX_QUESTION = 2000;         // characters
const MAX_EMAIL = 200;
const PER_SOURCE_PER_HOUR = 5;
const GLOBAL_PER_DAY = 300;        // hard ceiling. 300 writes against 100,000 available
const TOPICS = new Set(['schools', 'town', 'taxes', 'data', 'other', '']);

const json = (obj, status = 200, extra = {}) =>
  new Response(JSON.stringify(obj, null, 1), {
    status,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'no-store',
      'access-control-allow-origin': '*',
      ...extra,
    },
  });

async function sha256Hex(text) {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, '0')).join('');
}

/** Cloudflare Turnstile. FAILS CLOSED.
 *
 *  If TURNSTILE_SECRET is not configured this returns false and nothing is written. That
 *  is the deliberate choice: a form that silently drops its bot check the moment a secret
 *  goes missing is worse than a form that stops working, because the first failure is
 *  invisible and the second is reported immediately. */
async function turnstileOk(token, secret, ip) {
  if (!secret) return { ok: false, why: 'not-configured' };
  if (!token) return { ok: false, why: 'no-token' };
  const form = new FormData();
  form.append('secret', secret);
  form.append('response', token);
  if (ip) form.append('remoteip', ip);
  try {
    const r = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify',
      { method: 'POST', body: form });
    const j = await r.json();
    return { ok: j.success === true, why: (j['error-codes'] || []).join(',') || 'failed' };
  } catch (e) {
    return { ok: false, why: 'verify-unreachable' };
  }
}

export async function onRequestOptions() {
  return new Response(null, {
    status: 204,
    headers: {
      'access-control-allow-origin': '*',
      'access-control-allow-methods': 'POST, OPTIONS',
      'access-control-allow-headers': 'content-type',
      'access-control-max-age': '86400',
    },
  });
}

export async function onRequestPost({ request, env }) {
  const db = env.QUESTIONS;
  if (!db) {
    return json({ ok: false, error: 'The question inbox is not configured on this build.' }, 503);
  }

  // GATE 1 -- size, before parsing. A declared length over the cap is refused outright.
  const declared = Number(request.headers.get('content-length') || 0);
  if (declared > MAX_BODY_BYTES) {
    return json({ ok: false, error: 'That is longer than this form accepts.' }, 413);
  }
  let body;
  try {
    const text = await request.text();
    if (text.length > MAX_BODY_BYTES) {
      return json({ ok: false, error: 'That is longer than this form accepts.' }, 413);
    }
    body = JSON.parse(text);
  } catch {
    return json({ ok: false, error: 'Could not read that submission.' }, 400);
  }

  // GATE 2 -- shape.
  const question = String(body.question ?? '').trim();
  const email = String(body.email ?? '').trim();
  const topic = String(body.topic ?? '').trim().toLowerCase();
  if (question.length < 10) {
    return json({ ok: false, error: 'Please write a little more so we can answer it.' }, 400);
  }
  if (question.length > MAX_QUESTION) {
    return json({ ok: false, error: `Please keep it under ${MAX_QUESTION} characters.` }, 400);
  }
  if (email && (email.length > MAX_EMAIL || !email.includes('@'))) {
    return json({ ok: false, error: 'That email address does not look right.' }, 400);
  }
  if (!TOPICS.has(topic)) {
    return json({ ok: false, error: 'Unknown topic.' }, 400);
  }

  // GATE 3 -- Turnstile. Nothing is written without it.
  const ip = request.headers.get('cf-connecting-ip') || '';
  const check = await turnstileOk(body.token, env.TURNSTILE_SECRET, ip);
  if (!check.ok) {
    return json({
      ok: false,
      error: check.why === 'not-configured'
        ? 'The form is not accepting questions yet. Nothing was saved.'
        : 'That did not pass the spam check. Please try again.',
      reason: check.why,
    }, 403);
  }

  // The salt keeps the hash from being reversible by trying every address. Falls back to
  // a constant so a missing secret degrades the rate limit rather than breaking the form.
  const source = ip
    ? (await sha256Hex(ip + '|' + (env.SOURCE_SALT || 'lunenburg'))).slice(0, 16)
    : 'unknown';
  const now = new Date();
  const day = now.toISOString().slice(0, 10);
  const hourAgo = new Date(now.getTime() - 3600_000).toISOString();

  // GATE 4 -- per source, per hour.
  const mine = await db.prepare(
    'SELECT COUNT(*) AS n FROM question WHERE source_hash = ? AND asked_at > ?')
    .bind(source, hourAgo).first();
  if ((mine?.n ?? 0) >= PER_SOURCE_PER_HOUR) {
    return json({
      ok: false,
      error: 'You have sent several questions already. Please come back in an hour — '
           + 'they are all in the queue.',
    }, 429, { 'retry-after': '3600' });
  }

  // GATE 5 -- the global daily ceiling. The bound that holds even if everything else fails.
  const today = await db.prepare(
    'SELECT COUNT(*) AS n FROM question WHERE substr(asked_at, 1, 10) = ?')
    .bind(day).first();
  if ((today?.n ?? 0) >= GLOBAL_PER_DAY) {
    return json({
      ok: false,
      error: 'The inbox has taken all the questions it can hold today. Please try '
           + 'tomorrow — nothing else on this site is affected.',
    }, 429, { 'retry-after': '7200' });
  }

  const id = crypto.randomUUID().replace(/-/g, '').slice(0, 20);
  await db.prepare(
    'INSERT INTO question (id, asked_at, body, email, topic, source_hash, country, status) '
    + "VALUES (?, ?, ?, ?, ?, ?, ?, 'new')")
    .bind(id, now.toISOString(), question, email || null, topic || null, source,
          request.cf?.country || null)
    .run();

  return json({
    ok: true,
    id,
    message: 'Question received. Every one is read by a person.',
    accepted_today: (today?.n ?? 0) + 1,
    daily_capacity: GLOBAL_PER_DAY,
  });
}

export async function onRequestGet() {
  return json({
    resource: 'ask',
    method: 'POST',
    what: 'Ask a question about the Lunenburg town or school budget. Stored for review by '
        + 'a person; no automated answer is generated.',
    fields: {
      question: `required, 10-${MAX_QUESTION} characters`,
      email: 'optional, only so we can reply',
      topic: [...TOPICS].filter(Boolean),
      token: 'required, a Cloudflare Turnstile token from the form',
    },
    limits: {
      per_source_per_hour: PER_SOURCE_PER_HOUR,
      accepted_per_day: GLOBAL_PER_DAY,
      note: 'Submissions are stored in a database separate from the published data, so a '
          + 'flood here cannot affect the site or its query API.',
    },
  });
}
