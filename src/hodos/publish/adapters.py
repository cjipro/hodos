"""
hodos.publish.adapters — pluggable publish destinations

Abstracts *where* rendered output (HTML, JSON, or any text/binary
artifact) ends up, so the code that renders content never needs to know
whether the destination is a local directory, a GitHub Pages branch, or
nowhere at all (dry runs, tests). Swap destinations by changing
configuration, not by editing the code that produces the content.

This is the first module extracted from a private production system
(a daily customer-intelligence pipeline that has been pushing rendered
briefings to GitHub Pages on a cron since 2026-04) into Hodos. It has
had one deny-list feature stripped out on the way here: the private
system refuses to publish paths matching its own internal deny-list
(auth code, secrets, its own proprietary ledger). That deny-list was
tenant-specific and doesn't belong in a general-purpose engine — but
the *pattern* is worth keeping, so `GitHubPagesAdapter` still accepts
an optional `deny_patterns` argument if you want the same defense in
your own deployment.

Adapters:
    NullAdapter                        — no-op, useful for dry runs and tests
    LocalAdapter(root_dir)             — writes to a filesystem path
    GitHubPagesAdapter(repo_url, token, ...) — clone, write, commit, push

Contract:
    adapter.publish(relative_path, content) -> (ok: bool, message: str)
        relative_path   e.g. "reports/2026-09-13/index.html"
        content         str (text) or bytes (binary assets)
        ok              True on success (including "nothing to commit")
        message         human-readable outcome or error description

Credentials (GitHub token) are read from the environment, never from a
config file, so config can be committed without leaking secrets.
"""
from __future__ import annotations

import logging
import os
import re
import subprocess
import tempfile
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_COMMIT_SUBJECT = "publish: {path} {ts}"


# ── LF-safe writes ────────────────────────────────────────────────────────

def write_text_lf(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Write text with LF-only line endings, regardless of host OS.

    Default `Path.write_text` on Windows translates ``\\n`` to ``\\r\\n``.
    If you ever need to verify "what I pushed is what's being served" by
    comparing a checksum of a local copy against the remote file, that
    comparison only holds if both sides use the same line endings — most
    static hosts (GitHub Pages included) normalise to LF. Every adapter
    that writes text uses this helper so a local copy and the pushed copy
    are byte-identical.
    """
    normalised = content.replace("\r\n", "\n").replace("\r", "\n")
    # Writing bytes (rather than text with newline="\n", which needs
    # Python 3.10+) keeps this portable down to the declared 3.9 floor.
    path.write_bytes(normalised.encode(encoding))


def _is_binary(content: str | bytes) -> bool:
    return isinstance(content, (bytes, bytearray))


# ── Base ──────────────────────────────────────────────────────────────────

class PublishAdapter(ABC):
    """Common interface every publish destination implements."""

    @abstractmethod
    def publish(self, relative_path: str, content: str | bytes) -> tuple[bool, str]:
        """Publish `content` at `relative_path`. Returns (ok, message).

        `content` is `str` for text (HTML/CSS/JSON/etc — gets LF
        normalisation) and `bytes` for binary assets (images, fonts —
        written unchanged). Every adapter must handle both.
        """


# ── Null (no-op) — dry runs, tests ─────────────────────────────────────────

class NullAdapter(PublishAdapter):
    """Does nothing. Logs what it would have done."""

    def publish(self, relative_path: str, content: str | bytes) -> tuple[bool, str]:
        logger.info("[publish] NullAdapter — would publish %d bytes to %s",
                    len(content), relative_path)
        return True, f"null: {relative_path} ({len(content)} bytes)"


# ── Local filesystem ────────────────────────────────────────────────────────

class LocalAdapter(PublishAdapter):
    """Writes to a directory on disk. Useful for local dev and demos."""

    def __init__(self, root_dir: str | Path):
        self.root = Path(root_dir).expanduser().resolve()

    def publish(self, relative_path: str, content: str | bytes) -> tuple[bool, str]:
        dest = self.root / relative_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        if _is_binary(content):
            dest.write_bytes(content)
        else:
            write_text_lf(dest, content)
        logger.info("[publish] LocalAdapter wrote %d bytes to %s", len(content), dest)
        return True, f"local: {dest}"


# ── GitHub Pages ────────────────────────────────────────────────────────────

class GitHubPagesAdapter(PublishAdapter):
    """Clone, write, commit, push. Shallow clone (depth=1) of the target branch.

    Optionally accepts `deny_patterns` — compiled regexes checked against
    every `relative_path` before anything is written. Use this if your
    deployment publishes to a public repo and wants a defense-in-depth
    refusal for paths that should never reach it (source code, secrets,
    internal docs). Empty by default — bring your own list; this engine
    doesn't ship an opinion about what's sensitive in your deployment.
    """

    def __init__(self, repo_url: str, token: str,
                 branch: str = "main",
                 commit_subject_fmt: str = _DEFAULT_COMMIT_SUBJECT,
                 committer_email: str | None = None,
                 committer_name: str | None = None,
                 deny_patterns: tuple[re.Pattern, ...] = ()):
        if not repo_url:
            raise ValueError("GitHubPagesAdapter: repo_url is required")
        if not token:
            raise ValueError("GitHubPagesAdapter: token is required")
        self._repo_url = repo_url
        self._token = token
        self._branch = branch
        self._msg_fmt = commit_subject_fmt
        self._email = committer_email or _git_config("user.email") or "hodos@localhost"
        self._name = committer_name or _git_config("user.name") or "hodos"
        self._deny_patterns = deny_patterns

    def _auth_url(self) -> str:
        if self._repo_url.startswith("https://"):
            return self._repo_url.replace("https://", f"https://{self._token}@")
        slug = self._repo_url.rstrip("/")
        if not slug.endswith(".git"):
            slug += ".git"
        return f"https://{self._token}@github.com/{slug}"

    def _scrub(self, text: str) -> str:
        return text.replace(self._token, "***") if text else text

    def _assert_publishable(self, relative_path: str) -> None:
        for pat in self._deny_patterns:
            if pat.search(relative_path):
                raise ValueError(
                    f"refusing to publish '{relative_path}' "
                    f"(matched deny pattern {pat.pattern!r})"
                )

    def publish(self, relative_path: str, content: str | bytes) -> tuple[bool, str]:
        self._assert_publishable(relative_path)

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        commit_msg = self._msg_fmt.format(path=relative_path, ts=ts)

        with tempfile.TemporaryDirectory() as tmpdir:
            clone_dir = Path(tmpdir) / "pages_repo"

            logger.info("[publish] cloning %s (branch=%s)", self._repo_url, self._branch)
            r = subprocess.run(
                ["git", "clone", "--depth=1", "--branch", self._branch,
                 self._auth_url(), str(clone_dir)],
                capture_output=True, text=True, timeout=60,
            )
            if r.returncode != 0:
                return False, f"git clone failed: {self._scrub(r.stderr.strip())}"

            dest = clone_dir / relative_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            if _is_binary(content):
                dest.write_bytes(content)
            else:
                write_text_lf(dest, content)

            for cmd in (
                ["git", "-C", str(clone_dir), "config", "user.email", self._email],
                ["git", "-C", str(clone_dir), "config", "user.name", self._name],
            ):
                subprocess.run(cmd, capture_output=True)

            r = subprocess.run(
                ["git", "-C", str(clone_dir), "add", relative_path],
                capture_output=True, text=True,
            )
            if r.returncode != 0:
                return False, f"git add failed: {r.stderr.strip()}"

            r = subprocess.run(
                ["git", "-C", str(clone_dir), "commit", "-m", commit_msg],
                capture_output=True, text=True,
            )
            if r.returncode != 0:
                combined = (r.stderr + r.stdout).strip()
                if "nothing to commit" in combined:
                    return True, f"nothing to commit — {relative_path} up to date"
                return False, f"git commit failed: {combined}"

            r = subprocess.run(
                ["git", "-C", str(clone_dir), "push", "origin", self._branch],
                capture_output=True, text=True, timeout=60,
            )
            if r.returncode != 0:
                return False, f"git push failed: {self._scrub(r.stderr.strip())}"

        return True, commit_msg


def _git_config(key: str) -> str | None:
    try:
        r = subprocess.run(["git", "config", "--get", key],
                            capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or None
    except Exception:
        return None


# ── Factory ─────────────────────────────────────────────────────────────────

def get_adapter(config: dict | None = None) -> PublishAdapter:
    """Construct an adapter from a plain dict (your own config format).

    Expected shape:
        {"adapter": "null"}
        {"adapter": "local", "local": {"root_dir": "./published"}}
        {"adapter": "github_pages", "github_pages": {
            "repo_url": "...", "branch": "main"}}
        (GitHub token is read from the HODOS_GITHUB_TOKEN env var, never
        from config, so config can be committed safely.)

    Falls back to NullAdapter for an unrecognised or missing adapter type,
    or if github_pages is selected but no token is available — publishing
    should degrade to a safe no-op, never raise, when misconfigured.
    """
    cfg = config or {}
    adapter_type = (cfg.get("adapter") or "null").lower()

    if adapter_type == "github_pages":
        token = os.environ.get("HODOS_GITHUB_TOKEN", "")
        gh = cfg.get("github_pages", {}) or {}
        repo_url = gh.get("repo_url") or os.environ.get("HODOS_PUBLISH_REPO", "")
        if not token or not repo_url:
            logger.warning("[publish] github_pages selected but token/repo_url "
                            "missing — falling back to NullAdapter")
            return NullAdapter()
        return GitHubPagesAdapter(
            repo_url=repo_url,
            token=token,
            branch=gh.get("branch", "main"),
            commit_subject_fmt=gh.get("commit_subject", _DEFAULT_COMMIT_SUBJECT),
            committer_email=gh.get("committer_email"),
            committer_name=gh.get("committer_name"),
        )

    if adapter_type == "local":
        local = cfg.get("local", {}) or {}
        return LocalAdapter(local.get("root_dir", "./published"))

    return NullAdapter()
