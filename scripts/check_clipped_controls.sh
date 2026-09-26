#!/bin/bash
# IS ANY CONTROL CLIPPED OUT OF EXISTENCE? Measured, not eyeballed.
#
# A container with `overflow: hidden` and more content than height does not fail, does not
# warn and does not look broken -- it silently deletes whatever did not fit. The choropleth's
# scale switch went that way: the legend row was nested inside the map container instead of
# beside it, so it laid out below the drawing and past the clip. The column measured 846px
# with a scrollHeight of 899, and the missing 53px was the entire control.
#
# That is worth its own instrument because of how it PRESENTS: a control clipped out of
# existence is indistinguishable from a control never built, and it was reported here as a
# lost feature rather than a layout bug.
#
# So: render each route, find every element that hides its own overflow, and fail where the
# content is taller than the box. Scrollable containers are fine -- a reader can reach that
# content. `overflow: hidden` means they cannot.
#
#   bash scripts/check_clipped_controls.sh                      # the routes with charts
#   bash scripts/check_clipped_controls.sh /analysis/towns-like-us
set -u
cd "$(dirname "$0")/../fy28" || exit 1
export PATH="/Users/tj/.nvm/versions/node/v22.22.2/bin:$PATH"
CH="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
OUT=/tmp/preview-clip
PORT=8799
ROUTES="${*:-/analysis/towns-like-us}"

npx vite build --outDir "$OUT" > /tmp/check-clip-build.log 2>&1 || {
  echo "vite build failed; see /tmp/check-clip-build.log"; exit 1; }

cat > "$OUT/__clip.html" <<'HTML'
<!doctype html><meta charset=utf-8><body style="margin:0">
<iframe id=f style="width:1440px;height:900px;border:0"></iframe><pre id=out>pending</pre>
<script>
const f=document.getElementById('f'); f.src=location.hash.slice(1)||'/';
f.onload=()=>setTimeout(()=>{
  const d=f.contentDocument;
  const bad=[...d.querySelectorAll('body *')].filter(e=>{
    const cs=getComputedStyle(e);
    if(cs.overflowY!=='hidden'&&cs.overflow!=='hidden')return false;
    /* 2px of slack: subpixel rounding on a scaled SVG is not a clipped control. */
    return e.scrollHeight>e.clientHeight+2 && e.clientHeight>0;
  });
  const outer=bad.filter(e=>!bad.some(o=>o!==e&&o.contains(e)));
  document.getElementById('out').textContent='RESULT '+outer.length+' '+
    outer.slice(0,4).map(e=>e.tagName+'@'+e.clientHeight+'<'+e.scrollHeight).join(' | ');
},4000);
</script>
HTML

(npx vite preview --outDir "$OUT" --port $PORT --strictPort > /dev/null 2>&1 &)
sleep 3
bad=0; n=0
for r in $ROUTES; do
  n=$((n+1))
  res=$("$CH" --headless=new --disable-gpu --virtual-time-budget=20000 --window-size=1500,1100 \
        --dump-dom "http://localhost:$PORT/__clip.html#$r" 2>/dev/null | grep -o "RESULT [0-9]*[^<]*" | head -1)
  c=$(echo "$res" | awk '{print $2}')
  if [ -z "$c" ]; then echo "  ?      $r  (did not render)"; bad=$((bad+1))
  elif [ "$c" -gt 0 ]; then echo "  CLIP   $r  ${res#RESULT $c }"; bad=$((bad+1))
  else echo "  ok     $r"; fi
done
pkill -f "[v]ite preview --outDir $OUT --port $PORT"
rm -f "$OUT/__clip.html"
echo "$n route(s); $bad with content clipped out of an overflow:hidden box"
[ "$bad" -eq 0 ]
