#!/usr/bin/env python3
"""The documents a generated page actually rests on — TRACED, not declared.

Used by `build_money_flow.py` and `build_town_flow.py` to put a source list at the foot
of each diagram.

WHY THIS TRACES RATHER THAN LISTS

The obvious way to do this is a list at the top of each script naming its sources. That
list is wrong the first time a query changes and nothing fails — it is rule 2's problem
(a fact typed into prose) wearing rule 13's clothes (a derived thing quoted as observed),
and this project has shipped both.

So the page does not claim its sources. It **records** them: SQLite's authorizer fires on
every table read, so wrapping a render in `tracing()` returns the set of tables the page
genuinely touched, including through views — `v_revenue_classified` reports its own base
tables, which is what makes the trace trustworthy rather than a restatement of the FROM
clause somebody happened to write.

From the tables, the documents follow the same way: `ledger_snapshot` and `fund_activity`
carry `doc_id` on every row, so the documents are read out of the data rather than named.

WHERE IT IS STILL DECLARED, AND WHY THAT IS MARKED

Two tables carry no `doc_id` — `account` and `fund` are the chart of accounts, built by
`load_munis()` from the same MUNIS reports that produce `ledger_snapshot`, as a dimension
rather than as facts. There is nothing in a row of either to trace, so their origin is
DECLARED below and rendered with that word visible on the page. A reader can then tell
which half of the list was observed and which half somebody asserted, which is the whole
of rule 13 in one column.
"""

import hashlib
import os
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Tables with no `doc_id` to read. Rendered as `declared` on the page, never as traced.
TABLE_ORIGIN = {
    'account': ('the chart of accounts, built by load_munis() from the same MUNIS '
                'reports as the ledger below', 'ledger_snapshot'),
    'fund': ('the fund register, built by load_munis() from the same MUNIS reports as '
             'the ledger below', 'ledger_snapshot'),
}

# A table whose figures name a source in a column rather than a doc_id. The value is a
# loose reference — a filename the extractor recorded — so it is shown as given and not
# resolved to an address it may not have.
SOURCE_COLUMN = {'athletics_history': 'source'}


class tracing:
    """Context manager: `with tracing(conn) as seen:` collects every table read."""

    def __init__(self, conn):
        self.conn, self.seen = conn, set()

    def __enter__(self):
        def auth(action, arg1, arg2, dbname, trigger):
            if action == sqlite3.SQLITE_READ and arg1:
                self.seen.add(arg1)
            return sqlite3.SQLITE_OK
        self.conn.set_authorizer(auth)
        return self.seen

    def __exit__(self, *exc):
        self.conn.set_authorizer(None)
        return False


def _sha(path):
    full = os.path.join(ROOT, path)
    if not os.path.exists(full):
        return None, None
    h = hashlib.sha256()
    with open(full, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest(), os.path.getsize(full)


def collect(conn, tables, extra_files=()):
    """Resolve traced tables to the documents behind them.

    Returns a list of dicts, each with `how` = 'traced' or 'declared', so the caller
    cannot render the two indistinguishably.
    """
    real = sorted(t for t in tables
                  if not t.startswith('sqlite_') and not t.startswith('v_'))
    docs, seen_paths = [], set()

    def add(path, how, via, label=None):
        if path in seen_paths:
            for d in docs:                       # one document, several tables
                if d['path'] != path:
                    continue
                if via not in d['via']:
                    d['via'].append(via)
                # A document reached by ANY traced route IS traced. `account` sorts before
                # `ledger_snapshot`, so without this the declared route claimed every
                # ledger file first and the page reported eleven traced documents as
                # hand-named -- understating exactly the thing this column exists to say.
                if how == 'traced' and d['how'] != 'traced':
                    d['how'], d['label'] = 'traced', None
            return
        seen_paths.add(path)
        row = conn.execute(
            'SELECT url, local_sha256 FROM document WHERE doc_id = ?', (path,)).fetchone()
        rel = path[len('sources/'):] if path.startswith('sources/') else path
        sha, size = _sha(path)
        docs.append(dict(
            path=path, rel=rel, how=how, via=[via], label=label,
            url=('/docs/' + rel) if os.path.exists(os.path.join(ROOT, path)) else None,
            upstream=(row['url'] if row else None),
            sha=(row['local_sha256'] if row and row['local_sha256'] else sha),
            bytes=size))

    # Traced routes first: a declared route must never be the reason a document
    # is on the page if a traced one also reaches it.
    for t in sorted(real, key=lambda t: t in TABLE_ORIGIN):
        cols = {d[1] for d in conn.execute('PRAGMA table_info("%s")' % t)}
        if 'doc_id' in cols:
            for (d,) in conn.execute('SELECT DISTINCT doc_id FROM "%s" '
                                     'WHERE doc_id IS NOT NULL AND doc_id != ""' % t):
                add(d, 'traced', t)
        elif t in SOURCE_COLUMN:
            col = SOURCE_COLUMN[t]
            for (d,) in conn.execute('SELECT DISTINCT "%s" FROM "%s" WHERE "%s" != ""'
                                     % (col, t, col)):
                add(d, 'traced', t)
        elif t in TABLE_ORIGIN:
            note, like = TABLE_ORIGIN[t]
            for (d,) in conn.execute('SELECT DISTINCT doc_id FROM "%s" '
                                     'WHERE doc_id IS NOT NULL AND doc_id != ""' % like):
                add(d, 'declared', t, label=note)
        else:
            # A table loaded from one of our own CSVs. Rule 12: a spreadsheet we built is
            # a source too, and it gets published like any other.
            csv = 'sources/data/%s.csv' % t.replace('_', '-')
            if os.path.exists(os.path.join(ROOT, csv)):
                add(csv, 'traced', t)

    for f in extra_files:
        add(f, 'traced', 'read directly by the script')

    if not docs:
        raise SystemExit(
            'page_sources: traced %d table(s) and resolved NO documents.\n'
            '  A source list that matches nothing looks exactly like a page with no '
            'sources. Refusing to write it.' % len(real))
    docs.sort(key=lambda d: (d['how'] != 'traced', d['path']))
    return docs


def footer_html(docs, esc):
    """The source list, as a <section> matching the diagrams' own styling."""
    n_traced = sum(1 for d in docs if d['how'] == 'traced')
    o = ['<section class="stage"><h2>Where this page comes from</h2>',
         '<p class="cap">Every document behind the figures above. This list is '
         '<strong>recorded while the page is built</strong> — SQLite reports each table '
         'the render actually reads, and the documents come off <code>doc_id</code> on '
         'the rows themselves, so it cannot drift away from what the page does. ',
         (f'All {len(docs)} were traced that way.</p>' if n_traced == len(docs) else
          f'{n_traced} of {len(docs)} were traced that way; the other '
          f'{len(docs) - n_traced} are marked <em>declared</em> — they carry no document '
          'reference of their own and are named by hand, which is the part to trust '
          'least.</p>'),
         '<div class="scroll"><table><tr><th>document</th><th>feeds</th>'
         '<th>how we know</th><th>sha256</th></tr>']
    for d in docs:
        name = esc(d['rel'])
        cell = (f'<a href="https://lunenburgbudgetproject.org{esc(d["url"])}">{name}</a>'
                if d['url'] else name)
        if d['upstream']:
            cell += (f'<br><span class="sub">publisher: '
                     f'<a href="{esc(d["upstream"])}">{esc(d["upstream"][:68])}</a></span>')
        if d['label']:
            cell += f'<br><span class="sub">{esc(d["label"])}</span>'
        o.append(
            '<tr><td>%s</td><td class="ty">%s</td><td>%s</td><td class="ty">%s</td></tr>'
            % (cell, esc(', '.join(sorted(d['via']))), esc(d['how']),
               esc((d['sha'] or '')[:16]) + ('…' if d['sha'] else 'not on disk')))
    o.append('</table></div>')
    o.append('<p class="cap">Addresses resolve on the published site; the archive is '
             'also mirrored on GitHub. A sha256 is here because a file can be replaced '
             'at the same URL — see rule 12.</p></section>')
    return '\n'.join(o)
