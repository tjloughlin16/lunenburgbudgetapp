import type { ReactNode } from 'react'

/** A markdown renderer for the analyses, and a deliberately small one.
 *
 *  WHY THIS EXISTS RATHER THAN A DEPENDENCY. Seventeen analyses are written in Markdown and
 *  the Markdown is the source of truth -- rule 12, our processed copy, downloadable, still
 *  served at /docs/analyses/<id>.md. Hand-converting them to TSX would duplicate every
 *  figure in a file the verifiers do not read, which is this project's oldest defect shape:
 *  something derived written down, the thing it derived from moving, and nothing connecting
 *  the two. So the documents are RENDERED, never transcribed.
 *
 *  WHY NOT A LIBRARY. The site ships three dependencies and prerenders every route through
 *  headless Chrome. A markdown pipeline plus a sanitiser is a large amount of JavaScript on
 *  the critical path of a page whose whole content is prose, and none of these documents
 *  use anything past the subset below. If one ever does, the renderer prints the source
 *  line rather than swallowing it -- an unrendered line is visible, a dropped one is not.
 *
 *  NO RAW HTML IS EVER EMITTED. There is no `dangerouslySetInnerHTML` anywhere in this
 *  file. Every node is a real React element, so a document cannot inject markup into the
 *  page even though the documents are ours.
 *
 *  THE SUBSET, which is everything the seventeen analyses use: ATX headings, paragraphs,
 *  bulleted and numbered lists (one level of nesting), pipe tables with alignment,
 *  blockquotes, fenced code, thematic breaks, images, and inline emphasis, strong, code
 *  and links. */

export type Heading = { depth: number; text: string; id: string }

/** A stable, readable anchor for a heading, so a section of an analysis can be linked. */
export function slugify(text: string): string {
  return text.toLowerCase()
    .replace(/[`*_[\]()]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '') || 'section'
}

/* ---- inline ---------------------------------------------------------------
   One pass, longest-first, so `**bold**` is never seen as two `*emphasis*`
   markers. Code spans are taken before anything else: a backtick run may hold
   asterisks that are code, not emphasis. */

const INLINE = /(`[^`]+`)|(\*\*[^*]+\*\*)|(\[[^\]]*\]\([^)]*\))|(\*[^*]+\*)|(_[^_]+_)/

function inline(text: string, key = 'i'): ReactNode[] {
  const out: ReactNode[] = []
  let rest = text
  let n = 0
  while (rest) {
    const m = INLINE.exec(rest)
    if (!m || m.index === undefined) { out.push(rest); break }
    if (m.index > 0) out.push(rest.slice(0, m.index))
    const tok = m[0]
    const k = `${key}-${n++}`
    if (tok.startsWith('`')) {
      out.push(<code key={k} className="text-[0.9em] px-1 py-0.5 rounded"
        style={{ background: 'var(--surface-3)' }}>{tok.slice(1, -1)}</code>)
    } else if (tok.startsWith('**')) {
      out.push(<strong key={k}>{inline(tok.slice(2, -2), k)}</strong>)
    } else if (tok.startsWith('[')) {
      const cut = tok.indexOf('](')
      const label = tok.slice(1, cut)
      const href = tok.slice(cut + 2, -1)
      out.push(
        <a key={k} href={href} className="underline break-words"
          style={{ color: 'var(--series-cost)' }}
          {...(/^https?:/.test(href) ? { rel: 'noreferrer' } : {})}>
          {inline(label, k)}
        </a>)
    } else {
      out.push(<em key={k}>{inline(tok.slice(1, -1), k)}</em>)
    }
    rest = rest.slice(m.index + tok.length)
  }
  return out
}

/* ---- blocks -------------------------------------------------------------- */

const H_CLASS: Record<number, string> = {
  1: 'text-3xl font-bold tracking-tight mt-12 mb-3 max-w-3xl',
  2: 'text-2xl font-bold tracking-tight mt-12 mb-3 max-w-3xl',
  3: 'text-[17px] font-bold mt-8 mb-1 max-w-2xl',
  4: 'text-[15px] font-bold mt-6 mb-1 max-w-2xl',
  5: 'text-[15px] font-bold mt-6 mb-1 max-w-2xl',
  6: 'text-[15px] font-bold mt-6 mb-1 max-w-2xl',
}

/** Cell alignment, read off the table's own separator row. */
function aligns(sep: string): ('left' | 'right' | 'center')[] {
  return cells(sep).map(c => (c.endsWith(':') ? (c.startsWith(':') ? 'center' : 'right') : 'left'))
}

function cells(row: string): string[] {
  return row.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim())
}

const isTableSep = (s: string) => /^\|?[\s:-]*-[\s:|-]*\|?$/.test(s) && s.includes('-')

export type Rendered = { nodes: ReactNode[]; headings: Heading[] }

/** Render a whole document. `base` is where a relative image or link resolves against --
 *  the analyses reference `charts/foo.svg`, which is relative to /docs/analyses/. */
export function renderMarkdown(src: string, base = '/docs/analyses/'): Rendered {
  const lines = src.replace(/\r\n/g, '\n').split('\n')
  const nodes: ReactNode[] = []
  const headings: Heading[] = []
  const seen = new Map<string, number>()
  let i = 0
  let k = 0
  const key = () => `b${k++}`

  const resolve = (href: string) =>
    (/^(https?:|\/|#|mailto:)/.test(href) ? href : base + href)

  while (i < lines.length) {
    const line = lines[i]

    // blank
    if (!line.trim()) { i++; continue }

    // fenced code
    if (/^\s*```/.test(line)) {
      const body: string[] = []
      i++
      while (i < lines.length && !/^\s*```/.test(lines[i])) body.push(lines[i++])
      i++ // the closing fence
      nodes.push(
        <pre key={key()} className="card p-4 mt-4 overflow-x-auto text-[12.5px] leading-relaxed"
          style={{ color: 'var(--text-secondary)' }}><code>{body.join('\n')}</code></pre>)
      continue
    }

    // thematic break
    if (/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(line)) {
      nodes.push(<hr key={key()} className="mt-10 mb-2 border-0 border-t"
        style={{ borderColor: 'var(--grid)' }} />)
      i++
      continue
    }

    // heading
    const h = /^(#{1,6})\s+(.*)$/.exec(line)
    if (h) {
      const depth = h[1].length
      const text = h[2].replace(/\s+#+\s*$/, '').trim()
      let id = slugify(text)
      const dup = seen.get(id) ?? 0
      seen.set(id, dup + 1)
      if (dup) id = `${id}-${dup}`
      headings.push({ depth, text, id })
      const Tag = (`h${Math.min(depth, 6)}`) as 'h1'
      nodes.push(
        <Tag key={key()} id={id}
          className={`${H_CLASS[depth]} scroll-mt-[calc(var(--header-h)+1rem)]`}>
          {inline(text, id)}
        </Tag>)
      i++
      continue
    }

    // image on its own line -- the closeout analyses head their sections with a chart
    const img = /^!\[([^\]]*)\]\(([^)]+)\)\s*$/.exec(line.trim())
    if (img) {
      nodes.push(
        <figure key={key()} className="mt-6 max-w-3xl figure">
          <img src={resolve(img[2])} alt={img[1]} className="w-full rounded-lg border"
            style={{ borderColor: 'var(--grid)' }} />
          {img[1] && (
            <figcaption className="text-[12.5px] leading-relaxed mt-2"
              style={{ color: 'var(--text-muted)' }}>{inline(img[1], `f${k}`)}</figcaption>
          )}
        </figure>)
      i++
      continue
    }

    // table
    if (line.includes('|') && i + 1 < lines.length && isTableSep(lines[i + 1])) {
      const head = cells(line)
      const al = aligns(lines[i + 1])
      i += 2
      const rows: string[][] = []
      while (i < lines.length && lines[i].includes('|') && lines[i].trim()) rows.push(cells(lines[i++]))
      nodes.push(
        <div key={key()} className="mt-5 overflow-x-auto">
          <table className="w-full text-[13.5px] border-collapse">
            <thead>
              <tr className="border-b" style={{ borderColor: 'var(--axis)' }}>
                {head.map((c, x) => (
                  <th key={x} className="py-1.5 pr-4 font-semibold align-bottom"
                    style={{ textAlign: al[x] ?? 'left', color: 'var(--text-secondary)' }}>
                    {inline(c, `th${x}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, y) => (
                <tr key={y} className="border-b" style={{ borderColor: 'var(--grid)' }}>
                  {r.map((c, x) => (
                    <td key={x} className={`py-1.5 pr-4 align-top ${al[x] === 'right' ? 'tnum' : ''}`}
                      style={{ textAlign: al[x] ?? 'left' }}>{inline(c, `td${y}-${x}`)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>)
      continue
    }

    // blockquote
    if (/^\s*>/.test(line)) {
      const body: string[] = []
      while (i < lines.length && /^\s*>/.test(lines[i])) body.push(lines[i++].replace(/^\s*>\s?/, ''))
      nodes.push(
        <blockquote key={key()} className="mt-5 max-w-2xl pl-4 border-l-4"
          style={{ borderColor: 'var(--axis)' }}>
          {renderMarkdown(body.join('\n'), base).nodes}
        </blockquote>)
      continue
    }

    // list
    const bullet = /^(\s*)([-*+]|\d+\.)\s+(.*)$/.exec(line)
    if (bullet) {
      const ordered = /\d/.test(bullet[2])
      const items: ReactNode[] = []
      let n = 0
      while (i < lines.length) {
        const m = /^(\s*)([-*+]|\d+\.)\s+(.*)$/.exec(lines[i])
        if (!m) {
          // a continuation line belongs to the item above it
          if (items.length && lines[i].trim() && /^\s+\S/.test(lines[i])) {
            items[items.length - 1] = (
              <li key={`c${n}`} className="text-[15px] leading-relaxed">
                {(items[items.length - 1] as { props: { children: ReactNode } }).props.children}{' '}
                {inline(lines[i].trim(), `k${n}`)}
              </li>)
            i++
            continue
          }
          break
        }
        items.push(
          <li key={n++} className="text-[15px] leading-relaxed">{inline(m[3], `l${n}`)}</li>)
        i++
      }
      const Tag = ordered ? 'ol' : 'ul'
      nodes.push(
        <Tag key={key()}
          className={`mt-4 max-w-2xl space-y-2 pl-5 ${ordered ? 'list-decimal' : 'list-disc'}`}
          style={{ color: 'var(--text-secondary)' }}>{items}</Tag>)
      continue
    }

    // paragraph
    const para: string[] = []
    while (i < lines.length && lines[i].trim()
      && !/^(#{1,6}\s|\s*>|\s*```|\s*(-{3,}|\*{3,}|_{3,})\s*$)/.test(lines[i])
      && !/^(\s*)([-*+]|\d+\.)\s+/.test(lines[i])
      && !(lines[i].includes('|') && i + 1 < lines.length && isTableSep(lines[i + 1]))) {
      para.push(lines[i++])
    }
    if (!para.length) { i++; continue }  // nothing matched; do not spin
    nodes.push(
      <p key={key()} className="text-[15px] leading-relaxed max-w-2xl mt-4"
        style={{ color: 'var(--text-secondary)' }}>{inline(para.join(' '), key())}</p>)
  }

  return { nodes, headings }
}
