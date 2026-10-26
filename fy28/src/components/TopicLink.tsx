/** ONE SHAPE FOR A TOPIC, wherever a topic is listed -- the hub's cards and the shelves on
 *  /reports. TJ, 14 October 2026: on /athletics "the topic pages don't look like individual
 *  reports. They seem like metrics callouts. I think we need a convention of what topic
 *  pages look like so people get used to seeing a TOPIC page."
 *
 *  They read as callouts because the hub drew them as grey boxes with black titles -- the
 *  same weight as the facts grid above them -- while /reports drew the same topic as an
 *  underlined link. Two shapes for one thing, and neither said "a page". Chosen from four
 *  drawn concepts: a thin rule in the link colour, the title in the link colour with an
 *  arrow, the finding under it. No box, no "Topic" label, no reading time and no "Open"
 *  footer -- TJ judged those redundant, and a topic is meant to be short anyway. The hub
 *  card on /reports carries the same rule at 4px, so a hub and its topics read as one
 *  family. */
import { abs } from '../lib/abs'

export type TopicLinkData = { title: string; path: string; finding: string | null; ready: boolean }

/** ONE ENTRY IN A SHELF GROUP: a topic, or another HUB listed in the group (scripts/topics.py:
 *  a group may name a category). TJ, 26 October 2026: "the serf hub should also go into the
 *  main special education grouping". A hub is drawn in the topic's shape, its answer where a
 *  finding goes, so a sub-report reads as one more door on the shelf. */
type ShelfIndex = {
  categories: { id: string; title: string; path: string; answer: string | null }[]
  topics: Record<string, TopicLinkData & { id: string; shelves: string[] }>
}
export function shelfEntry(ix: ShelfIndex, id: string): (TopicLinkData & { id: string; shelves: string[] }) | null {
  if (ix.topics[id]) return ix.topics[id]
  const h = ix.categories.find(c => c.id === id)
  return h ? { id: h.id, title: h.title, path: h.path, finding: h.answer, ready: !!h.answer, shelves: [] } : null
}

export function TopicLink({ t, also }: { t: TopicLinkData; also?: string[] }) {
  return (
    <a href={abs(t.path)} className="group block pl-3 py-0.5 border-l-2 hover:border-l-4 hover:pl-2.5 transition-[border-width,padding]"
      style={{ borderColor: 'var(--series-cost)', opacity: t.ready ? 1 : 0.55 }}>
      <span className="block text-[15.5px] font-bold leading-snug group-hover:underline" style={{ color: 'var(--series-cost)' }}>
        {t.title} &rarr;</span>
      <span className="block text-[13.5px] leading-snug mt-0.5" style={{ color: 'var(--text-secondary)' }}>
        {t.finding ?? 'Being written.'}</span>
      {also?.length ? <span className="block text-[11.5px] mt-1" style={{ color: 'var(--text-muted)' }}>
        Also under {also.join(', ')}</span> : null}
    </a>
  )
}
