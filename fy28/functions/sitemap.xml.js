/** /sitemap.xml — served unchanged, and logged. See `_crawlerlog.js` for why only here. */
import { logAndServe } from './_crawlerlog.js'
export const onRequestGet = logAndServe
