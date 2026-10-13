// THE BREADCRUMB AND THE MENU MUST AGREE ABOUT WHERE A PAGE SITS.
//
// They are two maps of one site: routes.PARENT builds every breadcrumb, SiteMenu.GROUPS
// builds the Menu. Nothing kept them in step, and on 13 October 2026 the phone crumb for
// /this-week read "Reports and analyses" -- because a phone shows only the parent, a wrong
// PARENT is the whole breadcrumb there. TJ: "looks like breadcrumbs are very frequently
// wrong". This is the check that would have caught it.
//
// Each Menu group declares `under`: null (its pages sit directly under Home) or a tab
// (each page is that tab, or has it somewhere up its PARENT chain). Every Menu item that
// names a page -- by `to`, or by an `href` that is exactly a page's address -- is held to
// its group. Runs in `npm run build`, before vite, so a disagreement fails the build.
import { build } from 'esbuild'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
import { mkdirSync, writeFileSync } from 'node:fs'
import { pathToFileURL } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const out = await build({
  stdin: {
    contents: `export { PARENT, SLUG, crumbLabel } from './src/routes'\nexport { GROUPS } from './src/components/SiteMenu'`,
    resolveDir: root, loader: 'ts',
  },
  bundle: true, write: false, format: 'esm', platform: 'node', packages: 'external',
  jsx: 'automatic', logLevel: 'error',
})
// lib/title reads a <meta> at import time; a stub document is all it needs here.
globalThis.document ??= { querySelector: () => null }
// Written under node_modules so the bundle's bare imports (react) resolve as the app's do.
const tmp = join(root, 'node_modules', '.cache', 'check-crumbs.mjs')
mkdirSync(dirname(tmp), { recursive: true })
writeFileSync(tmp, out.outputFiles[0].text)
const { PARENT, SLUG, GROUPS, crumbLabel } = await import(pathToFileURL(tmp).href)

const bySlug = Object.fromEntries(Object.entries(SLUG).map(([t, s]) => ['/' + s, t]))
const chain = t => { const seen = []; for (let p = PARENT[t]; p && !seen.includes(p); p = PARENT[p]) seen.push(p); return seen }
const trail = t => ['Home', ...chain(t).reverse().map(crumbLabel), crumbLabel(t)].join(' > ')

const bad = []
let checked = 0
for (const g of GROUPS) {
  for (const it of g.items) {
    const tab = it.to ?? bySlug[it.href]
    if (!tab) continue          // a sub-page or a feed: its crumb is its own page's, not the Menu's
    checked++
    const ok = g.under === null ? PARENT[tab] === undefined
      : tab === g.under || chain(tab).includes(g.under)
    if (!ok) bad.push(`  "${it.label}" (${tab}) is in the Menu's "${g.title}", which sits ` +
      (g.under === null ? 'under Home' : `under ${crumbLabel(g.under)}`) +
      `,\n    but its breadcrumb reads ${trail(tab)}`)
  }
}
if (bad.length) {
  console.error(`check-crumbs: ${bad.length} of ${checked} Menu pages have a breadcrumb that disagrees with the Menu:\n` +
    bad.join('\n') + `\n\nFix PARENT in src/routes.ts, or the group's \`under\` in src/components/SiteMenu.tsx.`)
  process.exit(1)
}
console.log(`check-crumbs: ${checked} Menu pages, every breadcrumb agrees with the Menu.`)
