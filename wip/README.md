# wip/ — UNFINISHED WORK, saved so it cannot be lost

**Nothing in this folder is published, built, catalogued or checked.** No generator reads it, the
site does not serve it, and `build_source_index.py` does not scan it. It exists because work in a
working tree is one disk away from gone, and some work stops before it is ready to commit where it
belongs: an agent hits a usage limit, a session is paused.

TJ, 19 October 2026: *"we should have a way to commit this stuff that's unfinished. can you put it
into a folder or something and mark it as that?"*

## The convention

- One folder per piece of unfinished work: `wip/<YYYY-MM-DD>-<what>/`.
- `README.md` in it says **UNFINISHED** at the top, what it was for, what state it is in, its known
  defects, and how to resume.
- `files/` holds new files, copied at the path they would have in the repo.
- `patches/` holds `git diff` output for files that already exist in the repo, so the change can be
  re-applied with `git apply` without overwriting anyone else's later edits.
- **It is a copy.** The originals may still be in the working tree. Resuming means applying from
  here, checking, and committing the work where it belongs; then delete the wip folder in the same
  commit.
- Never put anything here that may not be public: no names-with-pay, no raw MUNIS, nothing from
  `build/private/`. This folder is pushed to GitHub like the rest of the repo.
