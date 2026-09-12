#!/bin/bash
# DOES ANY PAGE SCROLL SIDEWAYS ON A PHONE? Measured, not eyeballed.
#
# Renders every route at a true 400px viewport -- inside a same-origin iframe, because
# desktop Chrome clamps its own window to ~500px and a --window-size=400 screenshot is a
# crop, not a layout -- and reads documentElement.scrollWidth. Anything over 400 is a page
# that scrolls horizontally, and the report names the outermost element that escaped.
# Wide things (tables, charts, the chapter strip) are allowed to scroll THEMSELVES: an
# element inside an overflow-x container is not counted.
#
#   bash scripts/check_phone_width.sh            # every route in routes.ts
#   bash scripts/check_phone_width.sh /solutions # one or more
#
# Builds into /tmp/preview-dist (NEVER fy28/dist -- that clobbers the prerender).
set -u
cd "$(dirname "$0")/../fy28" || exit 1
export PATH="/Users/tj/.nvm/versions/node/v22.22.2/bin:$PATH"
CH="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
OUT=/tmp/preview-dist
PORT=8798
if [ $# -gt 0 ]; then ROUTES="$*"; else
  ROUTES=$(python3 - <<'PY'
import re
src=open('src/routes.ts').read()
m=re.search(r'export const SLUG[^{]*\{(.*?)\n\}', src, re.S)
slugs=re.findall(r":\s*'([^']*)'", m.group(1))
print(' '.join('/'+s if s else '/' for s in sorted(set(slugs))))
PY
)
fi
npx vite build --outDir "$OUT" > /tmp/check-phone-build.log 2>&1 || { echo "vite build failed; see /tmp/check-phone-build.log"; exit 1; }
cat > "$OUT/__measure.html" <<'HTML'
<!doctype html><meta charset=utf-8><body style="margin:0">
<iframe id=f style="width:400px;height:900px;border:0"></iframe><pre id=out>pending</pre>
<script>
const f=document.getElementById('f'); f.src=location.hash.slice(1)||'/';
f.onload=()=>setTimeout(()=>{
  const d=f.contentDocument, cw=d.documentElement.clientWidth;
  const scrolls=e=>{for(let p=e.parentElement;p;p=p.parentElement){const o=getComputedStyle(p).overflowX;if(o==='auto'||o==='scroll'||o==='hidden')return true}return false};
  const wide=[...d.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>cw+1&&!scrolls(e));
  const outer=wide.filter(e=>!wide.some(o=>o!==e&&o.contains(e))).slice(0,4).map(e=>e.tagName+'.'+(e.className||'').toString().slice(0,60)+'@'+Math.round(e.getBoundingClientRect().right));
  document.getElementById('out').textContent='RESULT '+d.documentElement.scrollWidth+' '+outer.join(' | ');
},3500);
</script>
HTML
(npx vite preview --outDir "$OUT" --port $PORT --strictPort > /dev/null 2>&1 &)
sleep 3
bad=0; n=0
for r in $ROUTES; do
  n=$((n+1))
  res=$("$CH" --headless=new --disable-gpu --virtual-time-budget=15000 --window-size=1000,1000 \
        --dump-dom "http://localhost:$PORT/__measure.html#$r" 2>/dev/null | grep -o "RESULT [0-9]*[^<]*" | head -1)
  w=$(echo "$res" | awk '{print $2}')
  if [ -z "$w" ]; then echo "  ?    $r  (did not render)"; bad=$((bad+1))
  elif [ "$w" -gt 400 ]; then echo "  ${w}px  $r  ${res#RESULT $w }"; bad=$((bad+1))
  else echo "  ok   $r"; fi
done
pkill -f "[v]ite preview --outDir $OUT --port $PORT"
rm -f "$OUT/__measure.html"
echo "$n routes at 400px; $bad scroll sideways"
[ "$bad" -eq 0 ]
