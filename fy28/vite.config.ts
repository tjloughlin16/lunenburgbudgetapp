import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { viteSingleFile } from 'vite-plugin-singlefile'

// `npm run build`        -> dist/            (normal multi-file build, for hosting)
// `SINGLE=1 npm run build` -> dist-single/   (one self-contained .html you can email)
const single = !!process.env.SINGLE

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
  plugins: [react(), tailwindcss(), ...(single ? [viteSingleFile()] : [])],
  build: single
    ? { outDir: 'dist-single', assetsInlineLimit: 100_000_000, cssCodeSplit: false,
        rollupOptions: { output: { inlineDynamicImports: true } } }
    : {},
})
