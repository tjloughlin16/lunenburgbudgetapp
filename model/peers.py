"""Local North Central Massachusetts districts, FY27 budget cycle.

Every figure below is taken from the district's own published FY27 budget document
or meeting minutes -- see sources/peer-districts/. `note` is quoted or closely paraphrased
from those documents.
"""

PEERS = [
 dict(id='lunenburg', name='Lunenburg', subject=True, enrollment=1581,
      budget=26_572_288, changePct=1.08, healthPct=7.9,
      chapter70Pct=None, overrideStatus='failed',
      protected=['Special education', 'Classroom teachers (partly)'],
      sacrificed=['All athletic transportation', 'Middle school & freshman sports',
                  'Grade 5 band', '4.0 classroom teachers', '1.5 interventionists',
                  'Assistant Principal', 'Custodian'],
      note='Both override questions failed on 16 May 2026, 33% and 29% yes. The town '
           'adopted the balanced budget: 253 staff, down from 256.5 at level service.',
      source='LPS FY27 budget documents; town election tally'),

 dict(id='groton-dunstable', name='Groton-Dunstable', subject=False, enrollment=2324,
      budget=54_187_751, changePct=6.46, healthPct=8.9,
      chapter70Pct=None, overrideStatus='needed',
      protected=['Nothing — the budget is below level service'],
      sacrificed=['3.0 FTE unfilled in FY26', 'Class offerings reduced',
                  'Staff and student support reduced', 'Athletic/K/preschool fees under review'],
      note='Budget reductions in FY24, FY25 and FY26 produced personnel cuts across all '
           'job classifications. The FY27 proposal is deliberately below level service. '
           'The district says an operational override is needed "now and in the '
           'foreseeable future."',
      source='GDRSD FY27 Budget Book, 28 Jan 2026'),

 dict(id='ashburnham-westminster', name='Ashburnham-Westminster', subject=False,
      enrollment=2184, budget=40_233_975, changePct=2.9, healthPct=13.1,
      chapter70Pct=2.05, overrideStatus='none',
      protected=['Athletics (+2.7%)', 'Marching band (+4.8%)', 'Class size',
                 'Girls ice hockey reinstated, funded by user fees'],
      sacrificed=['2.0 elementary teachers', 'Technology budget (-5.8%)',
                  'Out-of-district tuition budget (-$100k)', '$600k drawn from reserves'],
      note='District goals explicitly state: "Maintain Class Size" and "Ensure that '
           'co-curricular, arts, music and athletic budgets are preserved." To do it '
           'they cut two elementary teachers and drew $600,000 from reserves.',
      source='AWRSD Superintendent FY27 Preliminary Operating Budget, 5 Feb 2026'),

 dict(id='ayer-shirley', name='Ayer-Shirley', subject=False, enrollment=1704,
      budget=36_743_801, changePct=5.5, healthPct=14.4,
      chapter70Pct=1.5, overrideStatus='unknown',
      protected=[],
      sacrificed=['Central office budget offsets and reductions'],
      note='Level-service budget rose 5.5% while Chapter 70 aid rose 1.5%. Health '
           'insurance rose 14.4% — the steepest in this group.',
      source='Ayer-Shirley RSD Proposed FY27 Budget, 17 Mar 2026'),

 dict(id='north-middlesex', name='North Middlesex', subject=False, enrollment=3900,
      budget=38_381_000, changePct=3.0, healthPct=None,
      chapter70Pct=None, overrideStatus='unlikely',
      protected=[],
      sacrificed=['Soft spending freeze', 'Capital and technology projects deferred',
                  'Positions shifted onto grants', 'Vacancies held unfilled'],
      note='Projected a $64,000 deficit at 3% budget growth versus $1.5 million at 5%. '
           'Roughly 30% of students receive special education services. Townsend has not '
           'passed an override in 20 years.',
      source='NMRSD FY27 Budget Summit notes, 27 Oct 2025'),

 dict(id='wachusett', name='Wachusett', subject=False, enrollment=6507,
      budget=134_809_232, changePct=4.44, healthPct=None,
      chapter70Pct=None, overrideStatus='none',
      protected=[],
      sacrificed=['Member-town discretionary assessments raised 9.21%'],
      note='Closed its gap by charging member towns more: the discretionary assessment '
           'rose 9.21% while enrollment fell in four of five towns.',
      source='WRSD FY27 Budget Book, School Committee approved 9 Mar 2026'),
]

LESSONS = [
 dict(title='Nobody closed a gap this size with extras',
      body='Every district in this group covered its shortfall with personnel, reserves, '
           'deferrals or higher assessments. None of them found enough in supplies, '
           'athletics or arts to matter.'),
 dict(title='Priorities really are a choice',
      body='Ashburnham-Westminster wrote "preserve athletics, arts and music" into its '
           'district goals and cut two elementary teachers to honor it. Lunenburg cut '
           'athletics first and defended classroom staffing. Same pressures, opposite '
           'answers — which is why the ranking in this tool is yours to set.'),
 dict(title='Everyone charges fees — the question is how far they stretch',
      body='Lunenburg already charges, and raised the athletic fee for 2026-27 to $400 for '
           'a first child ($300 second, $225 third, $1,500 family cap), plus $180 a year '
           'for the bus. That is an estimated $187,000 — 54% of what it costs to field the '
           'teams that survived and get them to away games. '
           'Ashburnham-Westminster collects $215,000 overall and funds a whole team from '
           'fees; Groton-Dunstable is reviewing four fee categories. Because Lunenburg '
           'already charges, the easy headroom is gone: only the increase above today\'s '
           'fee is new money.'),
 dict(title='One-time money runs out',
      body='Ashburnham-Westminster balanced with $600,000 from reserves. Groton-Dunstable '
           'is deliberately weaning off $400,000 of one-time revenue. Lunenburg is doing '
           'the same thing with $453,722 in September. It works once.'),
 dict(title='The squeeze is structural, not local',
      body='Health insurance rose 8–14% across every district here while Chapter 70 aid '
           'rose 1.5–2%. No district in this group solved that; they only chose who absorbs it.'),
]
