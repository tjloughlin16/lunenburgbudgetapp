/** WHAT KIND OF MATTER THIS IS — a glyph, so twenty rows are scannable at a glance.
 *
 *  TJ: "is there any way to add iconography or color or something so the threads are easily
 *  discernible". The answer is SHAPE for the kind and colour for the state, and the reason
 *  is measured rather than stylistic.
 *
 *  THE SITE'S FIVE-COLOUR CATEGORICAL SET CANNOT CARRY THIS. `--subj-1..5` was the obvious
 *  candidate — five slots, five groups — and run through the palette validator it FAILS in
 *  dark mode: `--subj-4` (#d9a3e8) and `--subj-5` (#f7b7cd) fall outside the lightness
 *  band, #f7b7cd drops under the chroma floor and reads gray, and the two sit at ΔE 8.9 on
 *  the NORMAL-vision axis — under 15, which means full-colour readers cannot reliably tell
 *  them apart, and secondary encoding does not excuse that one. In light mode it also warns
 *  on protan separation (#0e8a6b↔#eb6834, ΔE 6.9) and on #e07fa8's contrast.
 *
 *  So colour stays on the one distinction already validated in both themes — open against
 *  settled, `--series-cost` / `--series-revenue` — and the KIND is carried by a shape,
 *  which is robust to every kind of colour vision and to a black-and-white print.
 *
 *  A thread may be more than one kind (`money;rule`); the first is the one drawn, and the
 *  title attribute names them all. */

const P: Record<string, { d: string; label: string }> = {
  // a coin
  money: { label: 'money — a fee, a rate, a cost residents pay',
    d: 'M8 2.6a5.4 5.4 0 100 10.8A5.4 5.4 0 008 2.6zM8 5v6M6.4 6.3h3.2M6.4 9.7h3.2' },
  // a page of rules
  rule: { label: 'a rule — a bylaw, a regulation, a policy',
    d: 'M3.6 2.2h6.2l2.6 2.6v9H3.6zM9.6 2.2v2.8h2.8M5.6 7.4h5M5.6 9.6h5M5.6 11.8h3' },
  // two people
  service: { label: 'a service — hours, staffing, a programme',
    d: 'M6 6.4a1.9 1.9 0 100-3.8 1.9 1.9 0 000 3.8zM2.6 13.4c0-2 1.5-3.4 3.4-3.4s3.4 1.4 3.4 3.4M11 6.6a1.6 1.6 0 100-3.2M11.4 10.2c1.3.3 2.2 1.5 2.2 3.2' },
  // a signed page
  contract: { label: 'a contract — a union agreement, a vendor, a lease',
    d: 'M3.8 2.2h8.4v11.6H3.8zM5.8 5.2h4.4M5.8 7.4h4.4M5.8 10.6c.9-1.1 1.6-1.1 2.2 0s1.3 1.1 2.2 0' },
  // a set square
  project: { label: 'a project — a study, a design, a build',
    d: 'M2.6 13.4L13.4 13.4L13.4 2.6zM5.6 13.4v-2M8.2 13.4v-3.4M10.8 13.4v-5' },
  // a building
  asset: { label: 'town land or a building',
    d: 'M2.6 13.6h10.8M3.8 13.6V6.2L8 3.1l4.2 3.1v7.4M6.3 13.6v-3h3.4v3M6.3 8h.9M8.8 8h.9' },
  // a seat that decides
  office: { label: 'an office — a post that decides things, vacant or contested',
    d: 'M4.6 2.8h6.8v5.4H4.6zM3.4 8.2h9.2M5.2 8.2v4.8M10.8 8.2v4.8M4.2 13h1.8M10 13h1.8' },
}

export function ThreadKind({ kind, tone, size = 16 }: { kind: string; tone: string; size?: number }) {
  const kinds = (kind || '').split(';').map(s => s.trim()).filter(Boolean)
  const first = kinds.find(k => P[k]) ?? 'rule'
  const title = kinds.map(k => P[k]?.label ?? k).join(' · ')
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" role="img" aria-label={title}
      className="inline-block shrink-0 align-[-2px]"
      fill="none" stroke={tone} strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
      <title>{title}</title>
      <path d={P[first].d} />
    </svg>
  )
}

export const KIND_LABEL = Object.fromEntries(Object.entries(P).map(([k, v]) => [k, v.label]))
export const KINDS = Object.keys(P)
