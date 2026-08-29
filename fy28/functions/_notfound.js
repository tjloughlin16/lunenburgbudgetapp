/**
 * Tell the truth about a missing archive document.
 *
 * The site is static, and Cloudflare Pages' default for an unmatched path is to serve
 * `index.html` with a 200. For app routes that is exactly right — `src/routes.ts` resolves
 * an unrecognized path to the front page on purpose, so that a link somebody shared two
 * years ago still lands them on the site rather than on an error they will never report.
 *
 * For the archive it is exactly wrong. A request for a source document that is not there
 * returned `200 OK` and the app shell, which means nothing reading status codes could tell
 * a document that exists from one that does not. A link checker sees two 200s. A crawler
 * indexes the home page under a document's URL. An assistant asked to verify a citation is
 * handed an HTML page and no indication that it is not the PDF it asked for. That is a
 * **soft 404**, and for an archive whose whole promise is "here is our copy, check it
 * yourself", it is the worst available failure.
 *
 * This cannot be done in `_redirects`. Cloudflare rejects a 404 there outright — "Valid
 * status codes are 200, 301, 302, 303, 307, or 308" — and rejects `/* /index.html 200` as
 * an infinite loop. Running `wrangler pages dev` reports `Parsed 0 valid redirect rules`,
 * which is worth knowing: every rule that file has ever contained was ignored, and the
 * behaviour attributed to it came from the platform default.
 *
 * Nor can it be done by adding a root `404.html`. Pages (and Netlify) treat that filename
 * as a convention and serve it for ANY unmatched path, which takes the app routes with it
 * and breaks the stale-link behaviour above. That is why the error page here is called
 * `not-found.html`.
 *
 * So: a Function on `/docs/*` and `/data/*` only. Everything else stays a pure static
 * asset request with no Worker in front of it.
 *
 * How it decides: nothing under those two prefixes is ever an HTML page — they hold PDFs,
 * spreadsheets, CSV, JSON, Markdown and plain text. So if the asset server answered 200
 * with `text/html`, it did not find the file and fell back to the shell.
 */

/** Serve the real error page with a real status, falling back to plain text. */
export async function notFound(context) {
  const { request, env } = context
  try {
    const page = await env.ASSETS.fetch(new URL('/not-found.html', request.url))
    return new Response(page.body, {
      status: 404,
      headers: {
        'content-type': 'text/html; charset=utf-8',
        'cache-control': 'no-store',
        // Named so that anything reading headers can see which rule fired.
        'x-archive-miss': 'document not in the archive',
      },
    })
  } catch {
    return new Response(
      'Not found. This document is not in the archive. See /sources or /llms.txt.\n',
      { status: 404, headers: { 'content-type': 'text/plain; charset=utf-8' } },
    )
  }
}

/** Pass a real file through; turn the app-shell fallback into a 404. */
export async function assetOr404(context) {
  const res = await context.next()
  if (res.status !== 200) return res
  const type = res.headers.get('content-type') || ''
  if (type.includes('text/html')) return notFound(context)
  return res
}
