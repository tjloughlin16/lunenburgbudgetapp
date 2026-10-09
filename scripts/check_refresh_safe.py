#!/usr/bin/env python3
"""Does the refresh's code contain any path that could destroy work? Fails if it does.

    python3 scripts/check_refresh_safe.py            # the refresh's files; exit 1 on any finding
    python3 scripts/check_refresh_safe.py --selftest # ...and prove it catches each banned form

TJ, 8 October 2026: *"this shouldnt have ANY chance of a destructive path"*. A promise in a
comment is how the last version got here: daily_refresh.sh said `add -A` was safe because
of a `reset --hard` 120 lines above it, and a later edit made the first true and the second
dangerous without anybody re-reading both. So the promise is a check, it runs with every
other check (scripts/check_generated.py), and a later edit cannot quietly put one back.

WHAT IT REFUSES, in daily_refresh.sh, refresh.py, refresh_git.py and triage_refresh.py:

  * git reset, clean, stash, checkout, restore, switch, rebase, rm -- each can discard a
    working-tree file, move a branch out from under a person, or (rebase --abort, 4 October
    2026) strand a day's work in the reflog;
  * git push --force / -f / --force-with-lease / a `+refspec`, and git branch -D/-d/-f/-M;
  * git update-ref -d, git worktree remove/prune;
  * rm / unlink / rmdir as commands, and os.remove, os.unlink, os.rmdir, shutil.rmtree,
    Path.unlink, Path.rmdir in Python -- UNLESS the path is provably under build/, which is
    gitignored and ours.

HOW IT READS. Comments are skipped (a comment explaining why `reset --hard` was removed is
not a reset), and so are Python docstrings. Python is read as a syntax tree: a git command
is found as a list beginning 'git', or as a call to a function named `git` (the helper in
refresh_git.py), whatever the spacing. A deletion's path is followed through the names it
was assigned from; one that cannot be shown to start under build/ is a finding. It errs
toward refusing: a false alarm costs an edit, a missed one costs somebody's work.
"""
import ast
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ['scripts/daily_refresh.sh', 'scripts/refresh.py', 'scripts/refresh_git.py',
         'scripts/triage_refresh.py']

BANNED_SUB = {'reset', 'clean', 'stash', 'checkout', 'restore', 'switch', 'rebase', 'rm'}
FORCE = {'-f', '--force', '--force-with-lease', '--force-if-includes'}
BRANCH_BAD = {'-D', '-d', '-f', '-M', '--delete', '--force', '--move'}
PY_DELETE = {('os', 'remove'), ('os', 'unlink'), ('os', 'rmdir'), ('os', 'removedirs'),
             ('shutil', 'rmtree')}
PY_DELETE_ATTR = {'unlink', 'rmdir', 'rmtree'}


def git_finding(args):
    """args: the words after `git` (strings; None where not a literal). -> reason or None."""
    words = [w for w in args if w is not None]
    sub = next((w for w in words if not w.startswith('-')), None)
    if sub is None:
        return None
    rest = words[words.index(sub) + 1:]
    if sub in BANNED_SUB:
        return 'git %s' % sub
    if sub == 'push' and (FORCE & set(rest) or any(w.startswith('+') for w in rest)):
        return 'git push --force'
    if sub == 'branch' and BRANCH_BAD & set(rest):
        return 'git branch %s' % ' '.join(sorted(BRANCH_BAD & set(rest)))
    if sub == 'update-ref' and '-d' in rest:
        return 'git update-ref -d'
    if sub == 'worktree' and rest[:1] and rest[0] in ('remove', 'prune'):
        return 'git worktree %s' % rest[0]
    return None


# ----------------------------------------------------------------------------- Python
def _strs(nodes):
    return [n.value if isinstance(n, ast.Constant) and isinstance(n.value, str) else None
            for n in nodes]


class PyScan(ast.NodeVisitor):
    def __init__(self, tree):
        self.findings = []
        self.assigned = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        self.assigned.setdefault(t.id, []).append(node.value)
        self.docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                body = getattr(node, 'body', [])
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                        and isinstance(body[0].value.value, str):
                    self.docstrings.add(id(body[0].value))

    def is_build(self, node, depth=0):
        """Can this path expression be shown to lie under build/?"""
        if depth > 8:
            return False
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            v = node.value.replace('\\', '/')
            return v == 'build' or v.startswith('build/') or '/build/' in v
        if isinstance(node, ast.Name):
            vals = self.assigned.get(node.id)
            return bool(vals) and all(self.is_build(v, depth + 1) for v in vals)
        if isinstance(node, ast.Call):
            f = node.func
            name = f.attr if isinstance(f, ast.Attribute) else getattr(f, 'id', '')
            if name == 'join':
                # os.path.join(ROOT, 'build', ...) or os.path.join(<build path>, ...)
                return any(self.is_build(a, depth + 1) for a in node.args[:2])
            if name in ('dirname', 'abspath', 'realpath') and node.args:
                return False          # dirname of a build path may be build/ itself, or above it
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
            return self.is_build(node.left, depth + 1)
        return False

    def visit_Constant(self, node):
        if isinstance(node.value, str) and id(node) not in self.docstrings:
            for m in re.finditer(r'\bgit\s+((?:[-\w+.]+\s*){1,4})', node.value):
                why = git_finding(m.group(1).split())
                if why:
                    self.findings.append((node.lineno, '%s in a string' % why))

    def _list(self, node):
        words = _strs(node.elts)
        if words and words[0] == 'git':
            why = git_finding(words[1:])
            if why:
                self.findings.append((node.lineno, why))
        if words and words[0] in ('rm', 'unlink', 'rmdir'):
            targets = [e for e, w in zip(node.elts[1:], words[1:]) if not (w or '').startswith('-')]
            if not targets or not all(self.is_build(e) for e in targets):
                self.findings.append((node.lineno, '`%s` on a path not under build/' % words[0]))
        self.generic_visit(node)

    visit_List = _list
    visit_Tuple = _list

    def visit_Call(self, node):
        f = node.func
        # git(root, 'reset', ...) / G.git(ROOT, ...): the helper in refresh_git.py
        fname = f.attr if isinstance(f, ast.Attribute) else getattr(f, 'id', '')
        if fname == 'git' and len(node.args) > 1:
            why = git_finding(_strs(node.args[1:]))
            if why:
                self.findings.append((node.lineno, why))
        if isinstance(f, ast.Attribute):
            owner = f.value.id if isinstance(f.value, ast.Name) else ''
            if (owner, f.attr) in PY_DELETE or (f.attr in PY_DELETE_ATTR and (owner, f.attr) not in PY_DELETE
                                                 and owner not in ('os', 'shutil')):
                target = node.args[0] if node.args else f.value
                if not self.is_build(target):
                    self.findings.append((node.lineno, '%s.%s on a path not shown to be under build/'
                                          % (owner or '<obj>', f.attr)))
        self.generic_visit(node)


def scan_python(text):
    tree = ast.parse(text)
    s = PyScan(tree)
    s.visit(tree)
    return s.findings


# ----------------------------------------------------------------------------- shell
def _strip_comment(line):
    out, q = [], None
    for i, ch in enumerate(line):
        if q:
            if ch == q:
                q = None
        elif ch in '"\'':
            q = ch
        elif ch == '#' and (i == 0 or line[i - 1].isspace()):
            break
        out.append(ch)
    return ''.join(out)


def scan_shell(text):
    findings = []
    lines = [_strip_comment(ln) for ln in text.splitlines()]
    assigned = {}
    for ln in lines:
        m = re.match(r'\s*(?:export\s+)?([A-Za-z_]\w*)=(.*)$', ln)
        if m:
            assigned.setdefault(m.group(1), []).append(m.group(2))

    def is_build(word):
        w = word.strip('"\'')
        if '/build/' in w or w.startswith('build/'):
            return True
        m = re.fullmatch(r'\$\{?([A-Za-z_]\w*)\}?', w)
        return bool(m) and bool(assigned.get(m.group(1))) and all(
            '/build/' in v or v.strip('"\'').startswith('build/') for v in assigned[m.group(1)])

    for n, ln in enumerate(lines, 1):
        for m in re.finditer(r'\bgit\s+((?:[^\s;&|)]+\s*){1,6})', ln):
            why = git_finding(m.group(1).split())
            if why:
                findings.append((n, why))
        for m in re.finditer(r'(?:^|[;&|(]|\bthen|\bdo|\belse)\s*(rm|unlink|rmdir)\s+([^;&|]*)', ln):
            targets = [w for w in m.group(2).split() if not w.startswith('-')]
            if not targets or not all(is_build(t) for t in targets):
                findings.append((n, '`%s` on a path not under build/' % m.group(1)))
    return findings


def scan(rel, text):
    return scan_shell(text) if rel.endswith('.sh') else scan_python(text)


# ----------------------------------------------------------------------------- self test
# EVERY BANNED FORM, AND THE CHECK MUST CATCH EACH. A check that has never failed is a check
# nobody knows works -- the athletics verifier passed for weeks on a sentence that was wrong.
MUST_CATCH = [
    ('x.sh', 'git reset --hard origin/main'), ('x.sh', 'git clean -fd'),
    ('x.sh', 'git stash push -u'), ('x.sh', 'git checkout -- sources/data/a.csv'),
    ('x.sh', 'git checkout main'), ('x.sh', 'git push -q -f origin x:x'),
    ('x.sh', 'git push --force origin HEAD:main'), ('x.sh', 'git branch -f saved HEAD'),
    ('x.sh', 'git rebase --abort'), ('x.sh', 'git restore sources/x.csv'),
    ('x.sh', 'rm -rf sources/data'), ('x.sh', 'if true; then rm -f "$X"; fi'),
    ('x.py', "subprocess.run(['git', 'reset', '-q', '--hard', 'HEAD'])"),
    ('x.py', "subprocess.run(['git', 'push', 'origin', '+HEAD:main'])"),
    ('x.py', "git(root, 'stash', 'push')"), ('x.py', "G.git(ROOT, 'clean', '-fd')"),
    ('x.py', "os.system('git checkout -- x')"),
    ('x.py', "os.remove(os.path.join(ROOT, 'sources', 'x.csv'))"),
    ('x.py', "P = os.path.join(ROOT, 'fy28')\nshutil.rmtree(P)"),
    ('x.py', "pathlib.Path('sources/x').unlink()"),
    ('x.py', "subprocess.run(['rm', '-f', path])"),
]
MUST_PASS = [
    ('x.sh', 'X="$HERE/build/refresh-ALERT.txt"\nrm -f "$X"'),
    ('x.sh', '# git reset --hard was removed on 9 October'),
    ('x.sh', 'git push -q origin HEAD:main'), ('x.sh', 'git worktree add --detach build/t HEAD'),
    ('x.py', "A = os.path.join(ROOT, 'build', 'a.txt')\nos.remove(A)"),
    ('x.py', 'def f():\n    """`git reset --hard` used to live here."""\n'),
    ('x.py', "git(root, 'push', '-q', remote, 'x:refs/heads/main')"),
    ('x.py', "os.replace(tmp, MEETINGS_INDEX)"),
]


def selftest():
    bad = 0
    for rel, text in MUST_CATCH:
        if not scan(rel, text):
            bad += 1
            print('  SELFTEST MISSED  %s' % text.replace('\n', ' | '))
    for rel, text in MUST_PASS:
        got = scan(rel, text)
        if got:
            bad += 1
            print('  SELFTEST FALSE ALARM  %s -> %s' % (text.replace('\n', ' | '), got))
    print('selftest: %d of %d banned forms caught, %d of %d safe forms passed'
          % (len(MUST_CATCH) - sum(1 for r, t in MUST_CATCH if not scan(r, t)), len(MUST_CATCH),
             len(MUST_PASS) - sum(1 for r, t in MUST_PASS if scan(r, t)), len(MUST_PASS)))
    return bad


def main():
    bad = selftest() if '--selftest' in sys.argv else 0
    findings = []
    for rel in FILES:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            findings.append((rel, 0, 'missing -- the check cannot vouch for a file it cannot read'))
            continue
        for line, why in scan(rel, open(path, encoding='utf-8').read()):
            findings.append((rel, line, why))
    for rel, line, why in findings:
        print('  DESTRUCTIVE  %s:%d  %s' % (rel, line, why))
    if findings or bad:
        print('the refresh has %d destructive path(s); it must only ever add' % len(findings))
        return 1
    print('ok: no destructive path in %d refresh files' % len(FILES))
    return 0


if __name__ == '__main__':
    sys.exit(main())
