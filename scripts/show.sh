#!/bin/bash
# Open a local page in Chrome, REUSING the tab if it is already open.
#
# Opening the same file repeatedly buries the window in duplicate tabs and loses the
# reader's scroll position on every rebuild. This reloads the tab that already holds the
# file, and only creates one when there is none.
#
#   scripts/show.sh notes/reference/data-model/school-money-flow.html [more...]
for f in "$@"; do
  abs="$(cd "$(dirname "$f")" && pwd)/$(basename "$f")"
  result=$(osascript - "$abs" <<'APPLESCRIPT'
on run argv
  set target to item 1 of argv
  set found to false
  tell application "Google Chrome"
    if (count of windows) is 0 then return
    repeat with w in windows
      set i to 0
      repeat with t in tabs of w
        set i to i + 1
        set u to URL of t
        -- a file:// URL is percent-encoded; compare on the basename, which is enough
        -- to identify one of our generated pages and survives the encoding
        if u contains (do shell script "basename " & quoted form of target) then
          tell t to reload
          set found to true
        end if
      end repeat
    end repeat
  end tell
  if not found then return "MISSING"
  return "RELOADED"
end run
APPLESCRIPT
)
  if [ "$result" != "RELOADED" ]; then open "$abs"; fi
done
