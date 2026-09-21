"""One name per stabilization fund, whatever the page happened to call it.

    from fund_names import canonical
    canonical('Unibank Sewer Capacity Reserve Stabilization')  -> 'Sewer Reserve Capacity'

WHY THIS IS A MODULE AND NOT A REGEX IN WHOEVER NEEDS IT

The town does not name these funds consistently, and neither does the scanner. Across
fifteen Treasurer's Cash pages one fund appears as all of:

    Unibank Sewer Reserve Capacity Stabilization
    Unibank Sewer Capacity Reserve Stabilization     <- the town swapped two words
    Sewer Reserve Capacity Stabilization Fund - Expendable

and another as `Unibank Sewer I/I Stabilization` and `Unibank Sewer I/1 Stabilization`,
where the difference is a capital I read as a one. The general fund is `Bartholomew
Stabilization Fund` on the cash page, a bare `STABILIZATION` in the trust table, and
`stabilization` in the MUNIS ledger.

Every one of those was silently splitting one fund into two in some count or other, and
the cost is not cosmetic: a coverage table built on the raw labels reported OPEB missing
for FY2022 to FY2025 when the archive holds all four, because the later pages write
`Bartholomew - OPEB` and the earlier ones write `OPEB`. A gap that is really a spelling
sends somebody to re-read a document that was read correctly the first time.

HOW IT DECIDES, and the order matters

1. The CUSTODIAN is not part of the name. `Unibank`, `Bartholomew`, `TD BankNorth`,
   `Main Street Bank` say where the money is kept, and it moves -- 8129 is at TD
   BankNorth in most years and the trust table never mentions a bank at all.
2. Then the distinguishing WORDS, as a set rather than a sequence, because the town
   swaps them. `{sewer, reserve, capacity}` is one fund however it is ordered.
3. `I/1` is `I/I`. A scanner cannot tell them apart in this typeface and neither can a
   reader without the context.

WHAT IT REFUSES TO DO. It returns None for anything it does not recognise, and callers
must handle that rather than falling back to the raw string -- because a fund silently
named after itself is exactly how the splitting happened in the first place. A new fund
appears here deliberately, once somebody has looked at it.
"""
import re

CUSTODIANS = re.compile(
    r'^\s*(bartholomew|batholomew|unibank|td\s*banknorth|main\s*street\s*bank|'
    r'bank\s*hometown|eastern\s*bank|fidelity\s*bank|century\s*bank|'
    r'belmont\s*savings\s*bank|newburyport\s*bank|harbor\s*one\s*bank|'
    r'enterprise\s*bank|bluestone\s*bank|people.s\s*united\s*bank)\s*-?\s*', re.I)

# Distinguishing words -> the one name. Matched as a SET, so word order cannot matter.
RULES = [
    (frozenset({'sewer', 'reserve', 'capacity'}), 'Sewer Reserve Capacity'),
    (frozenset({'sewer', 'capital', 'reserve'}), 'Sewer Capital Reserve'),
    (frozenset({'sewer', 'ii'}), 'Sewer Inflow/Infiltration'),
    (frozenset({'inflow'}), 'Sewer Inflow/Infiltration'),
    (frozenset({'infiltration'}), 'Sewer Inflow/Infiltration'),
    (frozenset({'health', 'insurance'}), 'Health Insurance'),
    (frozenset({'opioid'}), 'Opioid Settlement'),
    (frozenset({'opeb'}), 'OPEB'),
    (frozenset({'vehicle'}), 'Vehicle/Equipment'),
    (frozenset({'equipment'}), 'Vehicle/Equipment'),
    (frozenset({'zoning'}), 'Zoning Incentive'),
    (frozenset({'playground'}), 'Zoning Incentive'),   # the ledger's name for 8129
    (frozenset({'town', 'building'}), 'Town Building'),
    (frozenset({'special', 'purpose'}), 'Special Purpose'),
    (frozenset({'conservation'}), 'Conservation Trust'),
]

# The account number is the strongest identity where a document prints one.
BY_CODE = {'8124': 'Stabilization (general)', '8125': 'Conservation Trust',
           '8129': 'Zoning Incentive', '8132': 'Sewer Reserve Capacity',
           '8133': 'Sewer Inflow/Infiltration', '8136': 'Vehicle/Equipment',
           '8137': 'OPEB', '8138': 'Sewer Capital Reserve',
           '8140': 'Health Insurance', '8141': 'Opioid Settlement'}


# CYRILLIC LETTERS THAT LOOK EXACTLY LIKE LATIN ONES, which is what the recogniser
# sometimes returns. FY2023's page gives `Bartholomew - ОРЕВ` where every one of those
# four characters is Cyrillic: U+041E, U+0420, U+0415, U+0412. It renders identically to
# OPEB, compares equal to nothing, and cost that fund a year -- the coverage table said
# FY2023 was missing when the page prints it plainly.
#
# Nothing here can be spotted by reading the output, which is the whole problem: the only
# way to see it is to look at the codepoints. So they are folded before anything else.
HOMOGLYPHS = str.maketrans({
    '\u0410': 'A', '\u0412': 'B', '\u0415': 'E', '\u041a': 'K', '\u041c': 'M',
    '\u041d': 'H', '\u041e': 'O', '\u0420': 'P', '\u0421': 'C', '\u0422': 'T',
    '\u0425': 'X', '\u0430': 'a', '\u0435': 'e', '\u043e': 'o', '\u0440': 'p',
    '\u0441': 'c', '\u0443': 'y', '\u0445': 'x',
})


def canonical(label, code=None):
    """The fund's one name, or None where nothing here recognises it."""
    if code and str(code).strip() in BY_CODE:
        return BY_CODE[str(code).strip()]
    t = ' '.join((label or '').translate(HOMOGLYPHS).split())
    t = CUSTODIANS.sub('', t)
    # `I/1` is `I/I` -- a scanner cannot tell a capital I from a one in this face. It is
    # folded to a plain token FIRST, because the slash then has to go: leaving it in made
    # `vehicle/equipment` a single word, so the `vehicle` rule never matched and every
    # Vehicle/Equipment row fell through to the general fund.
    low = t.lower().replace('i/1', 'i/i').replace('l/i', 'i/i').replace('i/i', ' ii ')
    words = set(re.findall(r'[a-z]+', low))
    for keys, name in RULES:
        if keys <= words:
            return name
    # The general fund is the one with no distinguishing word at all: `Stabilization
    # Fund`, `STABILIZATION`, `stabilization`. It is matched LAST for that reason --
    # every other fund also contains the word.
    if 'stabilization' in words or low.strip() in ('stabilization', 'stabilization fund'):
        return 'Stabilization (general)'
    return None
