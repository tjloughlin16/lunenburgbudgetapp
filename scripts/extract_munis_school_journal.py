"""The school department's MUNIS journal detail, FY2023-FY2026 -- every posting, redacted by us.

    python3 scripts/extract_munis_school_journal.py            # extract, tie, redact, write
    python3 scripts/extract_munis_school_journal.py --check    # rebuild in memory; fail if an
                                                                #   output differs or a tie fails
    python3 scripts/extract_munis_school_journal.py --review   # print every DISTINCT vendor and
                                                                #   description AFTER redaction,
                                                                #   for a person to read; writes
                                                                #   nothing
    python3 scripts/extract_munis_school_journal.py --out DIR  # write (or --check) the three
                                                                #   outputs in DIR instead, and read
                                                                #   the by-eye reading from DIR --
                                                                #   a CANDIDATE, for a privacy read
                                                                #   before anything is published

THE SOURCE. `glytdbud`, YEAR-TO-DATE BUDGET REPORT, `FOR 2026 13`, run with `Print journal
detail: Y` from `2023/ 0` to `2026/13`, generated 10/07/2026 21:47: 1,744 pages, the Town's
second answer to the 4 September 2026 records request
(`sources/town-ledgers/account-details/PROVENANCE-fy2023-fy2026-p13-school-journal.md`).
The Town redacted it before sending; its redaction is INCOMPLETE on the rendered page, so the
raw is held PRIVATE (`sources/data/redactions.csv`) and is read here from the gitignored
local copy, or fetched from the private bucket into it. Nothing private is written by this
script: its three outputs are OUR redacted reading.

    sources/data/munis-school-journal.csv              one row per journal line
    sources/data/munis-school-journal-accounts.csv     one row per account: the FY2026 figures
                                                       the report prints, and its org and fund
    sources/data/munis-school-journal-image-pages.csv  the three picture pages' lines, through
                                                       the SAME redaction as the journal

HOW THE PAGE IS READ. The report is set in one monospaced face at a pitch of 4.8205pt from
x = 50.4pt, so every character's column is `round((x - 50.4) / 4.8205)` and the page
rebuilds as the fixed-width printout it was. Fields are then cut by COLUMN, never by
splitting on spaces -- a vendor name and the description beside it run together otherwise.
Three pages (34, 643, 1080) are pictures: the Town flattened them to burn its redactions
in. They were read by eye into `build/private/munis/munis-school-journal-image-pages-reading.csv`
-- PRIVATE, because a reading by eye is a reading of the raw -- and the ties below are what
prove that reading: each of the three accounts they fall in closes to the cent only with
them. What is PUBLISHED of those pages is that reading after `redact()`, exactly as the text
pages are redacted, so the by-eye file and the journal cannot disagree about a name.

WHAT TIES -- and the script refuses to write if any one fails (rule 13):

  1. Every account's FY2026 figures, as printed: ORIGINAL APPROP = the FY2026 `BUC` lines;
     TRANFRS/ADJSTMTS = the FY2026 `BUA` lines; YTD ACTUAL = the FY2026 actual sources
     (API, APM, PRJ, PRH, GEN, GRV, CRP); ENCUMBRANCES = the FY2026 encumbrance sources
     (POE, POL, POM, SOY, YEC, GEL). Which source belongs to which column was NOT assumed:
     it is the only assignment under which all 3,356 accounts close. (`GEL` was first put
     with the actuals and one FY2025 account failed by $258.72 -- an entry described `TO
     RECONCILE PO'S`, against a `POM` of the same amount. It is an encumbrance entry.)
  2. Every `TOTAL` line the report prints, against the accounts above it.
  3. The p1743 GRAND TOTAL, against every account.
  4. FY2023, FY2024 and FY2025 have no printed per-account figures in this run, so they are
     tied to the PUBLISHED period-13 spreadsheets (`sources/data/munis-school-ytd.csv`, run a
     day earlier): for every account both hold, journal actuals = YTD EXPENDED and BUC + BUA
     = REVISED BUDGET, every year.

OUR REDACTION -- the rule, declared here, applied to every row (CLAUDE.md 13e).

THE PRINCIPLE, TJ, 19 October 2026: "we need to remove ANYBODY who is directly named as a
parent or child getting services from the school. anybody contributing to those services as
vendors should be ID'd. It's not NAMES that I'm worried about. It's associating a name to a
disability that we are trying to avoid." So the RECIPIENTS of a school service -- a child, or
a parent or family acting for their child -- are masked wherever they appear, with every
residue that could point back to them (initials, fragments, their check, invoice and receipt
numbers, a sibling row of the same purchase). PROVIDERS and VENDORS are identified: name,
service, amount, invoice and check number. Disability and special education services and
their providers are public -- "knowing who we pay and how much is critical". What stays
confidential is: children; a family's own finances; health or medical detail about an
identifiable person; student incidents. Where a row is unclear the test is whether it lets a
reader attach a disability, a service or a family's circumstances to a person; if it does,
that person is masked.

  * A PERSON PAID AS A VENDOR IS SHOWN BY NAME -- a game official, a DJ, a photographer, a
    contractor (including one placed through an agency named in the description), a
    provider of a disability or special education service, a presenter, a tutor, a staff
    reimbursement or stipend, a scholarship recipient ("scholarships can be listed too"):
    name, vendor number, invoice number and check number all stay, and so does their own
    name inside their own description or invoice number (`hold_words`). A vendor is a person
    unless its name carries a business or public-body marker (`BUSINESS_RE`) or is on the
    declared list (`BUSINESSES`). `name_basis` names the public record that shows the person
    is an employee where one does (below), and otherwise says `paid as vendor` or
    `scholarship award`.
  * A PERSON PAID OR RECORDED AS A PARENT OR FAMILY IS MASKED: written `individual
    (redacted)`, with its vendor number, invoice number and check number dropped, and every
    word of the name removed from every description. The line says so (`PARENT`: a refund, a
    lunch balance or deposit, a bounced check or redeposit, a parent reimbursement, child
    care or extended day, a tuition or placement payment, a student who withdrew). A line
    about TRANSPORTING a child, or on an account of money families pay in (`PARENT_ACCOUNT`:
    activity fees, user charges, SPED transportation, tuition), says nothing on its own about
    who was paid, so there the PAYEE is classified across all their lines
    (`classify_payees`): a PARENT if any of their lines says so (`PARENT_WORD`) -- masked on
    every line; STAFF if any says `STAFF`, or they match an employee record, or (off the
    transport account) they are paid as a vendor on another line or are buying goods or
    paying for their own professional work (`VENDOR_WORDING`) -- shown on every line,
    the student in `STAFF TRANSPORTATION OF <x>` still masked; otherwise UNCERTAIN --
    masked, and counted. A reimbursement for a student incident or damage (`INCIDENT`) is
    masked: naming the staff member narrows which student.
  * TRANSPORTATION IS LISTED BY PAYEE, PARENTS INCLUDED -- TJ: "As long as its not SPECIAL
    EDUCATION." A transportation line is shown, parent or not, unless it posts to a special
    education account, org or fund (`SPED_ACCOUNTS`: SPECIAL ED TRANSPORTATION, the SPED
    circuit breaker fund, SPED grants such as IDEA/240 and 262, tuition, placement and
    out-of-district, student-service accounts) or its text names a special education
    service (`SPED_TEXT`). A special education family stays masked, residue and all.
  * A FAMILY'S PAYMENT INTO THE SCHOOLS -- a revenue line that is one family's money, not a
    day's takings (`FAMILY_REVENUE`: a bounced check, a redeposit, a refund, a corrected
    receipt, a check number), or any revenue line that names a payer we mask -- loses the
    family's check number (`CK#…`), any `RCPT #…` number and its receipt number in `doc_no`,
    whether or not a name was printed. So does a workers' compensation receipt.
  * AN EMPLOYEE NAMED IN TEXT is shown when a public record shows they are one and they are
    named in role (`CLOSE PER <name>`, `INCREASE PER <name>`, `CONFERENCE FOR <name>`) --
    on any account, special education included, since a staff member's name in role ties
    no child to anything; in role, where the 2-year window finds nobody, a roster of ANY
    year or a directory proves it (still ONE person).
    The records are the annual town report staff rosters, FY2011-FY2025
    (`staff-roster-entries.csv`, School Committee members excluded: elected, not employed),
    and the district's and the Town's current staff directories (`school-staff-directory.csv`,
    `staff-directory.csv`; the Town's alone shows a name only beside a town role,
    `TOWN_ROLE`). A match is the surname exactly AND the given name exactly, or its
    initial, or (where the 20-character vendor field cut it) a prefix of 4+ letters; in
    either order (`SURNAME, FIRST`, `SURNAME FIRST`, `FIRST SURNAME`, a login `LSURNAME`); in
    a roster within 2 fiscal years of the line, or a current directory for FY2025-FY2026;
    and it must be ONE person -- two candidates is ambiguous, and stays masked. A surname or
    a given name alone is partial and stays masked; initials alone (`JT`, `L C`) cannot be
    matched at all. EXCEPT on a family line (`FAMILY`: refunds, fees, deposits, tuition,
    placement, transport, tutoring, evaluation, gifts, jury duty and other student-service or
    personal lines), unless the name is an administrative act in role (`ROLE_BEFORE`:
    `CLOSE PER`, `INC`, `CANCEL PER` ...), which says nothing about whose child it is for.
  * A CHILD. In a special education placement, tuition or transport line (`SPED_LINE`), every
    word that is not on the declared vocabulary of those lines (`SPED_WORDS`) is masked. In
    a student-service line (`SERVICE_LINE`: `SERVICES FOR` on a student-service account,
    AT, TVI, vision, home/hospital tutoring or visits, an evaluation, assessment or testing
    FOR somebody, transport for a student, a special education line) every word
    after the trigger that is not on `SERVICE_WORDS` is masked, single letters and two-letter
    fragments included. The Town boxed the child's initials in that slot on every page but
    two; this catches those two and anything like them.
  * A PAYER. A bounced check or a redeposit (`NSF CK #143/<payer>`) names the family that
    wrote it; everything in those lines that is not the programme it paid for is masked, and
    so is the short fragment a receipt line ends on after its last `/`.
  * A CLAIM. A workers' compensation claim number identifies an injured employee; in a
    `WORKER'S COMP` / `CLAIM` / `MIIA` line every `#` number is masked.
  * A NAME IN TEXT that is none of these -- declared one by one in `NAME_TOKENS` and
    `NAMES_IN_TEXT`, from a reading of every distinct description and comment (`--review`).
  * RESIDUE. A 1-3 letter token immediately after `[redacted]`, or ending a field after a
    masked name, is the rest of that name, and is masked too. In a placement, tuition or
    student-service line ANY stray 1-2 letter token is an initial (`TWO_LETTER_OK` excepted).
  * AN IDENTIFIER. `ID#<number>` is masked everywhere, and any bare 7+ digit number on a
    person's line (`LONG_NUMBER`). A masked payee's line loses its CHECK NUMBER -- the Town's
    warrant prints the payee by check number -- and a masked revenue (REF) line loses its
    RECEIPT NUMBER in `doc_no`, for the same reason.
  * A PURCHASE IS MASKED WHOLE. If any row of a purchase order -- its PO rows, and each
    invoice with the PO line it liquidates -- masks its payee, every row of it does, every
    shown name on it is masked, and so are the payee's name and initials in its descriptions
    (`po_consistency`).
  * A SCHOLARSHIP AWARD keeps its fund, year, amount and recipient: a recipient is paid as a
    vendor (above), not as a family. Children named on placement, tuition and student-service
    lines are still masked.
  * A jury-duty line is a personal matter and masks the employee named on it. A private
    donor is masked by hash wherever named (`HASHED_NAMES`).
  * Kept: businesses, public bodies, the MUNIS login on the page, persons paid as vendors,
    and employees named in role.

Every mask writes `[redacted]` (the same token `redact.py` uses), and the script asserts
that no masked value survives anywhere in the output: no masked vendor's name, no declared
name word outside a protected phrase or a matched employee, no word a new rule masked (in
its own field), and none of the values the privacy read of 19 October 2026 found -- held
here only as hashes (`PRIVACY_READ`), because a parent's surname written into this file to
check for it would be published by the check.
"""
import argparse
import csv
import hashlib
import io
import os
import re
import sys
from collections import Counter, defaultdict
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
DATA = os.path.join(ROOT, 'sources', 'data')

RAW_KEY = 'town-ledgers/account-details/account-details-fy2023-fy2026-p13-school-journal.pdf'
RAW_SHA256 = '6d5d56ee70578b54de2066a2a75969dc62069caeba20cd92902fdfe2cf50da7a'
RAW_LOCAL = os.path.join(ROOT, 'build', 'private', 'munis', 'raw', RAW_KEY)
PRIVATE = os.path.join(ROOT, 'build', 'private', 'munis')
YTD_CSV = os.path.join(DATA, 'munis-school-ytd.csv')
OUT_NAME = 'munis-school-journal.csv'
OUT_ACCOUNTS_NAME = 'munis-school-journal-accounts.csv'
OUT_IMAGE_NAME = 'munis-school-journal-image-pages.csv'      # public: the reading, redacted
READING_NAME = 'munis-school-journal-image-pages-reading.csv'  # private: the reading by eye
ROSTER_CSV = os.path.join(DATA, 'staff-roster-entries.csv')
DIRECTORIES = ((os.path.join(DATA, 'school-staff-directory.csv'), 'district staff directory'),
               (os.path.join(DATA, 'staff-directory.csv'), 'town staff directory'))


def paths(out_dir=None):
    """Where the outputs go and where the by-eye reading is read from."""
    if out_dir:
        d = os.path.abspath(out_dir)
        return {'journal': os.path.join(d, OUT_NAME), 'accounts': os.path.join(d, OUT_ACCOUNTS_NAME),
                'image': os.path.join(d, OUT_IMAGE_NAME), 'reading': os.path.join(d, READING_NAME)}
    return {'journal': os.path.join(DATA, OUT_NAME), 'accounts': os.path.join(DATA, OUT_ACCOUNTS_NAME),
            'image': os.path.join(DATA, OUT_IMAGE_NAME), 'reading': os.path.join(PRIVATE, READING_NAME)}

PAGES = 1744
IMAGE_PAGES = (34, 643, 1080)
X0, PITCH = 50.4, 4.8205
MASK = '[redacted]'
INDIVIDUAL = 'individual (redacted)'

# Which journal source posts to which printed column -- proven by tie 1, not assumed. Defined
# ONCE, in scripts/journal.py, which every report on this journal reads too.
from journal import COLUMN_OF  # noqa: E402

J = re.compile(r'^  (\d{4})/(\d\d)/(\d{6}) (\d\d)/(\d\d)/(\d{4}) ([A-Z]{3}) ')
AMOUNT = re.compile(r'^.{31}\s*(-?[\d,]*\.\d\d) ')
ACC = re.compile(r'^(\d{4})-(\d)-(\d{3})-(\d{4})-(\d\d)-(\d)-(\d\d)-(\d)-(\d{6})\s+(.*)$')
NUM = r'(-?[\d,]*\.\d\d)'
FIGS = r'\s+'.join([NUM] * 6) + r'\s+(-?[\d.]+)%\*?\s*$'
FIG = re.compile(r'^\s+' + FIGS)
# A TOTAL line prints a percentage except `TOTAL REVENUES` / `TOTAL EXPENSES`, which do not.
TOT = re.compile(r'^\s+(GRAND TOTAL|TOTAL (.*?))\s+' + r'\s+'.join([NUM] * 6)
                 + r'(?:\s+(-?[\d.]+)%\*?)?\s*$')
ORG = re.compile(r'^([A-Z]?\d{5,8}) (\S.*)$')
FUND = re.compile(r'^(\d{4}) {2,}(.*?)\s+APPROP\s+ADJSTMTS')
FURNITURE = re.compile(
    r'^(\s*$|T O W|Y EA R|R.?e?p?o?r?t|U.?s?er:|P.?r?o?g?r?a?m|\s*FOR 2026 13\s+JOURNAL'
    r'|ACCOUNTS FOR:|\s+Page\s+\d+\s*$)')
COMMENT_INDENT = ' ' * 17
FIGURE_FIELDS = ('original_approp', 'transfers_adjustments', 'revised_budget',
                 'ytd_actual', 'encumbrances', 'available_budget')

FIELDS = ['fiscal_year', 'period', 'journal', 'effective_date', 'source', 'posts_to',
          'amount', 'fund', 'fund_name', 'org', 'org_name', 'account', 'object',
          'account_description', 'ref_type', 'vendor_no', 'vendor', 'doc_type', 'doc_no',
          'description', 'check_no', 'comment', 'page', 'line', 'read', 'masked',
          'name_basis']
IMAGE_FIELDS = ['page', 'line', 'journal', 'date', 'source', 'amount', 'ref_type', 'vendor_no',
                'doc_type', 'doc_no', 'vendor', 'description', 'check_no', 'name_basis']
ACCOUNT_FIELDS = ['fund', 'fund_name', 'org', 'org_name', 'account', 'object',
                  'account_description'] + list(FIGURE_FIELDS) + ['pct_used', 'journal_lines',
                                                                  'page']

# --- the redaction rule ------------------------------------------------------------------

# A vendor name containing one of these WORDS (or word-stems: the name is cut at 20
# characters, so `SERVIC` and `TECHNOLOG` are what survive) is a business or a public body.
# Every stem must START a word -- `PARK` is not allowed to match `CLARK`, nor `INN` `FINN`.
BUSINESS_STEMS = r"""
    INC LLC L.L.C LLP LTD CORP CO COMPAN ASSOC SCHOOL SCHOO SCH UNIVERS UNIVE COLLEGE COLL
    ACADEMY INSTITUTE HOSPITAL FOUNDAT SOCIETY COUNCIL COMMITTEE COMMISSION TOWN CITY COMM
    COMMONWEALTH DEPT DEPARTMENT DIVISION TREASU STATE REG REGIONAL DISTRICT COLLABORATIVE
    MASS MASSACHUSETT NATIONAL AMERICA AMER CENTRAL SERVIC SERV SUPPL SYSTEM TECHNOLOG
    TECHNICAL TECH SOFTWARE LEARNING EDUCATI PUBLISH BOOKS MUSIC SPORTS ATHLETIC EQUIP
    PRODUCT ENTERPRIS INDUSTR INTERNATIONAL HOLDING GROUP PARTNERS SOLUTION CONSULT
    ENGINEER ARCHITECT ELECTRI PLUMBING HVAC ROOFING LANDSCAP NURSERY FOODS FOODSERV
    RESTAURANT MARKET STORES RETAIL RENTAL LEASING TRANSPORTATION LIMOUSI TROPHY AWARDS
    PRINTING GRAPHIX APPAREL SILKSCREEN MUSEUM THEATRICALS STADIUM YMCA BOOSTERS CENTER
    NETWORK COMMUNICATI WIRELESS ANALYTIC DIAGNOSTIC LABORATOR THERAPEUTIC HEALTH MEDICAL
    NEUROLOGY PSYCHOLOGICA PEDIAT BEHAVIORAL AUTISM LITERACY PHONICS SCIENTIFIC BIOLOGICAL
    ROBOTICS COMPUTER ELECTRONIC RECREATIO ENTERTAINMENT FITNESS DISTRIBUT MANUFACTUR MFG
    POWER ENERGY RENEWABLE RESTROOM FLAGPOLE HARDWARE BUILDING CONSTRUCTION MOVING
    FINANCIAL BENEFITS LEDGER MEDIA POSTAL UNITED BUS FARM FARMS DAIRY BAKING GREENHOUSE
    IRRIGATION SIGN SIGNS MOTION PICTUR PRESS GARDE OFFICE ACTIVITY CLASS PETTY USA US LP
    THE OF FOR AND
"""
# A stem of six letters or more may begin a longer word; a shorter one must be the whole
# word, or `CO` would match `COHEN` and `POWER` would match a person called Powers.
BUSINESS_RE = re.compile(r"(?<![A-Z0-9])(" + "|".join(
    re.escape(w) + ('' if len(w) >= 6 else r'(?![A-Z0-9])')
    for w in sorted(BUSINESS_STEMS.split(), key=len, reverse=True))
    + r")|&|\.COM|\bINC\.|\bCO\.")

# Businesses and public bodies whose (truncated) name carries none of those words, named
# exactly as the report prints them. Read off the full vendor list, 18 October 2026.
BUSINESSES = {
    'A.S.C.D.',
    'A.S.E.',
    'ABOUND PARENTING,PBC',
    'ACCO BRANDS',
    'ACCURATE LABEL DESIG',
    'ACE-ENDICO',
    'ACTION KING ENTERPRI',
    'ADDICTION TREATMENT',
    'ADVANCED PRINT TECHN',
    'ADVANCED TRUCK ACCES',
    'AIREX CORPORATION',
    'AMAZING HERO ART',
    'AMPLIFIED',
    'ANIMAL ADVENTURES',
    'AP EXAMINATIONS',
    'APEX',
    'APPLESEED BUSINESS M',
    'ART-LAYERS-FINAL, IN',
    'ATLAS COPCO NORTH AM',
    'AVANT',
    'AYER SHIRLEY LUNENBU',
    'AYER SHIRLEY REGIONA',
    'BAND SHOPPE',
    'BAYSTATE',
    'BERKSHIRE',
    'BEST BUDDIES',
    'BIGGER FASTER STRONG',
    'BILINGUAL DICTIONARI',
    'BLICK DICK',
    'BLOOMERY',
    'BLUE TARP',
    'BRANDON RESIDENTIAL',
    'BROOKES PAUL H PUBLI',
    'CAMWEAR CUSTOM APPAR',
    'CDMMEA',
    'CDW GOVERNMENT',
    'CHAMPION',
    'CHERRYROAD',
    'CHRISTIAN BROTHERS O',
    'CLARK TERRY-UNH JAZZ',
    'COCHRANE VENTILATION',
    'COLONIAL HOTEL',
    'COMCAST BUSINESS',
    'COMMAND PERFORMANCE',
    'COMMONLIT',
    'COMMUNITY PROVIDERS',
    'COMPETITIVE EDGE',
    'COMPREHENSIBLE',
    'CONNECTICUT BUSINESS',
    'CRISIS PREVENTION',
    'CROCODILE RIVER MUSI',
    'CURRICULUM ASSOCIATE',
    'Central Mass Soccer',
    'DAIKIN APPLIED',
    "DAVIS' FARMLAND",
    'DECKER EQUIPMENT',
    'DELTA BECKWITH',
    'DEMCO',
    'DEMOULAS SUPER MARKE',
    'DEVENS',
    'E L HARVEY',
    'E RATE',
    'EAST COAST ELECTRONI',
    'EASTERN BEARINGS',
    'EASTERN STATES EXPOS',
    'ECOTARIUM',
    'EMERGENCY SIGNAL SYS',
    "EMPIRE/LAURI'S",
    'EQUITY PROCESS',
    'ETA',
    'FAT BRAIN TOYS',
    'FIREHOUSE',
    'FOLLETT CONTENT',
    'FOLLETT LIBRARY RESO',
    'FRONTLINE',
    'GALAXY INTEGRATED',
    'GALLAGHER AFFINITY I',
    'GENERATION GENIUS, I',
    'GEOSURFACES NORTHEAS',
    'GEOSURFACES SOUTHEAS',
    'GEYER INSTRUCTIONAL',
    'GO VINEYARD RUNNING',
    'GOGUARDIAN',
    'GOPHER SPORT',
    'GORDON FOOD',
    'GUARANTY GLASS',
    'HARVARD UNDERGRADUAT',
    'HILLOWEEN CHEER',
    'HOME DEPOT CREDIT SE',
    'HOUGHTON MIFFLIN COM',
    'IGNITE READING',
    'INSTANT PORTABLES IN',
    'INSTRUCTIONAL COACHI',
    'INSTRUMENTALIST',
    'INTERFACE FLOOR',
    'INTRADO INTERACTIVE',
    'JOHNSON CONTROLS',
    'KIDS DISCOVER',
    'KNIGHTS AIRPORT LIMO',
    'KODABLE',
    'LAKEVIEW DRIVING RAN',
    'LAKEVIEW TREE NURSER',
    'LANGUAGE TESTING',
    'LEOMINSTER PUBLIC SC',
    'LOWELL SUN',
    'LUNENBURG FLOWERS',
    'LUNENBURG TURKEY HIL',
    'LUNENBURG WATER DIST',
    'M.R.T.A.',
    'MASSPAC',
    'MATSOL',
    'MCA PROMO',
    'McGovern MHQ Inc.',
    'MIDLAND WACHUSETT SE',
    'MIDLAND-WACHUSETT IN',
    'MIIA USP',
    'MMA',
    'MONOGRAMS BY ANITA',
    'MOSYLE CORPORATION',
    'MPS VIRGINIA',
    'MSAA',
    'MTE EQUIPMENT SOLUTI',
    'MULCAHY LINE PAINTIN',
    'MYSTERY SCIENCE',
    'NAISMITH MEMORIAL',
    'NASHOBA YOUTH',
    'NASN',
    'NASSP',
    'NATURES CLASSROOM',
    'NEW ENGLAND DOOR SOL',
    'NEW ENGLAND ICE CREA',
    'NEW ENGLAND PRETZEL',
    'NINGENIUS STUDIOS LL',
    'NOREL',
    'NORTH RIVER',
    'NORTHEAST CUTLERY',
    'NORTHEAST GLASS WORK',
    'NORTHEAST SOUND',
    'NORTHEASTERN',
    'NYSTROM',
    'PATRIOT PROMOTIONAL',
    'PAWTUCKET RED SOX',
    'PEARTREE CORPORATION',
    'PLAYSCRIPTS',
    'PLT4M',
    'POLOLU CORPORATION',
    'PRECISION HUMAN RES',
    'PRESTWICK HOUSE',
    'PROFESSIONAL SOFTWAR',
    'PROQUEST',
    'QUILL CORPORATION',
    'QUINCY COMPRESSOR LL',
    'RAPS AUTO PARTS SUPP',
    'READING WITH TLC',
    'REALLY GOOD STUFF, I',
    'RED ROBIN INTERNATIO',
    'RIVERSIDE INSIGHTS',
    'ROYAL STEAM HEATER C',
    'SAVVAS',
    'SEELEY AUTOMOTIVE',
    'SENOR WOOLY',
    'SIGNCASTER COPORATIO',
    'SITSPOTS',
    'SOUTHWICK WILD ANIMA',
    'SPRAGUE OPERATING RE',
    'STAPLES',
    'STAR CLEANERS',
    'STERICYCLE',
    'SUPERINTENDENTS',
    "SWEET'S PROPERTY SOL",
    'SWEETWATER SOUND HOL',
    'TEACHER CREATED',
    'TEXHELP',
    'THIRD SECTOR NEW ENG',
    'TOWNSEND FORD',
    'TYPINGCLUB',
    'UNITIL',
    'USGS/DENVER',
    'VAN POOL',
    'VERIZON',
    'VERIZON BUSINESS',
    'VOYAGER SOPRIS LEARN',
    'W B MASON',
    'WACHUSETT',
    'WACHUSETT MOUNTAIN',
    'WESTED',
    'WILLIAM MARSH RICE U',
    'WILSON LANGUAGE TRAI',
    'WINDOW FILM DEPOT, I',
    'WONDER WORKSHOP',
    'WORCESTER COUNTY SUP',
    'XEROX',
    'YOGIBO',
    'ZOOM VIDEO COMMUNICA',
}

# And the reverse: names the stems call a business that are a person. `P &` is all the
# Town's redaction left of one name.
PERSONS = {'CONROY, JONATHAN &', 'P &'}


def is_business(name):
    if name in PERSONS:
        return False
    return name in BUSINESSES or bool(BUSINESS_RE.search(name))


# Words that belong in a special-education placement, tuition or transport line. Anything
# else in such a line is a child's name or initials, or part of one, and is masked.
# `\bPLACEM`, not `PLACEM`: `REPLACEMENT UNIFORMS` is not a placement.
SPED_LINE = re.compile(r'\bPLACEM|TUITION|TUIT\b|TUITIONS|\bOOD |OUT OF DIST')
SPED_WORDS = set('''
    DAY RES RESIDENTIAL PLACEMENT PLACEM PLACE PLACEMEN PLACEMENTS FOR TUITION TUITIONS
    TUIT TUITI TUITIO COLLAB COLLABORATIVE COLLABORATIVES COLLABORAT COLLABORATI
    PROGRAM PROG PROGR PROGRA PROGCODE CODE C CO FY AND ESY SUMMER SPED SPECIAL ED
    PRIVATE PRIV PUBLIC CONTRA CONTRACT OUT OF DISTRICT DIST OOD QUARTELY QUARTERLY
    KEYSTONE KEYSTO KEYST KEYS E AN THE TO STUDENT STUDENTS STUD DAYS FO FEES FEE
    FSU COURSE COURSES SCHOOL EXTENDED YEAR YR TRANSPORTATION TRANSP TRANS VAN
    REIMB REIMBURSEMENT CREDIT ADJ ADJUSTMENT BALANCE CLOSE PER P RECLASS REFUND
    INVOICE INV OCT NOV DEC JAN FEB MAR APR MAY JUN JUL AUG SEP SEPT JUNE JULY
    MONTH MONTHLY ANNUAL HALF FULL TERM SESSION REVOLVING SPRING FALL WINTER
    CAPS FLLAC COTTING HORACE MANN MAY INSTITUTE FRANCISCAN HOSPITAL CENTER APPLIED
    ADVOCATES INC EDUCATIONAL EDUCATIO NON RESIDENT REGULAR GRANT CIRCUIT BREAKER
    ADDITIONAL ADDTL ADD SVC SVCS SERVICES SERVICE ACADEMIC THERAPY OT PT SLP
    ABA EVAL EVALUATION AIDE ONE TO 1:1 RD TVI
'''.split()) - {'RD'}

# Names in descriptions and comments that are neither a vendor nor a child slot -- staff
# who closed a purchase order, a teacher sent to a conference, a student's class dues, an
# adult-education instructor -- found by reading every distinct token and every distinct
# description (`--review`, 18 October 2026). Matched as whole words, any case. Staff are
# masked with everyone else: the document does not say who is an employee.
NAME_TOKENS = set("""
    ADUGGAN ALIC ALICIA ALLYS ALLYSON ANDREW ANN ANNICA ANTHO ANTHON ANTHONY ARO ATUCHA
    AUGUSTE AY BARR BEALS BEARDM BEARDMORE BELLEZ BOLDUC BOOKIS BOONE BORNEMAN BOWEN BREN
    BRODEN BURN BURNHAM CALLAHA CALLAHAN CAMBELL CAMELLO CARBONE CARLA CARNONE CASS
    CASSIDY CESAR CFULLER CHRIS CMCN CONNEY CONNOR COONEY COONNEY CORMIER COURTNEY CYR
    DARLENE DAVID DEB DEFELICE DIPILATO DONIN DOW DRIGGER DRIGGERS DYLAN EHEVY HEVY FISHER
    FOSTER FULLER GILSON GUILLETTE GUIMOND HANSC HANSCOMCOURSE HEIDI HIEDI HICKE HSPINNEY
    JAMES JANE JASON JENNIFER JES JESS JODI JODY JOE JOHN JOHNI JORD JULI JULIA
    JULIANNA JULIE KATE KATRALIS KAYL KAYLA KBROCHU KBURNHAM KER KIM KORRY KRIS KRIST
    KRISTINA KYLE LANTIEGNE LAUREN LAURENE LAVERY LBRODEN LEESA LEVINE LISA LIVINGSTON
    LIZEK LIZS LOMB LORENZ LORENZEN LOURENS LPETERS LPETERSEN LUCIE LUCIER LYLA MAGGIE
    MALCOM MARTI MARY MAURA MAUREEN MCALLISTER MCC MCCA MCCAR MCCARTHY MCCARTY MCCOLL MCGUI
    MCGUIRE MCKINEY MCN MCNAMARA MICHA MILLER MOLL MONA NAD NADIN NADINE NORMAN PAM PAQUETTE
    PATRICIA PATTY PENNEY PERRINE PETERSEN PUKAITE PUSATERI PYLE RACHEL RESNICK RICHAR
    RICHARD ROB ROBINS ROBINSON RUTH SAM SANDR SANDRA SANTRY SCOT SCOTT SCOZIK SEBASTIAN
    SHAR SHAYNA SHEA SHEASGREEN SHEEHY SHEEY SPAULDI SPINNEY SQUIER SUSAN SZOCIK TANYA
    TCOONE TIBBETTS TINA TINAC TIRRELL TOBI TOM TOUSIGNANT TRAVERSO TREMO TUCKER VEGA WELN
    WITHERS YANINA YVON WILLIAM PAUL ROBIN SQU
    ALI SANT FER TIM SAN DAW SHA FAUC PARRILA TERRI SOMERS COHE HEI SARFDE SARFD VENTO
    BARRY GROVE TINC KSARFDE ASCOT BROOKS BURNHAM SCHIEVE
""".split())
# Phrases that contain one of those words and are NOT a person in a transaction: a fund or
# scholarship named for somebody, an event, or a business. Protected before masking.
KEEP_PHRASES = [r'JOE RUTH(?= SCHOLAR)', r'(?<=FLUID, )FISHER', r'[A-Z]+ CZELUSNIAK',
                # a class-funds release names its class officers, not a service recipient
                # (TJ, 19 October 2026): kept
                r'(?<=CLASS OF 2018 )[A-Z]+(?: [A-Z]+)?(?=\s*&|(?:19|20)\d\d$|$)', r'PAUL J ANDREWS', r'JOHN DEERE', r'FOR FOSTER', r'PAUL CENTER', r'RED ROBIN', r'STEVE WEISS',
                r'STEPHANIE STOLLER', r'DAVE AYOTTE', r'KING PHILIP', r'CLARK TERRY',
                r'WASS-ARTHUR', r'POWERS AND SULLIVAN', r'R STACHOWICZ', r'RICHARD STACHOWICZ']
# Initials and fragments a word list cannot see.
NAMES_IN_TEXT = [r'(?<![A-Z])K\.S(?![A-Z])', r'(?<![A-Z])K\.M\.', r'H SPINNER',
                 r'DEWALT PSYCHOLOGIST', r'(?<=DR\. )[A-Z](?![A-Za-z])', r'(?<=DR\.)[A-Z](?![A-Za-z])',
                 r'(?<=PER )[A-Z]$', r'(?<=VOLLEY BALL/)PA\b', r'(?<=PER )[A-Z]\.?\s?[A-Z](?=\s|$)',
                 r'(?<=FOOTBALL )FERR$']
NAME_RE = re.compile(r'(?<![A-Za-z])(' + '|'.join(sorted(NAME_TOKENS, key=len, reverse=True))
                     + r')(?![A-Za-z])', re.I)
KEEP_RE = re.compile('|'.join(KEEP_PHRASES))


def mask_names(text):
    keep = {}

    def hold(m):
        keep[f'\x00{len(keep)}\x00'] = m.group(0)
        return f'\x00{len(keep) - 1}\x00'
    out = KEEP_RE.sub(hold, text)
    out = NAME_RE.sub(MASK, out)
    for pat in NAMES_IN_TEXT:
        out = re.sub(pat, MASK, out)
    # an initial left beside a masked name is part of the name
    out = re.sub(r'(?<![A-Za-z0-9])[A-Za-z]\.?\s?\[redacted\]', MASK, out)
    out = re.sub(r'\[redacted\]\s?[A-Z]\.?(?![A-Za-z0-9])', MASK, out)
    # `SURNAME, [redacted]` -- a name printed surname first -- and the fragment of a name
    # the 20- or 30-character field cut off after a masked one
    out = re.sub(r"(?<![A-Za-z0-9])[A-Z][A-Z'-]+, \[redacted\]", MASK, out)
    out = re.sub(r'\[redacted\]\s[A-Z]{1,3}$', MASK, out)
    out = re.sub(r'(?<=PER )[A-Z]{1,3}$', MASK, out)
    for k, v in keep.items():
        out = out.replace(k, v)
    return out


def mask_words(text, words):
    """Remove each word (a person's name, token by token) from free text."""
    out = text
    for w in sorted(words, key=len, reverse=True):
        if len(w) < 2:
            continue
        out = re.sub(r'(?<![A-Z0-9])' + re.escape(w) + r'(?![A-Z0-9])', MASK, out)
    return out


# The only 1-2 letter tokens a placement or student-service line may keep. Any other stray
# letter or pair is a child's initials, wherever it falls in the line (`TUIT FOR , , P`).
TWO_LETTER_OK = {'FY', 'OT', 'PT', 'ED', 'AT', 'TO', 'OF', 'IN', 'VI', 'HS', 'MS', 'ES', 'OR',
                 'ON', 'BY', 'NO'}


def mask_sped(text):
    if not SPED_LINE.search(text):
        return text, 0
    n = 0

    def one(m):
        nonlocal n
        tok = m.group(0)
        core = re.sub(r'(19|20)\d\d$', '', tok)   # a PO line ends `...FOR C2024`
        if not core or not re.search(r'[A-Z]', core):
            return tok
        if core in SPED_WORDS and (len(core) > 2 or core in TWO_LETTER_OK):
            return tok                              # a stray 1-2 letter token is an initial
        n += 1
        return MASK + tok[len(core):]
    return re.sub(r"[A-Za-z][A-Za-z.'&-]*\d*", one, text), n


# --- a student-service line ----------------------------------------------------------------
# The child's name or initials follow the service: `AT SERVICES FOR <initials>`, `TVI SERVICES
# FOR <initial>`, `HOME HOSPITAL TUTORING - <initial>`. Everything
# after the trigger that is not on `SERVICE_WORDS` is masked -- single letters always.
SERVICE_LINE = re.compile(
    r"\bAT (?:SERV\w*|EVAL\w*)|ASSISTIVE|\bTVI\b|\bVISION\b|HOME[ /-]*HOSPITAL TUT\w*"
    r"|HOSPITAL TUT\w*|HOME TUTOR\w*|HOME VISITS? FOR|FOSTER STUD\w*|\bFOR STUD\w*", re.I)
# These are a student service only for a student: `TRANSPORTATION FOR FIELD TRIPS` and `WATER
# TESTING FOR PB` are not, so they fire on a student-service account or beside `STUDENT`.
SERVICE_FOR_STUDENT = re.compile(r"\b(?:EVAL\w*|ASSESSMENTS?|TESTING) FOR\b|TRANSPORT\w* (?:FOR|OF)\b",
                                 re.I)
STUDENT_IN_TEXT = re.compile(r"\bSTU|FOSTER|\bACE\b|\bOOD\b", re.I)
# A special education materials line (`SPED CLASSROOM SUPPLIES`) names a child only as a
# fragment -- `ES SPECIAL ED - LA`, `LAMINATE FOR SPECIAL ED (A` -- so there only the 1-3
# letter words that are not vocabulary are masked.
SPED_MATERIAL = re.compile(r"SPECIAL ED\w*|\bSPED\b", re.I)
# `SERVICES FOR` is a student service only on a student-service account: on the others it is
# `ELECTRIC SERVICES FOR UNITIL` and `IT SERVICES FOR FY25`.
SERVICES_FOR = re.compile(r'\bSERVICES? FOR\b', re.I)
STUDENT_ACCOUNT = re.compile(r'RELATED SERVICES|EVALUATION|TUTOR|SPED|SPEC ED|SPECIAL|THERAP'
                             r'|PHYSICIAN|PSYCH|NURS', re.I)
SERVICE_WORDS = SPED_WORDS | set('''
    AT TVI VI VISION VISUAL SERVICES SERVICE SERV ASSISTIVE TECHNOLOGY TECH EVAL EVALS
    EVALUATION EVALUATIONS ASSESSMENT ASSESSMENTS TESTING TEST HOME HOSPITAL TUTORING TUTOR
    TUTORS PARAS PARA STUDENT STUDENTS STUDNETS STUD STU ST HS MS ES LHS LMS LPS THES LMHS
    PRIM PRIMARY ELEM ELEMENTARY MIDDLE MIDDLES HIGH SPECIAL EDUCATION EDUCATIONAL PT OT SLP
    CFY AAC SPEECH LANGUAGE PSYCH PSYCHOLOGICAL BILINGUAL BI-LINGUAL INDEPENDENT OUTSIDE
    CONTRACTED TEACHER TEACHERS TEAACH DEAF HARD HEARING INTERPRETING INTERPRETER
    TRANSLATION TRANSLATING SOUND FIELD SYSTEM MATERIALS MATERIAL EQUIPMENT EQUIP SUPPLIES
    SUPPLY APP APPS APPLICATION IPAD CASE CASES ROCKER LAMINATE SENSORY CONFERENCE
    LEADERSHIP RECORDS DESTRUCTION IDEA EARLY CHILDHOOD IMPROVEMENT ALLOCATION GRADE GR
    PREK PRESCHOOL WITH HEALTH NEEDS MILEAGE REIMBURSE REIMBURSEMENT STAFF OF IN ALL NO
    CHECK AWARD AWARDS BEMIS MADIGAN COMMUNITY FOUNDATION INVESTMENT INVESTMENTS FUND
    MEMORIAL CLASS LEGAL ACH ACHIEVE TLC PLAYGROUND MATH READING ELA BEHAVIOR BCBA FOSTER
    CARE SEAL BILITERACY EXAM TRAINING ACE SCHOOLS BOSTON CHILDREN'S MEDICAL SCREENING
    NURSING NURSE COUNSELING SCREENER SCREENERS CB PMT SS CLA BCBA PROGRAM PROGRAMS PROG
    PROGR SVC
'''.split())
SERVICE_TOKEN = re.compile(r"\[redacted\]|[A-Za-z][A-Za-z.'&-]*\d*")


def mask_service(text, student_account):
    """Mask what follows the service in a student-service line. Returns (text, masked words)."""
    for_student = student_account or bool(STUDENT_IN_TEXT.search(text))
    hits = [(m, False) for m in (SERVICE_LINE.search(text),
                                 SERVICES_FOR.search(text) if student_account else None,
                                 SERVICE_FOR_STUDENT.search(text) if for_student else None) if m]
    m = SPED_MATERIAL.search(text)
    if m:
        hits.append((m, True))
    if not hits:
        return text, []
    m, fragments_only = min(hits, key=lambda h: (h[1], h[0].end()))
    cut = m.end()
    head, tail = text[:cut], text[cut:]
    masked = []

    def one(m):
        tok = m.group(0)
        if tok == MASK:
            return tok
        if m.start() > 0 and tail[m.start() - 1].isdigit():
            return tok                               # `3RD`, `4TH`: an ordinal, not a word
        core = re.sub(r'(19|20)\d\d$', '', tok)
        up = core.upper().rstrip('.')
        if not up or not re.search(r'[A-Z]', up):
            return tok
        last = not re.search(r'[A-Za-z]', tail[m.end():])
        if fragments_only and len(up) > 3:
            return tok
        if len(up) <= 2:
            if up in TWO_LETTER_OK:
                return tok
            masked.append(core)
            return MASK + tok[len(core):]
        if up in SERVICE_WORDS:
            return tok
        if last and len(up) >= 3 and any(w.startswith(up) for w in SERVICE_WORDS if len(w) > len(up)):
            return tok                               # the 20/30-character cut, mid-word
        masked.append(core)
        return MASK + tok[len(core):]
    return head + SERVICE_TOKEN.sub(one, tail), masked


# --- a payer, a claim, and the residue of a masked name ----------------------------------
# A bounced check or a redeposit names who wrote it: `NSF CK #143/<payer>`. What may stay is
# the programme the money was for.
PAYER_LINE = re.compile(r'\bNSF|\bREDEP', re.I)
PROGRAM_WORDS = set('''
    EXT DAY EXTENDED EXTD EXTDAY MSACT ESACT HSACT DWACT CANOBIE ATHLETIC ATHLETICS ATH FEES
    FEE ELEM ELEMENTARY SCH SCHOOL ACT ACTIVITY ACTIVITIES MID MIDDLE MUSIC CLASS DW HS MS ES
    GIFT ADULT TUITION STEM LUNCH REDEP NSF CK PER
'''.split())
# The end of a family's receipt: `CURRENT YR REFUND/MID SCH/<fragment>`. A short last segment
# that is not a programme word is the start of whoever paid.
RECEIPT_KEEP = PROGRAM_WORDS | set('''
    BOX YOGA ARTS SEP AUG APR APRIL ACE THES LPTO PTO NO ATHL MAINT TOL ART LAB BOOK FAIR CLUB
    CHEE STEA COLL OCT NOV DEC JAN FEB MAR MAY JUN JUL JUNE JULY TOTAL SOCC TOPS INC DEPT DEP DE ELE
'''.split())
CLAIM_LINE = re.compile(r"WORKER|\bCOMP\b|CLAIM|\bMIIA\b", re.I)
RESIDUE_STOP = {'FOR', 'AND', 'THE', 'TO', 'OF', 'IN', 'ON', 'AT', 'PER', 'BY', 'FY', 'INC',
                'LLC', 'CO', 'PO', 'INV', 'REF', 'ACH', 'CK', 'DEP', 'ADJ', 'HS', 'MS', 'ES',
                'LHS', 'LMS', 'LPS', 'SCH', 'ACT', 'FEE', 'DAY', 'ED', 'OT', 'PT', 'SLP'}
PER_KEEP = {'INVOICE', 'INV', 'MEMO', 'QUOTE', 'CONTRACT', 'EMAIL', 'BOARD', 'SC', 'DESE',
            'AUDIT', 'AGREEMENT', 'REQUEST', 'TOWN', 'STATE', 'PO', 'VOTE'}
EVENT_FOR_KEEP = {'SPE', 'SPED', 'ALL', 'THE', 'NEW', 'STAF', 'ELL', 'ESL', 'MATH', 'ART',
                  'ARTS', 'ELA', 'OT', 'PT', 'SLP', 'ABA', 'CPR', 'BCBA'}


def mask_payer(text):
    """In a bounced-check or redeposit line, keep the programme and mask the payer."""
    if not PAYER_LINE.search(text):
        return text, []
    masked = []
    segs = text.split('/')
    seen_ck = False
    for i, seg in enumerate(segs):
        m = re.search(r'CK\s?#?\s?\d+', seg)
        if m:
            seen_ck = True
            rest = seg[m.end():]
            words = re.findall(r"[A-Za-z][A-Za-z'.-]*", rest)
            if words and any(w.upper() not in PROGRAM_WORDS for w in words):
                masked += words
                segs[i] = seg[:m.end()] + ' ' + MASK
            continue
        words = re.findall(r"[A-Za-z][A-Za-z'.-]*", seg)
        if seen_ck and words and not all(
                w.upper().rstrip('.') in PROGRAM_WORDS
                or (j == len(words) - 1 and i == len(segs) - 1 and len(w) >= 3
                    and any(p.startswith(w.upper()) for p in PROGRAM_WORDS))
                for j, w in enumerate(words)):
            masked += words
            segs[i] = MASK
    return '/'.join(segs), masked


def mask_receipt_tail(text):
    """A family's receipt ends on the payer: a short last `/` segment that is no programme."""
    if '/' not in text:
        return text, []
    head, _, last = text.rpartition('/')
    words = re.findall(r"[A-Za-z]+", last)
    if (words and len(words) <= 2 and all(len(w) <= 4 for w in words)
            and not re.search(r'\d', last) and MASK not in last
            and any(w.upper() not in RECEIPT_KEEP for w in words)):
        return head + '/' + MASK, words
    return text, []


def mask_claim(text):
    if not CLAIM_LINE.search(text):
        return text, []
    found = re.findall(r'#\s?(\d{4,})', text)
    return re.sub(r'#\s?\d{4,}', '#' + MASK, text), found


RESIDUE_KEEP = RESIDUE_STOP | {w for w in SERVICE_WORDS if len(w) > 1}


def mask_residue(text):
    """The rest of a masked name: a 1-3 letter token straight after `[redacted]`, or a field
    ending on a fragment after one; a surname left after a masked given name; a name after
    PER at the end of a field; a fragment after `CONFERENCE FOR` at the end of a field."""
    masked = []

    def frag(m):
        w = m.group(2)
        if w.upper() in RESIDUE_KEEP:
            return m.group(0)
        masked.append(w)
        return MASK
    out = re.sub(r'\[redacted\](\s?)([A-Za-z]{1,3})(?=(?:19|20)\d\d$|[^A-Za-z0-9]|$)', frag, text)
    out = re.sub(r'\[redacted\]([\s,./-]+)([A-Za-z]{1,3})(?=(?:(?:19|20)\d\d)?$)', frag, out)

    def one(m):
        w = m.group(1)
        if w.upper() in PER_KEEP or w.upper() in RESIDUE_KEEP:
            return m.group(0)
        masked.append(w)
        return MASK + m.group(2)
    out = re.sub(r"(?<=\bPER )([A-Za-z][A-Za-z'-]*)(\s*(?:(?:19|20)\d\d)?)$", one, out)
    out = re.sub(r"(?<=FOR \[redacted\] )([A-Z][A-Za-z'-]+)(\s*(?:(?:19|20)\d\d)?)$", one, out)

    def event(m):
        w = m.group(1)
        if w.upper() in EVENT_FOR_KEEP:
            return m.group(0)
        masked.append(w)
        return MASK + m.group(2)
    out = re.sub(r"(?:(?<=CONFERENCE FOR )|(?<=TRAINING FOR )|(?<=WORKSHOP FOR ))"
                 r"([A-Za-z]{1,4})(\s*(?:(?:19|20)\d\d)?)$", event, out)
    return out, masked


# --- a public employee --------------------------------------------------------------------
ROSTER_WINDOW = 2                    # fiscal years either side of the journal line
DIRECTORY_YEARS = {2025, 2026}       # the directories are current: they prove FY2025-FY2026
NAME_SUFFIX = {'JR', 'SR', 'II', 'III', 'IV', 'DR', 'MR', 'MRS', 'MS', 'MISS'}
# A line that may concern the employee's OWN child or family. Tested against the description,
# the comment, the account and the org.
FAMILY = re.compile(
    r"REFUND|RFND|\bLUNCH|\bMEALS?\b|DEPOSIT|\bDEP\b|REDEP|\bNSF|TUITION|\bTUIT\b"
    r"|\bPLACEM|\bOOD\b|OUT OF DIST|TRANSPORT|\bTRANSP\b|FOSTER|\bSTUD(?:ENTS?|NETS)?\b(?! COUNCIL)"
    r"|SERVICES FOR|HOSPITAL|TUTOR|\bEVAL|ASSESSMENT|\bGIFT|DONATION|CLASS DUES|USER CHARGE"
    r"|JURY DUTY|\bFEES?\b|ESACT|HSACT|MSACT|DWACT|EXT ?DAY|EXTENDED DAY", re.I)
SCHOLARSHIP = re.compile(r'SCHOLAR', re.I)
# A person PAID AS A PARENT or family -- a refund, a bounced check, a deposit, mileage for
# their own child, child care, a tuition or placement reimbursement -- is masked. Anybody else
# paid for a service or a good is shown. Tested against the description, comment, account
# and org, like FAMILY; a gift or scholarship award is NOT a parent payment.
PARENT = re.compile(        # on the description and comment: the line SAYS it is a family's
    r"REFUND|RFND|(?<!BAGGED )\bLUNCH|\bMEALS?\b|DEPOSIT|\bDEP\b|REDEP|\bNSF"
    r"|TUITION(?!.*(?:COURSE|\bFSU\b|COLLEGE|UNIV))|\bTUIT\b|\bPLACEM|\bOOD\b|OUT OF DIST|PARENT REIMB|STUDENT (?:WITHDREW|CHANGED)"
    r"|(?:ACTIVITY|ATHLETIC|BUS|PARKING|LAB|STUDENT|CLASS|SCHOOL|PARTICIPATION|USER) FEES?\b"
    r"|FEE REFUND|ESACT|HSACT|MSACT|DWACT|EXT ?DAY|EXTENDED DAY|CHILD ?CARE|CLASS DUES", re.I)
PARENT_OTHER = re.compile(PARENT.pattern.replace('|PARENT REIMB', ''), re.I)
PARENT_ACCOUNT = re.compile(  # on the ACCOUNT (not the org, which is a programme): money
    r"ACTIVITY FEES|USER CHARGE|BUS FEE|^FEES$|SPECIAL ED TRANSPORTATION|TUITION|\bPLACEM"
    r"|REFUND", re.I)            # families pay in, or that is paid out for their child
# ...and a line masked only because of its ACCOUNT, or paid to somebody who may be staff --
# an employee match, or `STAFF` in the description -- is still masked, but counted as
# UNCERTAIN: it may be a staff reimbursement or a vendor, and nothing on the line says which.
STAFF_WORDING = re.compile(r"\bSTAFF\b", re.I)
# TJ, 19 October 2026: "transportation by payee is also ok to list names, including parents!
# As long as its not SPECIAL EDUCATION." A transportation payee -- a parent included -- is
# shown UNLESS the line posts to a special education account, org or fund (`SPED_ACCOUNTS`,
# tested on the account, org and fund names: the SPECIAL ED TRANSPORTATION object, the SPED
# circuit breaker fund, SPED grants such as IDEA/240 and 262, tuition, placement and
# out-of-district, and the student-service accounts), or its text names a special education
# service (`SPED_TEXT`). Only transportation: refunds, NSF, lunch and fees are unchanged.
# THE special education account list is defined ONCE, in scripts/journal.py, and imported: the
# accounts every special education report counts are exactly the accounts whose families this
# redaction masks.
from journal import SPED_ACCOUNTS  # noqa: E402
SPED_TEXT = re.compile(r"\bSPED\b|SPECIAL ED|\bIEP\b|\bOOD\b|OUT OF DIST|\bPLACEM|TUITION"
                       r"|\bACE\b|KEYSTONE|COLLAB", re.I)
# A line about transporting a child, or about money families pay in, says nothing on its own
# about WHO was paid: a parent driving their own child, or staff driving a student. So the
# PAYEE is classified across all their lines (`classify_payees`): a parent if any line says
# so (`PARENT_WORD`), staff if any says STAFF or they match an employee record (or, off the
# transport account, they are paid as a vendor elsewhere), and uncertain -- masked -- if
# nothing says which.
TRANSPORTISH = re.compile(r"TRANSPORT|\bTRANSP\b|TRASP|MILEAGE|FOSTER", re.I)
# Off the transport account, a payment for goods or for the payee's own professional work
# out of a fee account is a staff purchase, not a family's money.
VENDOR_WORDING = re.compile(r"SUPPL|EQUIP|PELLET|MATERIAL|\bITEMS\b|\bBOOKS?\b|COURSE"
                            r"|CONFERENCE|WORKSHOP|\bPD\b|TRAINING", re.I)
PARENT_WORD = re.compile(r"\bPARENT\b.*(?:REIMB|TRANSP|TRASP|MILEAGE)"
                         r"|(?:REIMB|TRANSP|MILEAGE).*\bPARENT\b", re.I)
# A reimbursement for what a student broke or did: naming the staff member narrows which
# student, so it is a family line too.
INCIDENT = re.compile(r"REIMB.*(?:\bINCID|BROKEN|DAMAG)|(?:\bINCID|BROKEN|DAMAG).*REIMB", re.I)
# A name matched in a public record that is NOT to be shown in text, held as the first eight
# hex digits of sha256 of `GIVEN SURNAME` (writing it down would publish it). Empty: since
# TJ's rule of 19 October 2026 a person paid as a vendor is shown, so nobody is held out.
NOT_IN_ROLE = {}
# A matched name on the Town's staff directory alone does not show it in the SCHOOL ledger,
# unless the line shows them acting in a town role.
TOWN_ROLE = re.compile(r"\b(?:FIRE|POLICE|DETAIL|DPW|HIGHWAY|TOWN)\b", re.I)
# Surnames that are not a person paid or acting in role -- a private donor -- masked wherever
# they appear: sha256 prefixes of the word, so the name is not written here.
HASHED_NAMES = {
    '0bc2f494': 'a private donor to a school gift fund',
}


def hashed(word):
    return hashlib.sha256(word.upper().encode()).hexdigest()[:8]


def mask_hashed(text):
    masked = []

    def one(m):
        if hashed(m.group(0)) in HASHED_NAMES:
            masked.append(m.group(0))
            return MASK
        return m.group(0)
    return re.sub(r"[A-Za-z]{3,}", one, text), masked


# A personal identifier printed in a description: a student or registration ID, or a long
# bare number on a person's line (a phone-bill or card number), is masked.
ID_NUMBER = re.compile(r"(?<![A-Za-z])ID\s?[#:]\s?[A-Z]?\d+", re.I)
LONG_NUMBER = re.compile(r"(?<![A-Za-z#\d:/-])\d{7,}(?![\d/-])")


def mask_ids(text, person_line):
    masked = [m.group(0) for m in ID_NUMBER.finditer(text)]
    out = ID_NUMBER.sub(lambda m: re.sub(r'[A-Z]?\d+$', MASK, m.group(0)), text)
    if person_line:
        masked += [m.group(0) for m in LONG_NUMBER.finditer(out)]
        out = LONG_NUMBER.sub(MASK, out)
    return out, masked


# ...unless the name is an administrative act in role, which says nothing about whose child.
ROLE_BEFORE = re.compile(r"(?:\bPER|\bBY|\bCLOSE|\bCLOSED|\bCANCEL|\bINC|\bINCREASE|\bDECRE"
                         r"|\bDECREASE|\bADJUST|\bADJ|\bRECLASS|\bAPPROVED"
                         r"|(?:CONFERENCE|TRAINING|WORKSHOP) FOR)\.?\s*$", re.I)
NAME_TOKEN = re.compile(r"[A-Za-z][A-Za-z'-]*")


def name_tokens(s):
    s = re.sub(r'\(.*?\)', ' ', s.upper()).replace("'", '')
    return [t.replace('-', '') for t in re.split(r'[^A-Z-]+', s)
            if t.strip('-') and t not in NAME_SUFFIX]


def person_key(name):
    """(given, surname) of a name as a roster or directory prints it."""
    if ',' in name:
        a, b = name.split(',', 1)
        sur, giv = name_tokens(a), name_tokens(b)
    else:
        t = name_tokens(name)
        sur, giv = t[-1:], (t[:1] if len(t) >= 2 else [])
    if not sur or not giv:
        return None
    return giv[0], sur[-1]


class Employees:
    """Who a public record shows was employed, and when. A match must be ONE person."""

    def __init__(self):
        self.by_sur = defaultdict(list)
        with open(ROSTER_CSV, encoding='utf-8') as fh:
            for r in csv.DictReader(fh):
                if 'COMMITTEE' in (r['grade_or_dept'] + ' ' + r['role_raw']).upper():
                    continue                        # elected, not employed
                k = person_key(r['name'])
                if k:
                    self.by_sur[k[1]].append(
                        (k[0], int(r['fy']), f"{r['document']} (FY{r['fy']} staff roster)"))
        for path, label in DIRECTORIES:
            with open(path, encoding='utf-8') as fh:
                for r in csv.DictReader(fh):
                    k = person_key(r['person'])
                    if k:
                        self.by_sur[k[1]].append(
                            (k[0], None if 'town' not in label else 'town',
                             f"{os.path.basename(path)} ({label}, fetched {r['fetched']})"))

    def lookup(self, giv, sur, fy, truncated=False, town_ok=False, any_year=False):
        """((given, surname), basis) if exactly one employee matches, else None."""
        giv, sur = giv.upper().replace('-', ''), sur.upper().replace('-', '')
        if len(sur) < 2 or not giv or not giv.isalpha() or not sur.isalpha():
            return None
        fy = int(fy)
        hits = {}
        for first, rfy, basis in self.by_sur.get(sur, ()):
            if rfy == 'town' and not town_ok:
                continue                            # the Town's directory proves a town job
            if any_year:
                score = 0 if rfy in (None, 'town') else abs(rfy - fy) + 0.5
            elif rfy is None or rfy == 'town':
                if fy not in DIRECTORY_YEARS:
                    continue
                score = 0
            elif abs(rfy - fy) > ROSTER_WINDOW:
                continue
            else:
                score = abs(rfy - fy) + 0.5
            if not (first == giv or (len(giv) == 1 and first[0] == giv)
                    or (truncated and len(giv) >= 4 and first.startswith(giv))):
                continue
            if first not in hits or (score, basis) < hits[first]:
                hits[first] = (score, basis)
        if not hits:
            return None
        firsts = sorted(hits, key=len)
        if any(not f.startswith(firsts[0]) for f in firsts):
            return None                             # two people: ambiguous
        best = min(hits.values())
        if hashed(f'{firsts[0]} {sur}') in NOT_IN_ROLE or any(
                hashed(f'{f} {sur}') in NOT_IN_ROLE for f in firsts):
            return None
        return (firsts[0], sur), best[1]

    def vendor(self, vendor, fy, town_ok=False):
        v = vendor.strip()
        cut = len(v) >= 19                          # the 20-character field may have cut it
        tries = []
        if ',' in v:
            a, b = v.split(',', 1)
            sur, giv = name_tokens(a), name_tokens(b)
            if sur and giv:
                tries.append((giv[0], sur[-1], cut and len(giv) == 1))
        else:
            t = name_tokens(v)
            if len(t) < 2:
                return None
            tries.append((t[1], t[0], cut and len(t) == 2))     # SURNAME FIRST [M]
            tries.append((t[0], t[-1], False))                  # FIRST [M] SURNAME
        found = {}
        for g, s_, tr in tries:
            r = self.lookup(g, s_, fy, tr, town_ok)
            if r:
                found[r[0]] = r[1]
        return next(iter(found.values())) if len(found) == 1 else None

    def spans(self, text, fy):
        """Every employee named in the text: [(start, end, basis)]."""
        town_ok = bool(TOWN_ROLE.search(text))
        toks = [(m.start(), m.end(), m.group(0)) for m in NAME_TOKEN.finditer(text)]
        out = []
        i = 0
        while i < len(toks):
            hit = None
            s1, e1, a = toks[i]
            # staff acting IN ROLE (`CLOSE PER <name>`) tie no child to anything: there any
            # roster year or directory proves the employee, not only the 2-year window
            role = bool(ROLE_BEFORE.search(text[:s1]))
            if i + 1 < len(toks):
                s2, e2, b = toks[i + 1]
                gap = text[e1:s2]
                if (re.fullmatch(r'\.?\s{1,2}|\.', gap)
                        and (len(a) > 1 or a.upper() not in ('A', 'I') or '.' in gap)):
                    r = (self.lookup(a, b, fy, town_ok=town_ok)
                         or (role and self.lookup(a, b, fy, town_ok=town_ok, any_year=True)))
                    if r:
                        hit = (s1, e2, r[1], 2)
                if not hit and re.fullmatch(r',\s?', gap) and len(b) >= 2:
                    r = (self.lookup(b, a, fy, town_ok=town_ok)  # SURNAME, GIVEN
                         or (role and self.lookup(b, a, fy, town_ok=town_ok, any_year=True)))
                    if r:
                        hit = (s1, e2, r[1], 2)
            if not hit and len(a) >= 5:
                r = (self.lookup(a[0], a[1:], fy, town_ok=town_ok)  # LSURNAME
                     or (role and self.lookup(a[0], a[1:], fy, town_ok=town_ok, any_year=True)))
                if r:
                    hit = (s1, e1, r[1], 1)
            if hit:
                out.append(hit[:3])
                i += hit[3]
            else:
                i += 1
        return out


def hold_employees(text, emp, fy, family, holds):
    """Swap each employee named in role for a placeholder nothing else can match, so no later
    rule masks them; in a family line, mask them instead. Returns (text, bases, masked)."""
    bases, masked = set(), []
    out = text
    for s, e, basis in reversed(emp.spans(text, fy)):
        if family and not ROLE_BEFORE.search(text[:s]):
            masked.append(text[s:e])
            out = out[:s] + MASK + out[e:]
            continue
        key = f'\x01{len(holds)}\x02'
        holds[key] = text[s:e]
        bases.add(basis)
        out = out[:s] + key + out[e:]
    return out, bases, masked


def hold_words(text, words, holds):
    """Hold each word of a shown payee's name -- or the cut-off start of one, ending the
    field -- so no name rule masks the payee on their own line."""
    up = {w.upper() for w in words}
    initials = {w[0] for w in up}

    def one(m):
        w = m.group(0).upper()
        last = not re.search(r'[A-Za-z]', text[m.end():])
        if (w in up or (last and len(w) >= 3 and any(x.startswith(w) for x in up))
                or any(len(x) >= 5 and w.startswith(x) for x in up)):   # `HANSCOMCOURSE`
            key = f'\x01\x03{len(holds)}\x02'
            holds[key] = m.group(0)
            return key
        return m.group(0)
    out = re.sub(r"[A-Za-z][A-Za-z'-]*", one, text)
    # `TOM WATSON` for THOMAS WATSON, `ALLYSON` for ALLISON: the word beside a held surname,
    # starting with the letter of one of the payee's names, is the payee's own name too.
    def near(m):
        w = m.group(0)
        if w.upper()[0] in initials and len(w) >= 2:
            key = f'\x01\x03{len(holds)}\x02'
            holds[key] = w
            return key
        return w
    out = re.sub(r"(?<![A-Za-z'\x02-])[A-Za-z][A-Za-z'-]*(?= \x01\x03\d+\x02)", near, out)
    return out


# The name words of every person shown as a vendor somewhere in the ledger, filled by
# `finish` before any row is redacted. On a line that is no family's, such a person named in
# the text (`SCHOOL PHYSICIAN FEE-DR. <name>`) is shown as they are on their own lines.
SHOWN_VENDORS = set()
FAMILY_END = re.compile(r"REFUND|RFND|\bNSF|REDEP|OVR ?PYMT|OVERPAY|LUNCH BALANCE", re.I)


def hold_shown(text, holds):
    def pair(m):
        a, b = m.group(1).upper(), m.group(2).upper()
        if (a, b) in SHOWN_VENDORS or (b, a) in SHOWN_VENDORS:
            key = f'\x01\x03{len(holds)}\x02'
            holds[key] = m.group(0)
            return key
        return m.group(0)
    out = re.sub(r"(?<![A-Za-z])([A-Za-z][A-Za-z'-]+) ([A-Za-z][A-Za-z'-]+)(?![A-Za-z])", pair, text)

    def doctor(m):                                  # `DR. <name>`, cut by the field
        w = m.group(0).upper()
        if any(x.startswith(w) for p in SHOWN_VENDORS for x in p):
            key = f'\x01\x03{len(holds)}\x02'
            holds[key] = m.group(0)
            return key
        return m.group(0)
    return re.sub(r"(?<=DR\. )[A-Za-z]{4,}|(?<=DR )[A-Za-z]{4,}", doctor, out)


def restore(text, holds):
    for k, v in holds.items():
        text = text.replace(k, v)
    return text


# The values the privacy read of 19 October 2026 found surviving, each of which must come out
# masked: (page, line, field, the first six hex digits of sha256 of `page:line:field:TOKEN`).
# Hashed, not written: the token is a child's initial or a parent's surname.
PRIVACY_READ = [
    (797, 29, 'description', 'f53454'),
    (109, 52, 'description', '72dac4'), (110, 25, 'description', 'f8dd67'),
    (110, 26, 'description', '3bf146'), (107, 44, 'description', 'bfb6aa'),
    (96, 35, 'description', 'd02d94'),
    (415, 21, 'description', '87cfac'), (414, 33, 'description', '7a8ebc'),
    (877, 17, 'description', '41d182'), (811, 26, 'description', '6a6a01'),
    (807, 44, 'description', '5c9025'), (699, 41, 'description', '27cd1e'),
    (604, 21, 'description', '74c8e2'), (604, 41, 'description', 'b98096'),
    (604, 44, 'description', '348126'), (606, 28, 'description', '44b1d7'),
    (1506, 14, 'description', '8d6c3d'), (807, 6, 'description', '0dc7a1'),
    (807, 10, 'description', 'e44567'), (836, 32, 'description', 'a85d78'),
    (1511, 6, 'description', '2d2d34'), (1446, 27, 'description', '73d9cf'),
    # the second read, 19 October 2026
    (640, 42, 'description', '82da17'), (1186, 40, 'description', 'c7e456'),
    (449, 29, 'description', '1d815d'), (1212, 35, 'description', 'd8dd35'),
    (861, 48, 'description', 'ea73fc'), (162, 31, 'description', 'ce3948'),
    (1506, 28, 'vendor', 'b7b842'), (1508, 27, 'vendor', '360dd5'),
]


def privacy_read_survivors(out):
    want = defaultdict(set)
    for p, l, field, h in PRIVACY_READ:
        want[(str(p), str(l), field)].add(h)
    bad = []
    for r in out:
        for field in ('vendor', 'doc_no', 'description', 'comment', 'check_no'):
            hs = want.get((r['page'], r['line'], field))
            if not hs:
                continue
            for tok in re.findall(r'[A-Za-z]+|\d+', r[field].replace(MASK, ' ')):
                h = hashlib.sha256(f"{r['page']}:{r['line']}:{field}:{tok.upper()}".encode()).hexdigest()[:6]
                if h in hs:
                    bad.append(f"p{r['page']}:{r['line']} {field}")
    return bad


# --- reading the page --------------------------------------------------------------------

def load_raw():
    if not os.path.exists(RAW_LOCAL):
        import archive_storage as A
        blob = A.get_private('raw/' + RAW_KEY)
        os.makedirs(os.path.dirname(RAW_LOCAL), exist_ok=True)
        with open(RAW_LOCAL + '.part', 'wb') as fh:
            fh.write(blob)
        os.replace(RAW_LOCAL + '.part', RAW_LOCAL)
    blob = open(RAW_LOCAL, 'rb').read()
    sha = hashlib.sha256(blob).hexdigest()
    if sha != RAW_SHA256:
        raise SystemExit(f'{RAW_LOCAL}: sha256 {sha[:12]}, expected {RAW_SHA256[:12]} -- not '
                         'the document this extractor was written against')
    return blob


def page_lines(page):
    tp = page.get_textpage()
    rows = defaultdict(dict)
    for i in range(tp.count_chars()):
        ch = tp.get_text_range(i, 1)
        if not ch.strip():
            continue
        l, b, r, t = tp.get_charbox(i, loose=True)
        rows[round(b)][round((l - X0) / PITCH)] = ch
    out = []
    for y in sorted(rows, reverse=True):
        r = rows[y]
        s = [' '] * (max(r) + 1)
        for k, c in r.items():
            if k >= 0:
                s[k] = c
        out.append(''.join(s))
    return out


def dec(s):
    s = s.strip().replace(',', '')
    return Decimal(s) if s else Decimal('0')


def split_journal(l):
    """Cut a journal line by column. Returns the raw fields, unmasked."""
    m = J.match(l)
    fy, per, seq, mm, dd, yyyy, src = m.groups()
    f = {'fiscal_year': fy, 'period': str(int(per)), 'journal': f'{fy}/{per}/{seq}',
         'effective_date': f'{yyyy}-{mm}-{dd}', 'source': src,
         'amount': str(dec(AMOUNT.match(l).group(1))),
         'ref_type': l[48:51].strip(), 'vendor_no': '', 'vendor': '', 'doc_type': '',
         'doc_no': '', 'description': '', 'check_no': ''}
    if f['ref_type'] == 'VND':
        f['vendor_no'] = l[52:58].strip()
        if l[59:61] == 'IN':
            f['doc_type'], f['doc_no'] = 'IN', l[62:83].strip()
            f['vendor'], f['description'] = l[83:103].strip(), l[104:122].strip()
            f['check_no'] = l[122:].strip()
        elif l[59:62] == 'DOC':
            f['doc_type'], f['doc_no'] = 'DOC', l[59:71].strip()
            f['vendor'], f['description'] = l[71:91].strip(), l[92:].strip()
        else:
            f['doc_type'], f['doc_no'] = l[59:61].strip(), l[62:70].strip()
            f['vendor'], f['description'] = l[71:91].strip(), l[92:].strip()
    elif f['ref_type'] == 'REF':
        f['doc_no'] = l[52:60].strip()
        f['description'] = re.sub(r'\s{2,}', ' ', l[60:].strip())
    else:
        raise ValueError('unknown reference type %r in %r' % (f['ref_type'], l))
    return f


def read_image_pages(reading):
    if not os.path.exists(reading):
        raise SystemExit(f'{reading}: the by-eye reading of pages {IMAGE_PAGES} is not there. It is '
                         'private and irreplaceable; copy it in, never regenerate it')
    by_page = defaultdict(list)
    with open(reading, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            fy, per, seq = r['journal'].split('/')
            mm, dd, yyyy = r['date'].split('/')
            by_page[int(r['page'])].append({
                'fiscal_year': fy, 'period': str(int(per)), 'journal': r['journal'],
                'effective_date': f'{yyyy}-{mm}-{dd}', 'source': r['source'],
                'amount': str(dec(r['amount'])), 'ref_type': r['ref_type'],
                'vendor_no': r['vendor_no'], 'vendor': r['vendor'], 'doc_type': r['doc_type'],
                'doc_no': r['doc_no'], 'description': r['description'],
                'check_no': r['check_no'], 'line': r['line'],
                '_date': r['date'], '_amount': r['amount']})
    if sorted(by_page) != list(IMAGE_PAGES):
        raise SystemExit('the read-by-eye file covers pages %s, expected %s'
                         % (sorted(by_page), IMAGE_PAGES))
    return by_page


def parse(blob, reading):
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(blob)
    if len(doc) != PAGES:
        raise SystemExit(f'{len(doc)} pages, expected {PAGES}')
    eye = read_image_pages(reading)
    accounts, rows, totals, problems, fund_starts = [], [], [], [], []
    fund = fund_name = org = org_name = ''
    pending = None
    cur = None
    grand = None
    for pn in range(1, PAGES + 1):
        lines = page_lines(doc[pn - 1])
        if not lines:
            if pn not in IMAGE_PAGES:
                problems.append(f'page {pn} has no text layer and is not a known picture page')
                continue
            for r in eye[pn]:
                r.update({'page': str(pn), 'read': 'by eye (picture page)', 'comment': ''})
                cur['lines'].append(r)
                rows.append((cur, r))
            continue
        if pn in IMAGE_PAGES:
            problems.append(f'page {pn} has a text layer; the read-by-eye file is stale')
        last = None
        for ln, l in enumerate(lines, 1):
            prev, last = last, None
            m = FUND.match(l)
            if m:
                if m.group(1) != fund:
                    fund_starts.append(len(accounts))
                fund, fund_name = m.group(1), m.group(2).strip()
                continue
            if FURNITURE.match(l):
                continue
            if J.match(l):
                f = split_journal(l)
                f.update({'page': str(pn), 'line': str(ln), 'read': 'text layer',
                          'comment': ''})
                cur['lines'].append(f)
                rows.append((cur, f))
                last = 'journal'
                continue
            if pn >= PAGES - 1 and ('END OF REPORT' in l or 'APPROP' in l or 'ORIGINAL' in l
                                     or pn == PAGES):
                continue          # the report options page, and the grand-total furniture
            m = ACC.match(l)
            if m:
                pending = (m.group(0).split()[0], m.group(9), m.group(10).strip(),
                           m.group(8))
                if m.group(1) != fund:
                    problems.append(f'p{pn}: account {pending[0]} under fund header {fund}')
                continue
            m = FIG.match(l)
            if m and pending:
                cur = {'fund': fund, 'fund_name': fund_name, 'org': org, 'org_name': org_name,
                       'account': pending[0], 'object': pending[1],
                       'account_description': pending[2], 'type_digit': pending[3],
                       'page': str(pn), 'lines': []}
                for k, v in zip(FIGURE_FIELDS, m.groups()[:6]):
                    cur[k] = dec(v)
                cur['pct_used'] = m.group(7)
                accounts.append(cur)
                pending = None
                continue
            m = TOT.match(l)
            if m:
                figs = [dec(x) for x in m.groups()[2:8]]
                if m.group(1) == 'GRAND TOTAL':
                    grand = figs
                else:
                    totals.append((pn, m.group(2).strip(), figs, len(accounts),
                                   fund_starts[-1]))
                continue
            m = ORG.match(l)
            if m:
                org, org_name = m.group(1), m.group(2).strip()
                continue
            if l.startswith(COMMENT_INDENT) and prev in ('journal', 'comment'):
                c = rows[-1][1]
                c['comment'] = (c['comment'] + ' ' + l.strip()).strip()
                last = 'comment'
                continue
            problems.append(f'p{pn} line {ln}: unrecognised: {l.strip()[:60]!r}')
    if problems:
        raise SystemExit('refusing: the page did not read cleanly\n  ' + '\n  '.join(problems[:20]))
    return accounts, rows, totals, grand


# --- the ties ----------------------------------------------------------------------------

def sums(lines, fy):
    s = defaultdict(Decimal)
    for r in lines:
        if r['fiscal_year'] == fy:
            s[COLUMN_OF[r['source']]] += Decimal(r['amount'])
    return s


def tie(accounts, totals, grand):
    fails = []
    for a in accounts:
        unknown = {r['source'] for r in a['lines']} - set(COLUMN_OF)
        if unknown:
            fails.append(f"{a['account']}: unknown source(s) {sorted(unknown)}")
            continue
        s = sums(a['lines'], '2026')
        want = {'original_approp': s['original_budget'], 'transfers_adjustments': s['transfer'],
                'revised_budget': s['original_budget'] + s['transfer'],
                'ytd_actual': s['actual'], 'encumbrances': s['encumbrance'],
                'available_budget': s['original_budget'] + s['transfer'] - s['actual']
                - s['encumbrance']}
        for k, v in want.items():
            if a[k] != v:
                fails.append(f"FY2026 {a['account']} (p{a['page']}): {k} printed {a[k]}, "
                             f"journal {v}")
    # Every TOTAL line, against the accounts it covers. The report prints three levels and
    # does not label them: an org total (the accounts since the last org total), a fund
    # total (every account in the fund), and inside a fund that has both, `TOTAL REVENUES`
    # and `TOTAL EXPENSES` (its revenue accounts -- type digit 4 -- and the rest). A line is
    # accepted at whichever level it closes, and every account must sit under an org total.
    def add(block):
        return [sum((a[k] for a in block), Decimal(0)) for k in FIGURE_FIELDS]
    prev = 0
    levels = Counter()
    for pn, name, figs, upto, fstart in totals:
        fund_block = accounts[fstart:upto]
        if add(accounts[prev:upto]) == figs and upto > prev:
            levels['org'] += 1
            prev = upto
        elif add(fund_block) == figs:
            levels['fund'] += 1
            prev = upto
        elif add([a for a in fund_block if a['type_digit'] == '4']) == figs:
            levels['revenue'] += 1
        elif add([a for a in fund_block if a['type_digit'] != '4']) == figs:
            levels['expense'] += 1
        elif upto == prev and all(v == 0 for v in figs):
            levels['empty'] += 1
        else:
            fails.append(f'p{pn} TOTAL {name}: printed {figs}, closes at no level')
    if prev != len(accounts):
        fails.append(f'{len(accounts) - prev} accounts after the last TOTAL line')
    tie.levels = levels
    if grand is None:
        fails.append('no GRAND TOTAL read')
    else:
        got = [sum((a[k] for a in accounts), Decimal(0)) for k in FIGURE_FIELDS]
        if got != grand:
            fails.append(f'GRAND TOTAL printed {grand}, accounts {got}')
    # the closed years, against the published period-13 spreadsheets
    ytd = {}
    with open(YTD_CSV, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            ytd[(r['fiscal_year'], r['account'])] = r
    by_acct = {a['account']: a for a in accounts}
    matched = Counter()
    q = Decimal('0.01')
    for (fy, acct), r in ytd.items():
        a = by_acct.get(acct)
        if a is None:
            continue
        s = sums(a['lines'], fy)
        e = Decimal(r['ytd_expended']).quantize(q)
        b = Decimal(r['revised_budget']).quantize(q)
        if s['actual'] != e:
            fails.append(f'FY{fy} {acct}: journal actual {s["actual"]}, period-13 '
                         f'spreadsheet {e}')
        if s['original_budget'] + s['transfer'] != b:
            fails.append(f'FY{fy} {acct}: journal budget '
                         f'{s["original_budget"] + s["transfer"]}, spreadsheet {b}')
        matched[fy] += 1
    return fails, matched, len(ytd)


# --- redaction ---------------------------------------------------------------------------

# A revenue line that is ONE family's money, not a day's takings: a bounced check, a
# redeposit, a refund, a receipt corrected, a check number. (A line naming its payer is
# caught too: any masked revenue line loses its receipt number, below.)
FAMILY_REVENUE = re.compile(r"\bNSF|REDEP|REFUND|RFND|\bRCPT\b|\bCK ?#|OVERPAY|OVR ?PYMT", re.I)


def row_kind(acct, f):
    """(incident, says-parent, soft, transport) for one person-vendor row."""
    text = f['description'] + ' ' + f['comment']
    incident = bool(INCIDENT.search(text))
    said = bool(PARENT.search(text))
    transport = bool(TRANSPORTISH.search(text)) or 'TRANSPORT' in acct['account_description']
    soft = transport or bool(PARENT_ACCOUNT.search(acct['account_description']))
    return incident, said, soft and not said, transport


def payee_key(f):
    return (f['vendor_no'], f['vendor'])


def classify_payees(pairs, emp):
    """parent / staff / uncertain for every person-vendor, from ALL their lines."""
    lines = defaultdict(list)
    for a, f in pairs:
        if (f['ref_type'] == 'VND' and f['vendor'] and f['vendor'] != MASK
                and not is_business(f['vendor'])):
            lines[payee_key(f)].append((a, f))
    out = {}
    for k, rows in lines.items():
        kinds = [row_kind(a, f) for a, f in rows]
        if any(PARENT_WORD.search(f['description'] + ' ' + f['comment']) for a, f in rows):
            out[k] = 'parent'
        elif any(STAFF_WORDING.search(f['description']) for a, f in rows) or any(
                emp.vendor(f['vendor'], f['fiscal_year']) for a, f in rows):
            out[k] = 'staff'
        elif not any(t for _, _, _, t in kinds) and (
                any(not (i or s or so) for i, s, so, _ in kinds)
                or any(VENDOR_WORDING.search(f['description']) for a, f in rows)):
            out[k] = 'staff'                        # paid as a vendor, or buying for the school
        else:
            out[k] = 'uncertain'
    return out


def redact(acct, f, emp):
    """Apply the declared rule to one row, in place. Returns the masked field names.

    A matched employee named in text is left as a placeholder in `f['_holds']` until every
    pass -- including the cross-row one in `build` -- has run, so nothing can mask them."""
    masked = []
    fy = f['fiscal_year']
    vendor = f['vendor']
    student_account = bool(STUDENT_ACCOUNT.search(acct['account_description'])
                           or STUDENT_ACCOUNT.search(acct['org_name']))
    context = ' | '.join([f['description'], f['comment'],
                          '' if 'DUES AND FEES' in acct['account_description']
                          else acct['account_description'], acct['org_name']])
    family = bool(FAMILY.search(context)) or bool(INCIDENT.search(f['description'] + ' ' + f['comment']))
    holds, bases, new_masks = {}, set(), []
    f['_vendor_shown'] = f['_vendor_family'] = False
    f['_person'] = f['ref_type'] == 'VND' and (vendor == MASK or not vendor or not is_business(vendor))
    f['_raw_vendor'], f['_raw_doc_no'] = vendor, f['doc_no']
    person_words = set()
    f['_uncertain'] = False
    own = set()
    if f['_person']:
        known = bool(vendor) and vendor != MASK
        basis = emp.vendor(vendor, fy, bool(TOWN_ROLE.search(f['description']))) if known else None
        incident = bool(INCIDENT.search(f['description'] + ' ' + f['comment']))
        said, soft, transport = row_kind(acct, f)[1:4]
        payee = f.get('_payee_class')
        text = f['description'] + ' ' + f['comment']
        open_transport = transport and not (
            SPED_ACCOUNTS.search(' | '.join([acct['account_description'], acct['org_name'],
                                             acct['fund_name']])) or SPED_TEXT.search(text))
        if open_transport and not incident and not PARENT_OTHER.search(text):
            said = False                            # a non-SPED transport payee is listed
            payee = 'staff' if payee in ('parent', 'uncertain') else payee
        parent = (incident or said or payee == 'parent'
                  or (soft and payee != 'staff'))
        if not vendor:
            # The printed payee field is BLANK: it stays blank -- writing `individual
            # (redacted)` would claim a name the source does not print. Nothing on the line
            # says who was paid, so the numbers that would lead back to them go.
            f['_person'] = False
            for k in ('vendor_no', 'check_no'):
                if f.get(k):
                    f[k] = ''
                    masked.append(k)
            if parent:
                if f['doc_type'] == 'IN' and f['doc_no']:
                    f['doc_no'] = ''
                    masked.append('doc_no')
        elif known and not parent:
            f['_vendor_shown'] = True               # paid as a vendor: shown
            bases.add(basis or ('scholarship award' if SCHOLARSHIP.search(context)
                                else 'paid as vendor'))
            own = {w for w in re.split(r"[\s,.]+", vendor) if len(w) >= 2}
        else:
            f['_vendor_family'] = bool(basis)
            f['_uncertain'] = known and not incident and not said and payee == 'uncertain'
            person_words = {w for w in re.split(r"[\s,.]+", vendor) if w and w != MASK}
            f['vendor'] = INDIVIDUAL
            f['vendor_no'] = ''
            masked += ['vendor', 'vendor_no']
            if f.get('check_no'):
                f['check_no'] = ''                  # the warrant prints the payee by check
                masked.append('check_no')
            if f['doc_type'] == 'IN' and f['doc_no']:
                f['doc_no'] = ''
                masked.append('doc_no')
    # A family's payment into the schools -- a bounced check, a redeposit, a refund, a fee,
    # user charge, extended-day, lunch or gift receipt -- carries the family's own check and
    # receipt numbers even where the Town blanked the payer: both go. So does the receipt
    # number of a workers' compensation line.
    family_rev = f['ref_type'] == 'REF' and bool(
        FAMILY_REVENUE.search(f['description'] + ' ' + f['comment'])
        or CLAIM_LINE.search(f['description']))
    if family_rev:
        if f['doc_no']:
            f['doc_no'] = ''
            masked.append('doc_no')
    if f['doc_no']:
        text = f['doc_no']
        new, b, m = hold_employees(text, emp, fy, family, holds)
        if own:
            new = hold_words(new, own, holds)
        bases |= b
        new = mask_names(new)
        new, m2 = mask_residue(new)
        new, m3 = mask_hashed(new)
        new_masks += [('doc_no', w) for w in m + m2 + m3]
        if new != text and MASK in new:
            masked.append('doc_no')
        f['doc_no'] = new
    for field in ('description', 'comment'):
        text = f[field]
        if not text:
            continue
        new, b, m = hold_employees(text, emp, fy, family, holds)
        bases |= b
        if own:
            new = hold_words(new, own, holds)       # a shown payee's own name stays
        if SHOWN_VENDORS and not PARENT.search(text) and not INCIDENT.search(text):
            new = hold_shown(new, holds)            # a vendor shown elsewhere, named here
        new = mask_words(new, person_words) if person_words else new
        new, _n = mask_sped(new)
        new, m1 = mask_service(new, student_account)
        new, m2 = mask_payer(new)
        new, m3 = mask_receipt_tail(new) if (f['ref_type'] == 'REF' and family) else (new, [])
        new, m4 = mask_claim(new)
        new, m6 = mask_ids(new, f['_person'] or f['ref_type'] == 'REF')
        new, m7 = mask_hashed(new)
        m4 = m4 + m6 + m7
        new = mask_names(new)
        new, m5 = mask_residue(new)
        if FAMILY_END.search(text):                 # a family line ends on the payer's initial
            new = re.sub(r"(?<![A-Za-z\x01-\x03])([A-Za-z]{1,2})(\s*(?:(?:19|20)\d\d)?)$",
                         lambda m: m.group(0) if m.group(1).upper() in TWO_LETTER_OK
                         else MASK + m.group(2), new)
        if family_rev:                              # the family's own check and receipt numbers
            new = re.sub(r'(CK ?#?\s*)\d+', lambda m: m.group(1) + MASK, new)
            new = re.sub(r'(RCPT\s*#\s*)\d+', lambda m: m.group(1) + MASK, new)
        if person_words:                            # the cut-off end of the payee's own name
            last = re.search(r"([A-Za-z]{3,})(\s*(?:(?:19|20)\d\d)?)$", new)
            if last and any(w.upper().startswith(last.group(1).upper())
                            and w.upper() != last.group(1).upper() for w in person_words):
                m5 = m5 + [last.group(1)]
                new = new[:last.start()] + MASK + last.group(2)
        new_masks += [(field, w) for w in m + m1 + m2 + m3 + m4 + m5]
        if MASK in new and new != text:
            masked.append(field)
        elif MASK in text and field not in masked:
            masked.append(field)      # masked at the reading (a picture page)
        f[field] = new
    f['_holds'] = holds
    f['_new_masks'] = new_masks
    f['name_basis'] = '; '.join(sorted(bases))
    return masked


def mask_payee(r):
    """Turn a shown payee's row into a masked one, in place."""
    r['vendor'], r['vendor_no'], r['check_no'] = INDIVIDUAL, '', ''
    if r['doc_type'] == 'IN':
        r['doc_no'] = ''
    r['masked'] = ';'.join(dict.fromkeys(
        [x for x in r['masked'].split(';') if x] + ['vendor', 'vendor_no']))
    r['_vendor_shown'] = False
    for k in list(r['_holds']):
        if k.startswith('\x01\x03'):
            r['_holds'][k] = MASK                   # their own name, held, goes with them
    if not any(v != MASK for v in r['_holds'].values()):
        r['name_basis'] = ''


def po_groups(out):
    """Rows that belong to one purchase: every PO row by its number, and each invoice (API)
    with the PO line (POL) it liquidates -- the next row, same vendor."""
    groups = defaultdict(list)
    for i, r in enumerate(out):
        if r['doc_type'] == 'PO' and r['_raw_doc_no']:
            groups[r['_raw_doc_no']].append(i)
        elif r['source'] == 'API' and i + 1 < len(out):
            n = out[i + 1]
            if (n['source'] == 'POL' and n['_raw_vendor'] == r['_raw_vendor']
                    and n['_raw_doc_no']):
                groups[n['_raw_doc_no']].append(i)
    return groups


def po_consistency(out):
    """If any row of a purchase masks its payee, every row of it does: no name on the PO
    while the invoice that pays it is masked. The payee's name and initials go too."""
    changed = 0
    for rows in po_groups(out).values():
        # a row with no payee printed at all is no evidence about who was paid
        if not any(out[i]['_person'] and out[i]['vendor'] == INDIVIDUAL and out[i]['_raw_vendor']
                   for i in rows):
            continue
        names = {out[i]['_raw_vendor'] for i in rows if out[i]['_person'] and out[i]['_raw_vendor']}
        words = {w for n in names for w in re.split(r"[\s,.]+", n) if len(w) > 1 and w != MASK}
        initials = set()
        for n in names:
            t = name_tokens(n)
            if len(t) >= 2:
                initials |= {(t[0][0], t[1][0]), (t[1][0], t[0][0])}
        for i in rows:
            r = out[i]
            if r['_person'] and r['vendor'] != INDIVIDUAL:
                mask_payee(r)
                changed += 1
            elif not r['_raw_vendor'] and r['ref_type'] == 'VND' and (r['vendor_no'] or r['check_no']):
                r['vendor_no'], r['check_no'] = '', ''      # a blank payee on a masked purchase
            for k in list(r['_holds']):
                r['_holds'][k] = MASK               # nobody on a masked purchase is shown
            for field in ('description', 'comment'):
                new = mask_words(r[field], words)
                for a, b in initials:
                    new = re.sub(r'(?<![A-Za-z])' + a + r'\.?\s?' + b + r'(?![A-Za-z])', MASK, new)
                if new != r[field]:
                    r['_new_masks'] += [(field, w) for w in words if w in r[field]]
                    r[field] = new
                    if field not in r['masked'].split(';'):
                        r['masked'] = ';'.join(x for x in (r['masked'], field) if x)
            if not r['_holds'] or all(v == MASK for v in r['_holds'].values()):
                if not r['_vendor_shown']:
                    r['name_basis'] = ''
    return changed


def build(blob, reading):
    accounts, pairs, totals, grand = parse(blob, reading)
    fails, matched, nytd = tie(accounts, totals, grand)
    if fails:
        raise SystemExit('refusing to write: %d tie(s) failed\n  %s'
                         % (len(fails), '\n  '.join(fails[:25])))
    return finish(accounts, pairs, totals, matched, nytd)


def finish(accounts, pairs, totals, matched, nytd):
    emp = Employees()
    classes = classify_payees(pairs, emp)
    for a, f in pairs:
        f['_payee_class'] = classes.get(payee_key(f))
    SHOWN_VENDORS.clear()
    for a, f in pairs:
        if (f['ref_type'] == 'VND' and f['vendor'] and f['vendor'] != MASK
                and not is_business(f['vendor']) and f['_payee_class'] != 'parent'):
            i, said, soft, _ = row_kind(a, f)
            if not (i or said or (soft and f['_payee_class'] != 'staff')):
                t = name_tokens(f['vendor'])
                if len(t) >= 2:
                    SHOWN_VENDORS.add((t[0], t[1]))
                    SHOWN_VENDORS.add((t[0], t[-1]))
    out = []
    counts = Counter()
    raw_vendors = {}
    for a, f in pairs:
        raw = dict(f)
        masked = redact(a, f, emp)
        for m in masked:
            counts[m] += 1
        if 'vendor' in masked and raw['vendor']:
            raw_vendors[raw['vendor']] = True
        row = {k: f.get(k, '') for k in FIELDS}
        row.update({'posts_to': COLUMN_OF[f['source']], 'fund': a['fund'],
                    'fund_name': a['fund_name'], 'org': a['org'], 'org_name': a['org_name'],
                    'account': a['account'], 'object': a['object'],
                    'account_description': a['account_description'],
                    'masked': ';'.join(dict.fromkeys(masked)),
                    '_holds': f['_holds'], '_new_masks': f['_new_masks'],
                    '_vendor_shown': f['_vendor_shown'], '_person': f['_person'],
                    '_uncertain': f['_uncertain'], '_payee_class': f.get('_payee_class'),
                    '_raw_vendor': f['_raw_vendor'], '_raw_doc_no': f['_raw_doc_no'],
                    '_date': f.get('_date', ''), '_amount': f.get('_amount', '')})
        out.append(row)
    counts['vendor (masked with the rest of its purchase order)'] = po_consistency(out)
    for r in out:
        if r['_person'] and r['vendor'] == INDIVIDUAL and r['_raw_vendor'] not in ('', MASK):
            raw_vendors[r['_raw_vendor']] = True
    # A person paid in one row is often NAMED in another -- `CPI TRAINING FOR <name>` on a
    # business's invoice. So every masked vendor name, in either order, is masked in every
    # description and comment -- except where it names a matched employee in role, which is
    # held as a placeholder and cannot match.
    variants = set()
    for v in raw_vendors:
        toks = [t for t in re.split(r'[\s,]+', v) if t]
        if v == MASK or len(v) <= 3 or len(toks) < 1:
            continue
        variants.add(' '.join(toks))
        if len(toks) >= 2:
            variants.add(' '.join(toks[1:] + toks[:1]))
            variants.add(' '.join(toks[-1:] + toks[:-1]))
    pat = re.compile(r'(?<![A-Z0-9])(' + '|'.join(
        re.escape(x) for x in sorted(variants, key=len, reverse=True)) + r')(?![A-Z0-9])')
    for r in out:
        for field in ('description', 'comment'):
            new = pat.sub(MASK, r[field])
            if new != r[field]:
                new, more = mask_residue(new)
                r['_new_masks'] += [(field, w) for w in more]
                r[field] = new
                if field not in r['masked'].split(';'):
                    r['masked'] = ';'.join(x for x in (r['masked'], field) if x)
                counts[field + ' (name of a person paid elsewhere)'] += 1
    # A receipt number on a masked revenue line points back to the payer, as a check number
    # does on a masked payee's line: both go.
    for r in out:
        if r['ref_type'] == 'REF' and r['masked'] and r['doc_no']:
            r['doc_no'] = ''
            if 'doc_no' not in r['masked'].split(';'):
                r['masked'] = ';'.join(x for x in (r['masked'], 'doc_no') if x)
            counts['doc_no (receipt on a masked revenue line)'] += 1
        if r['vendor'] == INDIVIDUAL and r['check_no']:
            r['check_no'] = ''
    # Every check below reads the rows with the matched employees still held out: a shown
    # employee is the one name allowed to survive.
    def visible(r, k):
        return '' if k == 'vendor' and r['_vendor_shown'] else r[k]
    text = '\n'.join('|'.join(visible(r, k) for k in FIELDS) for r in out)
    # every person's name that was masked must be absent from every field of the output
    leaks = [v for v in raw_vendors
             if v and v != MASK and len(v) > 3
             and re.search(r'(?<![A-Z])' + re.escape(v) + r'(?![A-Z])', text)]
    if leaks:
        raise SystemExit('refusing to write: %d masked vendor name(s) survive in the output'
                         % len(leaks))
    # and no declared name word survives in free text, outside a protected phrase
    survivors = Counter()
    for r in out:
        for field in ('description', 'comment', 'doc_no'):
            for m in NAME_RE.finditer(KEEP_RE.sub('', r[field])):
                survivors[m.group(0).upper()] += 1
    if survivors:
        raise SystemExit('refusing to write: declared names survive: %d' % sum(survivors.values()))
    # and no word a new rule masked survives in the field it was masked from
    back = []
    for r in out:
        for field, w in r['_new_masks']:
            w = re.sub(r'[^A-Za-z0-9]', '', w)
            if len(w) >= 3 and re.search(r'(?<![A-Za-z0-9])' + re.escape(w) + r'(?![A-Za-z0-9])',
                                         r[field], re.I):
                back.append(f"p{r['page']}:{r['line']} {field}")
    if back:
        raise SystemExit('refusing to write: %d masked word(s) survive in their own field: %s'
                         % (len(back), ', '.join(back[:10])))
    bad = privacy_read_survivors(out)
    if bad:
        raise SystemExit('refusing to write: %d value(s) the 19 October privacy read found '
                         'survive: %s' % (len(bad), ', '.join(bad)))
    # now, and only now, the matched employees go back in
    shown = Counter()
    for r in out:
        for field in ('doc_no', 'description', 'comment'):
            r[field] = restore(r[field], r['_holds'])
            if '\x01' in r[field]:
                raise SystemExit(f"p{r['page']}:{r['line']}: a placeholder was not restored")
        for k, v in r['_holds'].items():
            if v != MASK and not k.startswith('\x01\x03'):
                shown[(v.upper(), r['name_basis'])] += 1
        if r['_vendor_shown']:
            shown[(r['vendor'].upper(), r['name_basis'])] += 1
    image_rows = []
    for r in out:
        if r['read'] == 'text layer':
            continue
        ir = {k: r.get(k, '') for k in IMAGE_FIELDS}
        ir.update({'date': r['_date'], 'amount': r['_amount']})
        image_rows.append(ir)
    acc_rows = []
    for a in accounts:
        r = {k: a.get(k, '') for k in ACCOUNT_FIELDS}
        for k in FIGURE_FIELDS:
            r[k] = str(a[k])
        r['journal_lines'] = str(len(a['lines']))
        acc_rows.append(r)
    stats = {'rows': len(out), 'accounts': len(accounts), 'totals': len(totals),
             'matched': matched, 'ytd_rows': nytd, 'masked': counts,
             'by_eye': sum(1 for r in out if r['read'] != 'text layer'),
             'individual_vendors': len(raw_vendors), 'shown': shown,
             'employee_rows': sum(1 for r in out if r['name_basis']),
             'uncertain': sum(1 for r in out if r['_uncertain'] and r['vendor'] == INDIVIDUAL)}
    finish.rows = out                               # for a reviewer in the same process
    out = [{k: r[k] for k in FIELDS} for r in out]
    return out, acc_rows, image_rows, stats


def to_csv(fields, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator='\n')
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def review(out):
    """Every distinct vendor and description, after redaction, for a person to read."""
    vend = Counter(r['vendor'] for r in out)
    print('== %d distinct vendors (after redaction) ==' % len(vend))
    print(' | '.join(sorted(vend)))
    for field in ('description', 'comment', 'doc_no'):
        vals = Counter(re.sub(r'\d', '9', r[field]) for r in out if r[field])
        print('\n== %d distinct %s values (digits shown as 9) ==' % (len(vals), field))
        for v in sorted(vals):
            print(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--review', action='store_true')
    ap.add_argument('--out', metavar='DIR', help='write (or check) the outputs in DIR, and read '
                    'the by-eye reading from DIR/' + READING_NAME)
    args = ap.parse_args()
    where = paths(args.out)
    out, acc_rows, image_rows, st = build(load_raw(), where['reading'])
    if args.review:
        review(out)
        return 0
    outputs = {where['journal']: to_csv(FIELDS, out),
               where['accounts']: to_csv(ACCOUNT_FIELDS, acc_rows),
               where['image']: to_csv(IMAGE_FIELDS, image_rows)}
    print(f"{st['rows']:,} journal lines ({st['by_eye']} read by eye from the 3 picture "
          f"pages) in {st['accounts']:,} accounts")
    print(f"ties: every account's FY2026 figures, {st['totals']:,} TOTAL lines and the GRAND "
          f"TOTAL; FY2023-FY2026 against the period-13 spreadsheets for "
          f"{dict(sorted(st['matched'].items()))} accounts")
    print(f"masked: {dict(st['masked'])}; {st['individual_vendors']} distinct vendor names "
          f"masked as a parent or family")
    print(f"shown by name (vendors and employees in role): {len({n for n, _ in st['shown']})} distinct "
          f"on {st['employee_rows']:,} lines")
    if args.check:
        stale = [p for p, body in outputs.items()
                 if not os.path.exists(p) or open(p, encoding='utf-8').read() != body]
        if stale:
            print('--check: stale: ' + ', '.join(os.path.relpath(p, ROOT) for p in stale))
            return 1
        print('--check: outputs match a fresh rebuild; all ties pass')
        return 0
    for p, body in outputs.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = p + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='') as fh:
            fh.write(body)
        os.replace(tmp, p)
        print('wrote', os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
