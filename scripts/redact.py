#!/usr/bin/env python3
"""THE RAW IS PRIVATE. THE PUBLIC COPY IS OURS. THE DECISION BETWEEN THEM IS WRITTEN DOWN.

    python3 scripts/redact.py --pending          # what is held, and why
    python3 scripts/redact.py --review           # OCR / read what the screen could not, re-screen
    python3 scripts/redact.py --build            # make every redacted copy, stage and secure it
    python3 scripts/redact.py --check            # every redacted copy rebuilds byte for byte
    python3 scripts/redact.py --rescreen-published PREFIX   # what a weaker screen let out

TJ, 4 October 2026: *"i think we probably need a REDACTION mechanism, so that we can have a
private storage of the raw, and a public version with all redacted PII removed. This will
come up in MUNIS data too"* -- and, on what a redacted document must say first: *"UNOFFICIAL
DOCUMENT, REDACTION DONE BY LUNENBURGBUDGETPROJECT.ORG"*, *"official document available upon
request"*.

WHY IT EXISTS. A records-request delivery was pushed to the PUBLIC bucket, which cannot
delete anything for ten years, and 32 files reached it before anybody looked properly. One
held a named employee's number, start date, grade and salary. A keyword pass had seen the
word `salary` in its header and stopped there.

THE SHAPE, in three parts:

  1. THE GATE (`gate()`, called by `ingest.stage()` for every document with NO public
     upstream -- a records request, an email, a MUNIS run). It FAILS CLOSED: a document the
     screen flags, or cannot read, goes to the private bucket and waits as `pending`. It
     reaches the public bucket only when a row here says `publish`, or as our redacted copy.
     A document the publisher already put on a public website is not gated -- it is public
     already, and re-hosting it exposes nothing new.
  2. THE REGISTER, `sources/data/redactions.csv`: one row per raw document, keyed by its
     sha256 -- the decision, the rule, what was removed and how much, the reason, who
     decided. It never holds a redacted VALUE, only where one was.
  3. THE REDACTED COPY, built here from the raw bytes and a declared rule, deterministically,
     so `--check` can rebuild it and match the sha256. A redaction that cannot be
     reproduced is a hand edit, and a hand edit cannot be checked.

EVERY REDACTED COPY OPENS WITH THE NOTICE. A cover sheet for a workbook, a cover page for a
PDF, the first paragraph of a Word file, a banner on the first slide. Then: the original's
name as delivered, its sha256, what was removed and why.

TWO FAILURES THIS IS BUILT AGAINST, both named because both are common:

  * OVERLAY REDACTION -- black boxes drawn over text that is still in the text layer, so
    anyone can select it and copy it out. A redacted PDF here is REBUILT AS IMAGES: every
    page rendered, the boxes burned into the pixels, no text layer left underneath.
  * QUASI-IDENTIFIERS -- fields harmless alone that identify a person together. Removing
    the names from a staff list and keeping job title and hire date still names everybody
    in a department of four. So a rule removes the dates beside the names, and a document
    whose rows cannot be made anonymous is WITHHELD rather than redacted.

AND EVERY OUTPUT IS RE-SCREENED. A redacted copy must pass the same screen that flagged its
original, and every mask pattern must be gone from it, or nothing is written.
"""
import argparse
import csv
import datetime
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import archive_storage as A  # noqa: E402
import pii_screen  # noqa: E402

ROOT = os.path.dirname(HERE)
REGISTER = os.path.join(ROOT, 'sources', 'data', 'redactions.csv')
COLS = ['raw_sha256', 'delivered_as', 'raw_key', 'raw_private_key', 'decision', 'rule',
        'public_key', 'public_sha256', 'removed', 'findings', 'reason', 'decided_by',
        'decided_on', 'note']
DECISIONS = ('pending', 'publish', 'redact', 'withhold')

# What makes an OCR reading of a page trustworthy enough to clear it. Below LOW_DPI the
# annual reports' digits merged into the same pixels; below PAGE_MIN characters a page was
# not read, whatever it holds. Either keeps a document held for a person.
#
# THE BAR DEPENDS ON WHERE THE PICTURE CAME FROM. 150 dpi is a PAPER standard: FY2023 p25 of
# the annual reports is a scan at 93 dpi whose digits are the same pixels. A picture inside a
# DIGITAL document is almost always a screen capture -- taken at screen resolution, so 100 dpi
# is crisp. Of the eighteen Finance Committee documents held under the paper bar on
# 4 October 2026, every held page turned out to be a legible screenshot or a photo, at 69 to
# 145 dpi. Below 60 even a screen capture's digits merge, so that still goes to a person.
LOW_DPI = 150            # a page of a SCAN
LOW_DPI_SCREEN = 60      # a picture page inside an otherwise digital document
PAGE_MIN = 20

NOTICE = 'UNOFFICIAL DOCUMENT, REDACTION DONE BY LUNENBURGBUDGETPROJECT.ORG'
NOTICE_2 = 'Official document available upon request'
MASK = '[redacted]'
FIXED_TIME = (1980, 1, 1, 0, 0, 0)          # every zip entry, so a rebuild is byte-identical
FIXED_ISO = '1980-01-01T00:00:00Z'


# --- the register ----------------------------------------------------------------------

def load():
    if not os.path.exists(REGISTER):
        return []
    with open(REGISTER, newline='', encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def save(rows):
    tmp = REGISTER + '.tmp'
    with open(tmp, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, lineterminator='\n')
        w.writeheader()
        for r in sorted(rows, key=lambda r: (r['raw_key'], r['raw_sha256'])):
            w.writerow({c: r.get(c, '') for c in COLS})
    os.replace(tmp, REGISTER)


def by_sha(rows=None):
    return {r['raw_sha256']: r for r in (rows if rows is not None else load())}


def private_key_for(key):
    return 'raw/' + key


def upsert(row):
    """Insert or update ONE row, re-reading the file first: other things write it too."""
    rows = [r for r in load() if r['raw_sha256'] != row['raw_sha256']]
    rows.append(row)
    save(rows)


# --- the gate --------------------------------------------------------------------------

def gate(key, blob, upstream='', delivered_as=''):
    """None if this document may go to the PUBLIC bucket as it is; otherwise the reason it
    is held. A held document's raw bytes are in the private bucket before this returns."""
    if upstream:
        return None
    sha = hashlib.sha256(blob).hexdigest()
    rows = load()
    # Our own redacted copy, built by this file and registered against its original.
    if any(r['public_sha256'] == sha for r in rows if r['decision'] == 'redact'):
        return None
    row = by_sha(rows).get(sha)
    if row is None:
        findings = pii_screen.screen(key, blob)
        if not findings:
            return None
        row = {'raw_sha256': sha, 'delivered_as': delivered_as, 'raw_key': key,
               'raw_private_key': private_key_for(key), 'decision': 'pending',
               'findings': ' | '.join(findings),
               'decided_on': datetime.date.today().isoformat()}
    if row['decision'] == 'publish':
        return None
    if not row.get('raw_private_key'):
        row['raw_private_key'] = private_key_for(row.get('raw_key') or key)
    A.put_private(row['raw_private_key'], blob)
    upsert(row)
    return f'HELD ({row["decision"]}): {row.get("findings") or row.get("reason")}'


# --- redaction, by format --------------------------------------------------------------

def _masker(patterns):
    pats = [re.compile(p, re.S) for p in patterns]

    def mask(text):
        n = 0
        for p in pats:
            text, k = p.subn(MASK, text)
            n += k
        return text, n
    return mask, pats


def _notice_lines(row, removed):
    return [NOTICE, NOTICE_2, '',
            f'Original, as delivered: {row["delivered_as"] or row["raw_key"]}',
            f'Original sha256: {row["raw_sha256"]}',
            f'Removed: {removed}',
            f'Why: {row["reason"]}',
            'Register: https://lunenburgbudgetproject.org/data/redactions.csv']


def _normalise_zip(blob):
    """Rewrite an OOXML zip with fixed timestamps, so the same input gives the same bytes."""
    src = zipfile.ZipFile(io.BytesIO(blob))
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename == 'docProps/core.xml':
                data = re.sub(rb'(<dcterms:(created|modified)[^>]*>)[^<]*',
                              rb'\g<1>' + FIXED_ISO.encode(), data)
            zi = zipfile.ZipInfo(info.filename, FIXED_TIME)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, data)
    return out.getvalue()


def redact_xlsx(blob, rule, row):
    """Values only, never formulas: a formula can rebuild a name from the cells beside it."""
    import openpyxl
    from openpyxl.styles import Font
    wb = openpyxl.load_workbook(io.BytesIO(blob), data_only=True)
    # Column rules are PATTERNS, matched against the whole header cell, case-insensitively.
    # One workbook spelled the employee number five ways across its sheets -- `Emp No`,
    # `EmpNo`, `EMPNO`, `Emp#`, `Emp No.` -- and a rule of literal names missed four.
    cols = [re.compile(c, re.I) for c in rule.get('columns', [])]
    mask, _ = _masker(rule.get('mask', []))
    removed = 0
    for name in rule.get('drop_sheets', []):
        if name in wb.sheetnames:
            ws = wb[name]
            removed += sum(1 for r in ws.iter_rows() for c in r if c.value not in (None, ''))
            del wb[name]
    for ws in wb.worksheets:
        blank = set()
        for row_cells in ws.iter_rows():
            for c in row_cells:
                v = c.value
                if isinstance(v, str) and any(c_.fullmatch(v.strip()) for c_ in cols):
                    blank.add(c.column)
                    c.value = MASK
                    continue
                if c.column in blank and v not in (None, ''):
                    c.value = MASK
                    removed += 1
                elif isinstance(v, str) and rule.get('mask'):
                    new, n = mask(v)
                    if n:
                        c.value, removed = new, removed + n
    cover = wb.create_sheet('REDACTED', 0)
    for i, line in enumerate(_notice_lines(row, f'{removed} cell(s)'), 1):
        cover.cell(i, 1, line)
    cover['A1'].font = Font(bold=True, size=16, color='C00000')
    cover['A2'].font = Font(bold=True, size=12)
    cover.column_dimensions['A'].width = 110
    wb.active = 0
    out = io.BytesIO()
    wb.save(out)
    return _normalise_zip(out.getvalue()), '.xlsx', removed


def _xml_escape(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _mask_xml_text(xml, tag, mask):
    n_total = 0

    def sub(m):
        nonlocal n_total
        new, n = mask(m.group(2))
        n_total += n
        return m.group(1) + new + m.group(3)
    xml = re.sub(r'(<%s(?:\s[^>]*)?>)(.*?)(</%s>)' % (tag, tag), sub, xml, flags=re.S)
    return xml, n_total


def redact_docx(blob, rule, row):
    mask, _ = _masker(rule.get('mask', []))
    src = zipfile.ZipFile(io.BytesIO(blob))
    parts, removed = {}, 0
    for name in src.namelist():
        data = src.read(name)
        if name.startswith('word/') and name.endswith('.xml'):
            x, n = _mask_xml_text(data.decode('utf8'), 'w:t', mask)
            removed += n
            data = x.encode('utf8')
        parts[name] = data
    lines = _notice_lines(row, f'{removed} passage(s)')
    paras = ''.join(
        '<w:p><w:r><w:rPr>%s</w:rPr><w:t xml:space="preserve">%s</w:t></w:r></w:p>' % (
            '<w:b/><w:color w:val="C00000"/><w:sz w:val="32"/>' if i == 0 else
            ('<w:b/>' if i == 1 else ''), _xml_escape(t))
        for i, t in enumerate(lines))
    doc = parts['word/document.xml'].decode('utf8')
    doc = re.sub(r'(<w:body[^>]*>)', lambda m: m.group(1) + paras, doc, count=1)
    parts['word/document.xml'] = doc.encode('utf8')
    return _rezip(src, parts), '.docx', removed


def _rezip(src, parts):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for info in src.infolist():
            z.writestr(info.filename, parts[info.filename])
    return _normalise_zip(out.getvalue())


def _first_slide(src):
    pres = src.read('ppt/presentation.xml').decode('utf8')
    rels = src.read('ppt/_rels/presentation.xml.rels').decode('utf8')
    rid = re.search(r'<p:sldId [^>]*r:id="([^"]+)"', pres).group(1)
    target = re.search(r'<Relationship [^>]*Id="%s"[^>]*Target="([^"]+)"' % rid, rels) or \
        re.search(r'<Relationship [^>]*Target="([^"]+)"[^>]*Id="%s"' % rid, rels)
    return 'ppt/' + target.group(1).lstrip('/').replace('ppt/', '')


def redact_pptx(blob, rule, row):
    mask, _ = _masker(rule.get('mask', []))
    src = zipfile.ZipFile(io.BytesIO(blob))
    parts, removed = {}, 0
    for name in src.namelist():
        data = src.read(name)
        if name.startswith(('ppt/slides/', 'ppt/notesSlides/', 'ppt/comments')) \
                and name.endswith('.xml'):
            x, n = _mask_xml_text(data.decode('utf8'), 'a:t', mask)
            removed += n
            data = x.encode('utf8')
        parts[name] = data
    lines = _notice_lines(row, f'{removed} passage(s)')
    paras = ''.join(
        '<a:p><a:r><a:rPr lang="en-US" sz="%d" b="%d"><a:solidFill><a:srgbClr val="%s"/>'
        '</a:solidFill></a:rPr><a:t>%s</a:t></a:r></a:p>' % (
            2000 if i == 0 else 1100, 1 if i < 2 else 0, 'FFFFFF', _xml_escape(t))
        for i, t in enumerate(lines))
    shape = ('<p:sp><p:nvSpPr><p:cNvPr id="9999" name="Redaction notice"/><p:cNvSpPr '
             'txBox="1"/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="0" y="0"/>'
             '<a:ext cx="9144000" cy="2286000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/>'
             '</a:prstGeom><a:solidFill><a:srgbClr val="C00000"/></a:solidFill></p:spPr>'
             '<p:txBody><a:bodyPr wrap="square"/><a:lstStyle/>%s</p:txBody></p:sp>' % paras)
    first = _first_slide(src)
    x = parts[first].decode('utf8')
    x = x.replace('</p:spTree>', shape + '</p:spTree>', 1)
    parts[first] = x.encode('utf8')
    return _rezip(src, parts), os.path.splitext(row['raw_key'])[1].lower().replace(
        '.pptm', '.pptx'), removed


def redact_pdf(blob, rule, row):
    """Rebuilt as images. No text layer survives, so nothing under a box can be copied."""
    import logging
    import pdfplumber
    import pypdfium2 as pdfium
    logging.getLogger('pdfminer').setLevel(logging.ERROR)
    from PIL import Image, ImageDraw, ImageFont
    scale = 2.0                                    # 144 dpi
    _, pats = _masker(rule.get('mask', []))
    pages, removed = [], 0
    pdf = pdfium.PdfDocument(blob)
    with pdfplumber.open(io.BytesIO(blob)) as plumb:
        for i, page in enumerate(plumb.pages):
            img = pdf[i].render(scale=scale).to_pil().convert('RGB')
            draw = ImageDraw.Draw(img)
            words = page.extract_words(keep_blank_chars=False, use_text_flow=True)
            joined, spans, pos = '', [], 0
            for w in words:
                spans.append((pos, pos + len(w['text'])))
                joined += w['text'] + ' '
                pos = len(joined)
            hit = set()
            for p in pats:
                for m in p.finditer(joined):
                    removed += 1
                    hit.update(j for j, (a, b) in enumerate(spans)
                               if a < m.end() and b > m.start())
            for j in hit:
                w = words[j]
                draw.rectangle([w['x0'] * scale - 2, w['top'] * scale - 2,
                                w['x1'] * scale + 2, w['bottom'] * scale + 2], fill='black')
            for (pg, x0, t, x1, b) in rule.get('boxes', []):
                if pg == i + 1:
                    draw.rectangle([x0 * scale, t * scale, x1 * scale, b * scale], fill='black')
                    removed += 1
            pages.append(img)
    w, h = pages[0].size
    cover = Image.new('RGB', (w, h), 'white')
    d = ImageDraw.Draw(cover)
    try:
        big = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', int(w / 34))
        small = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', int(w / 60))
    except OSError:
        big = small = ImageFont.load_default()
    y = int(h * 0.08)
    for i, line in enumerate(_notice_lines(row, f'{removed} passage(s)')):
        font = big if i == 0 else small
        colour = (192, 0, 0) if i == 0 else (0, 0, 0)
        for chunk in _wrap(line, 95 if i else 60):
            d.text((int(w * 0.06), y), chunk, fill=colour, font=font)
            y += int((w / 30) if i == 0 else (w / 48))
        y += int(w / 120)
    out = io.BytesIO()
    cover.save(out, 'PDF', save_all=True, append_images=pages, resolution=144,
               creationDate=time.strptime('1980-01-01', '%Y-%m-%d'),
               modDate=time.strptime('1980-01-01', '%Y-%m-%d'))
    return out.getvalue(), '.pdf', removed


def _wrap(s, n):
    out, line = [], ''
    for word in s.split(' '):
        if len(line) + len(word) + 1 > n and line:
            out.append(line)
            line = word
        else:
            line = (line + ' ' + word).strip()
    return out + [line]


REDACTORS = {'.xlsx': redact_xlsx, '.xlsm': redact_xlsx, '.docx': redact_docx,
             '.pptx': redact_pptx, '.pptm': redact_pptx, '.pdf': redact_pdf}


def public_key_for(raw_key, ext):
    stem = os.path.splitext(raw_key)[0]
    return f'{stem}.redacted{ext}'


def full_rule(row):
    """The rule as the redactor needs it: the public part, plus the private part if any.

    A MASK IS THE THING IT HIDES. To remove a name you must write the name down, so a mask
    may never sit in this register, which is published -- it lives in the PRIVATE bucket,
    and the public rule carries only a pointer to it. Learned on 4 October 2026, when the
    first redacted copy printed its own reason on its cover and the register held the
    names the copy had removed.
    """
    rule = json.loads(row['rule'] or '{}')
    if rule.get('private_rule'):
        priv = json.loads(A.get_private(rule['private_rule']))
        rule = {**{k: v for k, v in rule.items() if k != 'private_rule'}, **priv}
    return rule


def build_one(row, blob):
    """(bytes, public key, count removed). Refuses if the output still fails the screen."""
    ext = os.path.splitext(row['raw_key'])[1].lower()
    fn = REDACTORS.get(ext)
    if not fn:
        raise SystemExit(f'no redactor for {ext}: {row["raw_key"]} -- withhold it instead')
    rule = full_rule(row)
    # THE NOTICE MUST NOT SAY WHAT WAS REMOVED. It is printed on page one of a public
    # document, so a reason that names or describes the redacted content undoes the
    # redaction -- which is exactly what the first one did.
    for p in rule.get('mask', []):
        if re.search(p, row['reason'] or '', re.S | re.I):
            raise SystemExit(f'{row["raw_key"]}: the public reason repeats what a mask '
                             f'removes. Write the reason as a category.')
    out, out_ext, removed = fn(blob, rule, row)
    key = public_key_for(row['raw_key'], out_ext)
    # A PUBLIC KEY NAMES ONE SET OF BYTES FOREVER: the bucket refuses to overwrite. A
    # rebuild that changes the copy gets a new key, suffixed by its own sha; the old one
    # stays where it is and is recorded, never replaced.
    sha = hashlib.sha256(out).hexdigest()
    if row.get('public_key') and row.get('public_sha256') == sha:
        key = row['public_key']
    elif row.get('public_key') and row.get('public_sha256') and row['public_sha256'] != sha:
        stem, e = os.path.splitext(key)
        key = f'{stem}-{sha[:8]}{e}'
    # The post-condition. A PDF is now images, which the screen cannot read -- which is the
    # point -- so for those the proof is the rebuild itself; for everything else the output
    # must screen clean and every mask pattern must be gone from its text.
    if out_ext != '.pdf':
        left = [f for f in pii_screen.screen(key, out)
                if not f.startswith('unscreenable')]
        if left:
            raise SystemExit(f'{key} still fails the screen after redaction: {left}')
        text = (pii_screen._xlsx(out, []) if out_ext == '.xlsx' else
                pii_screen._ooxml_text(out, ('word/', 'ppt/')))
        for p in rule.get('mask', []):
            if re.search(p, text, re.S):
                raise SystemExit(f'{key}: mask {p!r} still matches after redaction')
    if not removed:
        raise SystemExit(f'{key}: the rule removed nothing -- the rule is wrong, or the '
                         f'decision is')
    return out, key, removed


def build(stage=True):
    import ingest
    rows = load()
    for row in rows:
        if row['decision'] != 'redact':
            continue
        blob = A.get_private(row['raw_private_key'])
        out, key, removed = build_one(row, blob)
        row['public_key'], row['public_sha256'] = key, hashlib.sha256(out).hexdigest()
        row['removed'] = str(removed)
        save(rows)
        if stage:
            ok, why = ingest.stage(key, out, upstream='')
            if not ok:
                raise SystemExit(f'refused {key}: {why}')
        print(f'  redacted  {removed:>4}  {key}')
    if stage:
        ingest.secure()


def check():
    problems, n = [], 0
    for row in load():
        if row['decision'] not in DECISIONS:
            problems.append(f'unknown decision {row["decision"]!r}: {row["raw_key"]}')
        if 'mask' in json.loads(row.get('rule') or '{}'):
            problems.append(f'a mask is in the PUBLIC register -- the mask is the value it '
                            f'hides. Move it to a private rule: {row["raw_key"]}')
        if row['decision'] == 'redact':
            n += 1
            blob = A.get_private(row['raw_private_key'])
            if hashlib.sha256(blob).hexdigest() != row['raw_sha256']:
                problems.append(f'private raw differs from its register sha: {row["raw_key"]}')
                continue
            out, key, _ = build_one(row, blob)
            if hashlib.sha256(out).hexdigest() != row['public_sha256']:
                problems.append(f'does not rebuild byte for byte: {key}')
            if os.path.exists(A.local_path(row['raw_key'])) and \
                    not row.get('note', '').startswith('PUBLISHED BEFORE REVIEW'):
                problems.append(f'raw copy of a redacted document is in sources/: {row["raw_key"]}')
        if row['decision'] == 'withhold' and os.path.exists(A.local_path(row['raw_key'])):
            problems.append(f'withheld and present in sources/: {row["raw_key"]}')
    if problems:
        sys.exit('\n'.join(problems))
    pend = sum(1 for r in load() if r['decision'] == 'pending')
    print(f'ok: {n} redacted copies rebuild byte for byte; {pend} pending review')


# --- review: read what the screen could not, and screen it again ------------------------

def _readable_text(key, blob):
    ext = os.path.splitext(key)[1].lower()
    tmp = os.path.join(ROOT, 'build', 'redact-review')
    os.makedirs(tmp, exist_ok=True)
    src = os.path.join(tmp, 'in' + ext)
    open(src, 'wb').write(blob)
    out = os.path.join(tmp, 'out.txt')
    if os.path.exists(out):
        os.remove(out)
    if ext == '.pdf':
        # Page by page: the text layer where it reads, OCR only where it does not.
        import pdf_kind
        how = pdf_kind.extract_text(src, out)
        return (open(out).read() if os.path.exists(out) and 'FAILED' not in how
                else None), how
    if ext == '.doc':
        r = subprocess.run(['textutil', '-convert', 'txt', '-output', out, src],
                           capture_output=True)
        return open(out).read() if r.returncode == 0 else None, 'textutil'
    if ext == '.ppt':
        # PowerPoint 97 stores slide text as UTF-16LE and 8-bit runs inside an OLE file.
        runs = re.findall(rb'(?:[\x20-\x7e]\x00){4,}', blob)
        runs = [r.decode('utf-16le') for r in runs] + \
            [r.decode('latin1') for r in re.findall(rb'[\x20-\x7e]{6,}', blob)]
        return '\n'.join(runs), 'raw text runs'
    return None, 'none'


def review():
    rows = load()
    for row in rows:
        if row['decision'] != 'pending' or 'unscreenable' not in row.get('findings', ''):
            continue
        blob = A.get_private(row['raw_private_key'])
        text, how = _readable_text(row['raw_key'], blob)
        if text is None or len(re.sub(r'\s', '', text)) < pii_screen.MIN_TEXT:
            print(f'  still unreadable ({how}): {row["raw_key"]} -- a person must look')
            continue
        # A READING IS NOT CLEAN UNTIL EVERY PAGE OF IT WAS ACTUALLY READ. The annual
        # reports are where this was learned: a 93 dpi page OCRs confidently and wrongly
        # (`page-blocked.csv`, FY2023 p25), and a page that came back empty would screen as
        # "nothing found" when the truth is "nothing seen" (13c). Either keeps the document
        # held for a person.
        unread = []
        if row['raw_key'].lower().endswith('.pdf'):
            import pdf_kind
            k = pdf_kind.classify(blob)
            got = pdf_kind._split_pages(text)
            for p in k['pages']:
                if p['kind'] not in pdf_kind.OCR_KINDS:
                    continue
                n = len(re.sub(r'\s', '', got.get(p['page'], '')))
                bar = LOW_DPI if k['verdict'] == 'scan' else LOW_DPI_SCREEN
                low = p['dpi'] is not None and p['dpi'] < bar
                # LOW RESOLUTION MATTERS WHEN WORDS WERE READ FROM IT. FY2023 p25 OCR'd
                # confidently and wrongly at 93 dpi: text read off pixels that cannot hold
                # it. A low-resolution picture that yields NO words is a logo or a photo on
                # a slide, and holding a deck for its title-slide logo is noise that trains
                # people to wave holds through.
                if low and n >= PAGE_MIN:
                    unread.append(f'p{p["page"]} read at {p["dpi"]} dpi')
                elif not low and n < PAGE_MIN and k['verdict'] in ('scan',
                                                                   'digital, text unreadable'):
                    # A SCAN page that read nothing is a failed read. A picture inside a
                    # digital deck that read nothing is a picture.
                    unread.append(f'p{p["page"]} read {n} chars')
        found = pii_screen.screen_text(text, [])
        if unread:
            found = [f'pages not trustworthily read: {", ".join(unread[:8])}'
                     + (f' and {len(unread) - 8} more' if len(unread) > 8 else '')] + found
        if found:
            row['findings'] = f'after {how}: ' + ' | '.join(found)
            print(f'  HELD after {how}: {row["raw_key"]}\n      ' + '\n      '.join(found))
        else:
            # The reading is the document's text now, so the catalogue does not OCR it a
            # second time. Written ONLY for a document that is about to be published:
            # the text of a held one must never land in `sources/`.
            txt = os.path.join(A.SRC, os.path.dirname(row['raw_key']), 'text',
                               os.path.basename(row['raw_key']) + '.txt')
            os.makedirs(os.path.dirname(txt), exist_ok=True)
            open(txt, 'w').write(text)
            row.update(decision='publish', decided_by=f'screen, after {how}',
                       decided_on=datetime.date.today().isoformat(),
                       reason=f'unscreenable as delivered; read by {how} and nothing found')
            print(f'  clean after {how}: {row["raw_key"]}')
        save(rows)


def rescreen_published(prefix):
    """Screen what is ALREADY public under a prefix, with the screen as it is today.

    The screen gets stronger; what it passed before was passed by a weaker one. Run this
    after any change to `pii_screen.py` or `pdf_kind.py`. A finding cannot recall the public
    copy -- the bucket keeps it ten years -- so it is registered `pending` with that said in
    its note, the raw goes to the private bucket for `--review` to read, and a person decides
    whether a redacted copy should be catalogued in its place.
    """
    rows = load()
    known = {r['raw_sha256'] for r in rows}
    n = 0
    for key, m in sorted(A.read_manifest().items()):
        if not key.startswith(prefix) or m['sha256'] in known or '.redacted.' in key:
            continue
        path = A.local_path(key)
        if not os.path.exists(path):
            continue
        blob = open(path, 'rb').read()
        found = pii_screen.screen(key, blob)
        if not found:
            continue
        A.put_private(private_key_for(key), blob)
        rows.append({'raw_sha256': m['sha256'], 'raw_key': key,
                     'raw_private_key': private_key_for(key), 'decision': 'pending',
                     'findings': ' | '.join(found),
                     'decided_on': datetime.date.today().isoformat(),
                     'note': 'PUBLISHED BEFORE REVIEW: passed an earlier, weaker screen; '
                             'the raw is in the public bucket and cannot be deleted'})
        save(rows)
        n += 1
        print(f'  pending  {key}\n           {found[0]}')
    print(f'{n} already-public document(s) registered for review')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pending', action='store_true')
    ap.add_argument('--review', action='store_true')
    ap.add_argument('--build', action='store_true')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--rescreen-published', metavar='PREFIX')
    a = ap.parse_args()
    if a.rescreen_published:
        rescreen_published(a.rescreen_published)
        return
    if a.review:
        review()
    if a.build:
        build()
    if a.check:
        check()
    if a.pending or not (a.review or a.build or a.check):
        for r in load():
            if r['decision'] == 'pending':
                print(f'{r["raw_key"]}\n    {r["findings"]}')


if __name__ == '__main__':
    main()
