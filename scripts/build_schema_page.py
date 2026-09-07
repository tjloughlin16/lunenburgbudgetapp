#!/usr/bin/env python3
"""Every table in the database, what it holds, and whether it can answer your question.

    python3 scripts/build_schema_page.py
    python3 scripts/build_schema_page.py --check

Writes `notes/reference/data-model/schema.html`.

WHY THIS EXISTS ALONGSIDE SCHEMA.md AND schema.mmd

Three documents, three different jobs, and it is worth being clear which is which:

  SCHEMA.md      PROSE. The grain of the three fact tables, and the traps between them.
                 Hand-written, because "a period is not a stage" is an argument, not a
                 property of the file.
  schema.mmd     A PICTURE. Which table joins to which, with the match rate on the edge.
  this page      The INVENTORY. Every table, every column, its type, how many rows, and
                 which fiscal years it actually covers.

The inventory has to be generated, and the reason is rule 2 applied to a schema: a column
list typed into a document is wrong the first time a column is added and nothing fails.

WHAT THE TOP OF THE PAGE IS FOR, AND WHY IT LEADS

A schema tells you what columns exist. It does not tell you whether the question you
arrived with can be answered, and that is the thing somebody actually wants to know. So
the page opens with real questions, each one RUN against the live database at build time,
showing its row count and its first rows.

That means a question that has stopped answering breaks the build rather than sitting on
the page looking answerable. It also means the honest ones are visible: two of the
questions below return nothing, and the page says so in the same voice as the ones that
work, because "we hold five checked years" is a fact about this archive and hiding it
would make the page a brochure.

THE VERDICT COLUMN IS DERIVED, NOT WRITTEN

`answers` / `partly` / `not yet` is computed from what the query returned, never typed.

Two fields feed it and they are deliberately NOT the same thing, because the first draft
of this page conflated them and every question came out `partly`, which made the badge
carry no information at all:

  `partly`  the rows are NOT what was asked for. Q1 returns every revenue source with an
            amount and a class, and CANNOT say which department the money went on to pay
            for -- general fund money is fungible and no document closes it. Q4 was asked
            for what the town VOTED in FY24 and can only return what the district ASKED
            for, because that year has no `settled` stage. Those are shortfalls.
  `caveat`  the rows ARE what was asked for, and here is how to read them without getting
            it wrong. "A stage is not a stage" is guidance, not a shortfall.

Only `partly` moves the verdict. Both print, because a reader needs both.
"""

import argparse
import csv
import html
import json
import os
import random
import sqlite3
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
OUT = os.path.join(ROOT, 'notes', 'reference', 'data-model', 'schema.html')
MANIFEST = os.path.join(ROOT, 'fy28', 'src', 'data', 'agent-manifest.json')


def api_base():
    """Which API the page's modal queries. Never typed into this file.

    Three layers, most specific first, because there are three real situations:

      LUNENBURG_API   an environment variable — point a build at `wrangler dev`, or at a
                      preview deploy, without editing anything. TJ's suggestion, and the
                      reason it is needed is the note already on the page: this document
                      is generated from the LOCAL database and queries a PUBLISHED one, so
                      there has to be a way to aim it at the copy you are actually working
                      on.
      agent-manifest  the canonical site, read from the same file the rest of the build
                      reads it from. Rule 2: a URL typed into a generator is a figure
                      typed into prose, and this project has had a document number and a
                      bundle name go stale exactly that way.
      (no default)    if the manifest cannot be read, fail rather than guess — a page
                      silently pointing at the wrong database is the failure this whole
                      mechanism exists to prevent.

    A viewer can override it again at runtime with `?api=` — see the script on the page.
    """
    env = os.environ.get('LUNENBURG_API')
    if env:
        return env.rstrip('/')
    if not os.path.exists(MANIFEST):
        raise SystemExit(
            f'{os.path.relpath(MANIFEST, ROOT)} is missing and LUNENBURG_API is not set, '
            f'so there is no way to know which API this page should query.')
    with open(MANIFEST, encoding='utf-8') as fh:
        site = json.load(fh).get('site')
    if not site:
        raise SystemExit(f'no `site` in {os.path.relpath(MANIFEST, ROOT)}')
    return site.rstrip('/')

# --------------------------------------------------------------------------------------
# The questions. Each is RUN. `partly` is a declared limit on what the rows establish, and
# it is prose about the WORLD, not about the SQL -- see rule 7.
# --------------------------------------------------------------------------------------
QUESTIONS = [
    dict(
        q='Every source of revenue in FY2022, by name and amount, with our classification',
        sql="""SELECT fy, printed_name, label, class, amount, document, page
               FROM revenue_history WHERE fy = 2022 ORDER BY amount DESC""",
        partly=(
            '`class` says what KIND of revenue it is — levy, state aid, local receipt, '
            'transfer — which is a property of where the money came FROM. It does not say '
            'what the money went on to pay for, and for anything landing in the general '
            'fund nothing can: that money is fungible by law and no document apportions '
            'it. Only restricted funds have a traceable destination, and those are in '
            '`money_edges`.'),
        why='The classification is joined in at build time from `money_classification`, '
            'so the name the report printed and the group we assigned are in one row.'),
    dict(
        q='The same question for FY2023',
        sql='SELECT fy, printed_name, amount FROM revenue_history WHERE fy = 2023',
        why='Returns nothing, and that is the correct answer rather than a failure. '
            '`revenue_history` carries only years whose extract was CHECKED against the '
            'report’s own printed total. FY2023 has 10 unchecked rows in '
            '`annual_report_receipts`; loading them here would make five verified years '
            'and one guess look identical.'),
    dict(
        q='What was budgeted for the Superintendent, FY2022 to FY2025',
        sql="""SELECT fy, stage, label, value FROM budget_figure
               WHERE label LIKE '%Superintendent%' AND fy BETWEEN 2022 AND 2025
               ORDER BY fy, stage""",
        caveat=(
            'One row per **stage**, and they are different quantities: `proposed` is what '
            'was asked for, `settled` what was voted, `actual` what the later document '
            'reported. Rule 1 — never compute a growth rate from one stage to another.'),
        why='`budget_figure` is one row per line × year × stage × variant. Filtering on '
            'a label works here because "Superintendent" is unique; most lines are not, '
            'which is what `line_key` is for.'),
    dict(
        q='Every line in the school budget for FY2024, by name and amount',
        sql="""SELECT fy, stage, label, value FROM budget_figure
               WHERE fy = 2024 AND stage = 'proposed' ORDER BY value DESC""",
        partly=(
            'FY2024 has no `settled` stage in the archive — only `proposed` and `actual`. '
            'So this is what the district ASKED for that year, not what the town voted. '
            'The stage you get is not the stage you named, and the coverage table below '
            'is the only place that difference is visible before you query.'),
        why='Which stages exist varies by year, so a query written for one year can '
            'silently return nothing for another.'),
    dict(
        q='Where the money actually went in FY2026, by department, with who decides',
        sql="""SELECT department, control, voted, expended FROM v_spending_classified
               WHERE fy = 2026 AND period = 9 ORDER BY expended DESC LIMIT 12""",
        caveat=(
            '`control` is our classification of who holds the decision, not a published '
            'field. `voted` and `expended` are the town’s own figures; the column beside '
            'them is ours and is labelled that way everywhere it appears.'),
        why='Spending IS traceable to a department, which is why this answers where the '
            'revenue question above cannot.'),
    dict(
        q='The full ledger for one account across the year',
        sql="""SELECT l.fy, l.period, a.name, a.account_id, l.original, l.revised,
                      l.expended, l.available
               FROM ledger_snapshot l JOIN account a USING (account_id)
               WHERE a.account_id LIKE '0100-S%' AND l.fy = 2026
               ORDER BY l.expended DESC LIMIT 10""",
        caveat=(
            '`period` is a point in time inside the year, not a stage. Two periods of the '
            'same year are two different MUNIS reports and adding them double-counts.'),
        why='The `S` prefix is the structural way to find school accounts — it does not '
            'depend on any name, and MUNIS names are ten characters typed by a person.'),
]

# THE SEMANTICS LIVE IN TWO CSVs, NOT IN THIS FILE.
#
# TJ asked for descriptions of the tables and their columns, and then — reading the page —
# for the MAIN tables to be distinguishable from the rest: "there has to be some main
# tables right, fact tables, vs dimensions? Hard to tell." Seventy tables listed as equals
# is a directory, not a map.
#
# Where that description lives matters more than what it says. Three properties decided it:
#
#   1. It is DATA, so it loads into the database and `/api/query` can reach it. A
#      description trapped in a Python docstring is invisible to every caller that is not
#      reading this file.
#   2. It is CHECKABLE. `--check` fails if a table exists with no entry, or an entry names
#      a table that does not. That is the whole anti-drift mechanism this project runs on.
#   3. It is SMALL. 883 column instances share only 285 distinct names, and 110 of those
#      names cover 80% of the instances — so a shared glossary describes `v1`, `status`
#      and `fy` once each, which is right, because those mean the same dangerous thing
#      everywhere they appear.
#
# `sources/data/table-semantics.csv`  — one row per table: role, grain, what it answers.
# `sources/data/column-glossary.csv`  — one row per distinct column name.
#
# Coverage is deliberately printed on the page rather than rounded up to "documented".
ROLES = [
    ('fact', 'Facts — the measurements',
     'What was budgeted, what was spent, what a fund holds. These carry the figures; '
     'everything else in the database describes, extracts, classifies or checks them.'),
    ('dimension', 'Dimensions — what a key means',
     'Joined to, never summed. An account number, a fund, a line, a period.'),
    ('extract', 'Extracts — readings off a printed page',
     'What the annual reports print, before anything decides what it means. This is where '
     '`v1`..`v8` and `status` live, and neither may be used without reading its entry.'),
    ('classification', 'Our model — every row here is a judgement',
     'Not measurements. Each carries the basis for the call so it can be argued with.'),
    ('provenance', 'Provenance — where a figure came from, and whether it holds up',
     'Rule 12 in table form.'),
    ('derived', 'Derived — computed from the tables above',
     'Convenience, recomputable, never a source.'),
]

# The three grains SCHEMA.md names. Called out because confusing them is how a budget gets
# compared to an actual that is not its own, and because 33 fact tables all looking alike
# is the problem TJ reported.
SPINE = ('ledger_snapshot', 'budget_figure', 'workbook_figure')


def semantics():
    """Load both CSVs. Returns (per-table dict, per-column dict)."""
    def rows(name):
        path = os.path.join(ROOT, 'sources', 'data', name)
        if not os.path.exists(path):
            raise SystemExit('%s is missing — it is the source of the table and column '
                             'descriptions on this page.' % name)
        with open(path, newline='', encoding='utf-8') as fh:
            return list(csv.DictReader(fh))
    tabs = {r['table_name']: r for r in rows('table-semantics.csv')}
    cols = {r['column']: r for r in rows('column-glossary.csv')}
    return tabs, cols


def by_role(c, tabs):
    """Group every table by its declared role, or refuse to run."""
    tables = [r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    undescribed = sorted(set(tables) - set(tabs))
    if undescribed:
        raise SystemExit(
            'table(s) with no entry in sources/data/table-semantics.csv: %s\n'
            '  A table nobody described is a table nobody can use. Add a row giving its '
            'role, its grain and what it answers.' % ', '.join(undescribed))
    gone = sorted(set(tabs) - set(tables))
    if gone:
        raise SystemExit('table-semantics.csv describes table(s) that no longer exist: %s'
                         % ', '.join(gone))
    known = {r for r, _, _ in ROLES}
    bad = sorted({t for t, r in tabs.items() if r['role'] not in known})
    if bad:
        raise SystemExit('unknown role(s) on: %s. Roles are: %s'
                         % (', '.join(bad), ', '.join(sorted(known))))
    out = []
    for role, title, blurb in ROLES:
        members = [t for t in tables if tabs[t]['role'] == role]
        # the spine first, then the rest alphabetically
        members.sort(key=lambda t: (t not in SPINE, SPINE.index(t) if t in SPINE else 0, t))
        out.append((role, title, blurb, members))
    return out


# Columns that decide what a row IS. Omitting one does not raise -- it returns a number
# that is the sum of two different things. All four have been got wrong here.
SPLITTERS = [
    ('status', 'annual report extracts',
     '`checked`, `check failed`, `no check`. Summing across them mixes verified figures '
     'with unverified ones.'),
    ('level', '`account`, `ledger_snapshot`',
     '`department` roll-ups sit in the same table as their own detail. Summing both adds '
     'the budget to itself.'),
    ('account_type', '`account`',
     'Revenue is stored NEGATIVE. Omitting it once made the town’s whole budget compute '
     'as minus $997,871.'),
    ('period', '`ledger_snapshot`',
     'Two periods are two different MUNIS reports of the same year, not two halves of it.'),
    ('stage', '`budget_figure`',
     '`proposed`, `settled`, `actual`. Rule 1: a rate measured across stages is partly '
     'growth and partly the step between them.'),
    ('variant', '`budget_figure`',
     'FY27 has four whole budgets — Balanced, Core, Level Service, Restoration. Without '
     'this you sum all four.'),
    ('v1 … v8', 'annual report extracts',
     'ORDINALS, not column names: the first column of THAT PAGE that held figures. '
     'Summing `v1` down a run adds one page’s APPROPRIATED to another’s TOTAL EXPENDED.'),
]


def db():
    if not os.path.exists(DB):
        raise SystemExit(f'{DB} missing. Run: python3 scripts/build_db.py')
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def families(c):
    """Assign every table to a declared family, or refuse to run."""
    tables = [r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    placed, out = set(), []
    for title, blurb, members in FAMILIES:
        got = [t for t in members if t in tables]
        placed.update(got)
        out.append((title, blurb, got))
    orphan = sorted(set(tables) - placed)
    if orphan:
        raise SystemExit(
            'table(s) in no family: %s\n'
            '  Add each to FAMILIES in scripts/build_schema_page.py. A table nobody '
            'placed is a table nobody documented.' % ', '.join(orphan))
    missing = sorted({m for _, _, ms in FAMILIES for m in ms} - set(tables))
    if missing:
        raise SystemExit('FAMILIES names table(s) that do not exist: %s' % ', '.join(missing))
    return out


def sample(c, t, n=3):
    """`n` rows drawn from ACROSS the table — random, and reproducible.

    The first three rows are a bad sample and TJ said so: every extract begins with its
    tidiest year, so the head of a table shows none of what makes it awkward. A random
    sample shows the blanks, the negatives and the `check failed` rows.

    But this page is verified byte-for-byte by `--check`, so a sample that reshuffled on
    every rebuild would fail the build for no reason and — worse — teach somebody to
    re-run the generator until it passed. That is how a check stops meaning anything.

    So the randomness is SEEDED, on the table's own name. Spread through the table like a
    random sample, identical on every run, and different per table rather than always the
    same three positions.
    """
    try:
        n_rows = c.execute('SELECT COUNT(*) FROM "%s"' % t).fetchone()[0]
        if not n_rows:
            return []
        rng = random.Random(t)          # the table name IS the seed
        picks = sorted(rng.sample(range(n_rows), min(n, n_rows)))
        rs = c.execute('SELECT * FROM "%s" ORDER BY rowid' % t).fetchall()
    except sqlite3.OperationalError:
        return []                       # a WITHOUT ROWID table: no stable order to take
    return [rs[i] for i in picks]


def cell(v, width=44):
    """One value, trimmed for the page. Empty and NULL are DIFFERENT and shown that way."""
    if v is None:
        return '<span class="nul">NULL</span>'
    t = str(v)
    if t == '':
        return '<span class="nul">empty</span>'
    return esc(t if len(t) <= width else t[:width - 1] + '…')


def profile(c, t):
    """Row count, columns with declared type, and the fiscal years actually present."""
    n = c.execute('SELECT COUNT(*) FROM "%s"' % t).fetchone()[0]
    cols = [(d[1], d[2] or 'TEXT') for d in c.execute('PRAGMA table_info("%s")' % t)]
    years = ''
    if any(name == 'fy' for name, _ in cols) and n:
        ys = sorted({str(r[0]) for r in c.execute(
            'SELECT DISTINCT fy FROM "%s" WHERE fy IS NOT NULL' % t) if r[0] != ''})
        nums = [y for y in ys if y.isdigit()]
        if nums and len(nums) == len(ys) and int(nums[-1]) - int(nums[0]) == len(nums) - 1:
            years = '%s–%s' % (nums[0], nums[-1])          # a contiguous run
        elif ys:
            years = ', '.join(ys) if len(ys) <= 8 else '%s … %s (%d years)' % (
                ys[0], ys[-1], len(ys))
    return n, cols, years


def esc(x):
    return html.escape(str(x))


def run_questions(c):
    out = []
    for spec in QUESTIONS:
        rs = c.execute(spec['sql']).fetchall()
        # DERIVED, never typed: rows decide answers vs not-yet; `partly` narrows it.
        verdict = 'not yet' if not rs else ('partly' if spec.get('partly') else 'answers')
        # `caveat` deliberately does NOT appear here -- see the note at the top of the file.
        out.append((spec, rs, verdict))
    return out


def render(c):
    API_BASE = api_base()
    tabs, gloss = semantics()
    fams = by_role(c, tabs)
    qs = run_questions(c)
    n_tables = sum(len(m) for *_, m in fams)
    n_views = c.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='view'").fetchone()[0]
    n_rows = sum(c.execute('SELECT COUNT(*) FROM "%s"' % t).fetchone()[0]
                 for *_, ms in fams for t in ms)
    all_cols = [(t, d[1]) for *_, ms in fams for t in ms
                for d in c.execute('PRAGMA table_info("%s")' % t)]
    n_cols = len(all_cols)
    described = sum(1 for _, nm in all_cols if nm in gloss)

    B = []
    a = B.append

    # ---- the questions, first, because that is what somebody actually arrives with
    a('<div class="stage"><h2>Can I ask this?</h2>')
    a('<p class="cap">Every query below is <strong>run against the live database when '
      'this page is built</strong>, so a question that stops answering breaks the build '
      'rather than sitting here looking answerable. Two of them return nothing, and that '
      'is the honest state of the archive rather than a fault.</p>')
    for spec, rs, verdict in qs:
        a('<div class="q">')
        a(f'<div class="qhead"><span class="v v-{verdict.replace(" ", "-")}">'
          f'{esc(verdict)}</span><span class="qt">{esc(spec["q"])}</span></div>')
        a('<pre><code>%s</code></pre>' % esc(' '.join(spec['sql'].split())))
        a(f'<p class="rc">{len(rs):,} row{"" if len(rs) == 1 else "s"}</p>')
        if rs:
            keys = rs[0].keys()
            a('<div class="scroll"><table><tr>%s</tr>' %
              ''.join(f'<th>{esc(k)}</th>' for k in keys))
            for r in rs[:5]:
                a('<tr>%s</tr>' % ''.join(
                    '<td%s>%s</td>' % (' class="num"' if isinstance(r[k], (int, float))
                                       else '', esc(r[k])) for k in keys))
            a('</table></div>')
            if len(rs) > 5:
                a(f'<p class="cap">…and {len(rs) - 5:,} more.</p>')
        for field, cls in (('partly', 'warn shortfall'), ('caveat', 'warn')):
            if spec.get(field):
                a(f'<p class="{cls}">{md(spec[field])}</p>')
        a(f'<p class="cap">{md(spec["why"])}</p>')
        a('</div>')
    a('</div>')

    # ---- the columns that decide what a row is
    a('<div class="stage alt"><h2>The columns you cannot leave out</h2>')
    a('<p class="cap">None of these raises an error when omitted. Each returns a number '
      'that is the sum of two different things, which is why every one of them has been '
      'got wrong here at least once.</p>')
    a('<div class="scroll"><table><tr><th>column</th><th>in</th>'
      '<th>what happens if you omit it</th></tr>')
    for col, where, what in SPLITTERS:
        a(f'<tr><td><code>{esc(col)}</code></td><td>{md(where)}</td>'
          f'<td>{md(what)}</td></tr>')
    a('</table></div>')
    a('<p class="warn"><strong>And one that is now fixed.</strong> <code>fy</code> was '
      'stored as TEXT in 44 tables and INTEGER in 18, so <code>WHERE fy = 2023</code> '
      'answered against a third of the database and returned <em>zero rows, with no '
      'error,</em> against the rest. It is INTEGER everywhere now except three documented '
      'exceptions, and <code>check_fy_types</code> in <code>build_db.py</code> fails the '
      'build if a new table arrives without it.</p>')
    a('</div>')

    # ---- the inventory
    for role, title, blurb, members in fams:
        a(f'<div class="stage"><h2>{esc(title)}</h2>')
        if blurb:
            a(f'<p class="cap">{md(" ".join(blurb.split()))}</p>')
        for t in members:
            n, cols, years = profile(c, t)
            sem = tabs[t]
            spine = ' spine' if t in SPINE else ''
            a('<details class="t%s"><summary><code>%s</code>%s '
              '<span class="n">%s row%s</span>%s<span class="gr">%s</span></summary>'
              % (spine, esc(t),
                 ' <span class="badge">the spine</span>' if spine else '',
                 f'{n:,}', '' if n == 1 else 's',
                 f' <span class="yr">{esc(years)}</span>' if years else '',
                 esc(sem['grain'])))
            a(f'<p class="ans">{md(sem["what_it_answers"])}</p>')
            if sem.get('caution'):
                a(f'<p class="warn">{md(sem["caution"])}</p>')
            a('<div class="scroll"><table class="cols"><tr><th>column</th>'
              '<th>type</th><th>what it is</th></tr>')
            for name, typ in cols:
                g = gloss.get(name)
                if g:
                    what = md(g['meaning'])
                    if g.get('unit'):
                        what += f' <span class="unit">{esc(g["unit"])}</span>'
                    if g.get('caution'):
                        what += f'<br><span class="ccaut">{md(g["caution"])}</span>'
                else:
                    what = '<span class="nul">not described yet</span>'
                a(f'<tr><td><code>{esc(name)}</code></td>'
                  f'<td class="ty">{esc(typ)}</td><td>{what}</td></tr>')
            a('</table></div>')
            dq = sem.get('default_query') or ''
            qattr = ' data-q="%s"' % esc(dq) if dq else ''
            joined = 'opens with its names joined back &middot; ' if dq else ''
            a('<p class="openrow"><button class="open" data-t="%s"%s>'
              'Open full table &rarr;</button> <span class="cap sm">%s'
              'queries the live API</span></p>' % (esc(t), qattr, joined))
            rows = sample(c, t)
            if rows:
                a(f'<p class="cap sm">First {len(rows)} row'
                  f'{"" if len(rows) == 1 else "s"}, in rowid order:</p>')
                a('<div class="scroll"><table class="samp"><tr>%s</tr>' %
                  ''.join(f'<th>{esc(k)}</th>' for k in rows[0].keys()))
                for r in rows:
                    a('<tr>%s</tr>' % ''.join(
                        '<td%s>%s</td>' % (' class="num"' if isinstance(r[k], (int, float))
                                           else '', cell(r[k])) for k in r.keys()))
                a('</table></div>')
            else:
                a('<p class="cap sm">No rows. That is the honest state of this table, '
                  'not a load that failed — see its entry in <code>SCHEMA.md</code>.</p>')
            a('</details>')
        a('</div>')

    # ---- views
    a('<div class="stage alt"><h2>Views — the joins already written for you</h2>')
    a('<p class="cap">A view is the safe way to ask a question that needs two tables. '
      'Each one carries the splitting columns above in its own <code>WHERE</code>, so it '
      'cannot be got wrong the way a hand-written join can.</p>')
    a('<div class="scroll"><table><tr><th>view</th><th>columns</th></tr>')
    for (v,) in c.execute(
            "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name"):
        cs = ', '.join(d[1] for d in c.execute('PRAGMA table_info("%s")' % v))
        a(f'<tr><td><code>{esc(v)}</code></td><td class="ty">{esc(cs)}</td></tr>')
    a('</table></div></div>')

    # ---- what cannot be asked, straight out of the data
    gaps = c.execute('SELECT side, what, why FROM money_gaps ORDER BY side, what').fetchall()
    a('<div class="stage"><h2>What this database cannot tell you</h2>')
    a('<p class="cap">Read from <code>money_gaps</code>, so this list is data rather than '
      'a thing somebody remembered to write down. Each is a question the published '
      'documents do not close.</p>')
    a('<div class="scroll"><table><tr><th>side</th><th>what is missing</th>'
      '<th>why it cannot be answered</th></tr>')
    for g in gaps:
        a(f'<tr><td>{esc(g["side"])}</td><td>{md(g["what"])}</td>'
          f'<td>{md(g["why"])}</td></tr>')
    a('</table></div></div>')

    body = '\n'.join(B)
    return PAGE.format(
        body=body, n_tables=n_tables, n_views=n_views,
        n_rows=f'{n_rows:,}', n_cols=n_cols, api_base=API_BASE,
        pct_described=f'{described / n_cols:.0%}',
        gen=date.today().isoformat())


def md(s):
    """The three inline marks used above. Escapes first, so no input can inject markup."""
    s = esc(s)
    for mark, tag in (('**', 'strong'), ('`', 'code'), ('*', 'em')):
        parts = s.split(mark)
        s = parts[0] + ''.join(
            f'<{tag}>{p}</{tag}>' if i % 2 else p for i, p in enumerate(parts[1:], 1))
    return s


PAGE = '''<meta charset="utf-8">
<title>The database, table by table — Lunenburg Budget Project</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {{ --bg:#fbfaf8; --card:#fff; --ink:#191919; --muted:#6b6b6b; --grid:#e2ded7;
  --traced:#1f5c3d; --hi:#9a4f14; --warn:#8a6d10; --warn-bg:#faf3de; --code:#f3f1ec; --head-bar:#f5f3ee; --band:#faf9f6; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#141412; --card:#1c1b19; --ink:#eeebe6; --muted:#a09b93; --grid:#34322e;
    --traced:#79c39f; --hi:#e2a068; --warn:#d9bd67; --warn-bg:#2c2718; --code:#23221f; --head-bar:#201f1c; --band:#1a1917; }}
}}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--bg); color:var(--ink);
  font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  -webkit-text-size-adjust:100% }}
.wrap {{ max-width:880px; margin:0 auto; padding:22px 16px 80px }}
header {{ border-bottom:2px solid var(--ink); padding-bottom:14px }}
.kicker {{ font-size:11px; letter-spacing:.14em; text-transform:uppercase; color:var(--muted) }}
h1 {{ font-size:27px; line-height:1.15; margin:8px 0; letter-spacing:-.02em }}
.standfirst {{ font-size:16px; color:var(--muted); margin:0 }}
.metrics {{ display:grid; grid-template-columns:repeat(2,1fr); gap:1px; background:var(--grid);
  border:1px solid var(--grid); border-radius:10px; overflow:hidden; margin:16px 0 }}
.metric {{ background:var(--card); padding:12px 14px }}
.metric .v {{ font-size:22px; font-weight:600; letter-spacing:-.02em;
  font-family:ui-monospace,Menlo,monospace }}
.metric .l {{ font-size:11.5px; color:var(--muted); text-transform:uppercase;
  letter-spacing:.08em; margin-top:2px }}
.stage {{ background:var(--card); border:1px solid var(--grid); border-radius:10px;
  padding:16px 15px; margin:16px 0 }}
.stage.alt {{ background:transparent }}
h2 {{ font-size:17px; margin:0 0 6px; letter-spacing:-.01em }}
.cap {{ font-size:13.5px; color:var(--muted); margin:0 0 14px }}
.q {{ border-top:1px solid var(--grid); padding-top:13px; margin-top:13px }}
.qhead {{ display:flex; gap:9px; align-items:baseline; flex-wrap:wrap }}
.qt {{ font-weight:600; font-size:14.5px; flex:1; min-width:200px }}
.v {{ font-size:10.5px; letter-spacing:.09em; text-transform:uppercase; font-weight:700;
  padding:2px 7px; border-radius:20px; white-space:nowrap }}
.v-answers {{ background:var(--traced); color:var(--bg) }}
.v-partly {{ background:var(--hi); color:var(--bg) }}
.v-not-yet {{ background:transparent; color:var(--muted); border:1px solid var(--grid) }}
pre {{ background:var(--code); border-radius:7px; padding:10px 11px; overflow-x:auto;
  margin:9px 0 6px }}
pre code {{ font-size:12px; white-space:pre-wrap; overflow-wrap:anywhere }}
.rc {{ font-size:12px; color:var(--muted); margin:0 0 6px;
  font-family:ui-monospace,Menlo,monospace }}
.scroll {{ overflow-x:auto; -webkit-overflow-scrolling:touch }}
table {{ border-collapse:collapse; width:100%; font-size:13px }}
th,td {{ text-align:left; padding:5px 10px 5px 0; border-bottom:1px solid var(--grid);
  vertical-align:top }}
th {{ font-size:11px; text-transform:uppercase; letter-spacing:.07em; color:var(--muted);
  font-weight:600; white-space:nowrap }}
td.num {{ text-align:right; font-family:ui-monospace,Menlo,monospace; white-space:nowrap }}
td.ty {{ font-family:ui-monospace,Menlo,monospace; font-size:11.5px; color:var(--muted) }}
code {{ font-family:ui-monospace,Menlo,monospace; font-size:12.5px }}
.warn {{ background:var(--warn-bg); border-left:3px solid var(--warn);
  border-radius:0 6px 6px 0; padding:11px 13px; font-size:13.5px; margin:10px 0 }}
.warn.shortfall {{ border-left-color:var(--hi) }}
details {{ border-bottom:1px solid var(--grid); padding:7px 0 }}
details[open] {{ padding-bottom:11px }}
summary {{ cursor:pointer; font-size:14px }}
summary .n {{ color:var(--muted); font-size:12px;
  font-family:ui-monospace,Menlo,monospace }}
summary .yr {{ color:var(--traced); font-size:11.5px;
  font-family:ui-monospace,Menlo,monospace }}
details table.cols {{ margin-top:9px; max-width:420px }}
details table.samp {{ margin-top:5px; font-size:11.5px; white-space:nowrap }}
details table.samp td {{ padding-right:14px }}
.cap.sm {{ font-size:12px; margin:11px 0 0 }}
.nul {{ color:var(--muted); font-style:italic; font-size:.9em }}
.gen {{ margin-top:30px; font-size:12px; color:var(--muted) }}
@media (min-width:680px) {{ .metrics {{ grid-template-columns:repeat(5,1fr) }} }}
details.spine {{ border-left:3px solid var(--traced); padding-left:10px }}
.badge {{ font-size:10px; letter-spacing:.08em; text-transform:uppercase;
  background:var(--traced); color:var(--bg); padding:1px 6px; border-radius:20px }}
.gr {{ display:block; font-size:11.5px; color:var(--muted); margin-top:2px }}
.ans {{ font-size:13.5px; margin:8px 0 0 }}
.unit {{ font-size:10.5px; color:var(--muted); text-transform:uppercase;
  letter-spacing:.06em }}
.ccaut {{ font-size:12px; color:var(--hi) }}
.openrow {{ margin:10px 0 0 }}
button.open, #mrun, #mx {{ font:inherit; font-size:12px; padding:4px 10px;
  border:1px solid var(--grid); border-radius:6px; background:var(--card);
  color:var(--ink); cursor:pointer }}
button.open:hover, #mrun:hover {{ border-color:var(--traced); color:var(--traced) }}
#modal {{ position:fixed; inset:0; background:rgba(0,0,0,.5); z-index:9;
  display:flex; align-items:center; justify-content:center; padding:24px;
  backdrop-filter:blur(2px) }}
/* MUST come after the rule above. `hidden` is only a `display:none` in the UA stylesheet,
   so ANY display rule on the same element beats it — the modal was visible from page
   load, blank, and the close button set an attribute that changed nothing. */
#modal[hidden] {{ display:none }}
#modal .sheet {{ background:var(--bg); border-radius:12px; width:min(1500px,100%);
  height:min(88vh,100%); display:flex; flex-direction:column; overflow:hidden;
  border:1px solid var(--grid); box-shadow:0 18px 50px rgba(0,0,0,.3) }}

/* The bar is a control strip, so it gets its own ground and a real inset. Its parts are
   three different kinds of thing — what you are looking at, how to change it, what came
   back — and they are spaced as three groups rather than evenly. */
.mbar {{ display:flex; gap:12px; align-items:center; padding:13px 18px;
  border-bottom:1px solid var(--grid); background:var(--head-bar); flex-wrap:wrap }}
.mbar strong {{ font-family:ui-monospace,Menlo,monospace; font-size:14px;
  letter-spacing:-.01em }}
#msql {{ flex:1; min-width:240px; font:12.5px/1.5 ui-monospace,Menlo,monospace;
  padding:7px 11px; border:1px solid var(--grid); border-radius:7px;
  background:var(--bg); color:var(--ink) }}
#msql:focus {{ outline:none; border-color:var(--traced) }}
#mmeta {{ font-size:11.5px; color:var(--muted); white-space:nowrap;
  font-family:ui-monospace,Menlo,monospace; padding:3px 9px; border-radius:20px;
  background:var(--code) }}
#mmeta:empty {{ display:none }}
#mx {{ margin-left:auto; font-size:17px; line-height:1; padding:4px 11px 6px }}

/* The table wants to be full-bleed so the sticky header spans the sheet, but content
   flush to a container edge reads as an accident. So the INSET lives on the first and
   last cells rather than on the scroll box. */
.mwrap {{ overflow:auto; flex:1; background:var(--bg) }}
.mwrap table {{ font-size:12px; white-space:nowrap; border-collapse:separate;
  border-spacing:0; width:100% }}
.mwrap th, .mwrap td {{ padding:8px 16px; border-bottom:1px solid var(--grid);
  vertical-align:top; max-width:380px; overflow:hidden; text-overflow:ellipsis }}
.mwrap th:first-child, .mwrap td:first-child {{ padding-left:18px }}
.mwrap th:last-child, .mwrap td:last-child {{ padding-right:18px }}
.mwrap th {{ position:sticky; top:0; z-index:1; background:var(--head-bar);
  font-size:10.5px; text-transform:uppercase; letter-spacing:.07em; color:var(--muted);
  font-weight:600; border-bottom:2px solid var(--grid); white-space:nowrap }}
/* Row banding, not borders, to carry the eye across a wide table. Kept very low
   contrast: at 60+ columns a visible stripe becomes the loudest thing on screen. */
.mwrap tbody tr:nth-child(even) td {{ background:var(--band) }}
.mwrap tbody tr:hover td {{ background:var(--code) }}
.mwrap td.num {{ text-align:right; font-family:ui-monospace,Menlo,monospace;
  font-variant-numeric:tabular-nums }}
.mnote {{ padding:28px 20px; font-size:13.5px; color:var(--muted); text-align:center }}

/* Column controls. The header cell is a container for two affordances, so it stops being
   a label and becomes a control strip — which is why the sort button IS the label rather
   than sitting beside it: a second click target for the same idea reads as two ideas. */
.mwrap th {{ padding:0 }}
.thh {{ display:flex; align-items:stretch; gap:0 }}
.thh .srt {{ flex:1; text-align:left; font:inherit; font-size:10.5px; font-weight:600;
  text-transform:uppercase; letter-spacing:.07em; color:var(--muted); background:none;
  border:0; padding:9px 6px 9px 16px; cursor:pointer; white-space:nowrap }}
.thh .srt:hover {{ color:var(--ink) }}
.thh .srt i {{ display:inline-block; width:9px; margin-left:5px; opacity:.35 }}
.thh .srt i::after {{ content:'\2195' }}
.thh .srt.up, .thh .srt.down {{ color:var(--traced) }}
.thh .srt.up i, .thh .srt.down i {{ opacity:1 }}
.thh .srt.up i::after {{ content:'\2191' }}
.thh .srt.down i::after {{ content:'\2193' }}
.thh .flt {{ font:inherit; font-size:11px; background:none; border:0; color:var(--muted);
  padding:0 12px 0 4px; cursor:pointer }}
.thh .flt:hover {{ color:var(--ink) }}
.thh .flt.on {{ color:var(--hi); font-weight:700 }}
.mwrap th {{ position:sticky; top:0; overflow:visible }}
/* `overflow:visible` overrides the ellipsis rule the data cells share, or the filter
   panel is clipped to the header cell and appears as a 20px sliver. And `sticky` is
   already a positioned value, so it is the containing block for that panel — adding
   `relative` here would silently un-stick the header instead. */

.fpanel {{ position:absolute; z-index:5; margin-top:2px; right:0; width:270px;
  background:var(--bg); border:1px solid var(--grid); border-radius:9px;
  box-shadow:0 12px 30px rgba(0,0,0,.28); padding:9px; text-align:left;
  font-weight:400; text-transform:none; letter-spacing:0 }}
.fpanel .fq {{ width:100%; font:12px/1.4 ui-monospace,Menlo,monospace; padding:5px 8px;
  border:1px solid var(--grid); border-radius:6px; background:var(--code);
  color:var(--ink) }}
.fvals {{ max-height:230px; overflow:auto; margin:7px 0 }}
.fvals label {{ display:flex; gap:7px; align-items:baseline; padding:3px 4px;
  font-size:12px; color:var(--ink); border-radius:4px; cursor:pointer;
  white-space:nowrap }}
.fvals label:hover {{ background:var(--code) }}
.fvals label span {{ flex:1; overflow:hidden; text-overflow:ellipsis }}
.fvals label b {{ color:var(--muted); font-weight:400; font-size:11px;
  font-family:ui-monospace,Menlo,monospace }}
.fmore {{ font-size:11.5px; color:var(--muted); margin:6px 4px 0 }}
.fbar {{ display:flex; gap:7px; justify-content:flex-end }}
.fbar button {{ font:inherit; font-size:11.5px; padding:4px 11px; cursor:pointer;
  border:1px solid var(--grid); border-radius:6px; background:var(--bg);
  color:var(--ink) }}
.fbar .fdone {{ border-color:var(--traced); color:var(--traced) }}
</style>

<div class="wrap">
<header>
  <div class="kicker">Lunenburg Budget Project &middot; Data architecture</div>
  <h1>The database, table by table</h1>
  <p class="standfirst">Everything <code>sources/data/lunenburg.db</code> holds, what each
  table is for, which years it actually covers — and, first, whether the question you
  arrived with can be answered at all.</p>
</header>

<div class="metrics">
  <div class="metric"><div class="v">{n_tables}</div><div class="l">tables</div></div>
  <div class="metric"><div class="v">{n_views}</div><div class="l">views</div></div>
  <div class="metric"><div class="v">{n_rows}</div><div class="l">rows</div></div>
  <div class="metric"><div class="v">{n_cols}</div><div class="l">columns</div></div>
  <div class="metric"><div class="v">{pct_described}</div><div class="l">columns described</div></div>
</div>

<p class="warn"><strong>Two databases, and they are not always the same one.</strong>
Everything printed on this page — row counts, samples, coverage — is read from the LOCAL
<code>sources/data/lunenburg.db</code> when the page is built. <em>Open full table</em>
queries <code>{api_base}</code>, a copy pushed to Cloudflare D1 that can lag behind.
Point it elsewhere with <code>?api=&lt;base-url&gt;</code> on this page's own URL, or set
<code>LUNENBURG_API</code> before building.
If a table opens empty, or the button reports that it does not exist, that copy has not
been pushed yet: <code>python3 scripts/sync_d1.py</code>. This is stated rather than
hidden because two sources that usually agree are the ones that mislead when they
stop.</p>

{body}

<div id="modal" hidden>
  <div class="sheet">
    <div class="mbar">
      <strong id="mt"></strong>
      <input id="msql" spellcheck="false" autocomplete="off">
      <button id="mrun">Run</button>
      <span id="mmeta"></span>
      <button id="mx" title="close">&times;</button>
    </div>
    <div id="mbody" class="mwrap"></div>
  </div>
</div>
<script>
// WHY THIS QUERIES THE LIVE API RATHER THAN CARRYING THE ROWS.
//
// Embedding every row was measured first: 15.5 MB in this page, or 30.5 MB as one file
// per table. Both put the same data in a second place, where it can go stale against the
// database it was copied from, and land tens of megabytes in git on every rebuild.
//
// Fetching from a sibling file does not work: opened from disk this document has an
// opaque origin, so fetch() at a file:// URL is refused as cross-origin and there is no
// server to add a header to. But /api/query is on https and answers with
// `access-control-allow-origin: *`, which an opaque origin is allowed to read. So the
// data comes from the same public endpoint anybody else would use.
//
// SORTING AND FILTERING HAPPEN HERE, NOT IN SQL, AND THAT IS A REAL LIMIT.
//
// TJ: "This is for people who dont know sql but want to do some basic review." So every
// column header carries a sort control and a value picker, and neither requires typing.
//
// They act on the ROWS THAT CAME BACK — at most 1,000, because that is the API's cap.
// Sorting a thousand rows client-side is not the same as sorting the table: for a table
// with more rows than that, you are sorting a slice. The header says so whenever the cap
// is hit, because a sort that silently means something narrower than it appears is
// exactly the kind of quietly-wrong answer this project keeps finding.
const API = (new URLSearchParams(location.search).get('api') || '{api_base}')
              .replace(/\/$/, '') + '/api/query';
const modal = document.getElementById('modal'), mt = document.getElementById('mt'),
      msql = document.getElementById('msql'), mbody = document.getElementById('mbody'),
      mmeta = document.getElementById('mmeta');

let DATA = [], COLS = [], SORT = {{col: null, dir: 1}}, FILTERS = {{}}, CAPPED = false;

function esc(s) {{
  return String(s).replace(/[&<>"]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]));
}}
function show(v) {{
  if (v === null) return '<span class="nul">NULL</span>';
  if (v === '') return '<span class="nul">empty</span>';
  return esc(v);
}}

function visible() {{
  let rows = DATA.filter(r => COLS.every(c => {{
    const f = FILTERS[c];
    if (!f) return true;
    if (f.text && !String(r[c] ?? '').toLowerCase().includes(f.text)) return false;
    if (f.only && !f.only.has(String(r[c] ?? ''))) return false;
    return true;
  }}));
  if (SORT.col) {{
    const c = SORT.col;
    rows = rows.slice().sort((a, b) => {{
      const x = a[c], y = b[c];
      if (x === null || x === undefined) return 1;   // nulls last, both directions
      if (y === null || y === undefined) return -1;
      if (typeof x === 'number' && typeof y === 'number') return (x - y) * SORT.dir;
      return String(x).localeCompare(String(y), undefined, {{numeric: true}}) * SORT.dir;
    }});
  }}
  return rows;
}}

function draw() {{
  const rows = visible();
  const head = COLS.map(c => {{
    const active = SORT.col === c ? (SORT.dir === 1 ? ' up' : ' down') : '';
    const on = FILTERS[c] ? ' on' : '';
    return '<th><div class="thh"><button class="srt' + active + '" data-c="' + esc(c) +
      '" title="sort">' + esc(c) + '<i></i></button>' +
      '<button class="flt' + on + '" data-c="' + esc(c) + '" title="filter">&#9662;</button>' +
      '</div></th>';
  }}).join('');
  const body = rows.map(r => '<tr>' + COLS.map(c => {{
    const v = r[c];
    return '<td' + (typeof v === 'number' ? ' class="num"' : '') + '>' + show(v) + '</td>';
  }}).join('') + '</tr>').join('');
  mbody.innerHTML = '<table class="samp"><thead><tr>' + head + '</tr></thead><tbody>' +
    body + '</tbody></table>';
  const nf = Object.keys(FILTERS).length;
  mmeta.textContent = rows.length.toLocaleString() + ' of ' + DATA.length.toLocaleString() +
    (nf ? ' · ' + nf + ' filter' + (nf > 1 ? 's' : '') : '') +
    (CAPPED ? ' · capped at 1,000 by the API — sorting a slice, not the table' : '');
}}

function panel(col, btn) {{
  document.querySelectorAll('.fpanel').forEach(p => p.remove());
  const vals = new Map();
  for (const r of DATA) {{
    const k = String(r[col] ?? '');
    vals.set(k, (vals.get(k) || 0) + 1);
  }}
  const cur = FILTERS[col] || {{}};
  const list = [...vals.entries()].sort((a, b) => b[1] - a[1]);
  const p = document.createElement('div');
  p.className = 'fpanel';
  p.innerHTML =
    '<input class="fq" placeholder="contains…" value="' + esc(cur.text || '') + '">' +
    '<div class="fvals">' + list.slice(0, 400).map(([v, n]) =>
      '<label><input type="checkbox" value="' + esc(v) + '"' +
      (cur.only && cur.only.has(v) ? ' checked' : '') + '>' +
      '<span>' + (v === '' ? '<i class="nul">empty</i>' : esc(v)) + '</span>' +
      '<b>' + n.toLocaleString() + '</b></label>').join('') +
      (list.length > 400 ? '<p class="fmore">' + (list.length - 400).toLocaleString() +
        ' more values — use “contains” to narrow</p>' : '') +
    '</div><div class="fbar"><button class="fclear">clear</button>' +
    '<button class="fdone">apply</button></div>';
  btn.parentElement.appendChild(p);

  const apply = () => {{
    const text = p.querySelector('.fq').value.trim().toLowerCase();
    const only = new Set([...p.querySelectorAll('.fvals input:checked')].map(i => i.value));
    if (text || only.size) FILTERS[col] = {{text: text || null, only: only.size ? only : null}};
    else delete FILTERS[col];
    p.remove();
    draw();
  }};
  p.querySelector('.fdone').onclick = apply;
  p.querySelector('.fq').onkeydown = e => {{ if (e.key === 'Enter') apply(); }};
  p.querySelector('.fclear').onclick = () => {{ delete FILTERS[col]; p.remove(); draw(); }};
  p.querySelector('.fq').focus();
}}

async function run(sql) {{
  mbody.innerHTML = '<p class="mnote">querying…</p>';
  mmeta.textContent = '';
  DATA = []; COLS = []; SORT = {{col: null, dir: 1}}; FILTERS = {{}}; CAPPED = false;
  let r, j;
  try {{
    r = await fetch(API + '?sql=' + encodeURIComponent(sql));
    j = await r.json();
  }} catch (e) {{
    // The honest failure. This page works offline; the button does not.
    mbody.innerHTML = '<p class="mnote">Could not reach the API — this needs an internet ' +
      'connection, because the rows are not in this file. ' + esc(e.message) + '</p>';
    return;
  }}
  if (!r.ok || j.error) {{
    mbody.innerHTML = '<p class="mnote">' + esc(j.error || ('HTTP ' + r.status)) +
      (j.suggestion ? '<br>' + esc(j.suggestion) : '') + '</p>';
    return;
  }}
  const rows = j.rows || j.results || [];
  if (!rows.length) {{ mbody.innerHTML = '<p class="mnote">No rows.</p>'; return; }}
  DATA = rows; COLS = Object.keys(rows[0]); CAPPED = rows.length === 1000;
  draw();
  // rowsRead is the billable quantity and is NOT the number of rows returned — a GROUP BY
  // returning 14 rows can read 9,330. It is appended rather than replacing the counts.
  if (j.rowsRead != null) mmeta.textContent += ' · ' + j.rowsRead.toLocaleString() + ' read';
}}

document.addEventListener('click', e => {{
  const b = e.target.closest('button.open');
  if (b) {{
    mt.textContent = b.dataset.t;
    msql.value = b.dataset.q || ('SELECT * FROM ' + b.dataset.t + ' LIMIT 1000');
    modal.hidden = false;
    run(msql.value);
    return;
  }}
  const srt = e.target.closest('button.srt');
  if (srt) {{
    const c = srt.dataset.c;
    SORT = {{col: c, dir: SORT.col === c ? -SORT.dir : 1}};
    draw();
    return;
  }}
  const flt = e.target.closest('button.flt');
  if (flt) {{ panel(flt.dataset.c, flt); return; }}
  if (!e.target.closest('.fpanel')) document.querySelectorAll('.fpanel').forEach(p => p.remove());
  if (e.target.id === 'mrun') run(msql.value);
  if (e.target.id === 'mx' || e.target === modal) modal.hidden = true;
}});
msql.addEventListener('keydown', e => {{ if (e.key === 'Enter') run(msql.value); }});
document.addEventListener('keydown', e => {{ if (e.key === 'Escape') {{
  if (document.querySelector('.fpanel')) document.querySelectorAll('.fpanel').forEach(p => p.remove());
  else modal.hidden = true;
}} }});
</script>

<p class="gen">Generated by <code>scripts/build_schema_page.py</code> from the live
database on {gen}. Do not edit — run the script. The CSVs in <code>sources/data/</code>
are the source of truth; this database is a derived read model, rebuilt from scratch on
every run.</p>
</div>
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    fresh = render(db())
    rel = os.path.relpath(OUT, ROOT)
    if args.check:
        if not os.path.exists(OUT):
            raise SystemExit(f'{rel} does not exist. Run without --check.')
        if open(OUT, encoding='utf-8').read() != fresh:
            raise SystemExit(f'STALE: {rel} no longer reproduces.\n'
                             f'  Run: python3 scripts/build_schema_page.py')
        print(f'ok: {rel} still reproduces')
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(fresh)
    print(f'wrote {rel} ({len(fresh):,} bytes)')


if __name__ == '__main__':
    main()
