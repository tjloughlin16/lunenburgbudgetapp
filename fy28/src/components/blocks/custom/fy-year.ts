/** ONE FISCAL YEAR FOR THE WHOLE PAGE (fy-breakdown). TJ, 27 October 2026: "each chart
 *  shouldnt have its own FY selector. should maybe be a global setting on the page?"
 *
 *  The picker block and every chart on the page read the same year through this hook. It lives
 *  in the address (`?fy=FY2025`), so a year can be linked to and survives a reload, and a change
 *  is announced with one window event every block listens for. */
import { useCallback, useEffect, useState } from 'react'

const EVENT = 'fy-breakdown-year'
const PARAM = 'fy'

function fromAddress(years: string[]): string {
  const q = typeof window === 'undefined' ? null : new URLSearchParams(window.location.search).get(PARAM)
  return q && years.includes(q) ? q : years[years.length - 1]
}

export function useFyYear(years: string[]): [string, (fy: string) => void] {
  const [fy, setFy] = useState(() => fromAddress(years))
  useEffect(() => {
    const on = (e: Event) => { const v = (e as CustomEvent<string>).detail; if (years.includes(v)) setFy(v) }
    window.addEventListener(EVENT, on)
    return () => window.removeEventListener(EVENT, on)
  }, [years])
  const set = useCallback((v: string) => {
    const u = new URL(window.location.href)
    u.searchParams.set(PARAM, v)
    window.history.replaceState(window.history.state, '', u)
    window.dispatchEvent(new CustomEvent(EVENT, { detail: v }))
  }, [])
  return [fy, set]
}
