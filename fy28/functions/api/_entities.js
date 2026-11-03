/**
 * THE CURATED LAYER OF SEARCH: is there a page NAMED for what was typed?
 *
 * /api/search answers two questions. The full-text index answers "where do these words
 * appear?", ranked by how often they appear in a page's body -- which is why a person's
 * profile (their name, once) lost to a year of Select Board minutes (their name, forty
 * times), and a hub called "Free cash" lost to a workbook that prints the words on every
 * tab. This module answers the other question: which of the pages this project BUILT --
 * hubs, topic pages, reports, profiles, boards, departments, budget lines, funds,
 * contracts, the annual reports -- is called what the reader typed, or close to it?
 *
 * The list is fy28/public/data/search-entities.json (scripts/build_search_entities.py),
 * fetched once per isolate. Matching runs here, in memory: it reads ZERO rows of D1.
 *
 * HOW A NAME MATCHES. The query and every name are cut into words, stop-words dropped, and
 * each word compared with tolerance: the same stem (`reports` = `report`), a start
 * (`instr` -> `instructional`, three letters or more), or one typo in a word of five or more
 * (`chatper` -> `chapter`). Numbers must match exactly -- 1962 is not 1963. Each word is
 * weighted by how RARE it is across all the names (inverse document frequency), so `school`
 * -- in hundreds of names -- counts for little and `nuzzolo` for a lot. Then:
 *
 *     query coverage   how much of what was typed the name accounts for   (must be most of it)
 *     name coverage    how much of the name the query accounts for        (breaks ties)
 *
 * A name typed in full scores highest; a name that holds the query plus much else lower.
 * Keywords (hand-written tags, one-word addresses) match at a discount, and a result
 * matched only on one says so -- `via: 'keyword'` -- because a tag is ours, not the page's.
 */

const STOP = new Set(['the', 'a', 'an', 'of', 'and', 'or', 'for', 'in', 'on', 'to', 'at', 'by',
  'is', 'are', 'was', 'what', 'how', 'who', 'why', 'when', 'where', 'which', 'does', 'do',
  'it', 'its', 'our', 'we', 'this', 'that', 'with', 'from', 'as', 'be', 'about', 'page', 'mgl', 'g', 'l'])
const ENDING = /(ians|ian|ials|ial|ions|ion|ings|ing|ers|er|ed|es|s)$/

export function stem(w) {
  if (/^\d/.test(w)) return w
  if (w.length >= 6) {
    const s = w.replace(ENDING, '')
    if (s.length >= 4) return s
  }
  if (w.length >= 4 && w.endsWith('s') && !/(ss|us|is)$/.test(w)) return w.slice(0, -1)
  return w
}

export function tokens(s) {
  const raw = (s || '').toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '')
    .replace(/[’']s\b/g, '').replace(/[’']/g, '').match(/[a-z0-9]+/g) || []
  const kept = raw.filter(w => !STOP.has(w))
  return (kept.length ? kept : raw).map(stem)
}

/** The query's words as typed AND stemmed: a start is tested on what was TYPED, so `burns`
 *  (stem `burn`) does not reach `burndown`, while `instr` still reaches `instructional`. */
function queryWords(s) {
  const raw = (s || '').toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[’']s\b/g, '').replace(/[’']/g, '').match(/[a-z0-9]+/g) || []
  const kept = raw.filter(w => !STOP.has(w))
  const seen = new Set()
  return (kept.length ? kept : raw).map(w => ({ raw: w, s: stem(w) }))
    .filter(w => !seen.has(w.s) && seen.add(w.s)).slice(0, 8)
}

function lev1(a, b, max) {
  // Edit distance, stopping once it exceeds `max`. Short strings only.
  if (Math.abs(a.length - b.length) > max) return max + 1
  let prev = Array.from({ length: b.length + 1 }, (_, i) => i)
  for (let i = 1; i <= a.length; i++) {
    const cur = [i]
    let low = i
    for (let j = 1; j <= b.length; j++) {
      cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1))
      if (cur[j] < low) low = cur[j]
    }
    if (low > max) return max + 1
    prev = cur
  }
  return prev[b.length]
}

/** How well query word q ({raw, s}) matches name word n (stemmed), 0..1. */
export function wordMatch(qw, n) {
  const q = qw.s
  if (q === n) return 1
  if (/^\d/.test(q) || /^\d/.test(n)) return 0
  if (qw.raw.length >= 3 && n.startsWith(qw.raw)) return qw.raw.length >= 5 ? 0.92 : 0.85
  // The name word is the start of the query word (`custod` of `custodians`) -- but only when
  // it is most of it: `land` is not `landscaping`.
  if (n.length >= 4 && q.startsWith(n) && n.length >= 0.7 * q.length) return 0.85
  if (q.length >= 5 && n.length >= 5 && q[0] === n[0] && lev1(q, n, 1) <= 1) return 0.8
  if (q.length >= 8 && n.length >= 8 && q[0] === n[0] && lev1(q, n, 2) <= 2) return 0.7
  return 0
}

let cache = null
/** The list, prepared once: tokenised names, and how rare each word is across them. */
export function prepare(data) {
  const ents = (data && data.entities) || []
  const weights = (data && data.weights) || {}
  const df = new Map()
  const prepped = ents.map(e => {
    const names = [e.t, ...(e.a || [])].map(tokens).filter(t => t.length)
    const keys = (e.w || []).map(tokens).filter(t => t.length)
    for (const w of new Set([...names, ...keys].flat())) df.set(w, (df.get(w) || 0) + 1)
    return { e, names, keys, weight: weights[e.k] ?? 0.9 }
  })
  const N = prepped.length || 1
  const idf = w => Math.log(1 + N / (1 + (df.get(w) || 0)))
  return { prepped, idf, N }
}

export async function loadEntities(env, request) {
  if (cache) return cache
  try {
    const u = new URL('/data/search-entities.json', request.url)
    const res = await (env.ASSETS ? env.ASSETS.fetch(u) : fetch(u))
    cache = prepare(await res.json())
  } catch (e) {
    cache = prepare(null)
  }
  return cache
}

function scoreName(qt, nt, idf) {
  let qHave = 0, qAll = 0, nHave = 0, nAll = 0, every = true
  const usedN = new Array(nt.length).fill(0)
  for (const q of qt) {
    const wq = idf(q.s)
    qAll += wq
    let best = 0, at = -1
    for (let i = 0; i < nt.length; i++) {
      const m = wordMatch(q, nt[i])
      if (m > best) { best = m; at = i }
    }
    qHave += wq * best
    if (!best) every = false
    if (at >= 0) usedN[at] = Math.max(usedN[at], best)
  }
  for (let i = 0; i < nt.length; i++) { const w = idf(nt[i]); nAll += w; nHave += w * usedN[i] }
  const qcov = qAll ? qHave / qAll : 0
  const ncov = nAll ? nHave / nAll : 0
  return { qcov, ncov, every, score: qcov * (0.65 + 0.35 * ncov) }
}

/** The curated pages named for the query, best first. `limit` results at most. */
export function matchEntities(prep, q, limit = 6) {
  const qt = queryWords(q)
  if (!qt.length || !prep.prepped.length) return []
  const out = []
  for (const p of prep.prepped) {
    let best = null
    p.names.forEach((nt, i) => {
      const s = scoreName(qt, nt, prep.idf)
      // The page's own title, a shade above the other names it answers to.
      if (i > 0) s.score *= 0.97
      if (!best || s.score > best.score) best = { ...s, via: 'name' }
    })
    for (const kt of p.keys) {
      const s = scoreName(qt, kt, prep.idf)
      s.score *= 0.82
      if (!best || s.score > best.score) best = { ...s, via: 'keyword' }
    }
    // MOST OF WHAT WAS TYPED MUST BE IN THE NAME. One query word in three is not a match;
    // for a person every word must be, since half a name is somebody else.
    // `kim gauvin` is Kimberly Gauvin: every word must land, a start counts.
    if (!best) continue
    if (p.e.k === 'person' ? !(best.every && best.qcov >= 0.85) : best.qcov < (qt.length === 1 ? 0.8 : 0.72)) continue
    out.push({ ...best, score: best.score * p.weight, p })
  }
  out.sort((a, b) => b.score - a.score || a.p.e.t.length - b.p.e.t.length)
  // A CROWD OF ONE KIND IS CUT TO A FEW, so twelve Burnses or sixty-seven annual reports do
  // not push a hub off the list. The best of each kind always survives.
  const perKind = {}
  const kept = []
  for (const r of out) {
    const k = r.p.e.k
    perKind[k] = (perKind[k] || 0) + 1
    if (perKind[k] > (k === 'person' ? 4 : 3)) continue
    // Nothing far below the best: a strong match should stand alone rather than beside noise.
    if (kept.length && r.score < kept[0].score * 0.7) break
    kept.push(r)
    if (kept.length >= limit) break
  }
  return kept.map(r => ({
    kind: r.p.e.k, title: r.p.e.t, url: r.p.e.u, sub: r.p.e.s || '',
    score: Math.round(r.score * 1000) / 1000, via: r.via,
  }))
}
