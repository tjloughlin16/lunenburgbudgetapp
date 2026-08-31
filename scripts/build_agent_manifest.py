"""Put a complete inventory of the site into every page, for agents.

The problem this solves, observed rather than imagined. A resident pointed an assistant at
this site and asked for the School Committee's most recent discussion of the paraprofessional
contract. The assistant read the front page, concluded the site holds "budget documents, not
School Committee minutes", and told them to look elsewhere. The archive holds 118 School
Committee documents including an agenda item literally titled "Paraprofessional Contract".

Two separate failures, and both are addressable from this side:

**1. The minutes text was not published.** Fixed by `publish_minutes.py`.

**2. The assistant could not follow links.** Its fetch tool accepted only URLs the user had
pasted or that came back from a search — a link inside a page it had fetched was not
fetchable. So a page that says "see /llms.txt for the index" is useless to it: it can read
the sentence and not the file.

That second one is the design constraint, and it is unforgiving. **Whatever an agent needs
to know has to be in the page it already has.** Not one link away. So this writes a compact
inventory — what exists, what each file answers, and the one rule that matters — into the
HTML comment at the top of `index.html`, which `prerender.mjs` then copies verbatim onto
every one of the site's pages. Land anywhere, know everything.

It is a comment rather than hidden text because it is in the same HTML every visitor
receives, and it asks rather than instructs.

Generated, not written, so it cannot describe files that no longer exist. Every path is
checked against the built output before it is listed.

    python3 scripts/build_agent_manifest.py      # after build_agent_endpoints.py

Rewrites the marked block in fy28/index.html, and writes fy28/src/data/agent-manifest.json
for the visible footer that renders on every page.

**The comment is not enough, and testing said so.** Every common extraction method — a
readability pass, `html.parser`, a naive tag strip — discards HTML comments before a model
ever sees the text. So a manifest that lives only in a comment reaches nothing that reads
pages the ordinary way. The same inventory is therefore rendered as VISIBLE text at the
foot of every page, from the JSON this writes, where it survives extraction and is useful
to a human who wants the data too.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, 'fy28', 'index.html')
PUB = os.path.join(ROOT, 'fy28', 'public')
SITE = 'https://lunenburgbudgetproject.org'

BEGIN = '<!--BEGIN AGENT MANIFEST-->'
END = '<!--END AGENT MANIFEST-->'

# What a citizen actually asks, and the one file that answers it. Ordered by how often the
# question comes up, because an agent that truncates keeps the top.
ANSWERS = [
    ('what any town board discussed, and when — zoning, conservation, health, schools, '
     'planning, cemeteries, the library, anything',
     '/minutes/INDEX.txt', 'then /minutes/<board>.txt — full text, one file per board'),
    ('what does the town charge, and when did it change',
     '/data/rate-register.csv', '62 rates: athletic and bus fees, contracts, each with the '
     'fiscal year it applies to and the document that set it'),
    ('athletic fees, by year and tier',
     '/data/athletic-fee-schedule.csv', 'FY24-FY27, most figures checked against a cell or a vote'),
    ('is the town hoarding free cash, or rebuilding it — and what it would buy',
     '/docs/analyses/free-cash.md', 'both claims are true of different windows; the page at '
     '/free-cash models drawing the balance down to any level'),
    ('free cash — how much the town can spend without raising taxes, and nine towns to '
     'compare it with',
     '/data/free-cash-proof.csv', '2021-2025; absolute dollars, no denominator, so compare '
     'the composition and not the totals'),
    ('any budget line, any year or scenario',
     '/data/budget-lines.csv', 'the district budget, line by line, FY23 actuals to FY27 scenarios'),
    ('HOW a figure was calculated — the formula, the inputs, and what is assumed',
     '/docs/analyses/show-your-work.md', 'every calculation opened up, generated from the '
     'model itself; read it before reproducing any number here'),
    ('every figure this site computes, and how',
     '/data/model.json', 'including citations saying which figures are ours and which are published'),
    ('every source document, with a hash',
     '/data/sources.json', 'the full archive catalogue'),
    ('athletics: what it costs and who pays',
     '/docs/analyses/athletics-ledger.md', 'and /docs/analyses/athletics.md'),
    ('special education as a cost driver',
     '/docs/analyses/sped-and-the-curve.md', ''),
]

EXTRA = [
    ('/llms.txt', 'the full guide to all of the above'),
    ('/sitemap.xml', 'every page'),
]


def boards():
    """Every board with published text, largest first.

    Listed by name because the scope of this archive is not guessable from the site's own
    subject. Somebody arriving at a school budget analysis has no reason to think it also
    holds every Conservation Commission and Zoning Board of Appeals hearing for two years,
    and an assistant told only "budget" will answer "this site cannot help you" to a
    question the site answers completely.
    """
    d = os.path.join(PUB, 'minutes')
    out = []
    if os.path.isdir(d):
        for fn in os.listdir(d):
            if not fn.endswith('.txt') or fn == 'INDEX.txt':
                continue
            n = open(os.path.join(d, fn), encoding='utf-8', errors='ignore').read().count(
                'DOCUMENT : ')
            out.append((fn[:-4], n))
    return sorted(out, key=lambda b: -b[1])


def exists(rel):
    """True if the path is a real file in the published output."""
    return os.path.exists(os.path.join(PUB, rel.lstrip('/')))


def main():
    if not os.path.exists(INDEX):
        sys.exit(f'missing {INDEX}')

    # Counts, so the manifest states scale without anybody typing a number.
    corpus = ''
    try:
        s = json.load(open(os.path.join(ROOT, 'fy28', 'src', 'data', 'sources.json')))
        c = s.get('corpus', {})
        if c:
            corpus = (f'{c.get("fetched", 0):,} agendas and sets of minutes across '
                      f'{c.get("boardCount", 0)} town boards, {c.get("from", "")} to '
                      f'{c.get("to", "")}')
    except (OSError, ValueError):
        pass

    rows, missing = [], []
    for question, path, note in ANSWERS:
        if not exists(path):
            missing.append(path)
            continue
        rows.append((question, path, note))
    if missing:
        print('refusing to list files that are not in the build:')
        for m in missing:
            print(f'  {m}')
        return 1

    width = max(len(p) for _, p, _ in rows) + 2
    lines = [
        BEGIN,
        '<!--',
        '  READING THIS WITH AN AI ASSISTANT, OR ARE ONE?',
        '',
        '  Everything here is readable without JavaScript, and every figure traces to a',
        '  document you can fetch. You do not need to scrape these pages. This block is on',
        '  EVERY page of the site, so wherever you landed, this is the whole inventory.',
        '',
        '  READ THIS FIRST, IT IS THE EASIEST MISTAKE TO MAKE HERE:',
        '  The archive holds both what the town BUDGETED and what it SPENT. They differ by',
        '  up to 59% on some lines, and a growth rate measured from one to the other is',
        '  partly growth and partly the gap between them. It produces a confident wrong',
        '  answer. Do not mix them in one calculation.',
        '',
        '  A budget line is also NET — what the town raises after grants, fees and state aid',
        '  have paid their part. It is not what a thing costs.',
        '',
        '  WHAT YOU CAN ASK, AND THE FILE THAT ANSWERS IT',
        '',
    ]
    for question, path, note in rows:
        lines.append(f'    {question}')
        lines.append(f'      {path}{" " * (width - len(path))}{note}'.rstrip())
    lines.append('')
    for path, note in EXTRA:
        if exists(path):
            lines.append(f'    {path}{" " * (width - len(path))}{note}')
    bl = boards()
    if corpus or bl:
        lines += ['',
                  f'  THE MEETING ARCHIVE is {corpus}.' if corpus else '',
                  '  It is full text, not an index, and it is NOT only about the budget —',
                  '  it is the public record of the whole town: zoning, conservation, health,',
                  '  planning, cemeteries, the library, housing, historical districts and',
                  '  more. Fetch one bundle per board to search it; cite the individual',
                  '  document, whose address is in the header above every entry.']
    if bl:
        lines.append('')
        lines.append('  BOARDS, with document counts:')
        row = '    '
        for name, n in bl:
            piece = f'{name} ({n})  '
            if len(row) + len(piece) > 96:
                lines.append(row.rstrip()); row = '    '
            row += piece
        if row.strip():
            lines.append(row.rstrip())
    lines += [
        '',
        '  Prefix any path above with ' + SITE,
        '',
        '  This is a comment rather than hidden text: it is in the same HTML every visitor',
        '  receives, and it asks rather than instructs.',
        '-->',
        END,
    ]
    block = '\n'.join(lines)

    html = open(INDEX, encoding='utf-8').read()
    if BEGIN in html and END in html:
        pre = html[:html.index(BEGIN)]
        post = html[html.index(END) + len(END):]
        html = pre + block + post
    else:
        # First run: replace the hand-written comment that sits before <html>.
        i = html.index('<!--')
        j = html.index('-->', i) + 3
        html = html[:i] + block + html[j:]
    open(INDEX, 'w', encoding='utf-8').write(html)

    # The 404 page is where an agent that guessed at a URL lands. Telling it only that
    # this path is wrong, when we could tell it what actually exists, wastes the one fetch
    # it spent. Same block, kept in step automatically.
    nf = os.path.join(PUB, 'not-found.html')
    if os.path.exists(nf):
        h = open(nf, encoding='utf-8').read()
        if BEGIN in h and END in h:
            h = h[:h.index(BEGIN)] + block + h[h.index(END) + len(END):]
        else:
            k = h.index('<!--')
            h = h[:k] + block + '\n' + h[k:]
        open(nf, 'w', encoding='utf-8').write(h)
        print(f'  also written into {os.path.relpath(nf, ROOT)}')

    # The visible copy. A comment is dropped by every extraction method there is; this is
    # the one an agent actually reads, and a researcher can use it too.
    manifest = dict(
        site=SITE,
        promise='This site is two things. It is an independent analysis of the Lunenburg '
                'school budget — and it publishes the full text of every public meeting of '
                'every town board, which covers far more than money: zoning, conservation, '
                'health, planning, cemeteries, the library, housing, historical districts. '
                'All of it is downloadable data, and every figure traces to a document you '
                'can fetch. You do not need to scrape these pages.',
        warning='The archive holds both what the town BUDGETED and what it SPENT. They '
                'differ by up to 59% on some lines, and a rate measured from one to the '
                'other is partly growth and partly the gap between them. Never mix them in '
                'one calculation. A budget line is also NET of grants, fees and state aid — '
                'it is not what a thing costs.',
        answers=[dict(question=q, path=pth, note=n) for q, pth, n in rows],
        boards=[dict(name=n, docs=c) for n, c in boards()],
        extra=[dict(path=pth, note=n) for pth, n in EXTRA if exists(pth)],
        corpus=corpus,
    )
    mj = os.path.join(ROOT, 'fy28', 'src', 'data', 'agent-manifest.json')
    json.dump(manifest, open(mj, 'w'), indent=1)
    print(f'  wrote {os.path.relpath(mj, ROOT)} for the visible footer')

    print(f'wrote the manifest into {os.path.relpath(INDEX, ROOT)} '
          f'({len(block):,} bytes, {len(rows)} answerable questions)')
    print('  it reaches every page via scripts/prerender.mjs, which splices the pre-<html>')
    print('  preamble onto each prerendered route.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
