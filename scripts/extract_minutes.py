#!/usr/bin/env python3
"""Extract text from the agenda/minutes archive into a parallel `text/` tree.

Kept separate from the PDFs so the two can be versioned differently: the text is small
and greppable and belongs in git, the 400MB of scans does not. Anything with no text
layer is listed at the end — those are scans, and need scripts/ocr_pdf.swift.

**The town does not publish only PDFs.** This walked `*.pdf` and nothing else, which was
invisible for as long as the fetcher was also discarding everything that was not a PDF —
two halves of the same assumption, each hiding the other. 39 documents were published as
Word or Excel and were absent from the archive, and the search index over the archive
therefore answered "no result" for questions those documents answer. Every format the
town actually publishes is read here now.
"""
import pathlib, re, subprocess, sys, warnings, zipfile
warnings.filterwarnings('ignore')
from pypdf import PdfReader


def from_ooxml(path: pathlib.Path, part_prefix: str) -> str:
    """Text from a .docx or .xlsx, which are zips of XML. No dependency needed.

    Paragraph and row boundaries are preserved because a minutes document read as one
    unbroken string is greppable and unreadable, and somebody has to read the hit.
    """
    out = []
    with zipfile.ZipFile(path) as z:
        for name in sorted(n for n in z.namelist() if n.startswith(part_prefix)):
            if not name.endswith('.xml'):
                continue
            xml = z.read(name).decode('utf8', errors='replace')
            xml = re.sub(r'</w:p>|</a:p>|</row>', '\n', xml)
            xml = re.sub(r'<w:tab/>|</w:tc>', '\t', xml)
            out.append(re.sub(r'<[^>]+>', '', xml))
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(out))


def from_legacy_doc(path: pathlib.Path) -> str:
    """Pre-2007 Word. macOS ships `textutil`, which reads it; nothing in pip does well."""
    r = subprocess.run(['textutil', '-convert', 'txt', '-stdout', str(path)],
                       capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode('utf8', errors='replace').strip() or 'textutil failed')
    return r.stdout.decode('utf8', errors='replace')

ROOT = pathlib.Path(__file__).resolve().parent.parent / 'sources' / 'minutes'
TEXT = ROOT / 'text'
scanned, done, failed = [], 0, []

SOURCES = ('*.pdf', '*.docx', '*.doc', '*.xlsx')
by_format = {}

for src in sorted(p for pat in SOURCES for p in ROOT.rglob(pat)):
    if TEXT in src.parents:
        continue
    out = TEXT / src.relative_to(ROOT).with_suffix('.txt')
    if out.exists() and out.stat().st_mtime > src.stat().st_mtime:
        continue
    try:
        if src.suffix == '.pdf':
            pages = [(p.extract_text() or '') for p in PdfReader(str(src)).pages]
            body = '\n'.join(f'===PAGE {i+1}===\n{t}' for i, t in enumerate(pages))
        elif src.suffix == '.docx':
            pages = [from_ooxml(src, 'word/')]
            body = pages[0]
        elif src.suffix == '.xlsx':
            pages = [from_ooxml(src, 'xl/')]
            body = pages[0]
        else:
            pages = [from_legacy_doc(src)]
            body = pages[0]
    except Exception as e:
        failed.append(f'{src.relative_to(ROOT)}: {e}')
        continue
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body)
    done += 1
    by_format[src.suffix] = by_format.get(src.suffix, 0) + 1
    # A page averaging under ~200 characters is a scan, not a document. Only meaningful
    # for a PDF: a Word file that is short is short, not unscanned.
    if src.suffix == '.pdf' and sum(len(t) for t in pages) < 200 * max(1, len(pages)):
        scanned.append(str(src.relative_to(ROOT)))

print(f'extracted {done}' + (f'  ({", ".join(f"{k} {v}" for k, v in sorted(by_format.items()))})' if by_format else ''))
if failed:
    print(f'\nunreadable ({len(failed)}):'); [print('  ', f) for f in failed[:10]]
if scanned:
    print(f'\nno text layer — needs OCR ({len(scanned)}):')
    for s in scanned[:15]: print('  ', s)
    (TEXT / '_needs-ocr.txt').write_text('\n'.join(scanned) + '\n')
    print(f'  full list -> {TEXT / "_needs-ocr.txt"}')
