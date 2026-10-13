/* GROUPED LISTS, shared by the home page's live column and /this-week. TJ, 13 October 2026, on a phone: "i think we need to
 * restyle everything from 'This year's budget' and down... there HAS to be conventions of
 * how to show information on a mobile site like this."
 *
 * There are, and this is the commonest: the INSET GROUPED LIST (Apple's "inset grouped"
 * table, Material's list with dividers) -- Settings, Mail, every news app. Four rules:
 *   - ONE CONTAINER PER SECTION, rows split by hairlines. Never a box per item, and never
 *     a box in a box. The column had four box styles (bordered, dashed, edged, tinted).
 *   - A HEADER ROW: the label left, "All ›" right.
 *   - IDENTICAL ROWS: an eyebrow, one bold line, one muted line, a chevron; 44px or more,
 *     the whole row one tap target.
 *   - THREE TO FIVE ROWS, the rest behind "All". Footnotes leave the summary.
 * It keeps COMMON REGION (TJ, 25 September: the meetings needed "some type of wrapper"):
 * the section is the region now, rather than each row. */
export function ListSection({ title, all, allHref, children, label, footer }: {
  title: string; all?: string; allHref?: string; children: React.ReactNode; label: string; footer?: React.ReactNode
}) {
  return (
    <section aria-label={label}>
      <div className="flex items-baseline justify-between gap-3 mb-1.5 px-1">
        <h2 className="text-[13px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>{title}</h2>
        {all && allHref && (
          <a href={allHref} className="text-[13px] font-semibold" style={{ color: 'var(--series-cost)' }}>
            {all} <span aria-hidden>&rsaquo;</span>
          </a>
        )}
      </div>
      <ul className="card overflow-hidden" style={{ padding: 0 }}>{children}</ul>
      {footer}
    </section>
  )
}

export function Row({ href, eyebrow, title, sub, accent, muted, tag }: {
  href?: string; eyebrow?: string; title: string; sub?: string | null; accent?: boolean; muted?: boolean; tag?: string
}) {
  const body = (
    <span className="flex items-center gap-3 px-4 py-2.5 min-h-[48px]">
      <span className="min-w-0 flex-1">
        {eyebrow && (
          <span className="block text-[11px] font-bold uppercase tracking-wider"
            style={{ color: accent ? 'var(--series-cost)' : 'var(--text-muted)' }}>{eyebrow}</span>
        )}
        <span className="block text-[15px] font-semibold leading-snug"
          style={{ color: muted ? 'var(--text-muted)' : 'var(--text-primary)', fontWeight: muted ? 400 : 600 }}>
          {title}
          {tag && <span className="ml-1.5 align-middle text-[10px] font-bold uppercase tracking-widest"
            style={{ color: 'var(--series-cost)' }}>{tag}</span>}
        </span>
        {sub && (
          <span className="block text-[13px] leading-snug mt-0.5" style={{ color: 'var(--text-secondary)',
            display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>{sub}</span>
        )}
      </span>
      {href && <span aria-hidden className="text-[20px] leading-none shrink-0" style={{ color: 'var(--text-muted)' }}>&rsaquo;</span>}
    </span>
  )
  return (
    <li className="border-t first:border-t-0" style={{ borderColor: 'var(--grid)' }}>
      {href ? <a href={href} className="block transition-colors hover:bg-[var(--surface-3)]"
        {...(href.startsWith('http') ? { target: '_blank', rel: 'noreferrer' } : {})}>{body}</a> : body}
    </li>
  )
}
