#!/usr/bin/env python3
"""THE SPEND METER FOR AMAZON TEXTRACT. Every paid page goes through here, or it is not sent.

    python3 scripts/textract_spend.py --status     # this month: our ledger, AWS's own figure, the caps
    python3 scripts/textract_spend.py --rebuild    # the ledger was lost: one row per cached response

TJ, 27 October 2026: *"we need spend limits too. i need a way to check the spend along the way
... and then cut off this feature if the spend reaches a limit."*

FOUR LIMITS, and they do not share a failure:

  1. THE RUN CEILING   --max-usd, default twice the run's own estimate. Checked before every page.
  2. THE MONTHLY CAP   MONTHLY_CAP_USD below, a calendar month in UTC, which is how AWS bills.
                       Raising it is a commit, on purpose: a cap you can raise with a flag
                       is a suggestion.
  3. THE LATCH         reaching either cap writes build/STOP-TEXTRACT with the reason, and
                       NOTHING is sent while that file exists -- this run, the next run, any
                       run -- until a person reads it and deletes it. build/STOP-METERED, the
                       kill switch every other metered stream obeys, stops this one too.
  4. AWS'S OWN FIGURE  the `lunenburg-textract` budget, read at the start and every
                       AWS_CHECK_EVERY pages. It is a different instrument from our ledger: if
                       AWS has billed more than we recorded, something we cannot see is
                       spending and the run stops. It lags by hours, so it is the backstop,
                       never the meter. Behind it, the budget ACTION set up by
                       scripts/aws/setup_textract.sh denies the IAM user Textract outright at
                       the AWS limit, whether or not this script is running.

THE LEDGER RESERVES BEFORE IT SPENDS. A row is appended and fsynced BEFORE the request goes out,
so a crash mid-call over-counts and never under-counts. A failed call stays counted: whether AWS
billed it is not something we can observe, and the conservative answer is the safe one.

And the ledger is checked against the cache: every paid response is cached, so a cache holding
more responses than the ledger has rows means the ledger was lost or truncated, and the meter
refuses rather than restart at zero.
"""
import argparse
import csv
import datetime as dt
import fcntl
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = Path(os.environ.get('TEXTRACT_STATE') or ROOT / 'build' / 'textract')
LEDGER = STATE / 'ledger.csv'
LOCK = STATE / 'lock'
CACHE = STATE / 'cache'
CURRENT = STATE / 'current.json'      # the run in progress, for the dashboard
AWS_LAST = STATE / 'aws-last.json'    # the last time AWS's own figure was read, and what it said
# A SANDBOXED LEDGER GETS A SANDBOXED LATCH. Before 28 October 2026 a test that set TEXTRACT_STATE
# and forgot TEXTRACT_LATCH tripped the REAL latch on a $0.40 test cap -- safe, but a test must
# never be able to stop production.
LATCH = Path(os.environ.get('TEXTRACT_LATCH')
             or (Path(os.environ['TEXTRACT_STATE']) / 'STOP-TEXTRACT' if os.environ.get('TEXTRACT_STATE')
                 else ROOT / 'build' / 'STOP-TEXTRACT'))
METERED_STOP = ROOT / 'build' / 'STOP-METERED'

# US East (N. Virginia) list price, first million pages a month, read off
# https://aws.amazon.com/textract/pricing/ on 27 October 2026. Re-read it if the region changes.
PRICE_PER_PAGE = {'tables': 0.015, 'text': 0.0015,
                  # a SECOND tables read of a page whose grid came back wrong, sent as a rendered image
                  # (the 1991-2010 close-out, 30 Oct 2026): the same AnalyzeDocument price
                  'tables-reread': 0.015}

MONTHLY_CAP_USD = 8.00           # ours. The AWS budget sits ABOVE it, at $10, so this one should always
                                 # trip first and that one never. TJ, 31 October 2026, lowering both from
                                 # $70/$75 once the annual reports were finished: "reduce the textextract
                                 # limit again, backdown to like $10 a month". History: $50 -> $58 -> $70
                                 # (29-30 Oct 2026) for the 1959-1990 annual reports.
BUDGET_NAME = 'lunenburg-textract'
PROFILE = os.environ.get('TEXTRACT_PROFILE', 'lunenburg-textract')   # the narrow user, never default
if os.environ.get('TEXTRACT_STATE') and os.environ.get('TEXTRACT_TEST_CAP'):
    MONTHLY_CAP_USD = float(os.environ['TEXTRACT_TEST_CAP'])   # a sandboxed test only; never the real ledger
AWS_CHECK_EVERY = 100            # pages between reads of AWS's own figure
AWS_TOLERANCE_USD = 1.00         # AWS rounds and lags; past this, the gap is real

FIELDS = ['at', 'month', 'run', 'sha256', 'page', 'feature', 'usd', 'event']


class Refused(Exception):
    """The meter said no. The message says why, and is meant to be printed as it is."""


def month_of(t=None):
    return (t or dt.datetime.now(dt.timezone.utc)).strftime('%Y-%m')


def rows():
    if not LEDGER.exists():
        return []
    with open(LEDGER, newline='') as f:
        return list(csv.DictReader(f))


def spent(month=None, run=None):
    total = 0.0
    for r in rows():
        if r['event'] != 'reserve':
            continue
        if month and r['month'] != month:
            continue
        if run and r['run'] != run:
            continue
        total += float(r['usd'])
    return round(total, 4)


def spent_since(hours):
    cut = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=hours)
    return round(sum(float(r['usd']) for r in rows() if r['event'] == 'reserve'
                     and dt.datetime.fromisoformat(r['at']) >= cut), 4)


def cached_responses():
    return sorted(CACHE.glob('*/p*-*.json')) if CACHE.exists() else []


def check_ledger_intact():
    """More paid responses on disk than reservations in the ledger means the ledger lost rows."""
    reserved = {(r['sha256'], r['page'], r['feature']) for r in rows() if r['event'] == 'reserve'}
    missing = [p for p in cached_responses()
               if (p.parent.name, str(int(p.stem.split('-')[0][1:])), p.stem.split('-', 1)[1])
               not in reserved]
    if missing:
        raise Refused('the ledger is missing %d paid response(s) the cache holds, e.g. %s -- it was '
                      'lost or truncated. Run `textract_spend.py --rebuild` and read the result '
                      'before sending anything.' % (len(missing), missing[0]))


def latched():
    # TEXTRACT_IGNORE_METERED=1 lets Textract alone run while STOP-METERED keeps the meeting backlog
    # paused (30 Oct 2026, the annual-report re-reads). The latch, the caps and AWS's budget still bind.
    stops = (LATCH,) if os.environ.get('TEXTRACT_IGNORE_METERED') == '1' else (LATCH, METERED_STOP)
    for p in stops:
        if p.exists():
            return '%s exists: %s' % (p.name, p.read_text().strip() or '(no reason given)')
    return None


def trip(reason):
    """Cut the feature off until a person turns it back on."""
    LATCH.parent.mkdir(parents=True, exist_ok=True)
    LATCH.write_text('%s  %s\nDelete this file to allow Textract again, after reading why it tripped.\n'
                     % (dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'), reason))
    return reason


def _append(row):
    STATE.mkdir(parents=True, exist_ok=True)
    new = not LEDGER.exists()
    with open(LEDGER, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)
        f.flush()
        os.fsync(f.fileno())


def aws_actual(session=None):
    """AWS's own month-to-date Textract spend from the budget, or (None, why-not)."""
    try:
        import boto3
        s = session or boto3.Session(profile_name=PROFILE)
        account = s.client('sts').get_caller_identity()['Account']
        b = s.client('budgets', region_name='us-east-1').describe_budget(
            AccountId=account, BudgetName=BUDGET_NAME)['Budget']
        return float(b['CalculatedSpend']['ActualSpend']['Amount']), None
    except Exception as e:                                  # noqa: BLE001 -- reported, never hidden
        return None, '%s: %s' % (type(e).__name__, str(e).splitlines()[0][:160])


class Meter:
    """Hold the lock for a whole run, and price every page before it is sent."""

    def __init__(self, run, ceiling, aws=True, session=None, out=print):
        self.run, self.ceiling, self.aws, self.session, self.out = run, ceiling, aws, session, out
        self.sent = 0
        self._fh = None

    def __enter__(self):
        STATE.mkdir(parents=True, exist_ok=True)
        self._fh = open(LOCK, 'w')
        try:
            fcntl.flock(self._fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Refused('another Textract run holds %s; two runs would both pass the cap check'
                          % LOCK)
        check_ledger_intact()
        why = latched()
        if why:
            raise Refused(why)
        self.check_aws(start=True)
        return self

    def __exit__(self, *exc):
        CURRENT.unlink(missing_ok=True)
        if self._fh:
            fcntl.flock(self._fh, fcntl.LOCK_UN)
            self._fh.close()

    def check_aws(self, start=False):
        if not self.aws:
            return
        actual, why = aws_actual(self.session)
        mine = spent(month=month_of())
        AWS_LAST.write_text(json.dumps({'at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
                                        'actual': actual, 'ledger': mine, 'error': why}))
        if actual is None:
            if start:
                self.out('AWS budget NOT READABLE (%s) -- running on our ledger alone; the budget '
                         'action still denies Textract at the AWS limit' % why)
            return
        self.out('AWS reports $%.2f of Textract this month; our ledger says $%.2f' % (actual, mine))
        if actual > mine + AWS_TOLERANCE_USD:
            raise Refused(trip('AWS has billed $%.2f of Textract this month and our ledger holds $%.2f: '
                               'something we did not record is spending' % (actual, mine)))
        if actual >= MONTHLY_CAP_USD:
            raise Refused(trip('AWS reports $%.2f this month, at or past the $%.2f cap'
                               % (actual, MONTHLY_CAP_USD)))

    def progress(self, doc, planned, done):
        CURRENT.write_text(json.dumps({'run': self.run, 'doc': doc, 'planned': planned, 'done': done,
                                       'pid': os.getpid(), 'ceiling': self.ceiling,
                                       'spent': spent(run=self.run),
                                       'at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}))

    def reserve(self, sha256, page, feature):
        """Say yes or no to one page. Yes is written down before the caller spends it."""
        why = latched()
        if why:
            raise Refused(why)
        usd = PRICE_PER_PAGE[feature]
        month = spent(month=month_of())
        run = spent(run=self.run)
        if month + usd > MONTHLY_CAP_USD:
            raise Refused(trip('the monthly cap: $%.4f spent of $%.2f, and the next page is $%.4f'
                               % (month, MONTHLY_CAP_USD, usd)))
        if run + usd > self.ceiling:
            # The run ceiling stops THIS run. It does not latch: the next run brings its own estimate.
            raise Refused('the run ceiling: $%.4f spent of $%.2f' % (run, self.ceiling))
        _append({'at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
                 'month': month_of(), 'run': self.run, 'sha256': sha256, 'page': page,
                 'feature': feature, 'usd': usd, 'event': 'reserve'})
        self.sent += 1
        if self.sent % AWS_CHECK_EVERY == 0:
            self.check_aws()
        return usd

    def outcome(self, sha256, page, feature, event):
        """'ok' or 'failed:<reason>'. Costs nothing; the reservation already counted the page."""
        _append({'at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
                 'month': month_of(), 'run': self.run, 'sha256': sha256, 'page': page,
                 'feature': feature, 'usd': 0, 'event': event[:200]})


def running():
    """Is a run holding the lock? Asked of the lock itself, not of a process list (pgrep matches itself)."""
    if not LOCK.exists():
        return False
    with open(LOCK) as fh:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(fh, fcntl.LOCK_UN)
    return False


def configured():
    """Does this machine hold credentials for the narrow user? Read from the files, no network."""
    for f in ('credentials', 'config'):
        p = Path.home() / '.aws' / f
        if p.exists() and ('[%s]' % PROFILE in p.read_text() or '[profile %s]' % PROFILE in p.read_text()):
            return True
    return False


def dashboard():
    """Everything the ingestion dashboard shows, read from disk. No network: it runs every 20s."""
    cur = json.loads(CURRENT.read_text()) if CURRENT.exists() else None
    live = running()
    return {'running': live, 'current': cur if live else None,
            'stale_current': bool(cur and not live),
            'day': spent_since(24), 'month': spent(month=month_of()), 'all': spent(),
            'cap': MONTHLY_CAP_USD, 'latch': latched(),
            'pages_day': sum(1 for r in rows() if r['event'] == 'reserve' and
                             dt.datetime.fromisoformat(r['at']) >=
                             dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=24)),
            'failed_day': sum(1 for r in rows() if r['event'].startswith('failed') and
                              dt.datetime.fromisoformat(r['at']) >=
                              dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=24)),
            'aws': json.loads(AWS_LAST.read_text()) if AWS_LAST.exists() else None,
            'used': LEDGER.exists(), 'configured': configured()}


def status():
    m = month_of()
    mine = spent(month=m)
    print('Textract, %s (UTC)' % m)
    print('  our ledger      $%8.4f of the $%.2f monthly cap (%d%%), %d page(s) reserved'
          % (mine, MONTHLY_CAP_USD, 100 * mine / MONTHLY_CAP_USD,
             sum(1 for r in rows() if r['event'] == 'reserve' and r['month'] == m)))
    actual, why = aws_actual()
    print('  last 24 hours   $%8.4f' % spent_since(24))
    print('  AWS budget      ' + ('$%8.4f  (lags by hours; the backstop, not the meter)' % actual
                                  if actual is not None else 'not readable: ' + why))
    print('  all time        $%8.4f' % spent())
    print('  latch           ' + (latched() or 'off -- Textract allowed'))
    try:
        check_ledger_intact()
        print('  ledger          intact against %d cached response(s)' % len(cached_responses()))
    except Refused as e:
        print('  ledger          REFUSING: %s' % e)


def rebuild():
    """One reservation per cached response we have no row for, priced and dated by the file."""
    reserved = {(r['sha256'], r['page'], r['feature']) for r in rows() if r['event'] == 'reserve'}
    added = 0
    for p in cached_responses():
        sha, page, feature = p.parent.name, str(int(p.stem.split('-')[0][1:])), p.stem.split('-', 1)[1]
        if (sha, page, feature) in reserved:
            continue
        t = dt.datetime.fromtimestamp(p.stat().st_mtime, dt.timezone.utc)
        _append({'at': t.isoformat(timespec='seconds'), 'month': month_of(t), 'run': 'rebuilt',
                 'sha256': sha, 'page': page, 'feature': feature,
                 'usd': PRICE_PER_PAGE[feature], 'event': 'reserve'})
        added += 1
    print('rebuilt %d reservation(s) from the cache. Responses that FAILED were never cached, so the '
          'ledger may now read LOW: compare --status against the AWS budget before trusting it.' % added)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--status', action='store_true')
    g.add_argument('--rebuild', action='store_true')
    a = ap.parse_args()
    try:
        status() if a.status else rebuild()
    except Refused as e:
        sys.exit('REFUSED: %s' % e)
