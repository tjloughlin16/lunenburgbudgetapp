#!/usr/bin/env python3
"""Every department, board and school as an ORG CHART: who held which role, by year.

    python3 scripts/build_org_charts.py [--check]

Writes `sources/data/org-chart.csv` and `fy28/public/data/org-charts.json`.

TJ, 22 September 2026: *"I want to BUILD the org chart for every department, every board,
and the school, on one page 'Town Wide Org Charts'. Selectable by dropdown... and we can
do it for each FY... THEN we have the true mapping of personnel"*, and: *"this helps the
data model because the backend needs to map dept -> people in various roles."*

WHY THIS IS A TEST AND NOT JUST A PAGE. Every other reading in this project counts things:
how many staff, how many seats, how much money. A chart of WHO IS IN WHICH ROLE cannot be
counted into existence -- it either joins a department to named people with named roles or
it visibly does not, per year. That makes it the sharpest check the data model has, and it
found its first defect before a line of the page was written: 57 rows across ten years
hold a `person` like `Follow us on Facebook at...` under a `post` like
`TOTAL AREA- 26.63 MILES`, which is the town PROFILE page bleeding into the officials
listing. Those are rejected here and counted, never drawn.

AND IT IS THE FIRST ONE THAT EXISTS. TJ: *"not every department posts one publicly
(<cough> schools) so this is the first ever publicly available org chart for many
departments outside the annual report of hundreds of pages."* The material has always been
public; it has never been assembled.

FOUR SOURCES, ONE SHAPE. Each row is (fy, unit, section, role, person, status):

  town-personnel.csv       boards, committees and appointed officers, with the vacancies
                           the listing itself states
  department-rosters.csv   Police and Fire by name and rank, read off two- and
                           three-column pages
  staff-roster-entries.csv the four schools, by name and position
  department-staffing.csv  the departments that name their staff in prose -- the Council
                           on Aging, Building, IT -- and the two that state an
                           ESTABLISHMENT instead, the DPW and the Assessing office

STATUS IS NOT DECORATION. `filled` is a named person. `vacant` is a seat or post the town
itself prints as empty. `post` is an establishment position with no name attached, which
is the DPW's and the Assessing office's whole form -- and the distinction between a post
and a person is the one this project got wrong until 22 September.
"""
import argparse
import collections
import csv
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
DATA = os.path.join(ROOT, 'sources', 'data')
OUT_CSV = os.path.join(DATA, 'org-chart.csv')
OUT_JSON = os.path.join(ROOT, 'fy28', 'public', 'data', 'org-charts.json')
FIELDS = ['fy', 'unit', 'unit_kind', 'subunit', 'section', 'section_group', 'tier',
          'role', 'person', 'status', 'source']

# ---------------------------------------------------------------------------
# THE GRADE AND THE DEPARTMENT. TJ, 22 September 2026: *"so for the school, dont we hav
# grade and department info?! ... we should group by those."*
#
# We do: 3,460 of 3,847 school rows carry the block heading the roster was printed under.
# What stopped it being a grouping is that there are 203 distinct values and most of them
# are the same dozen things -- `Cafeteria`, `Cafeteria:`, `Cafeteria Services` and
# `Cafeteria Manager`; `Grade 4`, `4th Grade:` and `Fourth Grade Teachers`; `Special
# Education`, `SPECIAL EDUCATION` and `Special Ed. Middle School:`.
#
# `section` KEEPS WHAT THE PAGE SAYS and `section_group` is the normalisation, in a
# column of its own. Rule 13: the printed heading is the observation and the grouping is
# ours, so they do not get to be the same field.
#
# WHAT IS MERGED IS TYPOGRAPHY, NOT MEANING. Case, trailing punctuation, an ordinal
# spelled out, and the building name repeated inside a heading that already sits under
# that building. The families below are collapsed as well, and each is a department that
# every school prints under two or three names across fifteen years. `Specialists`,
# `Unified Arts` and `Special Areas` are NOT merged into each other: they plausibly name
# the same staff and nothing in the reports says so.
ORDINAL = {'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5, 'sixth': 6,
           'seventh': 7, 'eighth': 8, 'ninth': 9, 'tenth': 10, 'eleventh': 11,
           'twelfth': 12}
GRADE = re.compile(r'^(?:grade\s*(\d{1,2})\b|(\d{1,2})(?:st|nd|rd|th)\s+grade\b'
                   r'|(%s)\s+grade\b)' % '|'.join(ORDINAL), re.I)
# A heading that repeats the building it is already sitting under.
BUILDING_TAIL = re.compile(r'\s*[:,\-]?\s*(?:at\s+)?(?:the\s+)?'
                           r'(?:lunenburg\s+)?(?:middle|high|primary|elementary)'
                           r'\s+school\s*$', re.I)
SECTION_FAMILY = [
    (re.compile(r'cafeteria|food service|cook', re.I), 'Cafeteria and food service'),
    # THE TOWN'S TWO NAMES FOR ONE FUNCTION. A school prints `Custodians` and
    # `Facilities & Grounds` in the same roster with the same job titles under both.
    (re.compile(r'custod|facilities|grounds|maintenance', re.I),
     'Custodial and facilities'),
    (re.compile(r'athletic', re.I), 'Athletics'),
    (re.compile(r'parapro', re.I), 'Paraprofessionals'),
    (re.compile(r'special ed|\bsped\b|learning c(?:en)?t', re.I), 'Special education'),
    (re.compile(r'special services', re.I), 'Special services'),
    (re.compile(r'guidance|adjustment counsel', re.I), 'Guidance'),
    (re.compile(r'health office|^health$|nurse', re.I), 'Health office'),
    (re.compile(r'^achieve', re.I), 'Achieve'),
    (re.compile(r'central office', re.I), 'Central office'),
    (re.compile(r'administration|main office', re.I), 'Administration and office'),
    (re.compile(r'technology|network', re.I), 'Technology'),
    (re.compile(r'tutor', re.I), 'Tutors and aides'),
]


def canon_section(text):
    """The block heading, normalised into something a page can group on."""
    # `Career Firefighters+`, `Department+*` -- the roster's own footnote markers, which
    # made one service look like two.
    t = re.sub(r'[+*\u2020\u2021]+\s*$', '',
               re.sub(r'\s+', ' ', (text or '')).strip()).strip(':_.,;- ')
    if not t:
        return ''
    t = BUILDING_TAIL.sub('', t).strip(':_.,;- ') or t
    # `Ith Grade:` is the scanner's `7th Grade:` -- an I for a 7 -- and it published a
    # grade that does not exist beside the one it belongs to.
    t = re.sub(r'^[Il]th\s+Grade', '7th Grade', t)
    m = GRADE.match(t)
    if m:
        n = m.group(1) or m.group(2) or ORDINAL[m.group(3).lower()]
        return 'Grade %d' % int(n)
    if re.match(r'^(pre[- ]?school|preschool|pre[- ]?k)', t, re.I):
        return 'Pre-school'
    if re.match(r'^kindergarten', t, re.I):
        return 'Kindergarten'
    for pat, name in SECTION_FAMILY:
        if pat.search(t):
            return name
    return t[:1].upper() + t[1:]

# ---------------------------------------------------------------------------
# THE LADDER. A flat list of forty names is not an org chart, and the town prints the
# hierarchy on every roster it publishes: Chief, Deputy Chief, Captain, Lieutenant,
# Sergeant, Officer. TJ, 22 September 2026: *"i think the org chart needs some hierarchy.
# flat lists are hard to read, and i know there's hierarchy in here. ESP for the schools.
# but other depts have chiefs, captains, etc so it exists there too."*
#
# RULE 7 APPLIES TO THIS TABLE. The RANK is a fact -- the town printed it beside the name.
# The ORDER of the ranks is our reading of them, and two of these are genuinely arguable:
# a Business Manager and a Director of Facilities do not report to a Principal, and a
# board Chair is first among equals rather than anybody's superior. So the page calls
# these BANDS and not a reporting line, because nothing published says who reports to
# whom.
#
# ORDER MATTERS AND IS THE WHOLE TRICK: `Deputy Chief` must be tested before `Chief` and
# `Assistant Principal` before `Principal`, or every deputy in the town becomes a head.
# `INTERIM` IS NOT A DEMOTION. `Interim Chief Jeffrey Thibodeau` ran the Police
# Department for the back half of FY2024 and the first draft filed him one band below
# himself, because the word sat in the deputy list beside `acting` and `assistant`.
TIERS = [
    # AN ADMINISTRATIVE ASSISTANT IS NOT A DEPUTY CHIEF. `Part-Time Admin Assistant`
    # and `Police Executive Assistant` were ranked above the Lieutenant and every
    # Sergeant, because the word `assistant` is in both a deputy's title and a
    # secretary's. A deputy is an assistant TO A POST, never to an office.
    (3, re.compile(r'\b(?:admin(?:istrative)?|executive|office|clerical|staff)\s+'
                   r'assistant\b|\bassistant\s+to\b', re.I)),
    (1, re.compile(r'\bdeputy|\bassistant\b|\basst\.?\b|\bvice[- ]?chair|\bcapt\.?\b'
                   r'|\bcaptain\b', re.I)),
    # A PRINCIPAL CLERK IS NOT A PRINCIPAL. The word heads a school and, in the DPW and
    # the Assessing office, grades a clerk -- and matching it bare put the DPW's
    # principal clerk above the director who runs the department.
    (0, re.compile(r'\bsuperintendent\b|\btown manager\b|\bchief\b'
                   r'|\bprincipal\b(?!\s+clerk)'
                   r'|\bdirector\b|\bchair(?:man|person|woman)?\b|\blibrarian\b'
                   r'|\btown clerk\b|\btreasurer\b|\bcommissioner\b'
                   r'|\btax collector\b|^collector\b'
                   r'|\btown administrator\b|\bbusiness administrator\b', re.I)),
    (2, re.compile(r'\blieutenant\b|\blt\.?\b|\bsergeant\b|\bsgt\.?\b'
                   r'|\bdepartment head\b|\bdept\.? head\b|\bsupervisor\b'
                   r'|\bmanager\b|\bcoordinator\b|\bforeman\b|\bhead\b'
                   r'|\bclerk\b|\bsecretary\b|\badministrator\b'
                   r'|\bdetective\b|\bdet\.', re.I)),
]
TIER_SUPERVISOR = 2
TIER_STAFF = 3
# A FIFTH BAND, BELOW THE MEMBERS. The Planning Board and the Zoning Board of Appeals
# both seat ASSOCIATE members, and several boards seat somebody ex officio, honorary or
# expressly non-voting. The listing says so on the seat, and an associate member filed
# beside a full one loses the only distinction the town draws between them. The first
# draft had `associate` in the DEPUTY band, which put them above the members instead.
TIER_ASSOCIATE = 4
# ONE PERSON RUNS A BODY, AND THE REST OF THE TOP BAND REPORTS TO THEM. The School
# Central Office publishes a Superintendent beside a Director of Facilities, a Director
# of Special Services, a Food Service Director and a Business Manager, and all five read
# as heads -- nine of them in FY2017. A Director IS the head of the Library, of IT and of
# the Council on Aging, so the post cannot be demoted by name. It is demoted by CONTEXT:
# where a body already has a Superintendent, a Chief, a Town Manager, a Principal or a
# Chair, everyone else in the top band is a rank below.
# A HIGHWAY SUPERINTENDENT IS NOT THE SUPERINTENDENT. The DPW prints a Cemetery
# Superintendent and a Highway Superintendent under a Director, and reading the word
# alone put both of them above the man who runs the department.
STRONG_HEAD = re.compile(r'^(?:superintendent\b(?!\s+of\s+(?:cemeter|highway|street|water))'
                         r'|superintendent[- ]director)'
                         r'|\btown manager\b|\bchief\b|\bprincipal\b(?!\s+clerk)'
                         r'|\bchair(?:man|person|woman)?\b|\btown clerk\b'
                         r'|\bsuperintendent of schools\b', re.I)
# A DESIGNEE IS A FULL MEMBER. The School Committee and the Town Moderator each SEND
# somebody to the Charter Review Committee, and that person votes like anybody else --
# `designee` names who sent them, not a lesser seat.
ASSOCIATE = re.compile(r'\bassoc(?:iate)?\b|\bhonorary\b|\bnon-?voting\b|\bex[- ]officio\b'
                       r'|\balternate\b', re.I)


# A COMMITTEE OF DELEGATES HAS NO INTERNAL RANK. The Storm Water Task Force, the
# Taxation Aid Committee and the Building Design Committee are made of people sent by
# other bodies, and their printed title names the body they come FROM -- `Council on
# Aging Director`, `Assessors' Principal Clerk`, `Planning Board Representative`. Read as
# ranks they made a Principal Clerk the head of a committee and a Director its deputy.
DELEGATE = re.compile(r'\brepresentative\b|\bdesignee\b|\bliaison\b|\bmember at large\b'
                      r'|\bcitizen at large\b|\bex[- ]officio\b', re.I)


# A BOARD'S HIERARCHY IS CHAIR, VICE-CHAIR, CLERK. NOTHING ELSE.
#
# This is the rule that had to be written per TYPE of body rather than per word. A board
# member who is a Director somewhere else is not the board's deputy, and the Taxation Aid
# Committee proved it three ways at once: it seats the Assessors' Principal Clerk, the
# Council on Aging Director and the Assistant Town Manager, and reading their titles as
# ranks made a principal clerk the head of the committee and two directors its deputies.
# Their titles say which body SENT them; the committee's own officers are the ones it
# elects, and a body that elects none is a body of equals.
BOARD_RANKS = [
    (0, re.compile(r'\bchair(?:man|person|woman)?\b', re.I)),
    (1, re.compile(r'\bvice[- ]?chair', re.I)),
    # THE BOARD'S OWN CLERK, not somebody who is a clerk for a living. `Assessors'
    # Principal Clerk` is a job in the Assessing office and its holder sits on the
    # Taxation Aid Committee as an ordinary member.
    (2, re.compile(r'^(?:board\s+)?(?:clerk|secretary|treasurer)$'
                   r'|\b(?:clerk|secretary|treasurer)\s+of\s+the\b', re.I)),
    (4, ASSOCIATE),
]


def board_tier(role):
    """Where a seat sits on a board. Officers only; everybody else is a member."""
    t = (role or '').strip()
    for band, pat in ((1, BOARD_RANKS[1][1]), (0, BOARD_RANKS[0][1]),
                      (2, BOARD_RANKS[2][1]), (4, BOARD_RANKS[3][1])):
        if pat.search(t):
            return band
    return TIER_STAFF


# AN APPOINTED POST RANKS BY THE POST, NOT BY THE WORD `ASSISTANT`. Folding the posts
# into their departments put `Assistant Dam Keeper` in the deputy band and the Dam Keeper
# himself among the staff, because `assistant` is tested before anything else. The
# Inspector of Wiring is not the Building Commissioner's deputy and his assistant is not
# above him: the post sits with the supervisors and the assistant to it sits below.
APPOINTED_POST = re.compile(r'\binspector\b|\bkeeper\b|\bwarden\b|\bclockwinder\b|'
                            r'\bfield driver\b|\bcensus liaison\b|\btax custodian\b',
                            re.I)
ASSISTANT_TO = re.compile(r'\bassistant\b|\basst\.?\b|\bdeputy\b|\balternate\b', re.I)


def tier_of(role, kind):
    """Which band a printed role sits in. 0 head, 1 deputy, 2 supervisor, 3 everyone else.

    A BOARD SEAT IS NOT THE BOTTOM OF ANYTHING, but it has to sort somewhere, and putting
    members below the chair is the way every set of minutes in this town reads.
    """
    t = (role or '').strip()
    if not t:
        return TIER_STAFF
    # ...UNLESS THE SAME TITLE ALSO NAMES A HEAD. `Director & Tree Warden` is the man
    # who runs the DPW and happens to hold the Tree Warden appointment; matching the
    # appointment first put him two bands below his own principal clerk.
    # BY BAND, NOT BY POSITION IN THE LIST. `TIERS` is ordered so that `Deputy Chief`
    # is tested before `Chief`, which means the band-0 pattern is not TIERS[0] and
    # indexing by position picked up the deputy pattern instead.
    head_words = next(pat for band, pat in TIERS if band == 0)
    if APPOINTED_POST.search(t) and not head_words.search(t):
        return TIER_STAFF if ASSISTANT_TO.search(t) else TIER_SUPERVISOR
    if ASSOCIATE.search(t) and not DELEGATE.search(t):
        return TIER_ASSOCIATE
    if DELEGATE.search(t):
        return TIER_STAFF
    for band, pat in TIERS:
        if pat.search(t):
            return band
    return TIER_STAFF

# THE PROFILE PAGE IS NOT A BOARD. `TOTAL AREA- 26.63 MILES` and `Follow us on Facebook`
# come off the town's own statistics page, which sits inside the front matter the
# officials listing is read from.
JUNK = re.compile(r'https?://|facebook|instagram|follow us|@|^\W*$'
                  r'|\bMILES\b|\bTOTAL AREA\b|^\d+[\d,.]*$', re.I)
VACANT = re.compile(r'^\(?\s*(vacan\w*|open|unfilled|tbd)\s*\)?$', re.I)

# A LINE OF THE LISTING THAT IS NOT A POST. Found by building the chart and reading the
# unit list, which is the point of building it: `Terms Are For One Year Unless Otherwise
# Indicated.` is the listing's own footnote, and `Associate Members` is a SUB-HEADING
# inside a board -- the Planning Board and the Zoning Board of Appeals both print one --
# so promoting it to a unit invents a body the town does not have.
NOT_A_POST = re.compile(r'^terms are for|^associate members|^\W|^\d|^(lull|4vlv|got advisors)$'
                        r'|^senior citizen property tax work-off program', re.I)

# ONE POST, SEVERAL SPELLINGS. Every pair here was found by normalising the unit names and
# looking at what collided; each is the town's own typography or the scanner's, not a
# distinction the town draws.
ALIAS = {
    'town clock winders': 'Town Clockwinders',
    'town hall clockwinders': 'Town Clockwinders',
    'clock winders': 'Town Clockwinders',
    'fire chief/ emergency managementdirector/ forest warden':
        'Fire Chief / Emergency Management Director / Forest Warden',
    'fire chief/emergency managementdirector/forest warden':
        'Fire Chief / Emergency Management Director / Forest Warden',
    'fire chief/ emergency management director/ forest warden':
        'Fire Chief / Emergency Management Director / Forest Warden',
    'mericans with disabilities committee - - 3 yea':
        'Americans with Disabilities Committee',
    'mericans with disabilities committee': 'Americans with Disabilities Committee',
    # ONE BODY UNDER TWO SPELLINGS, OR TWO NAMES FOR THE SAME SEAT. Every pair was found
    # by reading the dropdown, which is what the dropdown is for.
    'park commission': 'Parks Commission',
    'sewer commission - 1/2': 'Sewer Commission',
    'architectural preservation district commission (apdc)':
        'Architectural Preservation District Commission',
    'bulding commissioner/zoning enforcement officer':
        'Building Commissioner/Zoning Enforcement Officer',
    'ocal census liaison': 'Local Census Liaison',
    'inspector of plumbing & gas fittings': 'Inspector Of Plumbing/Gas',
    'asst. inspector of plumbing & gas fittings': 'Asst. Inspector Of Plumbing/Gas',
    'election officers': 'Election Workers',
    'veterans services agent': "Veterans' Services",
    'interim veterans services agent': "Veterans' Services",
    'tax custodian': 'Tax Collector/Treasurer/Tax Custodian',
    'technology department': 'Information Technology',
    'gctf advisors': 'Green Community Task Force Advisors',
    'got advisors': 'Green Community Task Force Advisors',
    'open space committee (ad hoc)': 'Ad Hoc Open Space Advisory Committee',
    'lunenburg municipal building design committee (eff. 9/26/23)':
        'Lunenburg Municipal Building Design Committee',
    'montachusett regional vocational technical school committee':
        'Montachusett Regional Vocational Technical School Representative',
    'interim town manager': 'Town Manager',
    'interim veterans services agent': 'Veterans Services Agent',
    'veterans services agent': "Veterans' Services",
    'lunenburg municipal building design committee (eff. 9/26/23)':
        'Lunenburg Municipal Building Design Committee',
    # THE TOWN RENAMED ITS SELECTMEN. `Board of Selectmen` became `Select Board` at the
    # 2019 annual town meeting; it is one body and a reader looking for its history
    # should not have to know the date of the vote.
    'board of selectmen': 'Select Board',
    'board of selectmen representative': 'Select Board',
}
# The scanner's `Select Board`.
SEAT_FIX = {'slain board': 'Select Board', 'board of s': 'Select Board',
            'select boara kepresentative': 'Select Board Representative'}

# A SEAT ON A BOARD IS NOT A BODY OF ITS OWN. The listing prints `ZBA Associates` and
# `Associate Members` as sub-headings inside a board, and they arrived as separate units
# with their own dropdown entries -- so the Zoning Board of Appeals was published in two
# pieces, its full members in one and its associates in another.
FOLD_INTO = {
    'zba associates': ('Zoning Board Of Appeals', 'Associate Member'),
    'zba associate member': ('Zoning Board Of Appeals', 'Associate Member'),
}
# THE HEAD OF A DEPARTMENT BELONGS IN THE DEPARTMENT. The officials listing appoints the
# Police Chief, the DPW Director, the Fire Chief and the Council on Aging Director as
# POSTS, so each arrived as its own unit -- and the dropdown offered `Police Chief` and
# `Police Department` as two bodies while the department's own chart had the chief in it
# anyway. The appointment is real and worth keeping; it is a row in the department, not a
# department of one. The post's own name stays as the role, because
# `Fire Chief / Emergency Management Director / Forest Warden` is three jobs the town
# gives one person and no roster prints it that way.
HEAD_POST = {
    'police chief': ('Police Department', 'department', 'Police Chief'),
    'dpw director': ('Department of Public Works', 'department', 'DPW Director'),
    'council on aging director': ('Council on Aging', 'department',
                                  'Council on Aging Director'),
    'fire chief / emergency management director / forest warden':
        ('Fire Department', 'department',
         'Fire Chief / Emergency Management Director / Forest Warden'),
    'building commissioner': ('Building Department', 'department',
                              'Building Commissioner'),
    'building commissioner/zoning enforcement officer':
        ('Building Department', 'department',
         'Building Commissioner / Zoning Enforcement Officer'),
    'bulding commissioner/zoning enforcement officer':
        ('Building Department', 'department',
         'Building Commissioner / Zoning Enforcement Officer'),
    # THE POST AND THE OFFICE ARE ONE BODY. The listing appoints a Town Clerk and the
    # department is called Town Clerk, so the two arrived as `Town Clerk (appointed
    # post)` beside `Town Clerk (staff)` -- one of them holding the clerk and the other
    # her own office.
    'town clerk': ('Town Clerk', 'department', 'Town Clerk'),
    'town manager': ('Town Manager', 'department', 'Town Manager'),
    'tax collector/treasurer/tax custodian':
        ('Tax Collector/Treasurer/Tax Custodian', 'department',
         'Tax Collector / Treasurer / Tax Custodian'),
    "veterans' services": ("Veterans' Services", 'department', 'Veterans’ Services Agent'),
    'veterans services agent': ("Veterans' Services", 'department',
                                'Veterans’ Services Agent'),
}

# AN APPOINTED POST IS A JOB IN A DEPARTMENT, NOT A DEPARTMENT OF ONE. TJ: *"'appointed
# post' makes no sense. They must go into departments."*
#
# The officials listing appoints the Inspector of Wiring, the Dam Keeper, the Animal
# Control Officer and forty-three others, and each arrived in the dropdown as its own
# body — so a resident looking for the building inspectors had to know to look under
# `Asst. Inspector Of Wiring` rather than under Building. They are posts the town APPOINTS
# into a department, and the department is where a reader looks for them. The post keeps
# its own name as the role, because that is what the town appoints somebody to.
POST_IN = {
    'inspector of wiring': 'Building Department',
    'asst. inspector of wiring': 'Building Department',
    'assistant inspector of wiring': 'Building Department',
    'inspector of plumbing/gas': 'Building Department',
    'asst. inspector of plumbing/gas': 'Building Department',
    'local building inspector': 'Building Department',
    'assistant building inspector': 'Building Department',
    'building inspector (alternate)': 'Building Department',
    'inspector of weights & measures': 'Building Department',
    'inspector of animals': 'Building Department',
    'animal control officer': 'Police Department',
    'field driver': 'Police Department',
    'pound keeper': 'Police Department',
    'dam keeper': 'Department of Public Works',
    'assistant dam keeper': 'Department of Public Works',
    'tree warden': 'Department of Public Works',
    'hazardous waste coordinator': 'Department of Public Works',
    'assistant town clerk': 'Town Clerk',
    'local census liaison': 'Town Clerk',
    'assistant tax collector/treasurer': 'Tax Collector/Treasurer/Tax Custodian',
    'tax custodian': 'Tax Collector/Treasurer/Tax Custodian',
    # THE HEARINGS OFFICER IS THE TOWN MANAGER. Kerry A. Lafleur, Heather Lemieux and
    # Jennifer Warren-Dyment hold the post across ten years and all three are the Town
    # Manager of their year -- it is a function of the office, not a body of its own.
    'hearings officer': 'Town Manager',
    # THE TOWN'S OWN NAME FOR IT, off its staff directory: Facilities, Grounds and
    # Recreation are ONE department, and it is the one Chris Ruth directs. We had it as
    # `Parks and Recreation` holding a single Recreation Director, which is a third of
    # the department under a name the town does not use.
    'recreation director': 'Facilities, Grounds & Recreation',
    # TJ: *"Town Counsel can go into Town Manager group."* The firm is retained by the
    # town and works to the Town Manager; it is not a body and it is not five people.
    'town counsel': 'Town Manager',
    # TJ: *"same as Constable."* Appointed by the town and working to the manager's
    # office; the listing prints the post as elected in some years and appointed in
    # others, which is why it never settled anywhere on its own.
    'constable': 'Town Manager',
}

# THE FIVE THAT BELONG TO NOBODY GO IN ONE PLACE. TJ: *"lets not list all the appointed
# ones as individuals then. Group them all together into one Group."*
#
# A Constable, a Town Clockwinder, the Moderator, Town Counsel and a Wellness Coordinator
# are five separate lines in a dropdown of sixty-five bodies, and none of them is a body:
# they are posts the town fills that sit in no department. The annual report heads six
# pages `APPOINTED OFFICIALS` and names no appointing authority on any of them, and the
# charter that would say which belong to the Select Board and which to the Town Manager
# is not in this archive -- so grouping them under a department would be inventing a
# reporting line the town has not published. They go together, under what they actually
# have in common, with each post as its own block inside.
NO_DEPARTMENT = 'Officers in no department'
LOOSE_POST = {'moderator', 'town clockwinders', 'wellness coordinator',
              'town clock winders'}

# AND A COMMITTEE IS A COMMITTEE, whichever part of the listing printed it. The Charter
# Review Committee, the Building Reuse Committee, the MART Advisory Board and the three
# Montachusett bodies were all typed `appointed post` because of where they sat on the
# page, and were then ranked as though somebody ran them.
IS_A_COMMITTEE = re.compile(r'\b(committee|task force|advisors?|advisory|commission|'
                            r'organization|board)\b', re.I)

# A PERSON IS NOT A BODY, and neither is a listing sub-heading.
# A ROUTING TABLE IS NOT A BODY. `Public Records Access Officers` lists which officer
# handles which KIND OF REQUEST -- `General Requests: Jennifer Warren-Dyment`, `Fire
# Dept.: Karen Weller, Admin. Asst.` -- so half its rows have the subject where the name
# goes. It is a real and useful table and it is not an org unit.
NOT_A_UNIT = re.compile(r'^(ex officio members|john palumbo|'
                        r'public records access officers)', re.I)
# A FRAGMENT OF THE LISTING IS NOT A PERSON. `Serving until next annual`, `ssociate
# Members-(2) 2 year`, `elect Board Representative-R` -- a sub-heading or a footnote the
# column reader took for a name, with the first letter eaten by the bullet before it.
NOT_A_MEMBER = re.compile(r'^(serving|term|vacan|assoc|ssociate|elect board|'
                          r'members?\b|clerks?:|wardens?:|inspectors?:|'
                          r'deputy warden|general requests|community policing|'
                          r'open space committee|ritter memorial|\W|\d)'
                          r'|denotes|until next|\bmembers\s*[-\u2014(]', re.I)


# THE MEMBERSHIP IS NOT PART OF THE NAME. The listing prints `COUNCIL ON AGING- - (11
# MEMBERS)` in some years and `COUNCIL ON AGING` in others, so the same board arrived as
# two bodies with 78 and 35 rows. The stated size is already read into `stated_members`
# by extract_personnel.py; carrying it in the title as well splits the board in half.
SIZE_SUFFIX = re.compile(r'\s*[-—,]*\s*\(?\s*(?:no less than\s*)?\d+\s*'
                         r'(?:members?|member|yrs?|years?)[^)]*\)?\s*$', re.I)


# A COMMITTEE DOES NOT CHANGE INTO A DIFFERENT COMMITTEE BECAUSE THE LISTING PRINTED ITS
# EFFECTIVE DATE. `Lunenburg Municipal Building Design Committee (Eff. 9/26/23)`.
EFFECTIVE_SUFFIX = re.compile(r'\s*\((?:eff\.?|effective|as of)[^)]*\)?\s*$', re.I)


def canon_unit(name, kind):
    """One name per body. Case is not a distinction; `kind` is.

    `Council on Aging` the department and `Council On Aging` the board are two real
    things -- paid staff and an appointed volunteer board -- and they must not be told
    apart by a capital O. The kind carries the difference and the name is normalised.
    """
    name = EFFECTIVE_SUFFIX.sub(
        '', SIZE_SUFFIX.sub('', re.sub(r'\s+', ' ', name).strip())).strip(' -—,')
    key = name.lower()
    if key in ALIAS:
        return ALIAS[key]
    return name


# WHAT IS PRINTED ON A BOARD SEAT, and was going into the org chart as part of the
# person's name. TJ: *"make sure you apply this thinking to EVERY dropdown
# department/comission. if there are natural groupings and hierarchy use those."*
#
# Every board looked flat, and none of them is. 400 of 2,118 listing rows carry a seat
# role after a hyphen -- `Carolyn Rossi-Member at Large`, `John Rabbitt- Conservation
# Commission Representative`, `Julie Belliveau- Town Employee, Non-voting Member` -- and
# the listing marks its chairs with asterisks and says so in its own footnote:
# `** denotes chairperson`.
#
# THE SUFFIX IS NOT ALWAYS A ROLE, WHICH IS WHY THIS IS A WHITELIST. `Michael-Ray
# Jeffreys`, `Joanna Bilotta-Simeone` and `State Appointee-Karin Menard` all have a
# hyphen with a capitalised word after it, and two of those are surnames. A suffix
# becomes a seat only when it contains a word that names a seat or a body; otherwise the
# name is left exactly as printed. Nobody is dropped either way.
SEAT_WORD = re.compile(
    r'\b(member|members|large|represent\w*|rep|designee|assoc\w*|honorary|voting|'
    r'officio|chair\w*|clerk|secretary|director|supervisor|coordinator|appointee|'
    r'commissioner|selectman|selectmen|employee|operator|alternate|liaison|'
    r'board|committee|commission|authority|council|department|dpw|trustee)\b', re.I)
SEAT_SPLIT = re.compile(r'\s*[-\u2013\u2014]\s*(?=[A-Za-z(])')
CHAIR_MARK = re.compile(r'\s*\*+\s*')
TERM_TAIL = re.compile(r'\s*[-\u2013\u2014,]?\s*(?:19|20)\d\d\s*$')
NOTE_TAIL = re.compile(r'\s*[-\u2013\u2014(]?\s*((?:resign|retir|deceas|appoint|term|'
                       r'elect)\w*[^)]*)\)?\s*$', re.I)


def _seat(raw):
    """(name, seat role, note) off one printed listing entry. Additive: never a drop."""
    t = re.sub(r'\s+', ' ', raw or '').strip()
    chair = '*' in t
    t = CHAIR_MARK.sub(' ', t).strip(' ,')
    note = ''
    m = NOTE_TAIL.search(t)
    if m and not NAME_SHAPE.match(t):
        note, t = m.group(1).strip(' ).'), NOTE_TAIL.sub('', t).strip(' ,(')
    t = TERM_TAIL.sub('', t).strip(' ,')
    seat = ''
    # SPLIT AT THE HYPHEN THAT LEAVES A NAME, not at the first one. `Michael-Ray
    # Jeffreys- Select Board` has two, and taking the first made the member `Michael`
    # and his seat `Ray Jeffreys-Select Board`.
    cuts = [m.start() for m in SEAT_SPLIT.finditer(t)]
    # THE SEPARATOR IS SOMETIMES A COMMA. `Damon McQuaid, Planning Board` and `Mark
    # Erickson, Finance Committee` -- the Building Reuse Committee prints its seats that
    # way, and the whole string was going in as the person's name.
    cuts += [m.start() for m in re.finditer(r',\s+(?=[A-Z])', t)]
    cuts.sort()
    best = None
    for i in cuts:
        left, right = t[:i].strip(), SEAT_SPLIT.sub('', t[i:], count=1).strip(' .,')
        if SEAT_WORD.search(right) and (NAME_SHAPE.match(left) or best is None):
            best = (left, right)
            if NAME_SHAPE.match(left):
                break
    if best:
        t, seat = best
    elif cuts:
        left, right = t[:cuts[0]].strip(' .,'), SEAT_SPLIT.sub('', t[cuts[0]:], 1).strip()
        if SEAT_WORD.search(left) and NAME_SHAPE.match(right):
            # `State Appointee-Karin Menard` -- the seat is printed FIRST.
            seat, t = left, right
    seat = SEAT_FIX.get(seat.lower(), seat)
    if chair and not re.search(r'chair', seat, re.I):
        seat = ('Chairperson' if not seat else '%s, chairperson' % seat)
    return t.strip(), seat, note


def _rows_officials():
    p = os.path.join(DATA, 'town-personnel.csv')
    out, bad = [], 0
    if not os.path.exists(p):
        return out, bad
    for r in csv.DictReader(open(p, encoding='utf-8')):
        post, who = (r['post'] or '').strip(), (r['person'] or '').strip()
        if JUNK.search(post) or JUNK.search(who) or NOT_A_POST.match(post):
            bad += 1
            continue
        kind = ('board' if 'board seat' in r['kind'] else 'officer')
        name, seat, note = _seat(who)
        # `Steve Archambault-202 /`, `Michelle Durkee.` -- the term year half-scanned off
        # the end of a name, and a full stop the listing puts after it.
        name = re.sub(r'[\s,/\\-]*\d[\d/ .-]*$', '', name).strip(' .,/-')
        # `Mike Mackin-until next annual`, `elect Board Representative-R` -- a note or a
        # sub-heading the seat reader could not split off because it is not a seat.
        name = re.sub(r'\s*[-\u2013\u2014]\s*(?:until|serving|term|elect)\b.*$', '',
                      name, flags=re.I).strip(' .,/-')
        # TESTED AGAINST WHAT WILL BE PUBLISHED. Where the seat reader finds no name it
        # falls back to the printed string, so checking only `name` let the fragments
        # straight through under the fallback.
        if NOT_A_MEMBER.match(name or who):
            bad += 1
            continue
        # ELECTED OR APPOINTED is the listing's own division and it is on every row.
        band = (r['section'] or '').strip().title()
        if who:
            out.append(dict(fy=r['fy'], unit=canon_unit(post.title(), kind),
                            unit_kind=kind, subunit='', section=band,
                            role=seat or r['kind'],
                            # A NAME THAT WILL NOT PARSE KEEPS ITS PRINTED FORM. The
                            # seat reader is additive: if it cannot find a role it
                            # changes nothing, and nobody falls out of the chart for
                            # failing to match a pattern.
                            person=name or who,
                            status='vacant' if VACANT.match(name or who) else 'filled',
                            source='officials listing p%s%s'
                                   % (r['page'], ' (%s)' % note if note else '')))
        for _ in range(int(r['vacancies'] or 0)):
            out.append(dict(fy=r['fy'], unit=canon_unit(post.title(), kind),
                            unit_kind=kind, subunit='', section=band,
                            role=r['kind'], person='', status='vacant',
                            source='officials listing p%s' % r['page']))
    return out, bad


# THE RANK IS IN THE NAME, in the years the Police roster prints it that way. 114 of 291
# Police rows carry an empty `rank` and a name reading `Off. Jeffrey Hill`, so every
# officer in those years arrived unranked, fell into the bottom band, and the only
# grouping left was the printed shift. TJ, seeing the FY2024 chart: *"you put the police
# chief under admins... group by RANK or department or SOMETHING, there are very natural
# groupings to all these departments."* The department prints BOTH a rank and a bureau or
# shift; this recovers the first so the second can be what it is.
EMBEDDED_RANK = re.compile(
    r'^(Desk Officer|Reserve Officer|Part-Time Clerk|Animal Control Officer|'
    r'K-?9 Officer|Deputy Chief|Off\.|Ofc\.|Officer|Det\.|Detective|Sgt\.|Sergeant|'
    r'Lt\.|Lieutenant|Chief|Capt\.|Captain|Patrolman|Clerk)\s+(?=[A-Z])', re.I)

# SEVERAL OFFICERS IN ONE ROW. Before FY2020 the Police roster is set as a paragraph, so
# the column reader hands back `Charles Deming Jr., Officer Patrick Barney, Officer Robert
# Diconza, Officer Sean Zrate,` as ONE name. Four officers. The first version of this
# rejected the row for not being name-shaped and lost all four -- which is the failure TJ
# named before it was found: *"make sure if the data is 'bad' we dont lose people because
# they dont match the hierarchy."*
# The comma is not always there -- `Bob Diconza Officer Ben Campbell` is two people and
# one space.
SPLIT_MULTI = re.compile(r',?\s+(?=(?:Off\.|Ofc\.|Officer|Det\.|Detective|Sgt\.|Sergeant|'
                         r'Lt\.|Lieutenant|FF|Firefighter)\s+[A-Z][a-z])')
# A RANK LEFT BEHIND BY A LINE BREAK. The roster runs on, so a name ends `Jonathan Broc,
# Officer` with the next officer's name on the following line.
TRAILING_RANK = re.compile(r',?\s+(?:Off|Ofc|Officer|Det|Detective|Sgt|Sergeant|Lt|'
                           r'Lieutenant|FF|Firefighter)\.?\s*$', re.I)
# `J.Gregory Massak` -- the scanner drops the space after an initial.
TIGHT_INITIAL = re.compile(r'\b([A-Z])\.(?=[A-Z][a-z])')
# `(K9-Jerry)`, `(Full Time Officer)`, `(Reserve Officer)`, `(FY21)` -- a note about the
# post, printed after the name. Not part of it, and not a reason to throw the name away.
PAREN_NOTE = re.compile(r'\s*\(([^)]*)\)\s*$')

# A NAME, ALLOWING INITIALS. The first version required a word of two or more letters
# first, so `J. Gregory Massak` -- a Fire lieutenant in five separate years -- failed the
# test and was dropped five times.
NAME_SHAPE = re.compile(r"^[A-Z](?:[A-Za-z'\-]+)?\.?(?:\s*[A-Z]\.)*"
                        r"(?:\s+(?:[A-Z]\.|[A-Z][A-Za-z'\-]+\.?)){1,3}"
                        r"(?:,?\s+(?:Jr|Sr|II|III)\.?)?$")
# A SENTENCE ABOUT SOMEBODY IS NOT A ROSTER ENTRY. `Alphone J. Baron was hired by the
# Lunenburg Police Department as a full time officer on October 18, 1971. He retired`.
PROSE = re.compile(r'\b(?:retired|resigned|graduated|began|started|served|obtained|'
                   r'elevated|hired|wish|would|was|were|has|have|will|from|with|the)\b')
# A HEADING OVER THE NAMES BENEATH IT: `Patrol Officers`, `Reserve Intermittent Officers`,
# `Traffic Bureau`, `Newly Appointed`. The first version dropped these too. They are not
# people and they are not noise -- they are the department's OWN grouping, so they become
# the section the names under them belong to.
ROSTER_HEADING = re.compile(r'\b(officers|firefighters|bureau|shift|division|newly|'
                            r'arrivals|reserve|patrol|administration|call|career|'
                            r'intermittent|animal control|supervisors|community policing|traffic|school resource)\b', re.I)


def _roster_name(raw):
    """(kind, name, note) for one printed roster entry. Never silently a nobody."""
    note = ''
    raw = TIGHT_INITIAL.sub(r'\1. ', TRAILING_RANK.sub('', raw.strip()))
    m = PAREN_NOTE.search(raw)
    if m:
        note, raw = m.group(1).strip(), PAREN_NOTE.sub('', raw).strip()
    raw = raw.strip(' ,.;')
    if not raw:
        return ('empty', '', note)
    if VACANT.match(raw) or VACANT.match(note):
        return ('vacant', '', note or raw)
    # THE HEADING TEST COMES FIRST. `Patrol Officers` is two capitalised words and
    # passes any name-shape test ever written, so testing for a name first filed the
    # department's own section headings as members of staff -- `Patrol Officers`,
    # `New Arrivals`, `Animal Control`, `Reserve Intermittent O`.
    if ROSTER_HEADING.search(raw) and not PROSE.search(raw) and len(raw.split()) <= 4:
        return ('heading', raw, note)
    if NAME_SHAPE.match(raw):
        return ('person', raw, note)
    return ('prose', raw, note)


def _rows_rosters():
    p = os.path.join(DATA, 'department-rosters.csv')
    out, lost, heading = [], [], {}
    if not os.path.exists(p):
        return out, lost
    for r in csv.DictReader(open(p, encoding='utf-8')):
        rank = (r['rank'] or '').strip()
        key = (r['fy'], r['department'], r['page'])
        for part in SPLIT_MULTI.split((r['name'] or '').strip()):
            role = rank
            m = EMBEDDED_RANK.match(part.strip())
            if m:
                role = rank or m.group(1)
                part = part.strip()[m.end():]
            kind, who, note = _roster_name(part)
            # A ROLE THAT CONTAINS A NAME IS TWO ROWS STUCK TOGETHER. `Sergeant Sean
            # Connery` as a RANK, beside `Patrol Supervisors` as a NAME, is one printed
            # line read across a column boundary.
            # ONLY WHEN A RANK IS ACTUALLY IN FRONT OF A NAME. The first version
            # tested whether the whole ROLE looked like a name, and `Deputy Chief` is
            # two capitalised words -- so Peter J. Hyatt, Deputy Chief of the Fire
            # Department in every year from FY2012, was thrown away fourteen times and
            # the department was published with a Lieutenant as its second officer.
            if kind == 'person' and role and EMBEDDED_RANK.match(role) \
                    and NAME_SHAPE.match(EMBEDDED_RANK.sub('', role).strip()):
                lost.append((r['fy'], r['department'], '%s / %s' % (role, who)))
                continue
            if kind == 'empty':
                continue
            if kind == 'heading':
                # The department's own grouping, kept for the names that follow it.
                heading[key] = who
                continue
            if kind == 'prose':
                lost.append((r['fy'], r['department'], who))
                continue
            out.append(dict(fy=r['fy'], unit=r['department'], unit_kind='department',
                            subunit='',
                            section=(r['section'] or '').strip() or heading.get(key, ''),
                            role=role, person=who,
                            status='vacant' if kind == 'vacant' else 'filled',
                            source='department roster p%s' % r['page']))
    return out, lost


MONTY = 'Montachusett Regional Vocational Technical School'
SCHOOL = {'primary': 'Lunenburg Primary School', 'turkey-hill': 'Turkey Hill Elementary School',
          'middle': 'Lunenburg Middle School', 'high': 'Lunenburg High School',
          'central-office': 'School Central Office', 'passios': 'T.C. Passios Elementary School',
          'monty-tech': 'Montachusett Regional Vocational Technical School'}


def _rows_schools():
    """The district as ONE unit, each school a SUBUNIT inside it.

    TJ: *"the school org chart needs to be the FULL school, with sub-selections for each
    school. i want to see the whole thing in one place."* He is right about the shape:
    Lunenburg Public Schools is one organisation with four buildings, and splitting it
    into four units made the district the only body on this page you could not see whole.
    A principal belongs to a school; a superintendent belongs to none of them.

    Montachusett Regional is NOT folded in. It is a separate district that Lunenburg sends
    students to, and putting its staff inside Lunenburg's chart would be a claim about who
    employs whom.
    """
    p = os.path.join(DATA, 'staff-roster-entries.csv')
    out = []
    if not os.path.exists(p):
        return out
    for r in csv.DictReader(open(p, encoding='utf-8')):
        who = (r['name'] or '').strip()
        school = SCHOOL.get(r['school'], r['school'].title())
        # THE SCHOOL COMMITTEE IS PRINTED INSIDE THE CENTRAL OFFICE BLOCK and is not
        # staff of it. Six years of the district's own chart opened with a
        # `Vice-Chairperson` because the committee that HIRES the superintendent was
        # being read as somebody who works for him. TJ, earlier: *"make sure to show the
        # committees separately than the departments they run."*
        if re.search(r'chair', (r['position'] or r['role_raw'] or ''), re.I) \
                and 'central' in r['school']:
            out.append(dict(fy=r['fy'], unit='School Committee', unit_kind='board',
                            subunit='', section='',
                            role=(r['position'] or r['role_raw'] or '').strip(),
                            person=who, status='filled',
                            source='school roster p%s' % r['page']))
            continue
        # The key is `monty-tech`, not `montachusett` -- checking for the long
        # form silently folded a separate district into Lunenburg's chart.
        regional = re.search(r'monty|montachusett', r['school'], re.I) is not None
        out.append(dict(fy=r['fy'],
                        unit=school if regional else 'Lunenburg Public Schools',
                        unit_kind='school',
                        subunit='' if regional else school,
                        section=(r['grade_or_dept'] or '').strip(),
                        role=(r['position'] or r['role_raw'] or '').strip(),
                        person='' if VACANT.match(who) else who,
                        status='vacant' if VACANT.match(who) else 'filled',
                        source='school roster p%s' % r['page']))
    return out


# THE DISTRICT'S OWN SUBUNIT NAMES, ONTO THE ONES THIS CHART ALREADY DRAWS. The school
# directories name four buildings and an office; the chart has been calling the office
# `School Central Office` since it was read out of the annual reports, and inventing a
# second name for it would split one body in two.
#
# `Lunenburg Middle High School` IS LEFT AS ITS OWN SUBUNIT, deliberately. It is the
# building the middle and high schools share and the district's roll-up uses it as a
# value of its own -- so mapping it to either school would be us deciding which of the two
# a person works for, which is the question, not the answer.
DIRECTORY_SUBUNIT = {
    'district office': 'School Central Office',
    'district': 'School Central Office',
    'district (office at thes)': 'School Central Office',
    'district (office at lmhs)': 'School Central Office',
    'district (office at primary)': 'School Central Office',
}


def _rows_school_directory():
    """The district's people as the schools themselves list them, today.

    WHY THIS IS NOT JUST ANOTHER ROSTER. Every other people-source feeding this chart is
    read out of an annual report, so the district's staff arrive a year or more late and
    only in the shape the report printed. These are the buildings' own contact sheets, and
    they carry a GROUPING the reports do not -- Turkey Hill prints `Grade 4`, `Achieve/TLC`,
    `Custodians` over its people, which is what `section` draws a band from.

    A SHARED PERSON BECOMES TWO ROWS, AND THE SCHEMA WANTS THAT. `org-chart.csv` is keyed
    on (fy, unit, subunit, person), so somebody the high school and the middle school both
    list lands in two subunits by construction -- no merge, no dedup, and `check_org_charts`
    groups by subunit so its DOUBLED test does not fire on the finding. That is the whole
    reason TJ gave the five per-school addresses, and it needed nothing added here to work.

    THE ROLL-UP FILLS IN ONLY WHO THE BUILDINGS LEAVE OUT. It names 45 people no school
    listing does -- Primary omits its own paraprofessionals from the sheet the school
    keeps -- so dropping it would lose them, and using it for everybody would draw
    everyone twice. Neither list is a superset of the other, which is a fact about the
    district's record-keeping and is registered as a gap rather than resolved here.

    AND NOBODY IS RANKED BY IT. A contact sheet publishes no reporting line, so every row
    arrives with its printed title and `tier_of` bands it exactly as it bands a roster --
    a principal to the top because the word `Principal` is in the title, not because this
    source claims to know who reports to whom.
    """
    p = os.path.join(DATA, 'school-staff-directory.csv')
    out = []
    if not os.path.exists(p):
        return out
    rows = list(csv.DictReader(open(p, encoding='utf-8')))
    placed = {(r['fy'], r['person_key']) for r in rows if r['listing_kind'] == 'school'}
    for r in rows:
        if r['listing_kind'] == 'school':
            named = r['listing']
        elif (r['fy'], r['person_key']) in placed:
            continue                    # a building already lists them; the roll-up repeats it
        else:
            named = r['school'] or r['school_as_printed']
        sub = DIRECTORY_SUBUNIT.get(named.strip().lower(), named.strip())
        who = re.sub(r'\s{2,}', ' ', r['person']).strip()
        if not who:
            continue
        out.append(dict(fy=r['fy'], unit='Lunenburg Public Schools', unit_kind='school',
                        subunit=sub, section=r['section'],
                        role=(r['title'] or '').strip(), person=who, status='filled',
                        source='school staff directory (%s), fetched %s'
                               % (r['listing'], r['fetched'])))
    return out


def _rows_prose():
    """The departments that NAME their staff in prose, and the two that state posts."""
    p = os.path.join(DATA, 'department-staffing.csv')
    out = []
    if not os.path.exists(p):
        return out
    for r in csv.DictReader(open(p, encoding='utf-8')):
        if r['parsed'] != 'yes' or not r['positions']:
            continue
        parts = [x.strip() for x in r['positions'].split(';') if x.strip()]
        establishment = 'establishment' in r['measure']
        for part in parts:
            m = re.match(r'^(\d+)\s+(.*)$', part)
            n, label = (int(m.group(1)), m.group(2)) if m else (1, part)
            title = ''
            if not establishment and ',' in label:
                # `Steve Malandrinos, Information Technology Director` -- the IT
                # department prints a title beside every name and it was going into the
                # chart as part of the name. The Council on Aging prints names ALONE,
                # which is why that one stays flat: a fact about the report, not about us.
                head, rest = label.split(',', 1)
                if NAME_SHAPE.match(head.strip()) and rest.strip():
                    label, title = head.strip(), rest.strip()
            for _ in range(n):
                out.append(dict(
                    fy=r['fy'], unit=r['department'], unit_kind='department',
                    subunit='', section='',
                    role=label if establishment else title,
                    person='' if establishment else label,
                    # AN ESTABLISHMENT POST IS NOT A PERSON. The DPW and the Assessing
                    # office publish posts and never say who fills them, and the Assessing
                    # office's own FY2024 report -- "fully staffed for the first time in
                    # over a year" -- is why that distinction is kept rather than flattened.
                    status='post' if establishment else 'filled',
                    source='department report p%s' % r['page']))
    return out


# ---------------------------------------------------------------------------
# THE FIFTH SOURCE: WHO SIGNED THE REPORT.
#
# Most bodies in this town publish no roster at all. The Library, the Town Clerk, the
# Sewer Commission, Conservation, Veterans' Services -- fifteen years of reports and not
# one list of staff between them. What every one of them DOES print is the block that
# ends the report:
#
#     Respectfully submitted,
#     Muir Haman, Director, Lunenburg Public Library
#
# That is the head of the body, named, dated to the year, in the town's own words. It is
# the top layer of the chart for about thirty bodies that otherwise have nobody in it at
# all, and `extract_report_signatures.py` has 182 of them across thirteen years.
#
# THE NAMES NEED NORMALISING AND THAT IS OCR WORK, NOT INTERPRETATION. Every key below
# is a spelling of a body the contents page already names somewhere else in the same
# archive -- `LUNENBURG PUBLIC SCHOOLS` in capitals, `Lunenburg Public Library` with the
# town in front, `Veteran's Agent` where a later year says `Veterans' Services`.
SIG_SCHOOL = {
    'primary school': 'Lunenburg Primary School',
    'lunenburg primary school': 'Lunenburg Primary School',
    'turkey hill elementary': 'Turkey Hill Elementary School',
    'turkey hill elementary school': 'Turkey Hill Elementary School',
    'turkey hill middle school': 'Turkey Hill Elementary School',
    'middle school': 'Lunenburg Middle School',
    'lunenburg middle school': 'Lunenburg Middle School',
    'high school': 'Lunenburg High School',
    'lunenburg high school': 'Lunenburg High School',
}
# The district's own offices. They are not buildings, and the annual report files each
# under its own heading -- so they become SECTIONS of the central office rather than
# schools, which is what they are.
SIG_CENTRAL = {
    'superintendent message': 'Superintendent',
    "superintendent's message": 'Superintendent',
    'school facilities': 'Facilities and Grounds',
    'special services': 'Special Services',
    'special services department': 'Special Services',
    'review special services department': 'Special Services',
    'school lunch program': 'Food Service',
    'lunenburg school food service': 'Food Service',
    'pd update lunenburg school food service': 'Food Service',
    'teaching & learning models and pd update': 'Teaching and Learning',
    'teaching & learning models and': 'Teaching and Learning',
}
SIG_ALIAS = {
    'lunenburg public schools': 'Lunenburg Public Schools',
    'town manager': 'Town Manager', 'town manager report': 'Town Manager',
    'report of the town manager': 'Town Manager',
    'town manager report-heather r. lemieux': 'Town Manager',
    'public library': 'Public Library', 'lunenburg public library': 'Public Library',
    'public library 67,': 'Public Library',
    'housing authority submitted lunenburg public library': 'Public Library',
    "veteran's agent": "Veterans' Services", 'veterans services': "Veterans' Services",
    "veterans' services": "Veterans' Services",
    'police department **•': 'Police Department',
    'committee submitted zoning board of appeals': 'Zoning Board of Appeals',
    'ad hoc open space advisory committee to the planning board':
        'Ad Hoc Open Space Advisory Committee',
    'montachusett regional vocational': MONTY,
    'montachusett regional vocational technical school': MONTY,
    'montachusett regional vocational technical school district': MONTY,
    'montachusett regional vocational technical school ooooooooooo a o': MONTY,
    'technical school': MONTY,
}
# A TOWN MEETING IS NOT A DEPARTMENT. These are contents entries the signature extractor
# attributes a signing block to because the block sits on their pages -- the moderator's
# name at the end of a warrant, a line of an election return. Dropped rather than drawn.
SIG_DROP = re.compile(r'town meeting|town election|collection of taxes|omnibus|'
                      r'revenue funds|capital projects|vital records|excerpts', re.I)

# THE TOWN'S OWN DIRECTORY, AS A SIXTH SOURCE. TJ, after it had been fetched, extracted,
# catalogued and hashed: *"I still dont see Chris Ruth."* He was right -- it was a dataset
# and not yet a source, which is the difference between holding a document and reading it.
#
# THE YEAR COMES WITH THE ROW. `extract_staff_directory.py` stamps every row with the
# date the pages were fetched and the fiscal year that falls in -- so this reads a column
# rather than computing a date a second time. TJ: *"so just to be clear, you are labeling
# the directory departments and personnel dataset as FY27. and then joining"* -- that is
# the right order, and the first version had it the wrong way round: the dataset was
# undated and the JOIN applied a year, which left `staff-directory.csv` unable to say when
# it was from when anything else read it.
#
# WHAT IS NOT A YEAR IS WHAT THE SOURCE COVERS. The directory lists PAID STAFF ONLY -- no
# teacher, no board member, no volunteer -- so its year appears in the menu of the bodies
# it holds and nowhere else, and the page says what a reader is looking at.

# THE FOLDINGS THE DIRECTORY DOES NOT KNOW ABOUT. It files Animal Control and the three
# inspectorates as their own entries because they have their own phone numbers; the
# Police Department's own FY27 chart puts `ACO Kathy Comeau` under the Chief, and the
# inspectors work to the Building Commissioner. A contact list is not an org chart.
DIRECTORY_INTO = {
    'animal control department': 'Police Department',
    'electrical inspector': 'Building Department',
    'plumbing / gas inspector': 'Building Department',
    'weight & measures': 'Building Department',
    'select board': 'Town Manager',
    'planning board department': 'Planning Board',
}


def _rows_directory(units):
    """Who the town publishes today, matched to bodies the chart already holds."""
    p = os.path.join(DATA, 'staff-directory.csv')
    out, unmatched = [], []
    if not os.path.exists(p):
        return out, unmatched

    def words(name):
        n = re.sub(r"\s*\((staff|board|schools|appointed post)\)$", '', name or '',
                   flags=re.I)
        ws = re.findall(r'[a-z]+', n.lower().replace("'s", 's'))
        return {w.rstrip('s') for w in ws
                if w not in ('the', 'of', 'and', 'lunenburg', 'department', 'town',
                             'office', 'pac') and len(w) > 2}

    index = [(words(u), u, k) for u, k in sorted(units)]
    for r in csv.DictReader(open(p, encoding='utf-8')):
        dept = DIRECTORY_INTO.get(r['department'].strip().lower(), r['department'])
        mine = words(dept)
        hit = None
        for theirs, unit, kind in index:
            if mine and theirs and len(mine & theirs) >= min(2, len(mine), len(theirs)):
                hit = (unit, kind)
                break
        if not hit:
            # A DEPARTMENT THE TOWN PUBLISHES AND THIS PROJECT HAS NEVER HELD. Accounting
            # and Human Resources file no annual report and neither head is an APPOINTED
            # OFFICIAL, so both of the other sources miss them and always will. The
            # directory is the town's own list and it is enough on its own to say the
            # department exists.
            unmatched.append((dept, r['person']))
            hit = (dept.strip(), 'department')
        unit, kind = hit
        if not r.get('fy'):
            continue                    # an undated row cannot be placed in a year
        out.append(dict(fy=r['fy'], unit=unit, unit_kind=kind, subunit='',
                        section='', role=r['title'].strip(),
                        person=re.sub(r'\s{2,}', ' ', r['person']).strip(),
                        status='filled',
                        source='town staff directory, did=%s' % r['did']))
    return out, unmatched


def _sig_title(title, person):
    """The post, with the person's own name taken back out of it.

    `Chief James P. Marino` is what the block prints and it is a RANK plus a NAME, so the
    chart read `Chief James P. Marino — James P. Marino`. And `nham, Superintendent` is
    the tail of `Kate Burnham` landing in front of the title.
    """
    t = re.sub(r'^[a-z]{2,12},\s*', '', (title or '').strip())
    for part in sorted(person.split(), key=len, reverse=True):
        if len(part) > 2:
            t = re.sub(r'\b%s\b\.?' % re.escape(part), '', t)
    t = re.sub(r'\s{2,}', ' ', t).strip(' ,.')
    return t or 'signed the report'


def _rows_signatures():
    """The head of every body that signs its own report."""
    p = os.path.join(DATA, 'report-signatures.csv')
    out = []
    if not os.path.exists(p):
        return out
    for r in csv.DictReader(open(p, encoding='utf-8')):
        raw = re.sub(r'\s+', ' ', (r['department'] or '')).strip()
        # The orphaned `Submitted` of the PREVIOUS contents entry lands at the front of
        # the next name often enough to be worth cutting here as well as there.
        raw = re.sub(r'^.*\bSubmitted\b\s*', '', raw).strip() or raw
        if not raw or SIG_DROP.search(raw):
            continue
        key = raw.lower()
        if key in SIG_SCHOOL:
            unit, kind, sub, sect = ('Lunenburg Public Schools', 'school',
                                     SIG_SCHOOL[key], '')
        elif key in SIG_CENTRAL:
            unit, kind, sub, sect = ('Lunenburg Public Schools', 'school',
                                     'School Central Office', SIG_CENTRAL[key])
        else:
            unit = SIG_ALIAS.get(key, raw.title() if raw.isupper() else raw)
            if unit == 'Lunenburg Public Schools':
                kind, sub, sect = 'school', '', ''
            elif unit == MONTY:
                kind, sub, sect = 'school', '', ''
            # THE SIGNER'S TITLE DECIDES WHAT KIND OF BODY IT IS, not the body's name.
            # `Council on Aging` has the word `council` in it and is a DEPARTMENT with
            # eleven paid staff -- the mistake TJ caught the first time round: *"council
            # on aging... you said they were all paid positions?! They are showing as
            # board spots."* Its report is signed by a Director. A Chairperson heads a
            # board; a Director, Chief or Superintendent heads a department.
            elif re.search(r'chair|moderator', r['title'], re.I):
                kind, sub, sect = 'board', '', ''
            elif re.search(r'director|chief|superintendent|manager|librarian|agent|'
                           r'administrator|principal', r['title'], re.I):
                kind, sub, sect = 'department', '', ''
            elif re.search(r'commission|committee|board|authority', unit, re.I):
                kind, sub, sect = 'board', '', ''
            else:
                kind, sub, sect = 'department', '', ''
        out.append(dict(fy=r['fy'], unit=canon_unit(unit, kind), unit_kind=kind,
                        subunit=sub, section=sect,
                        # THE TITLE IS THE TOWN'S, NOT OURS. Where the block prints no
                        # title the person still signed the report, and `signed the
                        # report` is the only thing we can say about them.
                        # `nham, Superintendent` -- the scanner cuts the name in half
                        # and the tail of it lands in front of the title.
                        role=_sig_title(r['title'], r['person']),
                        person=r['person'].strip(), status='filled',
                        source='report signature p%s' % r['page']))
    # A BODY'S NAME IS NOT A SIGNER. `Information Technology` came through as a person
    # who had `signed the report`, off a block whose name line was the heading above it.
    out = [x for x in out if not re.search(
        r'\b(department|committee|commission|school|services|technology|office)\b',
        x['person'], re.I)]
    return out


def _norm_body(u):
    """A body's name reduced to what does not vary: no case, no punctuation, no filler."""
    u = re.sub(r'\s*\((staff|board|schools|appointed post)\)$', '', u, flags=re.I)
    return re.sub(r'[^a-z]', '',
                  re.sub(r'\b(the|of|and|lunenburg|department|town|report|committee)\b',
                         '', u.lower()))


def _rows_chairs(units):
    """THE CHAIR OF EVERY BOARD, from the body's own report.

    A QA pass over all 104 units found 274 bodies with members and NOBODY AT THE TOP --
    the Planning Board, the Finance Committee, the School Committee, the Board of Health,
    every one of them headless. The officials listing marks its chairs with asterisks and
    a footnote saying so, and stops doing it after about FY2015.

    The chairs never stopped being published; they moved into the reports. 263 mentions
    across fourteen years, read by `extract_board_chairs.py`.

    MATCHED AGAINST BODIES THAT ALREADY EXIST, never used to invent one. The contents page
    is scanned text, so it yields `Sewer Commission 70,` and `105 Capital Planning
    Committe lanning Boar` alongside the clean names; a chair whose body cannot be matched
    to a unit the chart already holds is counted and dropped rather than published under a
    body nobody can find.
    """
    p = os.path.join(DATA, 'board-chairs.csv')
    out, unmatched = [], []
    if not os.path.exists(p):
        return out, unmatched
    # SORTED, BECAUSE A SET IS NOT AN ORDER. Two units can normalise to the same key,
    # and whichever arrived first won -- which made the output depend on Python's
    # per-process string hashing, so `--check` failed at random.
    index = {}
    for u, kind in sorted(units):
        index.setdefault(_norm_body(u), (u, kind))
    for r in csv.DictReader(open(p, encoding='utf-8')):
        hit = index.get(_norm_body(r['department']))
        # A DEPARTMENT HAS NO CHAIR. The Fire Department's own pages carry the Board of
        # Health's chairman and the Police Chief's signature block, and the contents page
        # hands whole spreads to one body -- so a `Chair` landing on a department is an
        # attribution error every time, never a post.
        if hit and hit[1] not in ('board', 'officer'):
            unmatched.append((r['fy'], r['department'], r['person']))
            continue
        if not hit:
            unmatched.append((r['fy'], r['department'], r['person']))
            continue
        unit, kind = hit
        out.append(dict(fy=r['fy'], unit=unit, unit_kind=kind, subunit='', section='',
                        role=r['title'], person=r['person'].strip(), status='filled',
                        source='report p%s, names its own chair' % r['page']))
    return out, unmatched


KIND_SUFFIX = {'department': 'staff', 'board': 'board', 'officer': 'appointed post',
               'school': 'schools'}


def _one_spelling(rows):
    """One spelling per body, chosen by weight of rows rather than by a table.

    Four sources name the same bodies and none of them agrees on capitals: the officials
    listing is read through `.title()` so it says `Board Of Assessors`, the contents page
    says `Board of Assessors`, and the two arrived as two bodies sitting next to each
    other in the dropdown. Case is not a distinction the town draws, so the most-used
    spelling wins and every row takes it. `_disambiguate` still splits on KIND afterwards,
    which is a real distinction and survives this.
    """
    weight = collections.defaultdict(collections.Counter)
    for r in rows:
        weight[r['unit'].lower()][r['unit']] += 1
    # Most rows wins, and the alphabet breaks ties -- `most_common` leaves equal counts
    # in insertion order, which is not stable across runs.
    best = {k: sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
            for k, c in weight.items()}
    for r in rows:
        r['unit'] = best[r['unit'].lower()]
    return rows


def _disambiguate(rows):
    """A name that exists under two KINDS gets the kind in its title.

    TJ: *"im confused. council on aging... you said they were all paid positions?! They
    are showing as board spots."* Both are true and the page could not say so: `Council
    on Aging` the DEPARTMENT is eleven paid staff, every one of whom is on the town's
    2025 gross wages list, and `Council On Aging` the BOARD is eleven appointed
    volunteers. Two real bodies, one name, told apart by a capital O.
    """
    kinds = collections.defaultdict(collections.Counter)
    for r in rows:
        kinds[r['unit'].lower()][r['unit_kind']] += 1
    for r in rows:
        seen = kinds[r['unit'].lower()]
        # ONLY A DEPARTMENT AND A BOARD ARE TWO BODIES. `board` and `officer` are two
        # words the officials listing uses for the same committee depending on which
        # part of the page it was printed in, and splitting on them published the Storm
        # Water Task Force, the Taxation Aid Committee, the Constables and the Green
        # Community Task Force as pairs of half-empty units. Where the split is not real,
        # the majority kind wins and the body stays whole.
        # A ONE-ROW DEPARTMENT BESIDE A REAL BOARD IS A MISATTRIBUTION. One signature
        # read off a page the contents page gave to the wrong body invented
        # `Conservation Commission (staff)` -- a department of one, in one year, holding
        # the Council on Aging's director. A body that publishes staff publishes them
        # more than once.
        if 'department' in seen and len(seen) > 1 and seen['department'] < 3:
            r['unit_kind'] = sorted(((k, v) for k, v in seen.items() if k != 'department'),
                                    key=lambda kv: (-kv[1], kv[0]))[0][0]
        elif 'department' in seen and len(seen) > 1:
            r['unit'] = '%s (%s)' % (r['unit'], KIND_SUFFIX.get(r['unit_kind'],
                                                                r['unit_kind']))
        elif len(seen) > 1:
            r['unit_kind'] = sorted(seen.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    return rows


def build():
    rows, bad = _rows_officials()
    roster, lost_prose = _rows_rosters()
    rows += roster + _rows_schools() + _rows_prose() + _rows_signatures()
    rows += _rows_school_directory()
    keep = []
    for r in rows:
        key = r['unit'].lower()
        if NOT_A_UNIT.match(key):
            bad += 1
            continue
        # NOT GATED ON THE KIND. The Constable and the Moderator are typed `board` at
        # this point -- the listing prints them among the elected -- and the conversion
        # to `officer` happens further down, so testing for it here left both of them
        # standing alone in the dropdown after everything else had been grouped.
        if key in LOOSE_POST:
            post = r['unit']
            r['unit'], r['section'] = NO_DEPARTMENT, post
            if r['role'] in ('officer', 'board seat', ''):
                r['role'] = post
        # Not gated on the kind either, for the same reason: the listing prints the
        # Constable among the ELECTED in some years, so it never reached this branch.
        elif key in POST_IN:
            post = r['unit']
            r['unit'], r['unit_kind'] = POST_IN[key], 'department'
            if r['role'] in ('officer', 'board seat', ''):
                r['role'] = post
        elif r['unit_kind'] == 'officer' and IS_A_COMMITTEE.search(r['unit']):
            r['unit_kind'] = 'board'
        if key in HEAD_POST:
            r['unit'], r['unit_kind'], label = HEAD_POST[key]
            if r['role'] in ('officer', ''):
                r['role'] = label
        if key in FOLD_INTO:
            r['unit'], r['role'] = FOLD_INTO[key][0], FOLD_INTO[key][1]
            r['unit_kind'] = 'board'
        keep.append(r)
    rows = _disambiguate(_one_spelling(keep))

    # A PRINCIPAL BELONGS TO A BUILDING. A signature block says `Respectfully submitted,
    # Chad Adams, Principal` and the contents page gives the whole education section to
    # `Lunenburg Public Schools`, so three principals and a superintendent arrived in the
    # district bucket with no school between them -- and FY2021 had four buildings with
    # nobody at the top of any of them. The title names the building where it can
    # (`Principal, THES`, `LMHS Principal`); where it does not, the person's own name on
    # ONE building's roster THAT YEAR does. Same year only: a join, not a guess about
    # where somebody probably was.
    def _who2(name):
        parts = [x for x in re.split(r'\s+', name.strip()) if x]
        return (parts[-1].lower().strip('.,'), parts[0][:1].lower()) if parts else ('', '')

    where = collections.defaultdict(set)
    for r in rows:
        if r['unit_kind'] == 'school' and r['subunit'] and r['person']:
            # Surname and first initial: the roster says `Steve McKenna` and the
            # signature says `Stephen McKenna`.
            where[(r['fy'],) + _who2(r['person'])].add(r['subunit'])
    abbrev = [('lmhs', 'Lunenburg High School'), ('lhs', 'Lunenburg High School'),
              ('lms', 'Lunenburg Middle School'), ('thes', 'Turkey Hill Elementary School'),
              ('turkey hill', 'Turkey Hill Elementary School'),
              ('high school', 'Lunenburg High School'),
              ('middle school', 'Lunenburg Middle School'),
              ('primary', 'Lunenburg Primary School')]
    for r in rows:
        if r['unit_kind'] != 'school' or r['subunit'] or not r['person']:
            continue
        for key, school in abbrev:
            if re.search(r'\b%s\b' % re.escape(key), r['role'], re.I):
                r['subunit'] = school
                break
        else:
            seen = where.get((r['fy'],) + _who2(r['person']), set())
            if len(seen) == 1 and re.search(r'principal', r['role'], re.I):
                r['subunit'] = next(iter(seen))

    directory, unmatched_dir = _rows_directory({(r['unit'], r['unit_kind'])
                                                for r in rows})
    rows += directory

    # THE CHAIRS COME IN BEFORE THE BANDS ARE ASSIGNED, because a chair is the top band.
    # A POST ONE PERSON HOLDS IS NOT A BOARD. The Moderator, the Constable and the Town
    # Clerk were coming through as boards with a single `board seat`, because the
    # listing's own wording varies and the majority vote followed it.
    peak = collections.Counter()
    for r in rows:
        peak[(r['unit'], r['fy'])] += 1
    most = collections.defaultdict(int)
    for (unit, _fy), n in peak.items():
        most[unit] = max(most[unit], n)
    for r in rows:
        # ...but a body whose NAME says it is a committee stays one, however few people
        # the listing printed for it in a given year. The MART Advisory Board and the
        # Town Forest Committee were being converted back into appointed posts for
        # having a single member in a thin year.
        if r['unit_kind'] == 'board' and most[r['unit']] == 1 \
                and not IS_A_COMMITTEE.search(r['unit']):
            r['unit_kind'] = 'officer'
            if r['role'] == 'board seat':
                r['role'] = 'officer'

    chairs, unmatched = _rows_chairs({(r['unit'], r['unit_kind']) for r in rows})
    rows += chairs
    solo = collections.Counter((r['fy'], r['unit']) for r in rows)
    for r in rows:
        r['section_group'] = canon_section(r['section'])
        # AN APPOINTED POST IS ITS OWN HEAD -- BUT ONLY WHEN IT IS ONE POST. The
        # listing files whole committees under `officer` (the Charter Review Committee,
        # the Election Workers, the Building Design Committee), and calling every row a
        # head printed nine people as nine heads of one body. A unit holding one person
        # in a year has a head; a unit holding nine has members.
        r['tier'] = (board_tier(r['role']) if r['unit_kind'] == 'board'
                     else tier_of(r['role'], r['unit_kind']))
        # `Cemetery Superintendent`, `Highway Superintendent` -- heads of a DIVISION,
        # under the Director who heads the department.
        if r['tier'] == 0 and re.search(r'\w\s+superintendent\b', r['role'], re.I):
            r['tier'] = 2
        if r['unit_kind'] == 'officer':
            r['tier'] = (0 if solo[(r['fy'], r['unit'])] == 1
                         else board_tier(r['role']))

    # ONE ROW PER PERSON PER BAND. `Chief` off the roster and `Chief P` off the signature
    # block are the same post, and both were drawn. Where a person appears twice in one
    # body, one year and one band, the tidier role wins -- shortest that still names a
    # post -- because the duplicate is always a worse scan of the same words.
    # ONE ROW PER PERSON PER BODY PER YEAR, ACROSS THE BANDS. A chair is also a member,
    # and the listing prints them as one of the seats -- so adding the chairs put every
    # one of them in the chart twice, once at the top and once among the members. Where
    # one row names a real post and the other says only `board seat`, the post wins; the
    # person is one person either way.
    GENERIC = ('', 'board seat', 'officer')

    def _rank(r):
        return (r['role'].strip().lower() in GENERIC, r['tier'], -len(r['person']),
                len(r['role']))

    # ONE PERSON, TWO SPELLINGS. `Patrick A. Sullivan` off the roster and `Patrick
    # Sullivan` off the appointed-post listing are the same fire chief, and both were
    # drawn at the top of the department. Keyed on surname and first initial, within one
    # body and one year, which is as loose as this can safely go: two people in one
    # small department sharing both is not something these books contain.
    def _who(name):
        parts = [x for x in re.split(r'\s+', name.strip()) if x]
        return (parts[-1].lower().strip('.,'), parts[0][:1].lower()) if parts else ('', '')

    best = {}
    for r in rows:
        if not r['person']:
            continue
        # ONE PERSON, ONE ROW, AT THEIR MOST SENIOR POST. Keying on the section as well
        # was tried, so the high school's Athletic Director -- who is also an assistant
        # principal -- would appear under Athletics too. It brought back 178 duplicates
        # across the archive, which is far worse for a reader than Athletics showing its
        # secretary. The page says plainly that a person under two roles is one person
        # doing two jobs.
        k = (r['fy'], r['unit'], r['subunit']) + _who(r['person'])
        cur = best.get(k)
        if cur is None or _rank(r) < _rank(cur):
            best[k] = r
    rows = [r for r in rows
            if not r['person']
            or best[(r['fy'], r['unit'], r['subunit']) + _who(r['person'])] is r]
    # A COUNCIL SOMEBODY SITS ON IS NOT A RANK THEY HOLD. The Turkey Hill roster prints
    # its School Council -- the principal, two teachers and three parents -- and the
    # principal's row inside it was banding the whole council under him. TJ, earlier:
    # *"make sure to show the committees separately than the departments they run."*
    for r in rows:
        if re.search(r'council|advisory|committee', r['section_group'], re.I) \
                and not re.search(r'principal|superintendent|chair', r['role'], re.I):
            r['tier'] = TIER_STAFF

    # A TITLE THAT NAMES ANOTHER BODY IS A DELEGATE'S SEAT. The Taxation Aid Committee
    # seats the Assessors' Principal Clerk, the Council on Aging Director and the
    # Assistant Town Manager, and read as ranks they made a principal clerk the head of
    # the committee and two directors its deputies. Nobody sent by another body outranks
    # anybody here; the committee's own head is whoever it calls Chair.
    # INSIDE A SCHOOL BUILDING, THE HIERARCHY IS THE PRINCIPAL AND THE ASSISTANT
    # PRINCIPAL. A `Director` on a primary-school roster runs the after-school programme
    # or the district's facilities; neither is second in command of the building.
    for r in rows:
        if r['unit_kind'] == 'school' and r['subunit'] and r['tier'] < TIER_STAFF \
                and not re.search(r'principal|head', r['role'], re.I):
            r['tier'] = TIER_SUPERVISOR if r['section_group'] else TIER_STAFF

    # A CHAIR OF A BOARD SITS ON THAT BOARD. Matched on surname and first initial,
    # because the listing says `Timothy Russell Willsmer` and the report says `Timothy
    # Willsmer`, and an exact match finds neither in the other.
    def _who(name):
        parts = [x for x in re.split(r'\s+', name.strip()) if x]
        return (parts[-1].lower().strip('.,'), parts[0][:1].lower()) if parts else ('', '')

    # A CHAIR OF A BOARD SITS ON THAT BOARD. Where a body-year has several people
    # called chair and only some of them are among its members, the others were read off
    # a page the contents attributed to the wrong body -- the Planning Board and the
    # Zoning Board of Appeals print back to back, and the ZBA's chairman arrived as the
    # Planning Board's third. Only dropped when a member-chair exists to prefer.
    members = collections.defaultdict(set)
    seats = collections.defaultdict(set)
    for r in rows:
        if r['role'] in ('board seat', 'officer') or not re.search(r'chair', r['role'],
                                                                   re.I):
            members[(r['fy'], r['unit'])].add(_who(r['person']))
            seats[(r['fy'],) + _who(r['person'])].add(r['unit'])

    # A DELEGATE'S TITLE NAMES THE BODY THEY COME FROM, and that is a membership this
    # archive states out loud: the Storm Water Task Force seats `Jenny Pewtherer -
    # Conservation Commission`, which is the Conservation Commission saying she is one of
    # theirs. Without reading it, she and a chair who belongs to somebody else were
    # indistinguishable -- both seated on some other body, neither seated here.
    byname = {}
    for r in rows:
        byname.setdefault(_norm_body(r['unit']), r['unit'])
    for r in rows:
        if not r['person'] or not r['role']:
            continue
        home = byname.get(_norm_body(r['role']))
        if home and home != r['unit']:
            members[(r['fy'], home)].add(_who(r['person']))
            seats[(r['fy'],) + _who(r['person'])].add(home)

    drop = set()
    chairs_by = collections.defaultdict(list)
    for r in rows:
        if re.search(r'^chair', r['role'], re.I):
            chairs_by[(r['fy'], r['unit'])].append(r)
    for (fy, unit), cand in chairs_by.items():
        # `Christine C.` and `Christine C. Higdon` are one person with the surname
        # scanned off the end, so the surname test cannot pair them. A name that is a
        # prefix of another name on the same body in the same year is that name.
        full = sorted({c['person'] for c in cand}, key=len, reverse=True)
        for c in cand:
            for f in full:
                if f != c['person'] and f.lower().startswith(c['person'].lower().rstrip(' .')):
                    c['person'] = f
                    break
        if len({c['person'] for c in cand}) < 2:
            continue
        inside = [c for c in cand if _who(c['person']) in members[(fy, unit)]]
        if inside:
            drop |= {id(c) for c in cand if c not in inside}
            continue
        # NOBODY IS A MEMBER OF THIS BODY, so ask where they ARE one. Deb Lincoln
        # chaired the Council on Aging and arrived as a second chair of the Conservation
        # Commission, because the two reports share a page and the contents page hands
        # whole spreads to one body.
        # NOBODY HERE IS A SEATED MEMBER, so ask who is seated SOMEWHERE ELSE. Deb
        # Lincoln holds a seat on the Council on Aging and none on the Conservation
        # Commission, and she arrived as its second chair because FY2025 pages 47-48
        # carry the Council's report inside the Commission's stated range. Only ever
        # applied when another candidate remains, so a chair whose own seat this archive
        # missed is not deleted for sitting on something else.
        elsewhere = [c for c in cand
                     if seats.get((fy,) + _who(c['person']), set()) - {unit}]
        if elsewhere and len(elsewhere) < len(cand):
            drop |= {id(c) for c in elsewhere}
            continue
        # THREE CHAIRS IS NOT A SUCCESSION. Two can be: a board that changes chair
        # mid-year prints both, and the reports do. Three means the page range covered
        # somebody else's report, and nothing here can say which one is ours -- so the
        # body is published headless rather than with a guess at the top.
        if len({c['person'] for c in cand}) > 2:
            drop |= {id(c) for c in cand}
    rows = [r for r in rows if id(r) not in drop]

    # ONE PERSON, ONE CHAIR. Somebody who turns up chairing two bodies in one year is
    # chairing the one they sit on. Deb Lincoln chaired the Council on Aging and arrived
    # as a second chair of the Conservation Commission, because FY2025 pages 47 and 48
    # carry the Council's report inside the Commission's stated range.
    chairing = collections.defaultdict(list)
    for r in rows:
        if re.search(r'^chair', r['role'], re.I):
            chairing[(r['fy'],) + _who(r['person'])].append(r)
    gone = set()
    for k, cand in chairing.items():
        if len({c['unit'] for c in cand}) < 2:
            continue
        home = [c for c in cand if c['unit'] in seats.get(k, set())]
        if home:
            gone |= {id(c) for c in cand if c not in home}
    rows = [r for r in rows if id(r) not in gone]

    # A BOARD HAS NO DIRECTOR AND NO CHIEF. Where a signature block lands on a board --
    # the contents page hands whole spreads to one body, and FY2025 pages 47-48 carry the
    # Council on Aging's report inside the Conservation Commission's stated range -- the
    # giveaway is the TITLE. A board elects a chair, a vice-chair and a clerk; anybody
    # arriving at one with `Director` after their name came off somebody else's page.
    rows = [r for r in rows
            if not (r['unit_kind'] == 'board'
                    and r['source'].startswith(('report signature', 'report p'))
                    and not re.search(r'chair|clerk|secretary', r['role'], re.I))]

    # AN UNNAMED POST AND THE PERSON APPOINTED TO IT ARE ONE JOB. The DPW publishes an
    # ESTABLISHMENT -- `Director`, with no name, because that is how the department
    # states its strength -- and the officials listing appoints William Bernard as DPW
    # Director. Both are true and drawing both puts two directors at the top of the
    # department. The post keeps its place and the name fills it.
    named = collections.defaultdict(set)
    for r in rows:
        if r['person'] and r['role']:
            named[(r['fy'], r['unit'], r['subunit'])].add(
                re.sub(r'[^a-z]', '', r['role'].lower()))
    rows = [r for r in rows
            if r['status'] != 'post'
            or not any(k and (k in re.sub(r'[^a-z]', '', r['role'].lower())
                              or re.sub(r'[^a-z]', '', r['role'].lower()) in k)
                       for k in named[(r['fy'], r['unit'], r['subunit'])])]

    # ONLY A SUPERINTENDENT HEADS THE DISTRICT. FY2019 opened with four Directors in
    # the top band because no superintendent row reached that year; a Director of Food
    # Service does not run Lunenburg Public Schools in any year, including the ones where
    # we have not found the superintendent.
    for r in rows:
        if r['unit_kind'] == 'school' and not r['subunit'] and r['tier'] == 0 \
                and not re.search(r'superintendent', r['role'], re.I):
            r['tier'] = 1

    strong = {(r['fy'], r['unit'], r['subunit']) for r in rows
              if r['tier'] == 0 and STRONG_HEAD.search(r['role'])}
    for r in rows:
        if r['tier'] == 0 and not STRONG_HEAD.search(r['role']) \
                and (r['fy'], r['unit'], r['subunit']) in strong:
            r['tier'] = 1

    # A GROUPING IS KEPT ONLY WHERE IT DIVIDES A BAND. `Elected` written over every
    # member of an elected board, `Administration` over a Police Chief who is the only
    # person in his band -- a line of type between the reader and the names. Per BAND
    # rather than per body, which is what keeps `Career` and `Call` beside each other at
    # every rank of the Fire Department while the Chief above them stands ungrouped.
    spread = collections.defaultdict(set)
    for r in rows:
        spread[(r['fy'], r['unit'], r['subunit'], r['tier'])].add(r['section_group'])
    # ...UNLESS THE GROUP RUNS ACROSS THE RANKS. A band holding one group is usually a
    # heading of one -- `Administration` over a Police Chief standing alone. But the Fire
    # Department's `Career Firefighters` holds its lieutenant in one band and its
    # firefighters in another, and blanking the lone lieutenant's group broke the
    # department in half: the page could no longer see that Career and Call run through
    # every rank, and drew it a rank at a time instead of a service at a time.
    elsewhere = collections.defaultdict(set)
    for r in rows:
        elsewhere[(r['fy'], r['unit'], r['subunit'], r['section_group'])].add(r['tier'])
    for r in rows:
        if r['unit'] == NO_DEPARTMENT:
            continue                      # the post IS the grouping here
        alone = len(spread[(r['fy'], r['unit'], r['subunit'], r['tier'])]) <= 1
        spans = len(elsewhere[(r['fy'], r['unit'], r['subunit'],
                               r['section_group'])]) > 1
        if alone and not spans:
            r['section_group'] = ''
    seen, uniq = set(), []
    for r in rows:
        k = (r['fy'], r['unit'], r['subunit'], r['section'], r['role'], r['person'],
             r['status'])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    uniq.sort(key=lambda r: (r['unit'].lower(), r['fy'], r['subunit'].lower(),
                             r['tier'], r['section_group'].lower(), r['role'].lower(),
                             r['person'].lower()))
    return uniq, bad, lost_prose, unmatched, unmatched_dir


# HOW A BODY IS DRAWN IS A PROPERTY OF THE BODY. TJ: *"every department needs their own
# way to generate their org chart based on their structure."*
#
# The first version had the page guess, from whether a grouping happened to cross two
# bands — and a guess that is right for the Police Department is wrong for the schools:
# laying the district out a group at a time threw the four buildings away and printed
# four principals in a row. So the LAYOUT is decided here, per body, published in the
# payload beside it, and the page switches on it. It can be read, checked and argued
# with, which a heuristic buried in a component cannot.
#
#   buildings  a body made of places before anything else. The district is four schools,
#              each with its own principal; the building is the container and the ranks
#              sit inside it.
#   shifts     a body made of parallel units that each run through every rank. The Police
#              Department publishes its own chart this way in its FY27 budget
#              presentation: the Chief, then the Administrative Lieutenant and the office,
#              then `Day Shift 0700-1500`, `Evening Shift`, `Night Shift`, `Investigative
#              Bureau`, `Community Policing Bureau` side by side, each headed by its
#              sergeant. The Fire Department is the same shape with Career and Call.
#   board      a body that elects officers and is otherwise equals — chair, vice-chair,
#              clerk, then the members.
#   ranks      everything else: a head, a deputy, supervisors, staff.
LAYOUTS = ('buildings', 'shifts', 'board', 'ranks')


def layout_of(unit_rows):
    """Which of the four shapes this body is drawn in, and why."""
    if any(r['subunit'] for r in unit_rows):
        return 'buildings'
    if unit_rows[0]['unit'] == NO_DEPARTMENT:
        # Not a hierarchy at all: five unrelated posts that happen to share a page.
        return 'shifts'
    if unit_rows[0]['unit_kind'] in ('board', 'officer'):
        return 'board'
    # A group that holds more than one rank is a real division of the body, not a label
    # on one row -- a shift with its sergeant and its officers, a service with its
    # captain and its firefighters.
    #
    # ELECTED AND APPOINTED ARE NOT DIVISIONS. They are how somebody GOT the post, an
    # attribute of the seat rather than a part of the body, and they span every rank by
    # definition -- so the Building Department, the Town Clerk and the Treasurer were all
    # typed `shifts` on the strength of a word that tells a reader nothing about how the
    # department is arranged. Then FY2027, which has no groups at all, rendered through
    # the shift layout and put an Assistant Electrical Inspector above the Building
    # Commissioner.
    by_group = collections.defaultdict(set)
    for r in unit_rows:
        if r['section_group'] and r['section_group'] not in ('Elected', 'Appointed'):
            by_group[r['section_group']].add(r['tier'])
    if any(len(t) > 1 for t in by_group.values()):
        return 'shifts'
    return 'ranks'


CROSSWALK = os.path.join(DATA, 'body-crosswalk.csv')


def crosswalk():
    """Each body's money page and its headcount by year, read off `body-crosswalk.csv`.

    NOT COMPUTED HERE. `build_body_crosswalk.py` owns the name join and both payloads read
    its output, because the chart needs to send a reader to the money and the finance page
    needs to send one to the people -- and a map written once in each is the defect
    CLAUDE.md names sixth. If the file is absent the chart simply carries no links, which
    is the same page it was before, rather than a build that fails.

    THE SERIES IS THE CHART'S OWN COUNT. `people` is recomputed here from these very rows
    rather than copied from the crosswalk, so a reader following a link can never meet two
    different headcounts for one body and one year -- and `--check` on the crosswalk is what
    says the two agree.
    """
    if not os.path.exists(CROSSWALK):
        return {}
    out = {}
    for r in csv.DictReader(open(CROSSWALK, encoding='utf-8')):
        out[r['unit']] = {k: r[k] for k in
                          ('money_url', 'money_slug', 'money_kind', 'board_url',
                           'board_slug', 'basis', 'why')}
    return out


def payload(rows):
    # TIER TRAVELS AS A STRING, because the CSV has always carried it as one and the page
    # compares against `'0'`. Emitting an int here made two bugs at once in JavaScript:
    # `r.tier || '3'` treats the integer 0 as MISSING, so every head in the archive was
    # filed with the staff -- Patrick A. Sullivan, Chief of Department, under `Members,
    # seats and staff`, below his own deputy -- and `tier === '0'` never matched, so the
    # band that should have had no indent got one and rendered as a second staff band.
    # Nothing could catch it from the data, which was right the whole time.
    rows = [dict(r, tier=str(r['tier'])) for r in rows]
    years = sorted({r['fy'] for r in rows})
    units = collections.defaultdict(lambda: dict(years=set(), kind='', n=0, subs=set()))
    for r in rows:
        u = units[r['unit']]
        u['years'].add(r['fy'])
        u['kind'] = u['kind'] or r['unit_kind']
        u['n'] += 1
        if r['subunit']:
            u['subs'].add(r['subunit'])
    # HOW MANY NAMED PEOPLE EACH BODY HOLDS, YEAR BY YEAR -- the trend, drawn from the same
    # rows the chart draws. Distinct PEOPLE, not rows: somebody who holds two posts in one
    # body is one person, and counting rows made the Select Board look twice its size in the
    # years its members also sat as sewer commissioners. A vacancy is a post, not a person.
    people = collections.defaultdict(lambda: collections.defaultdict(set))
    for r in rows:
        if r['status'] == 'filled' and r['person'].strip():
            people[r['unit']][r['fy']].add(r['person'].strip().lower())
    link = crosswalk()
    return dict(
        generated_by='scripts/build_org_charts.py',
        years=years,
        units=[dict(unit=k, kind=v['kind'], rows=v['n'], years=sorted(v['years']),
                    subunits=sorted(v['subs']),
                    people={fy: len(who) for fy, who in sorted(people[k].items())},
                    links=link.get(k, {}),
                    layout=layout_of([r for r in rows if r['unit'] == k]))
               for k, v in sorted(units.items(), key=lambda kv: (-kv[1]['n'], kv[0]))],
        rows=rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows, bad, lost, unmatched, unmatched_dir = build()
    pay = payload(rows)
    if a.check:
        old = list(csv.DictReader(open(OUT_CSV, encoding='utf-8'))) \
            if os.path.exists(OUT_CSV) else []
        if len(old) != len(rows) or any(
                any(str(r[k]) != o[k] for k in FIELDS) for r, o in zip(rows, old)):
            print('STALE %s' % OUT_CSV)
            return 1
        return 0
    with open(OUT_CSV, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    json.dump(pay, open(OUT_JSON, 'w', encoding='utf-8'), indent=1, sort_keys=True)
    st = collections.Counter(r['status'] for r in rows)
    print('%d rows across %d units and %d years' % (len(rows), len(pay['units']),
                                                    len(pay['years'])))
    print('  filled %d, vacant %d, establishment posts %d'
          % (st['filled'], st['vacant'], st['post']))
    print('  REJECTED %d rows: town-profile text, listing footnotes, sub-headings' % bad)
    # NAMED, SO A LOST PERSON IS VISIBLE RATHER THAN MISSING. Every line below is a
    # SENTENCE the column reader handed back as a name; if a real name is ever in this
    # list it is a defect, and the only way anybody finds out is by printing them.
    print('  %d roster lines read as prose, not people:' % len(lost))
    for fy, dept, txt in lost[:200]:
        print('      FY%s %-18s %s' % (fy, dept[:18], txt[:88]))
    print('  %d chair mentions could not be matched to a body in the chart' % len(unmatched))
    print('  %d staff-directory people could not be matched to a body:' % len(unmatched_dir))
    for dept, who_ in unmatched_dir[:12]:
        print('      %-42s %s' % (dept[:42], who_))
    thin = [u for u in pay['units'] if len(u['years']) == 1]
    print('  %d unit(s) appear in ONE year only — read them before trusting them'
          % len(thin))
    return 0


if __name__ == '__main__':
    sys.exit(main())
