"""Lunenburg business certificate (DBA) registrations.

Source: the town's own business certificate records, cleaned and categorised in a
separate project (~/lunenburgbusiness). Copied to sources/data/business/.

IMPORTANT about what this is. A business certificate is a d/b/a filing under
M.G.L. c.110 §5 -- required of sole proprietorships and partnerships trading under a
name that is not the owner's. Corporations and LLCs register with the Secretary of the
Commonwealth instead, so they are NOT all here. These counts measure *registrations*,
not employment, revenue or floor space, and they are a different universe from the 234
establishments the Census counts.

Coverage: certificates run four years, and the town's file retains expired ones back to
roughly 2018. Every record issued 2016-2021 is now lapsed, renewed or discontinued,
which is exactly what a four-year term predicts -- so 2018 onward is usable and anything
earlier is incomplete. 2026 is a partial year (records pulled May 2026).
"""
import csv, collections, os

DATA = os.path.join(os.path.dirname(__file__), '..', 'sources', 'data', 'business')

def _load(name):
    with open(os.path.join(DATA, name)) as fh:
        return list(csv.DictReader(fh))

ROWS = _load('merged_dataset.csv')
CATS = {r['cert_number']: r for r in _load('categorized.csv')}

ACTIVE = [r for r in ROWS if r['status'] == 'active']

# New formations vs renewals, by year of issue
_new = collections.Counter(); _renew = collections.Counter()
for r in ROWS:
    y = r['issue_date'][:4] if r['issue_date'] else None
    if not y:
        continue
    (_renew if r['prior_cert_number'] else _new)[y] += 1

FORMATION_HISTORY = [
    dict(year=int(y), new=_new[y], renewals=_renew[y],
         partial=(y == '2026'))
    for y in sorted(set(_new) | set(_renew)) if y >= '2018'
]

# Categories that normally require commercial premises rather than a spare room
NEEDS_PREMISES = {'food_beverage', 'retail', 'automotive_transport',
                  'personal_services', 'pet_services'}

CATEGORIES = collections.Counter(
    CATS.get(r['cert_number'], {}).get('category', 'unknown') for r in ACTIVE)

# Address analysis: which are on the town's commercial corridors
CORRIDOR_KEYS = ['massachusetts ave', 'mass ave', 'chase rd', 'chase road',
                 'leominster-shirley', 'leominster shirley', 'electric ave',
                 'summer st', 'main st']

_addr = collections.Counter((r['address'] or '').lower().strip() for r in ACTIVE)
_on_corridor = sum(1 for r in ACTIVE
                   if any(k in (r['address'] or '').lower() for k in CORRIDOR_KEYS))
_multi = [(a, c) for a, c in _addr.items() if c > 1 and a]

SUMMARY = dict(
    activeCertificates=len(ACTIVE),
    totalRecords=len(ROWS),
    onCorridor=_on_corridor,
    onResidentialStreet=len(ACTIVE) - _on_corridor,
    corridorPct=round(_on_corridor / len(ACTIVE) * 100, 1),
    multiTenantAddresses=len(_multi),
    businessesAtMultiTenant=sum(c for _, c in _multi),
    needsPremises=sum(1 for r in ACTIVE
                      if CATS.get(r['cert_number'], {}).get('category') in NEEDS_PREMISES),
    peakYear=max((f for f in FORMATION_HISTORY if not f['partial']),
                 key=lambda f: f['new'])['year'],
    peakNew=max(f['new'] for f in FORMATION_HISTORY if not f['partial']),
    latestFull=[f for f in FORMATION_HISTORY if not f['partial']][-1],
)
SUMMARY['declineFromPeak'] = round(
    (SUMMARY['latestFull']['new'] / SUMMARY['peakNew'] - 1) * 100, 1)
SUMMARY['needsPremisesPct'] = round(
    SUMMARY['needsPremises'] / SUMMARY['activeCertificates'] * 100)

TOP_CATEGORIES = [dict(category=k, count=v) for k, v in CATEGORIES.most_common(10)]

if __name__ == '__main__':
    print('FORMATIONS BY YEAR')
    for f in FORMATION_HISTORY:
        print(f"  {f['year']}{'*' if f['partial'] else ' '}  new {f['new']:>4}  renewals {f['renewals']:>4}")
    print('\nSUMMARY')
    for k, v in SUMMARY.items():
        print(f'  {k:<26} {v}')
