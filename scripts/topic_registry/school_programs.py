"""The School programs shelf. See scripts/topics.py for the model and the title rule.

Absorbs /what-courses-actually-ran ('courses'), /ap-exams ('ap'), /cut-register ('cuts'),
/what-stopped-being-funded ('stopped') and /when-grants-end ('unwind'). Each source page reads
one generated payload, and scripts/build_school_programs_topics.py reads those payloads.

Four different instruments sit on this shelf and none of them is a count of children taught:
DESE's class-size file counts SECTIONS that ran; DESE's AP files count exam SITTINGS and the
children who sat at least one; the district's cut lists are CLAIMS it published; the budget
book and DESE's End of Year Financial Report count DOLLARS. Every page says which it is.

Teacher FTE by subject is HOME on the School staffing shelf and out-of-district tuition on the
Special education shelf; both are listed here, one page on two shelves.
"""
CATEGORY = dict(
    id='school-programs', shelf='School programs', title='Programs and cuts', area='school',
    order=25,
    groups=[
        ('What ran', ['high-school-sections', 'world-languages', 'history-courses',
                      'computer-science-courses']),
        ('Advanced Placement', ['ap-participation', 'ap-scores', 'ap-subjects']),
        ('What was cut', ['announced-cuts', 'override-cut-lists', 'cuts-against-state-counts',
                          'lines-cut-to-zero']),
        ('When grants end', ['grant-endings', 'outside-money-share']),
        ('On other shelves', ['teachers-by-subject', 'out-of-district-tuition']),
    ],
    elsewhere=[('/what-we-cannot-answer', 'What we cannot answer')])
GENERATOR = 'build_school_programs_topics.py'
TOPICS = {
    'high-school-sections': 'High school sections',
    'world-languages': 'World languages',
    'history-courses': 'History courses',
    'computer-science-courses': 'Computer science',
    'ap-participation': 'AP participation',
    'ap-scores': 'AP scores',
    'ap-subjects': 'AP subjects',
    'announced-cuts': 'Announced cuts',
    'override-cut-lists': 'Override cut lists',
    'cuts-against-state-counts': 'Cuts against state counts',
    'lines-cut-to-zero': 'Lines cut to zero',
    'grant-endings': 'Grant endings',
    'outside-money-share': 'Outside money share',
}
