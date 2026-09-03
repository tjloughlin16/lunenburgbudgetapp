"""Has anything we sent to the Town drifted from what we now hold?

    python3 scripts/check_sent_documents.py

A document that has been sent is a fixed object held by somebody else. Ours can move --
these are generated, so a change to a rate, a bucket or an extractor rewrites them without
anybody touching a sentence. When that happens the official is holding figures that no
longer match ours, and may quote them back.

That is not a reason to avoid changing anything. It is a reason to KNOW. So each folder
of sent documents carries a MANIFEST.json recording the sha256 of the PDF that went out
and of the Markdown it was built from, and this script re-hashes the Markdown and reports
what no longer matches.

**Drift is not a failure.** The right response is almost never to quietly rebuild the PDF
in the sent folder -- that would destroy the only record of what the recipient actually
has. It is to send a correction that says which version it corrects. So this script exits
0 and reports, unless --strict is given.

This is rule 12 pointed outwards: every inbound source carries a checksum because a file
can be replaced in place. The same is true of a document we mailed, except that the copy
we cannot change is the one that matters.
"""
import argparse
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTES = os.path.join(ROOT, 'notes')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(65536), b''):
            h.update(block)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--strict', action='store_true',
                    help='exit non-zero if anything has drifted')
    args = ap.parse_args()

    folders = sorted(
        os.path.join(NOTES, d) for d in os.listdir(NOTES)
        if d.startswith('sent-') and os.path.isfile(
            os.path.join(NOTES, d, 'MANIFEST.json')))
    if not folders:
        print('nothing recorded as sent')
        return 0

    drifted = 0
    for folder in folders:
        man = json.load(open(os.path.join(folder, 'MANIFEST.json')))
        print('%s  (recorded %s)' % (os.path.relpath(folder, ROOT), man['recorded']))
        for doc in man['documents']:
            pdf = os.path.join(folder, doc['pdf'])
            src = os.path.join(ROOT, doc['source'])
            notes = []
            if not os.path.exists(pdf):
                notes.append('the sent PDF is GONE')
            elif sha256(pdf) != doc['pdf_sha256']:
                # The sent copy is the record. If it changed, the record is lost.
                notes.append('the sent PDF has been MODIFIED — it is no longer what '
                             'was sent')
            if not os.path.exists(src):
                notes.append('its source is gone')
            elif sha256(src) != doc['source_sha256_when_sent']:
                notes.append('our copy has moved since it went out')
            sent = doc.get('sent') or 'date not filled in'
            if notes:
                drifted += 1
                print('  DRIFTED  %-28s to the %s (%s)'
                      % (doc['pdf'], doc['to'], sent))
                for n in notes:
                    print('           - %s' % n)
                print('           rebuild and compare:  python3 %s' % doc['generator'])
            else:
                print('  same     %-28s to the %s (%s)'
                      % (doc['pdf'], doc['to'], sent))

    if drifted:
        print('\n%d document(s) differ from what was sent. That is information, not an '
              'error.' % drifted)
        print('Do NOT rebuild the PDF inside the sent folder: it is the only record of '
              'what the')
        print('recipient actually holds. Send a correction that names the version it '
              'corrects.')
    else:
        print('\nEverything sent still matches what we hold.')
    return 1 if (drifted and args.strict) else 0


if __name__ == '__main__':
    sys.exit(main())
