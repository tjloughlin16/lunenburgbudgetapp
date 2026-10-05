#!/usr/bin/env python3
"""IS THIS PDF A SCAN? Decided from what is ON each page, never from what an extractor got.

    import pdf_kind
    k = pdf_kind.classify(path_or_bytes)
    k['verdict']        # 'digital' | 'scan' | 'mixed' | 'digital, text unreadable'
                        #   | 'outlines' | 'blank'
    k['pages']          # one kind per page, and the evidence for it
    k['text']           # the best text either reader got, page-marked
    pdf_kind.needs_ocr(k)

    python3 scripts/pdf_kind.py FILE...

THE RULE. TJ, 4 October 2026, after the archive had assumed it again: *"just make sure they
aren't digital-first. you made that mistake before"* -- and then: *"put this as a rule
somewhere in the extraction/ingestion flow, to validate digital text vs assuming"*.

Four places in this repository decided a PDF was a scan because an extractor returned fewer
than about 200 characters: `fetch_town_docs.extract()`, `fetch_school_budget_docs`,
`extract_minutes.py` and `pii_screen.py`. That measures the EXTRACTOR. A digital PDF whose
fonts carry no Unicode mapping returns nothing; so does one whose words were converted to
outlines; so does a reader that failed to open it at all. Each of those was being reported
as "a scan", which is a claim about how the document was MADE -- and then OCR'd, with its
output labelled `ocr` as if a camera had been involved. CLAUDE.md 13c is the same mistake
pointed at a document: a pattern that did not match is not an absence.

So this classifies by STRUCTURE, a page at a time:

  text              the page has fonts and a reader got text from them
  text+image        fonts AND a picture -- a slide with a photo, or a scan carrying its own
                    OCR layer. Either way the text is there to read
  image             a picture and no usable text: a scan. The only kind OCR is FOR
  text, unreadable  the page has fonts and BOTH readers got nothing -- digital, not a scan.
                    OCR can rescue it, but the label must say why it was needed
  outlines          no fonts and no picture, but the page draws paths: words turned to
                    shapes, or a chart. Neither extraction nor OCR sees it until rasterised
  blank             nothing drawn at all

TWO READERS before a page is called unreadable: pypdf and pdfium. They fail on different
files, and a page one cannot read is often a page the other can.

And the counting instrument is checked too: the page count comes from the file, and a
document whose pages cannot be enumerated is an ERROR, never a verdict.
"""
import io
import logging
import re
import sys

logging.getLogger('pypdf').setLevel(logging.CRITICAL)
logging.getLogger('pdfminer').setLevel(logging.CRITICAL)

# Below this many characters a page that ALSO carries a picture is read as a scan with a
# stamp on it -- a Bates number, a date, a scanner's footer -- rather than as text.
STAMP_CHARS = 100


def walk_resources(res, seen, acc, depth=0):
    """Does this resource tree reach a font, or a raster image?

    Form XObjects nest, and the archive contains files whose only image sits two levels
    down inside one. A non-recursive check reported those as neither text nor picture.
    (Moved here from `build_minutes_searchable.diagnose()`, which now calls this.)
    """
    if depth > 6 or res is None:
        return
    try:
        res = res.get_object()
    except Exception:
        return
    if not hasattr(res, 'get'):
        return
    if res.get('/Font'):
        acc['font'] = True
    xobjects = res.get('/XObject')
    if not xobjects:
        return
    try:
        xobjects = xobjects.get_object()
    except Exception:
        return
    for key in list(xobjects.keys()):
        try:
            obj = xobjects[key].get_object()
        except Exception:
            continue
        subtype = obj.get('/Subtype')
        if subtype == '/Image':
            acc['image'] = True
            try:
                acc['img_px'] = max(acc.get('img_px', 0), int(obj.get('/Width') or 0),
                                    int(obj.get('/Height') or 0))
            except Exception:
                pass
        elif subtype == '/Form':
            if id(obj) in seen:
                continue
            seen.add(id(obj))
            walk_resources(obj.get('/Resources'), seen, acc, depth + 1)


def _chars(t):
    return len(re.sub(r'\s', '', t or ''))


def classify(src):
    """Per-page kinds, a document verdict, and the best text either reader got."""
    import pypdf
    import pypdfium2 as pdfium
    blob = src if isinstance(src, (bytes, bytearray)) else open(src, 'rb').read()
    reader = pypdf.PdfReader(io.BytesIO(blob))
    pages = list(reader.pages)
    doc = pdfium.PdfDocument(blob)
    if len(pages) != len(doc):
        raise ValueError(f'the two readers disagree on the page count: pypdf {len(pages)}, '
                         f'pdfium {len(doc)}')
    if not pages:
        raise ValueError('no pages could be enumerated -- a read failure, not a verdict')
    kinds, texts = [], []
    for i, page in enumerate(pages):
        acc = {'font': False, 'image': False}
        try:
            walk_resources(page.get_inherited('/Resources'), set(), acc)
        except Exception:
            pass
        try:
            a = page.extract_text() or ''
        except Exception:
            a = ''
        try:
            b = doc[i].get_textpage().get_text_range() or ''
        except Exception:
            b = ''
        text = a if _chars(a) >= _chars(b) else b
        n = _chars(text)
        if acc['image'] and n < STAMP_CHARS:
            kind = 'image'
        elif acc['font'] and n == 0:
            kind = 'text, unreadable'
        elif n and acc['image']:
            kind = 'text+image'
        elif n:
            kind = 'text'
        else:
            try:
                c = page.get_contents()
                data = c.get_data() if c is not None else b''
            except Exception:
                data = b''
            kind = ('outlines' if re.search(rb'(?<![A-Za-z])[ml](?![A-Za-z])', data)
                    else 'blank')
        # The resolution a picture page was stored at -- the largest image's long side over
        # the page's long side. FY2023 p25 of the annual reports is 93 dpi and its digits
        # are the same pixels whatever the render scale (`page-blocked.csv`); OCR returns
        # confident text from it that is wrong. A low number here is a reason to distrust
        # any reading of the page, including a clean screen.
        dpi = None
        if acc.get('img_px'):
            try:
                box = page.mediabox
                dpi = round(acc['img_px'] / max(float(box.width), float(box.height)) * 72)
            except Exception:
                dpi = None
        kinds.append({'page': i + 1, 'kind': kind, 'font': acc['font'],
                      'image': acc['image'], 'chars': n, 'dpi': dpi})
        texts.append(text)
    present = {k['kind'] for k in kinds} - {'blank'}
    if not present:
        verdict = 'blank'
    elif present <= {'text', 'text+image'}:
        verdict = 'digital'
    elif present == {'image'}:
        verdict = 'scan'
    elif present == {'text, unreadable'}:
        verdict = 'digital, text unreadable'
    elif present == {'outlines'}:
        verdict = 'outlines'
    else:
        verdict = 'mixed'
    return {'verdict': verdict, 'pages': kinds,
            'text': '\n'.join(f'===PAGE {i + 1}===\n{t}' for i, t in enumerate(texts))}


def needs_ocr(k):
    """True if any page holds words that only rasterising and OCR can reach."""
    return any(p['kind'] in ('image', 'text, unreadable', 'outlines') for p in k['pages'])


def ocr_label(k):
    """How the text was read, saying WHY OCR was needed rather than implying a camera."""
    return {'scan': 'ocr (scan)',
            'digital, text unreadable': 'ocr (digital, text layer unreadable)',
            'outlines': 'ocr (digital, text drawn as outlines)',
            'mixed': 'ocr (some pages scanned)'}.get(k['verdict'], 'ocr')


OCR_KINDS = ('image', 'text, unreadable', 'outlines')


def _split_pages(text):
    out, cur, buf = {}, None, []
    for line in text.splitlines():
        m = re.match(r'===PAGE (\d+)===$', line)
        if m:
            if cur is not None:
                out[cur] = '\n'.join(buf)
            cur, buf = int(m.group(1)), []
        else:
            buf.append(line)
    if cur is not None:
        out[cur] = '\n'.join(buf)
    return out


def extract_text(path, out_txt):
    """Write the text of a PDF, page-marked, and say how each part was read.

    A page whose text layer reads keeps it. Only the pages this module classifies as
    pictures, unreadable fonts or outlines are taken from OCR -- so a digital deck with a
    few screenshot slides keeps its own text and gains the screenshots, rather than either
    losing the screenshots (the old 200-character rule) or swapping good text for OCR.
    """
    import os
    import subprocess
    import tempfile
    k = classify(path)
    if not needs_ocr(k):
        open(out_txt, 'w').write(k['text'])
        return 'pdf text layer'
    # OCR ONLY THE PAGES THAT NEED IT. They are copied into a temporary PDF and its page
    # numbers mapped back: a 50-page deck with three screenshot slides used to be OCR'd in
    # full, fifty pages of Vision to keep three.
    import pypdf
    want = [p['page'] for p in k['pages'] if p['kind'] in OCR_KINDS]
    with tempfile.TemporaryDirectory() as d:
        sub = os.path.join(d, 'pages.pdf')
        w = pypdf.PdfWriter()
        src = pypdf.PdfReader(path)
        for n in want:
            w.add_page(src.pages[n - 1])
        with open(sub, 'wb') as fh:
            w.write(fh)
        tmp = os.path.join(d, 'ocr.txt')
        r = subprocess.run(['swift', os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                  'ocr_pdf.swift'), sub, tmp],
                           capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(tmp):
            open(out_txt, 'w').write(k['text'])
            return f'{ocr_label(k)} FAILED; text layer only ({k["verdict"]})'
        got = _split_pages(open(tmp).read())
        ocr = {want[i - 1]: t for i, t in got.items() if 0 < i <= len(want)}
    layer = _split_pages(k['text'])
    n_ocr = 0
    parts = []
    for p in k['pages']:
        i = p['page']
        if p['kind'] in OCR_KINDS:
            n_ocr += 1
            parts.append(f'===PAGE {i}===\n{ocr.get(i, "")}')
        else:
            parts.append(f'===PAGE {i}===\n{layer.get(i, "")}')
    open(out_txt, 'w').write('\n'.join(parts))
    if k['verdict'] == 'mixed':
        return f'pdf text layer + ocr ({n_ocr} of {len(k["pages"])} pages)'
    return ocr_label(k)


def summary(k):
    counts = {}
    for p in k['pages']:
        counts[p['kind']] = counts.get(p['kind'], 0) + 1
    return f'{k["verdict"]}: ' + ', '.join(f'{v} {n}' for n, v in sorted(counts.items()))


if __name__ == '__main__':
    for f in sys.argv[1:]:
        try:
            print(f'{summary(classify(f)):<55} {f}')
        except Exception as e:
            print(f'ERROR {type(e).__name__}: {e}  {f}')
