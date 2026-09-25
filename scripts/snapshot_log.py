#!/usr/bin/env python3
"""A SNAPSHOT PER CHANGE, AND A LOG OF EVERY TIME WE LOOKED.

Shared by the two staff-directory fetchers, which are the only sources in this archive that
have to be re-fetched on a schedule to exist at all: the town and the district both publish
their people on pages they overwrite in place, so there is no FY2026 version of either
anywhere and the only history that will exist is the one this archive keeps.

WHY NOT SIMPLY KEEP EVERY FETCH. Because a daily fetch of a page nobody edited writes 365
identical copies a year, and a document in the R2 bucket is frozen for ten years and cannot
be deleted -- so the cost of a snapshot that says nothing is permanent. One snapshot per
actual change is the record; the rest is duplication with a date on it.

WHY A LOG IS NEEDED ANYWAY, AND THIS IS THE HALF THAT IS EASY TO SKIP. Without one, "the
directory did not change between July and October" is indistinguishable from "nobody looked
between July and October" -- a gap in the record reading as stability, which is the same
mistake as a grep that finds nothing reading as nobody said it. So every run appends a row
saying it looked, whether or not anything came of it, and `checked.csv` is the answer to how
current a snapshot is. It is DERIVED and small and belongs in git, not in the bucket.

The term for the shape is a slowly changing dimension: the publisher keeps only the current
value, so the archive has to keep the versions and the dates they were true between.
"""
import csv
import hashlib
import os

FIELDS = ['checked', 'changed', 'snapshot', 'files', 'note']


def digests(blobs):
    """{name: sha256} for what a fetch just pulled down."""
    return {n: hashlib.sha256(b).hexdigest() for n, b in blobs.items()}


def snapshots(root):
    """The snapshot folders, oldest first. A folder name that is not a date is not one."""
    import re
    if not os.path.isdir(root):
        return []
    return sorted(d for d in os.listdir(root)
                  if re.fullmatch(r'\d{4}-\d{2}-\d{2}', d)
                  and os.path.isdir(os.path.join(root, d)))


def latest(root):
    s = snapshots(root)
    return s[-1] if s else None


def same_as_latest(root, blobs, only=None):
    """Is what we just fetched the same as the newest snapshot held?

    Compares the FILES ON DISK rather than the catalogue, because the catalogue is a
    separate claim about them and this question is about the bytes. A file the fetch
    produced and the snapshot lacks, or the reverse, counts as CHANGED -- a page that
    appeared or went away is exactly the kind of change worth keeping.

    `only` NAMES THE FILES THAT ARE ACTUALLY COMPARABLE, and passing it is not an
    optimisation. HALF OF WHAT THESE FETCHERS DOWNLOAD IS NOT BYTE-REPRODUCIBLE: Google
    stamps a fresh `nonce` into every `pubhtml` response and the district's Sites page
    comes back a different length each time, so two fetches a second apart differ while the
    people on the page are identical. Comparing everything therefore reports CHANGED on
    every run, which would write a snapshot a day forever -- and each one is frozen in the
    bucket for ten years. The CSV exports ARE stable, byte for byte, and they are the rows.

    So the rule is: compare the DATA, keep the rendering. A caller that passes nothing gets
    the strict comparison, which is right for a source whose every file is reproducible.
    """
    day = latest(root)
    if not day:
        return None, False
    d = os.path.join(root, day)
    held = {f: hashlib.sha256(open(os.path.join(d, f), 'rb').read()).hexdigest()
            for f in os.listdir(d) if os.path.isfile(os.path.join(d, f))}
    got = digests(blobs)
    if only is not None:
        keep = set(only)
        held = {k: v for k, v in held.items() if k in keep}
        got = {k: v for k, v in got.items() if k in keep}
    return day, bool(got) and held == got


def record(root, checked, changed, snapshot='', files=0, note=''):
    """Append one row saying we looked. Never rewrites the file."""
    p = os.path.join(root, 'checked.csv')
    new = not os.path.exists(p)
    os.makedirs(root, exist_ok=True)
    with open(p, 'a', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({'checked': checked, 'changed': 'yes' if changed else 'no',
                    'snapshot': snapshot, 'files': files, 'note': note})
    return p
