#!/usr/bin/env python3
"""READ THE ANNUAL TOWN REPORTS WITH TEXTRACT, A BATCH AT A TIME, NEWEST FIRST, IN PARALLEL.

    python3 scripts/read_annual_reports.py --batch 10 --dry-run   # which reports, how many pages, the cost
    python3 scripts/read_annual_reports.py --batch 10             # send them, through the meter
    python3 scripts/read_annual_reports.py --status               # what each report has had read

TJ, 28 October 2026: *"run this as fast as possible, because with aws we can parallelize right?!
but confirm costs along the way. batches of 10, then if costs map out, double to 20, etc"* -- and
before that, *"dont blow out budgets accidentally"*.

So a batch is N reports, and it prints, at the end, the estimate beside what the ledger recorded,
so the next batch is sized from a measurement rather than a hope.

PARALLEL, WITHOUT LOOSENING THE METER. textract_spend.Meter refuses a second PROCESS, because two
runs would both pass the cap check. So the parallelism is inside one process and one meter: the
main thread prepares each page, RESERVES it (the cap check, written down before anything is
sent), and only the AWS call itself goes to a worker thread. Every ledger write -- reserve and
outcome -- happens on the main thread, so the meter sees exactly the sequence a serial run would.
Page rendering stays on the main thread too: pdfium is not thread-safe.

The batch's ceiling is its own estimate plus a margin, so a batch cannot spend past what it
said it would. The monthly cap and the latch behave as they always have.

Which reports: the calendar-year editions in town-annual-reports/ (named `<id>-<year>-annual-
town-report.pdf`), newest first, that still have pages not read in this feature. The FY2011-FY2025
reports were read and proven on Vision and are not in scope.
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import textract_pages as T                                            # noqa: E402
import textract_spend as M                                            # noqa: E402

DOCS = M.ROOT / 'sources' / 'town-annual-reports' / 'docs'
EDITION = re.compile(r'^\d+-(\d{4})-annual-town-report$')
MARGIN = 1.10                       # a batch's ceiling over its estimate


def reports():
    """[(year, path)] for the calendar-year editions, newest first."""
    out = []
    for p in DOCS.glob('*.pdf'):
        m = EDITION.match(p.stem)
        if m:
            out.append((int(m.group(1)), p))
    return sorted(out, key=lambda t: (-t[0], t[1].name))


def todo_of(path, feature):
    sha = T.sha256_of(path)
    n = T.page_count(path)
    return sha, n, [p for p in range(1, n + 1) if not T.cache_path(sha, p, feature).exists()]


def status(feature):
    rows = reports()
    full = 0
    for year, path in rows:
        sha, n, todo = todo_of(path, feature)
        full += not todo
        print('  %d  %-40s %4d pages  %4d read  %s' % (year, path.name, n, n - len(todo),
                                                     'done' if not todo else ''))
    print('%d of %d reports fully read (%s)' % (full, len(rows), feature))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--batch', type=int, help='how many reports this run reads')
    ap.add_argument('--feature', choices=sorted(M.PRICE_PER_PAGE), default='text')
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--status', action='store_true')
    ap.add_argument('--no-aws-check', action='store_true', help='skip reading the AWS budget (tests)')
    a = ap.parse_args()
    if a.status:
        return status(a.feature)
    if not a.batch:
        sys.exit('--batch N is required: say how many reports this run may read')

    price = M.PRICE_PER_PAGE[a.feature]
    plan = []
    for year, path in reports():
        if len(plan) == a.batch:
            break
        sha, n, todo = todo_of(path, a.feature)
        if not todo:
            continue
        if not T.landed(sha):
            print('  %d  %s NOT LANDED -- skipped; run it through scripts/ingest.py' % (year, path.name))
            continue
        plan.append((year, path, sha, todo))
    pages = sum(len(t) for *_, t in plan)
    est = round(pages * price, 4)
    ceiling = round(est * MARGIN + 0.01, 2)
    before = M.spent(month=M.month_of())
    for year, path, sha, todo in plan:
        print('  %d  %-40s %4d page(s) to read' % (year, path.name, len(todo)))
    print('%d report(s), %d page(s) at $%.4f (%s): estimate $%.4f, ceiling $%.2f; this month $%.2f of '
          'the $%.2f cap' % (len(plan), pages, price, a.feature, est, ceiling, before, M.MONTHLY_CAP_USD))
    if a.dry_run or not plan:
        return

    run = '%s-batch-%d' % (dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ'), os.getpid())
    tx = T.client()
    stopped, done, failed = None, 0, 0
    t_start = time.time()
    try:
        with M.Meter(run, ceiling, aws=not a.no_aws_check) as meter, \
                cf.ThreadPoolExecutor(max_workers=a.workers) as pool:
            inflight = {}

            def settle(fut):
                nonlocal done, failed
                sha, page, name = inflight.pop(fut)
                try:
                    resp = fut.result()
                except Exception as e:                       # noqa: BLE001 -- counted as spent, reported
                    meter.outcome(sha, page, a.feature, 'failed:%s' % type(e).__name__)
                    failed += 1
                    print('  %s p%d FAILED (counted as spent): %s'
                          % (name, page, str(e).splitlines()[0][:160]), flush=True)
                    return
                resp.pop('ResponseMetadata', None)
                cp = T.cache_path(sha, page, a.feature)
                cp.parent.mkdir(parents=True, exist_ok=True)
                tmp = cp.with_suffix('.tmp')
                tmp.write_text(json.dumps(resp))
                os.replace(tmp, cp)
                meter.outcome(sha, page, a.feature, 'ok')
                done += 1
                meter.progress(name, pages, done)

            def drain(until):
                while len(inflight) > until:
                    finished, _ = cf.wait(list(inflight), return_when=cf.FIRST_COMPLETED)
                    for f in finished:
                        settle(f)

            try:
                for year, path, sha, todo in plan:
                    for page in todo:
                        try:
                            data, _form = T.page_bytes(path, page)
                        except Exception as e:               # noqa: BLE001 -- nothing sent, nothing spent
                            print('  %s p%d NOT SENT: %s' % (path.name, page, e))
                            continue
                        drain(a.workers - 1)
                        meter.reserve(sha, page, a.feature)
                        inflight[pool.submit(T.call, tx, data, a.feature)] = (sha, page, path.name)
                    print('  %d  %s: all pages sent' % (year, path.name), flush=True)
            finally:
                drain(0)                     # a refusal stops SENDING; what is in flight is kept
    except M.Refused as e:
        stopped = str(e)

    for year, path, sha, todo in plan:
        T.write_out(path, sha, a.feature)
    spent = M.spent(run=run)
    after = M.spent(month=M.month_of())
    print('\nsent %d page(s) (%d failed) in %.0fs with %d workers' % (done + failed, failed,
                                                                     time.time() - t_start, a.workers))
    print('COST: estimate $%.4f | ledger, this run $%.4f | %d pages x $%.4f = $%.4f | month $%.2f -> $%.2f'
          % (est, spent, done + failed, price, (done + failed) * price, before, after))
    M.check_ledger_intact()
    print('ledger intact against the cache')
    if stopped:
        sys.exit('STOPPED: %s' % stopped)


if __name__ == '__main__':
    main()
