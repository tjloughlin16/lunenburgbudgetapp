#!/usr/bin/env python3
"""Is every generated file still what its generator would produce?

    python3 scripts/check_generated.py

THE ROOT CAUSE THIS EXISTS FOR

Nearly every defect found in this project on 5 September 2026 was one shape:
**something derived was written down, the thing it derived from moved, and nothing
connected the two.** Thirteen instances in a day.

  * a word index moved folders and llms.txt kept citing the old URL
  * a provenance join hardcoded `town-budget/index.csv` and resolved 0 of 225 rows
  * eight scripts globbed `town-budget/docs` for reports that had left it
  * 43 document rows named files that no longer existed, and were still being cited as
    the place to check a figure
  * a caveat quoted a series -- 0, 5, 4, 4, 0 -- typed from a field that the same commit
    had already fixed, so it repeated the undercount it existed to explain

Three sub-causes, and each has a countermeasure:

  1. **A LOCATION WAS HARDCODED where location is not identity.** This archive is keyed on
     provenance and re-files documents on purpose; a literal folder path in a script is a
     latent break with a date on it. Read the manifest or glob every `sources/*/index.csv`.
  2. **A FIGURE OR A NAME WAS TYPED into prose.** Rule 2 was stated for the projection and
     never applied to llms.txt, the READMEs, the caveats, the worked examples or the check
     fixtures -- all of which are prose that ships.
  3. **A JOIN THAT MATCHES NOTHING LOOKS EXACTLY LIKE DATA THAT IS ABSENT.** Four of the
     thirteen were silent zeros. A join whose result is used must assert that it matched.

This runs the `--check` mode of every generator, which is the mechanical half of the
answer: if an input moved, the output no longer reproduces, and this says so. It does not
catch a figure typed into a sentence that nothing regenerates -- for that the only defence
is deriving it, which is why the caveats and examples now are.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Every generator that can check itself. Ordered cheapest first, so a fast failure comes
# back fast. `sync_d1` is last because it is the only one that touches the network.
CHECKS = [
    ('build_readme.py', ['--check']),
    # Added 6 Sept 2026, after it had already drifted: two analyses were published
    # and /reports went on listing thirteen. Nothing caught it because this file is
    # the thing that catches it, and this generator was not in it.
    ('build_reports_index.py', ['--check']),
    ('build_money_flow.py', ['--check']),
    ('build_sitemap.py', ['--check']),
    ('check_github_mirror.py', []),
    ('classify_roster_roles.py', ['--check']),
    ('build_views.py', ['--check']),
    ('build_archive_guide.py', ['--check']),
    ('build_show_your_work.py', ['--check']),
    ('build_data_model_grids.py', ['--check']),
    ('split_large_text.py', ['--check']),
    ('build_question_bank.py', ['--check']),
    ('build_db.py', ['--check']),
    ('check_archive_layout.py', []),
    ('check_moved_docs.py', []),
    ('build_source_index.py', []),
    ('sync_d1.py', ['--check']),
]


def main():
    failed = []
    for script, args in CHECKS:
        path = os.path.join(ROOT, 'scripts', script)
        if not os.path.exists(path):
            continue
        label = script + (' ' + ' '.join(args) if args else '')
        r = subprocess.run([sys.executable, path, *args], cwd=ROOT,
                           capture_output=True, text=True)
        mark = ' ok ' if r.returncode == 0 else 'FAIL'
        tail = (r.stdout or r.stderr).strip().splitlines()
        print(f'  {mark}  {label:42s} {tail[-1][:60] if tail else ""}')
        if r.returncode != 0:
            failed.append((label, (r.stdout or r.stderr).strip()))

    print()
    if failed:
        print(f'{len(failed)} generator(s) no longer reproduce their output:\n')
        for label, out in failed:
            print(f'--- {label}')
            print('\n'.join(out.splitlines()[-6:]))
            print()
        print('Something a generated file depends on has moved or changed. That is the '
              'shape\nof nearly every defect in this project: a derived thing written '
              'down, and the\nthing it derived from moved underneath it.')
        return 1
    print(f'ok: all {len(CHECKS)} generators still reproduce what is committed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
