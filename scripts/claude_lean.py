"""THE ONE PLACE a scripted `claude -p` call is built. Every script that spawns `claude`
goes through here, so the call starts with the least context it can.

WHY. Run from the repo, a one-word prompt carries CLAUDE.md, the memory index, the project
settings and every MCP server into the first turn. Measured 29 October 2026, haiku, one-word
prompt, `--tools Read`, cache-creation tokens:

    from the repo, no other flags                         82,615 tokens   $0.0165
    + --setting-sources "" --strict-mcp-config             5,134 tokens   $0.0010
    + cwd = an empty scratch directory                    ~1,700 tokens   $0.00014

WHAT IT ADDS. `--setting-sources ""` (no CLAUDE.md, settings, hooks), `--strict-mcp-config`
(no MCP servers), `--no-session-persistence` (unless session=True), `--add-dir` for each
directory the call must READ, and a cwd that is an empty directory under build/.

WHAT IT DOES NOT DO. `--bare` is not used: it refuses OAuth and this account is a Max
login. Because settings no longer load, a caller must pass every permission it needs as a
flag (`--tools`, `--allowedTools`); and a path in a prompt must be ABSOLUTE.

A script that needs the repo's CLAUDE.md or settings does not belong here (generate_report,
triage_refresh); it says so beside its own call.

    import claude_lean
    r = claude_lean.run(['claude', '-p', '--tools', '', ...], input=prompt,
                        capture_output=True, text=True, env=env, timeout=900)
"""
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMPTY_DIR = os.path.join(ROOT, 'build', 'claude-lean-cwd')


def empty_dir():
    """An empty directory, created on demand. Empty matters: the CLI looks at its cwd."""
    os.makedirs(EMPTY_DIR, exist_ok=True)
    return EMPTY_DIR


def argv(args, add_dirs=(), session=False):
    """`args` is a full command starting with 'claude'. Our flags go straight after it.
    --add-dir is variadic in the CLI, so it is placed first and is followed by another flag."""
    if not args or os.path.basename(args[0]) != 'claude':
        raise ValueError('claude_lean.argv: expected a command starting with claude')
    out = [args[0]]
    for d in add_dirs:
        out += ['--add-dir', os.path.abspath(str(d))]
    out += ['--setting-sources', '', '--strict-mcp-config']
    if not session:
        out.append('--no-session-persistence')
    return out + list(args[1:])


def run(args, add_dirs=(), session=False, **kw):
    """subprocess.run(argv(...), cwd=<empty dir>, **kw). A cwd passed by the caller is
    ignored: a repo cwd is exactly what this exists to avoid."""
    kw.pop('cwd', None)
    return subprocess.run(argv(args, add_dirs, session), cwd=empty_dir(), **kw)
