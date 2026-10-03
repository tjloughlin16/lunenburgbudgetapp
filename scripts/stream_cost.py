#!/usr/bin/env python3
"""What a metered stream ACTUALLY costs per item, measured from its own output.

Every file `extract_official_votes.py` and `write_recording_minutes.py` write carries a
`cost_usd` for the call that produced it. So the cost of a stream is a measurement, and
the only reason it was ever a constant in prose is that nobody read the field.

WHY THIS EXISTS. The ingest dashboard and notes/generated/AGENTIC-BACKLOG.md both stated
`~0.03% of the week each` for the votes stream. Measured over 256 runs on 3 October 2026
it is $0.1113, which against the calibrated `1% of the week >= $5.70` is **0.0195% or
less** -- an overstatement of 35 to 55%, in the figure anybody sizes a batch against.

It is rule 2 in a place rule 2 had not been applied: *a number typed into a sentence is
the only thing here that can be silently wrong*, and the sentence was the one that tells
you what a thousand model calls will cost.

THE DENOMINATOR IS A BOUND, NOT A RATE. `WEEK_USD` is the measured LOWER bound on what 1%
of the weekly allowance is worth, so the percentage this returns is an UPPER bound on the
share -- which is the right direction for a figure used to decide whether to start.
notes/findings/METERED-BATCH-COST.md carries the derivation and what it does not settle.
"""
import glob
import json
import os
import statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 1% of the weekly allowance, in API-equivalent dollars: a LOWER bound, measured
# 3 October 2026 from the weekly bar moving 37% -> 42% against $28.50 of scripted spend
# while an interactive session also consumed part of it. ~/.claude/CLAUDE.md's standing
# convention is ~$5; this is the measurement that refines it.
WEEK_USD = 5.70

# The most recent N files, so the figure follows the model and the prompt rather than
# averaging over every run since the stream began.
RECENT = 300


def measured(subdir, field='cost_usd'):
    """(mean usd, n) over the most recently written files, or (None, 0) if none price."""
    paths = glob.glob(os.path.join(ROOT, 'sources', 'data', subdir, '*', '*.json'))
    paths.sort(key=os.path.getmtime, reverse=True)
    costs = []
    for p in paths[:RECENT]:
        try:
            v = json.load(open(p, encoding='utf-8')).get(field)
        except (ValueError, OSError):
            continue
        if isinstance(v, (int, float)) and v > 0:
            costs.append(float(v))
    if not costs:
        return None, 0
    return statistics.mean(costs), len(costs)


def phrase(subdir, fallback, html=True):
    """A cost line, derived -- or `fallback` if nothing prices yet.

    Says `<=` because WEEK_USD is a lower bound, and names the sample, because a mean over
    four runs and a mean over three hundred are not the same claim.

    `html=False` for a caller writing MARKDOWN. The first version returned `&le;`
    unconditionally and the generated backlog came out reading `&le;0.019% of the week`,
    which is the entity leaking into a file an agent reads as plain text.
    """
    mean, n = measured(subdir)
    if not mean:
        return fallback
    return ('%s%.3f%% of the week each (measured: $%.3f over the last %d), runs by itself'
            % ('&le;' if html else '\u2264', mean / WEEK_USD, mean, n))


if __name__ == '__main__':
    for d in ('official-votes', 'recording-minutes'):
        m, n = measured(d)
        print('%-20s %s' % (d, 'nothing priced' if not m else
                            '$%.4f mean over %d  ->  <=%.4f%% of the week each' % (m, n, m / WEEK_USD)))
