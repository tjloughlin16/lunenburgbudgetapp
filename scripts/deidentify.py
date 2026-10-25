"""PEOPLE NAMED BY ROLE, NOT NAME, on every page we publish.

A person on this list is shown by role on our pages, never by name. Empty since 24 October
2026: the one name added was a public official, and TJ confirmed it may appear. A
quotation is still checked VERBATIM against the minutes it came from (rule 13); only
what is SHOWN changes, and the change is marked the way an edited quotation is always marked,
with square brackets: "[the Director of Special Services] states there is no formula".

Add a person here, never at a call site, so one list governs every page.
"""
import re

# name as the minutes print it -> the role it is shown as
ROLES = {}


def shown(quote):
    """A verified quotation as published: each listed name replaced by its role, in brackets."""
    for name, role in ROLES.items():
        quote = re.sub(re.escape(name), '[%s]' % role, quote)
    return quote


def original(quote):
    """The quotation as the source prints it, for a verifier: each bracketed role put back to
    the name it stands for. Only the roles on this list are restored, so any other bracket a
    quote carries still has to match the source as it is."""
    for name, role in ROLES.items():
        quote = quote.replace('[%s]' % role, name)
    return quote


def check(text, where):
    """Refuse to publish text that still carries a listed name."""
    for name in ROLES:
        for part in name.split():
            if re.search(r'\b%s\b' % re.escape(part), text, re.I):
                raise SystemExit('%s names %r; show the role instead (scripts/deidentify.py)'
                                 % (where, part))
    return text
