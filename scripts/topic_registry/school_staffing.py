"""The School staffing shelf. See scripts/topics.py for the model and the title rule.

Absorbs /school-staffing ('staffing'), /who-works-in-each-school ('schoolstaff') and /paras
('parastaff'), all three selected out of one build: scripts/build_staffing_charts.py. These
pages are about PEOPLE -- counts of posts, counts of people, counts of printed names -- and
each says which of those it is, because they are three different quantities.

The money for paraprofessionals is HOME on two other shelves and is only LISTED here: the
paraprofessional budget line (special education) and the FY2026 paraprofessional overrun
(FY2026 closeout). One question, one page, one address.
"""
CATEGORY = dict(
    id='school-staffing', shelf='School staffing', title='School staff', area='school',
    order=22,
    groups=[
        ('Teachers', ['teacher-fte-over-time', 'teachers-per-pupil', 'teachers-by-school',
                      'teachers-by-subject']),
        ('Paraprofessionals', ['paraprofessional-fte', 'paraprofessional-counts',
                               'staff-by-programme']),
        ('People and records', ['headcount-and-fte', 'staff-retention', 'school-support-staff',
                                'printed-school-rosters', 'district-staff-directory']),
        ('Paraprofessional money', ['in-district-special-education',
                                    'fy2026-paraprofessional-overrun']),
    ],
    elsewhere=[('/what-we-cannot-answer', 'What we cannot answer')])
GENERATOR = 'build_school_staffing_topics.py'
TOPICS = {
    'teacher-fte-over-time': 'Teachers over time',
    'teachers-per-pupil': 'Teachers per pupil',
    'teachers-by-school': 'Teachers by school',
    'teachers-by-subject': 'Teachers by subject',
    'paraprofessional-fte': 'Paraprofessionals over time',
    'paraprofessional-counts': 'Paraprofessional counts compared',
    'staff-by-programme': 'Staff by programme',
    'headcount-and-fte': 'People and posts',
    'staff-retention': 'Staff retention',
    'school-support-staff': 'Support staff',
    'printed-school-rosters': 'Printed school rosters',
    'district-staff-directory': 'District staff directory',
}
