"""Does the publisher's own copy of each archived document still open?

On 29 August 2026 the answer turned out to be: for 60% of the district's, no. Every
failure was a Google Drive or Docs link; the town's own web server answered 81 of 81 and
the state 8 of 8. Among the restricted ones was the FY27 proposed budget document, which
is where the $26,572,288 appropriation the whole site is built on comes from.

This is the archive's reason for existing, demonstrated. It is also a live risk to the
site's credibility in a specific way: a source link that opens a Google sign-in wall reads
to a resident as though the project is citing something it cannot show, which is the
opposite of true. So the status is recorded, and the sources page says "our copy is the
only public one" instead of sending somebody to a login screen.

Slow on purpose -- one request per document, no concurrency, a real user agent. Run it
occasionally, not in the build; the build reads the CSV this writes.

    python3 scripts/check_source_links.py
"""
import os, sys, csv, json, subprocess, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, 'fy28/src/data/sources.json')
OUT = os.path.join(ROOT, 'sources/data/link-status.csv')
# Same identity as the crawlers. Checking whether a link is public is a request like any
# other, and a checker that disguises itself as a browser would be measuring what a
# disguised request gets rather than what a resident gets.
UA = ('Mozilla/5.0 (compatible; LunenburgBudgetProject/1.0; '
      '+https://lunenburgbudgetproject.org)')


def status(url):
    r = subprocess.run(['curl', '-s', '-o', os.devnull, '-w', '%{http_code}',
                        '-L', '--max-time', '15', '-A', UA, url],
                       capture_output=True, text=True)
    return r.stdout.strip() or '000'


def main():
    doc = json.load(open(INDEX))
    items = [(g['section'], i['path'], i.get('stars', 0), i['title'], i['upstream'])
             for g in doc['groups'] for i in g['items'] if i.get('upstream')]
    print(f'checking {len(items)} upstream links, one at a time\n')
    rows, bad = [], 0
    for n, (sec, path, stars, title, url) in enumerate(items, 1):
        code = status(url)
        ok = code.startswith('2')
        bad += not ok
        rows.append(dict(path=path, section=sec, stars=stars, url=url, code=code,
                         public=int(ok)))
        if not ok:
            print(f'  {code}  {title[:56]}')
        if n % 25 == 0:
            print(f'  ... {n}/{len(items)}')
    today = datetime.date.today().isoformat()
    with open(OUT, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['path', 'section', 'stars', 'url', 'code', 'public', 'checked'])
        for r in rows:
            w.writerow([r['path'], r['section'], r['stars'], r['url'], r['code'],
                        r['public'], today])
    print(f'\n{len(rows) - bad} of {len(rows)} still open to the public')
    hosts = {}
    for r in rows:
        h = r['url'].split('/')[2]
        hosts.setdefault(h, [0, 0])[0 if r['public'] else 1] += 1
    for h, (ok, no) in sorted(hosts.items(), key=lambda x: -x[1][1]):
        print(f'   {h:<26} {ok:>4} open  {no:>4} restricted')
    print(f'wrote {OUT}')


if __name__ == '__main__':
    main()
