/**
 * Log who fetched a file, so "has anything crawled us" can be answered from our own
 * server rather than from a search engine's word or an agent's recollection.
 *
 * WHY THIS EXISTS
 *
 * Three agents could not read anything under the homepage and two of them said the domain
 * is not in any search index. That is a report, not a measurement. The APIs that would
 * measure it — Google's URL Inspection, Bing's GetUrlInfo — need accounts and keys, and
 * `CLAUDE.md` forbids the shortcut of scraping a `site:` query and calling the count a
 * measurement, because a result page is a rendering.
 *
 * This is the one honest signal available with no account anywhere: **our own server
 * watching who arrives.** A request from Googlebot is not somebody's claim about Google.
 *
 * WHY ONLY THESE TWO PATHS
 *
 * Pages serves prerendered HTML as a static asset, with no Function and therefore no log.
 * A root `_middleware.js` would see everything and would also run on every request to the
 * site, which is real latency on every page load for a diagnostic.
 *
 * `/robots.txt` and `/sitemap.xml` are the two files a crawler fetches on purpose and a
 * person almost never does. So they carry nearly all of the signal and almost none of the
 * traffic. That is the whole trade.
 *
 * WHAT IT CANNOT TELL YOU
 *
 * **Crawled is not indexed.** Googlebot fetching the sitemap proves discovery and nothing
 * beyond it: a URL can be crawled and deliberately left out of the index, which is what
 * `Crawled - currently not indexed` means in Search Console. So a hit here is proof the
 * door is open; silence is proof nothing came. Neither is the indexing answer, and this
 * comment exists so a later reader does not quietly promote one into the other.
 *
 * WHAT IS LOGGED
 *
 * The user agent, the path, the ASN and the country. Not the IP address: the question is
 * "which crawler", and an IP would be personal data about the humans who also land here,
 * collected for a diagnostic that does not need it.
 */

/** Crawlers worth naming in the log line. Anything else is logged as `other`. */
const KNOWN = [
  [/googlebot/i, 'Googlebot'],
  [/bingbot|adidxbot/i, 'Bingbot'],
  [/yandex/i, 'YandexBot'],
  [/duckduckbot/i, 'DuckDuckBot'],
  [/applebot/i, 'Applebot'],
  [/gptbot|oai-searchbot|chatgpt-user/i, 'OpenAI'],
  [/claudebot|claude-web|anthropic/i, 'Anthropic'],
  [/perplexitybot|perplexity-user/i, 'Perplexity'],
  [/ccbot/i, 'CommonCrawl'],
  [/seznambot/i, 'SeznamBot'],
  [/naver|yeti/i, 'NaverBot'],
]

function label(ua) {
  for (const [re, name] of KNOWN) if (re.test(ua)) return name
  return 'other'
}

/** Serve the static file unchanged, and log one line about who asked for it. */
export async function logAndServe(context) {
  const { request, env } = context
  const ua = request.headers.get('user-agent') || ''
  const url = new URL(request.url)
  const cf = request.cf || {}
  // One line, greppable, fixed field order — `wrangler pages deployment tail` is the
  // reader, and a shape that changes is a shape nobody can filter on.
  console.log(`CRAWL ${label(ua)} ${url.pathname} asn=${cf.asn ?? '?'} ` +
    `cc=${cf.country ?? '?'} ua=${ua.slice(0, 160)}`)
  // The asset itself, byte for byte. This must never become a place that also rewrites
  // the file: robots.txt and sitemap.xml are load-bearing and a diagnostic must not edit
  // what it observes.
  return env.ASSETS.fetch(request)
}
