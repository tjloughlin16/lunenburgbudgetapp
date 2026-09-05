#!/usr/bin/env python3
"""Measure the rate limit on /api/query, and check the documentation matches.

    python3 scripts/check_rate_limit.py [--record]

The limit lives in a Cloudflare zone rule, not in this repository, so nothing here can
know it. That makes it exactly the kind of number rule 2 forbids typing into a sentence --
and llms.txt has to state it, because an agent that gets a seventeen-byte
`error code: 1015` and does not know what it means will report the site as broken.

So it is MEASURED: send requests until one is refused, count the ones that got through.
Then compare that with what `sources/data/rate-limit.txt` says, which is what the published
prose is generated from. If somebody changes the zone rule and not the file, this fails.

It costs one burst of small queries and ten seconds of being blocked, which is the price
of the number being true.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORD = os.path.join(ROOT, 'sources', 'data', 'rate-limit.txt')
URL = ('https://lunenburgbudgetproject.org/api/query?sql=SELECT%201%20AS%20a&probe=')
UA = {'User-Agent': 'lunenburgbudgetproject.org rate-limit probe'}


def measure(cap=40):
    allowed = 0
    for i in range(cap):
        try:
            urllib.request.urlopen(
                urllib.request.Request(f'{URL}{i}', headers=UA), timeout=30)
            allowed += 1
        except urllib.error.HTTPError as e:
            if e.code == 429:
                return allowed
            raise
    return None          # never refused within `cap`


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--record', action='store_true',
                    help='write the measured limit as the documented one')
    args = ap.parse_args()

    print('probing — this deliberately trips the limit and waits it out')
    got = measure()
    if got is None:
        print('  no refusal within 40 requests: either no rule is active, or its '
              'threshold is above 40')
        return 1
    print(f'  {got} requests answered before HTTP 429')
    time.sleep(11)       # let the mitigation window pass

    if args.record:
        with open(RECORD, 'w') as fh:
            fh.write(f'{got}\n')
        print(f'  recorded {got} in {os.path.relpath(RECORD, ROOT)}')
        return 0

    want = int(open(RECORD).read().strip()) if os.path.exists(RECORD) else None
    if want is None:
        print('\n  nothing recorded yet — run with --record')
        return 1

    # A BAND, not equality. The counter is per colo and the window rolls, so two probes
    # minutes apart measured 8 and 12 against a rule set to 10. Asserting equality would
    # fail half the time for no reason, and a check that flaps is a check nobody reads.
    #
    # What matters is the direction: if the real limit is much TIGHTER than what this
    # project publishes, agents are being turned away while being told they will not be.
    # Looser than published is harmless.
    if got < want / 2:
        print(f'\n  the zone refused after {got} requests; this repository publishes '
              f'about {want}.\n  Agents are being turned away sooner than they are told. '
              f'Either raise the rule or\n  lower the published figure — the published one '
              f'is what they will believe.')
        return 1
    print(f'\nok: refused after {got}, published as about {want} — within tolerance.\n'
          f'  The count varies between probes because the window rolls and the counter is '
          f'per colo,\n  which is why this checks a band rather than a number.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
