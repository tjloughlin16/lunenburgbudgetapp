#!/usr/bin/env python3
"""Extract text from the agenda/minutes archive into a parallel `text/` tree.

Kept separate from the PDFs so the two can be versioned differently: the text is small
and greppable and belongs in git, the 400MB of scans does not. Anything with no text
layer is listed at the end — those are scans, and need scripts/ocr_pdf.swift.
"""
import pathlib, sys, warnings
warnings.filterwarnings('ignore')
from pypdf import PdfReader

ROOT = pathlib.Path(__file__).resolve().parent.parent / 'sources' / 'minutes'
TEXT = ROOT / 'text'
scanned, done, failed = [], 0, []

for pdf in sorted(ROOT.rglob('*.pdf')):
    out = TEXT / pdf.relative_to(ROOT).with_suffix('.txt')
    if out.exists() and out.stat().st_mtime > pdf.stat().st_mtime:
        continue
    try:
        r = PdfReader(str(pdf))
        pages = [(p.extract_text() or '') for p in r.pages]
    except Exception as e:
        failed.append(f'{pdf.relative_to(ROOT)}: {e}')
        continue
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('\n'.join(f'===PAGE {i+1}===\n{t}' for i, t in enumerate(pages)))
    done += 1
    # A page averaging under ~200 characters is a scan, not a document.
    if sum(len(t) for t in pages) < 200 * max(1, len(pages)):
        scanned.append(str(pdf.relative_to(ROOT)))

print(f'extracted {done}')
if failed:
    print(f'\nunreadable ({len(failed)}):'); [print('  ', f) for f in failed[:10]]
if scanned:
    print(f'\nno text layer — needs OCR ({len(scanned)}):')
    for s in scanned[:15]: print('  ', s)
    (TEXT / '_needs-ocr.txt').write_text('\n'.join(scanned) + '\n')
    print(f'  full list -> {TEXT / "_needs-ocr.txt"}')
