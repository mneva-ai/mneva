"""Git provenance detection.

Answers "which repo, branch, and commit was this memory captured against".
`repo` is the filter key and must survive being cloned to another machine, so
it is derived from the remote URL rather than the local path.

Everything here degrades to ``None`` rather than raising. Capture must never
fail because git is missing, slow, or pointed at a directory that is not a
repository.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

# git can block for a long time on network-mounted working trees. Capture is
# interactive, so bound it hard rather than letting the user wait.
_TIMEOUT_S = 5.0


@dataclass(frozen=True, slots=True)
class GitContext:
    """Git provenance for a captured record.

    `repo` is the only field used for filtering. `repo_path` is a local hint
    only: it is machine-specific and does not survive a clone.
    """

    repo: str
    repo_path: str
    branch: str | None
    commit_sha: str | None


def normalize_remote_url(raw: str) -> str:
    """Fold the many spellings of one remote into a single identity.

    ``git@github.com:Org/Repo.git``, ``https://github.com/org/repo``, and
    ``ssh://git@github.com/org/repo.git`` all collapse to
    ``github.com/org/repo``.

    Case is folded deliberately: this value is a filter key, and
    ``github.com/Foo/Bar`` vs ``github.com/foo/bar`` are the same repository.
    A case mismatch would silently drop records from the default filter, which
    is exactly the failure mode this field exists to prevent.
    """
    url = raw.strip()
    # 1. Strip the scheme, remembering whether there was one. Only a
    #    scheme-less remote can be scp-like, and conflating the two makes
    #    `https://user:token@host/...` parse as host=user, path=token@host/...
    stripped = re.sub(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", "", url)
    had_scheme = stripped != url
    url = stripped
    # 2. Strip userinfo. Bounded to the first path segment so an '@' inside a
    #    path (host/org/re@po) is left alone.
    url = re.sub(r"^[^/]*@", "", url)
    # 3. scp-like form (git@host:org/repo) puts the path after a colon.
    if not had_scheme:
        head, sep, tail = url.partition(":")
        if sep and "/" not in head:
            url = f"{head}/{tail}"
    url = url.rstrip("/")
    if url.endswith(".git"):
        url = url[: -len(".git")]
    return url.lower()


def as_record_fields(ctx: GitContext | None) -> dict[str, str | None]:
    """Spread a GitContext into Record kwargs. Empty dict when there is none.

    Lets every capture path (CLI, MCP, HTTP, distill) build a Record the same
    way without each one repeating the four field names.
    """
    if ctx is None:
        return {}
    return {
        "repo": ctx.repo,
        "repo_path": ctx.repo_path,
        "branch": ctx.branch,
        "commit_sha": ctx.commit_sha,
    }


def _run(args: list[str], *, cwd: Path) -> str | None:
    """Run a git command, returning stripped stdout or None on any failure."""
    try:
        # S603/S607: `args` is always an internal literal list -- no user input
        # reaches the command itself, and shell=False means `cwd` cannot be
        # interpreted as anything but a directory. Resolving git's absolute
        # path would break portability across the platforms we ship on.
        proc = subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_S,
        )
    except (OSError, subprocess.SubprocessError):
        # OSError covers git-not-installed (FileNotFoundError) and unreadable
        # cwd; SubprocessError covers TimeoutExpired.
        return None
    if proc.returncode != 0:
        return None
    out = proc.stdout.strip()
    return out or None


def detect(start: Path | None = None) -> GitContext | None:
    """Detect git provenance for *start* (default: current directory).

    Returns ``None`` when *start* is not inside a git repository, when git is
    unavailable, or when git fails for any other reason.
    """
    cwd = Path(start) if start is not None else Path.cwd()
    if not cwd.is_dir():
        return None

    toplevel = _run(["rev-parse", "--show-toplevel"], cwd=cwd)
    if toplevel is None:
        return None
    # git prints forward slashes even on Windows; resolve() also settles the
    # macOS /var -> /private/var symlink so paths compare equal.
    repo_path = Path(toplevel).resolve()

    remote = _run(["config", "--get", "remote.origin.url"], cwd=cwd)
    repo = normalize_remote_url(remote) if remote else f"local:{repo_path.name}"

    branch = _run(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    if branch == "HEAD":
        # Detached HEAD: there is no branch to record.
        branch = None

    # Fails in a repository with no commits yet; identity is still valid.
    commit_sha = _run(["rev-parse", "HEAD"], cwd=cwd)

    return GitContext(
        repo=repo,
        repo_path=str(repo_path),
        branch=branch,
        commit_sha=commit_sha,
    )
