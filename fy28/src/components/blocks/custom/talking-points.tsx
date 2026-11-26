/** TALKING POINTS (the FY2026 closeout hub, 25 November 2026).
 *
 *  TJ, on the hub's earlier findings -- a statement, two or three metric tiles and a link each:
 *  "it's just a lot ... I'm still not seeing the conclusions." A hub states what a resident
 *  could repeat at a meeting, one sentence each, its figure inside the sentence, and the
 *  sentence itself is the link to the page that proves it. Grouped under short bold heads.
 *  Every string is formatted and checked by the generator (rule 2); this prints the text. */
import type { CustomProps } from './index'

type Point = { text: string; href: string; page: string }
type Group = { title: string; points: Point[] }
type Data = { groups: Group[] }

export default function TalkingPoints({ data, alt }: CustomProps) {
  const d = data as Data
  return (
    <div aria-label={alt} className="max-w-3xl">
      {d.groups.map(g => (
        <section key={g.title} className="mt-5 first:mt-1">
          <h3 className="text-[15px] font-bold" style={{ color: 'var(--text-primary)' }}>{g.title}</h3>
          <ul className="mt-1.5 space-y-2">
            {g.points.map((p, i) => (
              <li key={i} className="text-[15px] leading-relaxed pl-3 border-l-[3px]"
                style={{ borderColor: 'var(--series-cost)' }}>
                <a href={p.href} className="no-underline hover:underline" style={{ color: 'var(--text-primary)' }}
                  title={`Shown on ${p.page}`}>{p.text}
                  <span className="ml-1.5 text-[13px] whitespace-nowrap" style={{ color: 'var(--text-muted)' }}>
                    {p.page} &rarr;</span></a>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  )
}
