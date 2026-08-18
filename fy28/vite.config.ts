import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { viteSingleFile } from 'vite-plugin-singlefile'

// `npm run build`        -> dist/            (normal multi-file build, for hosting)
// `SINGLE=1 npm run build` -> dist-single/   (one self-contained .html you can email)
const single = !!process.env.SINGLE

export default defineConfig({
  base: './',
  plugins: [react(), tailwindcss(), ...(single ? [viteSingleFile()] : [])],
  build: single
    ? { outDir: 'dist-single', assetsInlineLimit: 100_000_000, cssCodeSplit: false,
        rollupOptions: { output: { inlineDynamicImports: true } } }
    : {},
})
