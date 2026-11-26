# Avoiding full-site renders

TJ, 26 November 2026, after the sixth full render in thirteen days: *"we need to stop doing full
site rebuilds"*, and *"any commit that attempts to get merged that causes a full re-render is now
considered blocked, and we need to figure out how to prevent that from now on."*

The gate is `scripts/check_full_render.py` (test: `scripts/test_check_full_render.py`). Before
committing anything under `fy28/`, run:

    python3.11 scripts/check_full_render.py --staged

## What causes one

The prerender reuses a cached page only while one key, shared by every route, is unchanged
(`fy28/scripts/prerender.mjs`, `global`): the built `index.html` from `<html` on, plus the probe,
plus the prerender script's own text. The built `index.html` names the hashed bundle. **The site
is one bundle with no code splitting**, so anything that changes a byte of the bundle re-renders
all ~3,900 pages:

| changes the key | does not |
|---|---|
| anything under `fy28/src/`, **including the JSON in `fy28/src/data/`** | `fy28/public/` (served files, fetched at run time) |
| `fy28/index.html` from `<html` on | the preamble before `<html` (spliced, not keyed, since `8fccee7b3`) |
| `fy28/scripts/prerender.mjs` | `sources/`, `scripts/` other than the prerender, `notes/` |
| `vite.config.ts`, `package.json`, `package-lock.json`, `tsconfig*.json` | |

## The measurement

From 16 to 26 November 2026, 149 commits reached main. The gate would have refused **66**:

- **38 only for data**: the refresh rewriting `fy28/src/data/sources.json` (30 commits) and
  `agent-manifest.json` (13). No code changed, and every page was invalidated anyway.
- **28 for code**: new pages' components, menu, blocks, routes.
- 22 of the 49 daily-refresh commits were among them.

(`check_full_render.py`'s `triggers()` run over `git rev-list --since=2026-11-16 main`.)

## How a commit avoids one, from now on

1. **Data the refresh rewrites never lives in `fy28/src/data/`.** Put it in `fy28/public/data/`
   and `fetch` it at run time, the way reports already fetch `/data/<id>.json`. `sources.json`
   already has a twin there. Moving `sources.json` and `agent-manifest.json` out of the bundle
   is the biggest single fix (38 of 66). It is itself a code change, so it costs **one** full
   render, once.
2. **A new page is a payload, not a component, wherever the existing blocks can carry it.** A
   generator writing `/data/<id>.json` for `report.tsx` and the topic blocks to render needs no
   code change. A new custom block under `components/blocks/custom/` is code, and code is a full
   render.
3. **Frontend code lands in batches**, so the full render it causes is paid once per batch
   instead of once per commit. Code waits on a branch; data and generators keep landing on main.
4. **Do not touch `prerender.mjs`, the build config or the shell after `<html` in passing.**
   Each is a full render on its own.
5. **Comment-only and type-only edits under `fy28/src/` are refused too.** The gate predicts from
   paths and errs toward refusing. esbuild would strip them, but the gate cannot know that
   without building.

## What ends it structurally

- **Incremental render** (task *incremental render*, T-HY3QY): when only the bundle changed,
  keep each cached page and swap its asset link; re-render new pages and pages whose data
  changed; a scheduled full render weekly. TJ schedules this himself (26 November 2026).
- **Code splitting** (lazy routes, each page keyed on the chunks it loads) is the larger
  alternative. Shared chunks would still invalidate everything when they change.

## Arming the gate

The hooks are installed and do nothing until `ops/FULL-RENDER-GATE-ARMED` exists. Arming is
TJ's decision. Until rule 1 above is done, an armed gate also refuses the daily refresh's own
commit whenever `sources.json` changes. The owner's override for one commit or push is
`FULL_RENDER_APPROVED="who and why"`, logged to `build/full-render-gate/overrides.log`.
