import { createContext, useContext, type AnchorHTMLAttributes, type MouseEvent } from 'react'
import { pathFor, type Tab } from '../routes'

/** A LINK IS AN `<a href>`. Nothing else is.
 *
 *  Every navigation on this site used to be a `<button onClick={() => go(tab)}>`: the
 *  four doors, the header tabs, the breadcrumb, the thirty-two report cards on /the-money.
 *  On 15 September 2026 that page was measured at 11 real links and 69 buttons. A
 *  button routes on click and does nothing else -- and a reader relies on everything
 *  else without knowing they do: right-click and middle-click to open in a new tab, the
 *  URL in the status bar on hover, a visited colour on a grid of thirty cards so they
 *  can tell what they have already read, and a link they can copy to text a neighbour.
 *  A crawler, and an assistant fetching the page, sees no link at all.
 *
 *  The term is LINK AFFORDANCE, and it is not decoration: the browser behaviours that
 *  come with an anchor are the ones a resident uses to share this site.
 *
 *  So: `<Go to="walk">` renders a real anchor to the tab's real address. A plain left
 *  click is intercepted and routed in-app, exactly as the button did, so the page does
 *  not reload; a modified click, a middle click, or a click with JavaScript off is left
 *  to the browser and lands on the same address, prerendered. Same look -- Tailwind's
 *  preflight leaves an anchor unstyled, so a className written for the button carries
 *  over unchanged.
 *
 *  The router itself (`go` in App.tsx) is provided through context rather than threaded
 *  down as an `onJump` prop, because a link should be writable anywhere without every
 *  component between it and App having to know about it. */

export type Go = (t: Tab, anchor?: string) => void

const NavCtx = createContext<Go | null>(null)
export const NavProvider = NavCtx.Provider

/** The router, or -- outside the provider, which is only tests and the prerenderer --
 *  a full navigation to the same address. Either way the link goes where it says. */
export function useGo(): Go {
  const g = useContext(NavCtx)
  return g ?? ((t, a) => { window.location.assign(pathFor(t) + (a ? `#${a}` : '')) })
}

/** Is this the kind of click the app should handle, or one the browser owns? A modifier
 *  key or a non-primary button is the reader asking for a new tab or window; taking it
 *  over would break the one thing the anchor was added to provide. */
export const plainClick = (e: MouseEvent) =>
  e.button === 0 && !e.metaKey && !e.ctrlKey && !e.shiftKey && !e.altKey && !e.defaultPrevented

export const hrefFor = (to: Tab, anchor?: string) => pathFor(to) + (anchor ? `#${anchor}` : '')

/** An in-app link to a tab. Everything an `<a>` accepts, plus `to` and an optional
 *  `anchor`. An `onClick` passed in runs first, so a link can also set state on the way. */
export function Go({ to, anchor, onClick, children, ...rest }:
  { to: Tab; anchor?: string } & AnchorHTMLAttributes<HTMLAnchorElement>) {
  const go = useGo()
  return (
    <a href={hrefFor(to, anchor)}
      onClick={e => {
        onClick?.(e)
        if (!plainClick(e)) return
        e.preventDefault()
        go(to, anchor)
      }}
      {...rest}>
      {children}
    </a>
  )
}
