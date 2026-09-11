import { readFile } from 'node:fs/promises'
import { join } from 'node:path'
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { viteSingleFile } from 'vite-plugin-singlefile'

// `npm run build`        -> dist/            (normal multi-file build, for hosting)
// `SINGLE=1 npm run build` -> dist-single/   (one self-contained .html you can email)
const single = !!process.env.SINGLE

/** THE 48 POSTS, SERVED IN DEV AND IN NO BUILD. The review copy, and only locally.
 *
 *  TJ: *"we can even prebuild all the blogs and you can show me in-app what they look
 *  like, but they need to not show up anywhere or be fetchable. So we can review all the
 *  blogs ahead of time."* Reading the markdown is not the same as seeing the post, and the
 *  thing he is judging is whether it works as a post.
 *
 *  WHY IT CANNOT LIVE IN `public/`. Vite copies that directory into `dist/` WHOLESALE --
 *  every file, whether or not anything imports it -- so a full payload there is a deployed
 *  full payload however carefully the pages filter it. That is the exact failure TJ's rule
 *  names: *"the content shouldnt exist on the site anywhere"*.
 *
 *  So `scripts/build_blog.py --all` writes it to `build/blog-all.json`, which is
 *  gitignored, and this serves it at `/data/blog-all.json` from the DEV SERVER ONLY. There
 *  is no `transform`, no `generateBundle` and no `closeBundle` hook here: the plugin
 *  contributes literally nothing to a build, so `npm run build` cannot emit it even by
 *  accident. The app's own fetch of it is behind `import.meta.env.DEV`, which is replaced
 *  with `false` and eliminated, so the production bundle does not even name the file. */
function devOnlyBlogPreview(): Plugin {
  return {
    name: 'lunenburg-dev-blog-preview',
    apply: 'serve',
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        const url = req.url ?? ''
        if (url.startsWith('/data/blog-all.json')) {
          try {
            const body = await readFile(join(__dirname, '..', 'build', 'blog-all.json'))
            res.setHeader('content-type', 'application/json')
            res.end(body)
          } catch {
            res.statusCode = 404
            res.end('{"posts":[],"counts":{"published":0,"prepared":0},' +
              '"note":"run: python3 scripts/build_blog.py --all"}')
          }
          return
        }
        // The share cards of posts that are not up. The published ones are real files in
        // `public/share/` and vite serves those itself; this fills in the rest from
        // `build/share/`, so the review page can show the actual 1200x630 card rather than
        // a mock of it. Same directory, same gitignore, same absence from every build.
        const card = /^\/share\/([a-z0-9-]+\.html)(?:\?|$)/.exec(url)
        if (card) {
          try {
            const body = await readFile(join(__dirname, '..', 'build', 'share', card[1]))
            res.setHeader('content-type', 'text/html; charset=utf-8')
            res.end(body)
            return
          } catch { /* falls through: vite serves the published one, or 404s */ }
        }
        return next()
      })
    },
  }
}

export default defineConfig({
  // ABSOLUTE for the hosted build, RELATIVE only for the single-file one.
  //
  // `./` was set for the emailable build, where a relative asset path is the whole point:
  // there is no server and the file has to find its own siblings. It was applied to both,
  // and for a year that was invisible because every route on the site had exactly ONE path
  // segment -- `./assets/index.js` from `/reports` resolves to `/assets/index.js`, which is
  // right by accident.
  //
  // It stops being right the moment a route has two. `/analysis/free-cash` resolves the
  // same tag to `/analysis/assets/index.js`, the host answers with the SPA fallback HTML,
  // the browser is handed a page where it expected a module, and React never boots. The
  // page is not blank in a way anybody would notice from a screenshot -- the prerendered
  // markup is still there -- and no error reaches the console. Seventeen routes rendered
  // zero characters of text before this was found.
  //
  // The hosted site is served from the domain root, so `/` is correct there; the
  // single-file build keeps `./` because it is opened from a filesystem.
  base: single ? './' : '/',
  plugins: [react(), tailwindcss(), devOnlyBlogPreview(),
            ...(single ? [viteSingleFile()] : [])],
  build: single
    ? { outDir: 'dist-single', assetsInlineLimit: 100_000_000, cssCodeSplit: false,
        rollupOptions: { output: { inlineDynamicImports: true } } }
    : {},
})
