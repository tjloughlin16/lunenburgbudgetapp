"""Render an analysis document to PDF, for reading away from a screen.

    python3 scripts/build_analysis_pdf.py fy26-closeout
    python3 scripts/build_analysis_pdf.py --all

Writes `fy28/public/docs/analyses/<name>.pdf` beside the Markdown the site already
publishes, so the address is predictable and the PDF is a published source like any other.

No new dependency. Markdown is converted here -- only the subset these documents actually
use -- and Chrome, which the prerender step already requires, prints the result. Pandoc
would be better at Markdown and would be a dependency a resident has to install before
they can reproduce anything, which is the trade this project keeps making the other way.

The PDF carries the same provenance the document does: what produced it, when, and which
verifier asserts its figures. A printed page is the copy most likely to be quoted from
after the numbers have moved, so it says on its face how to check whether they have.
"""
import argparse
import html
import os
import re
import subprocess
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources', 'analyses')
OUT = os.path.join(ROOT, 'fy28', 'public', 'docs', 'analyses')

CHROME = next((p for p in (
    os.environ.get('CHROME'),
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/usr/bin/google-chrome',
) if p and os.path.exists(p)), None)

CSS = """
@page { size: Letter; margin: 20mm 16mm 18mm 16mm; }
* { box-sizing: border-box; }
body { font: 10.5pt/1.55 Georgia, 'Times New Roman', serif; color: #16130f; margin: 0; }
h1 { font-size: 22pt; line-height: 1.2; margin: 0 0 4pt; letter-spacing: -0.01em; }
h2 { font-size: 14pt; margin: 22pt 0 6pt; padding-top: 10pt;
     border-top: 1.5px solid #16130f; page-break-after: avoid; }
h3 { font-size: 10.5pt; margin: 14pt 0 4pt; text-transform: uppercase;
     letter-spacing: 0.08em; color: #6b5f4f; page-break-after: avoid; }
p, li { margin: 0 0 8pt; }
blockquote { margin: 8pt 0 8pt 12pt; padding-left: 10pt; border-left: 2px solid #c9bda9;
             color: #4a4034; font-style: italic; }
table { border-collapse: collapse; width: 100%; margin: 8pt 0 12pt;
        font-size: 9pt; page-break-inside: avoid; }
th { text-align: left; border-bottom: 1px solid #16130f; padding: 3pt 5pt;
     font-family: -apple-system, Helvetica, sans-serif; font-size: 8pt;
     text-transform: uppercase; letter-spacing: 0.05em; }
td { border-bottom: 1px solid #e5ded2; padding: 3pt 5pt; vertical-align: top; }
td.r, th.r { text-align: right; font-variant-numeric: tabular-nums; }
code { font: 9pt 'SF Mono', Menlo, Consolas, monospace; background: #f4f0e8;
       padding: 0 2px; border-radius: 2px; }
pre { font: 8.5pt/1.4 'SF Mono', Menlo, Consolas, monospace; background: #f4f0e8;
      padding: 7pt 9pt; border-radius: 3px; overflow-x: hidden;
      white-space: pre-wrap; word-break: break-word; page-break-inside: avoid; }
hr { border: 0; border-top: 1px solid #d8cfc0; margin: 16pt 0; }
strong { font-weight: 700; }
.masthead { border-bottom: 2.5px solid #16130f; padding-bottom: 8pt; margin-bottom: 14pt; }
.kicker { font-family: -apple-system, Helvetica, sans-serif; font-size: 8pt;
          text-transform: uppercase; letter-spacing: 0.14em; color: #8a7a63; }
.stamp { font-family: -apple-system, Helvetica, sans-serif; font-size: 7.5pt;
         color: #6b5f4f; line-height: 1.5; margin-top: 6pt; }
.stamp b { color: #16130f; }
"""


def inline(t):
    """Bold, italic, code and links. Escaped first, so a stray < cannot inject markup."""
    t = html.escape(t)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)', r'<em>\1</em>', t)
    t = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1', t)          # links are noise in print
    return t


def to_html(md, title, stamp):
    out, i, lines = [], 0, md.split('\n')
    while i < len(lines):
        ln = lines[i]

        if ln.startswith('    ') and ln.strip():             # indented code block
            block = []
            while i < len(lines) and (lines[i].startswith('    ') or not lines[i].strip()):
                block.append(lines[i][4:])
                i += 1
            while block and not block[-1].strip():
                block.pop()
            out.append('<pre>%s</pre>' % html.escape('\n'.join(block)))
            continue

        if ln.startswith('|'):                                # table
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                rows.append(lines[i])
                i += 1
            cells = [[c.strip() for c in r.strip().strip('|').split('|')] for r in rows]
            align = []
            body = cells
            if len(cells) > 1 and all(set(c) <= set('-: ') for c in cells[1]):
                align = ['r' if c.endswith(':') else '' for c in cells[1]]
                body = [cells[0]] + cells[2:]
                head = True
            else:
                head = False
            t = ['<table>']
            for n, row in enumerate(body):
                tag = 'th' if head and n == 0 else 'td'
                t.append('<tr>' + ''.join(
                    '<%s class="%s">%s</%s>' % (tag, (align[j] if j < len(align) else ''),
                                                inline(c), tag)
                    for j, c in enumerate(row)) + '</tr>')
            t.append('</table>')
            out.append('\n'.join(t))
            continue

        if ln.startswith('> '):                               # blockquote
            block = []
            while i < len(lines) and lines[i].startswith('>'):
                block.append(lines[i].lstrip('>').strip())
                i += 1
            out.append('<blockquote>%s</blockquote>' % inline(' '.join(block)))
            continue

        if re.match(r'^\s*[-*] ', ln) or re.match(r'^\s*\d+\. ', ln):
            tag = 'ul' if re.match(r'^\s*[-*] ', ln) else 'ol'
            items = []
            while i < len(lines) and (re.match(r'^\s*[-*] ', lines[i])
                                      or re.match(r'^\s*\d+\. ', lines[i])
                                      or (lines[i].startswith('   ') and lines[i].strip())):
                if re.match(r'^\s*([-*]|\d+\.) ', lines[i]):
                    items.append(re.sub(r'^\s*([-*]|\d+\.) ', '', lines[i]))
                else:
                    items[-1] += ' ' + lines[i].strip()
                i += 1
            out.append('<%s>%s</%s>' % (
                tag, ''.join('<li>%s</li>' % inline(x) for x in items), tag))
            continue

        m = re.match(r'^(#{1,4}) (.+)', ln)
        if m:
            lvl = len(m.group(1))
            out.append('<h%d>%s</h%d>' % (lvl, inline(m.group(2)), lvl))
            i += 1
            continue

        if ln.strip() in ('---', '***'):
            out.append('<hr>')
            i += 1
            continue

        if ln.strip():
            para = []
            while i < len(lines) and lines[i].strip() and not re.match(
                    r'^(#{1,4} |\||> |---$|\s*[-*] |\s*\d+\. |    )', lines[i]):
                para.append(lines[i].strip())
                i += 1
            out.append('<p>%s</p>' % inline(' '.join(para)))
            continue
        i += 1

    return ('<!doctype html><meta charset="utf-8"><title>%s</title><style>%s</style>'
            '<div class="masthead"><div class="kicker">Lunenburg Budget Project</div>'
            '%s<div class="stamp">%s</div></div>%s'
            % (html.escape(title), CSS, out[0] if out and out[0].startswith('<h1')
               else '<h1>%s</h1>' % html.escape(title), stamp,
               '\n'.join(out[1:] if out and out[0].startswith('<h1') else out)))


def build(name):
    md_path = os.path.join(SRC, name + '.md')
    if not os.path.exists(md_path):
        print('no such analysis: %s' % name)
        return 1
    md = open(md_path, encoding='utf-8').read()
    title = md.split('\n', 1)[0].lstrip('# ').strip()

    verifier = os.path.join(ROOT, 'scripts', 'verify_%s.py' % name.replace('-', '_'))
    stamp = (
        'Generated %s from <b>sources/analyses/%s.md</b>. '
        'Every figure is recomputed from <b>sources/data/lunenburg.db</b> by '
        '<b>%s</b>. '
        'A printed page outlives the numbers on it: re-run that script before quoting '
        'anything here.'
        % (date.today().isoformat(), name,
           'scripts/' + os.path.basename(verifier) if os.path.exists(verifier)
           else 'no verifier — treat every figure as unchecked')
    )

    os.makedirs(OUT, exist_ok=True)
    tmp = os.path.join(OUT, name + '.print.html')
    with open(tmp, 'w', encoding='utf-8') as fh:
        fh.write(to_html(md, title, stamp))

    if not CHROME:
        print('no Chrome found; wrote %s only' % os.path.relpath(tmp, ROOT))
        return 1
    pdf = os.path.join(OUT, name + '.pdf')
    subprocess.run([CHROME, '--headless', '--disable-gpu', '--no-pdf-header-footer',
                    '--print-to-pdf=' + pdf, '--virtual-time-budget=4000',
                    'file://' + tmp], check=True, capture_output=True)
    os.remove(tmp)
    print('wrote %s  (%.0f KB)' % (os.path.relpath(pdf, ROOT),
                                   os.path.getsize(pdf) / 1024))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('name', nargs='?')
    ap.add_argument('--all', action='store_true')
    a = ap.parse_args()
    if a.all:
        names = [f[:-3] for f in sorted(os.listdir(SRC)) if f.endswith('.md')]
    elif a.name:
        names = [a.name.removesuffix('.md')]
    else:
        ap.error('give an analysis name, or --all')
    return max(build(n) for n in names)


if __name__ == '__main__':
    sys.exit(main())
