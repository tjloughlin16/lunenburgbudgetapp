/** A POPUP'S TOP RIGHT: the line's or the fund's own page, and Close, on one row (TJ, 28 October
 *  2026: "i want people to be able to share urls to direct links for each fund, school line"; then
 *  "the side by side buttons is akward ... i dont think we even need that button" -- the copy
 *  button went, because the page it opens has the address a reader shares). A page itself carries
 *  no link to itself. Strings from /data/fy-breakdown/index.json. */
import { useItemIndex, withYear } from './fy-items'

export function PopupActions({ href, fy, close, onClose }: { href: string | undefined; fy: string; close: string; onClose: () => void }) {
  const ix = useItemIndex()
  return (
    <div className="flex items-center gap-4 shrink-0 text-[13px]">
      {href && ix ? (
        <a href={withYear(href, fy)} className="underline whitespace-nowrap" style={{ color: 'var(--link, var(--thread-2))' }}>{ix.text.link} ↗</a>)
        : null}
      <button type="button" onClick={onClose} className="px-2.5 py-1 rounded border whitespace-nowrap hover:bg-[var(--surface-2)]"
        style={{ borderColor: 'var(--grid)', color: 'var(--text-primary)' }}>{close} ✕</button>
    </div>)
}
