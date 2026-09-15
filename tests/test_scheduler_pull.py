"""The 06:55 pull never leaves the repo half-rebased (2026-09-15: a wake sitting's commit was dropped that way)."""

from types import SimpleNamespace

from agent.scheduler import git_pull


class PullGit:
    """Fake git: scripted pull rc; a ``rebase-merge`` marker dir that a failed pull leaves behind."""

    def __init__(self, tmp_path, pull_rc=0, marker_before=False):
        self.calls = []
        self.marker = tmp_path / ".git" / "rebase-merge"
        self.pull_rc = pull_rc
        if marker_before:
            self.marker.mkdir(parents=True)

    def __call__(self, repo_dir, *args, check=True, **kw):
        self.calls.append(args)
        if args[:2] == ("rev-parse", "--git-path"):
            p = self.marker if args[2] == "rebase-merge" else self.marker.parent / "rebase-apply"
            return SimpleNamespace(stdout=str(p) + "\n", stderr="", returncode=0)
        if args[:1] == ("pull",):
            if self.pull_rc:
                self.marker.mkdir(parents=True, exist_ok=True)  # the rebase stops at the conflict
            err = "CONFLICT (content): memory/wiki/skills/README.md" if self.pull_rc else ""
            return SimpleNamespace(stdout="", stderr=err, returncode=self.pull_rc)
        if args == ("rebase", "--abort"):
            self.marker.rmdir()
        return SimpleNamespace(stdout="", stderr="", returncode=0)


def _repo(tmp_path):
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    return repo


def test_pull_clean(tmp_path):
    repo = _repo(tmp_path)
    git = PullGit(repo)
    assert git_pull(repo, git) is True
    assert ("pull", "--rebase", "--quiet") in git.calls
    assert ("rebase", "--abort") not in git.calls


def test_pull_conflict_aborts_the_rebase_it_started_and_tells_her(tmp_path):
    repo = _repo(tmp_path)
    git = PullGit(repo, pull_rc=1)
    notes = []
    assert git_pull(repo, git, notes.append) is False
    assert ("rebase", "--abort") in git.calls
    assert not git.marker.exists()  # back on the branch: the day's commits will not be dropped
    assert len(notes) == 1 and "aborted" in notes[0] and "README.md" in notes[0]


def test_pull_leaves_someone_elses_half_done_rebase_alone(tmp_path):
    repo = _repo(tmp_path)
    git = PullGit(repo, marker_before=True)
    notes = []
    assert git_pull(repo, git, notes.append) is False
    assert ("pull", "--rebase", "--quiet") not in git.calls
    assert ("rebase", "--abort") not in git.calls
    assert git.marker.exists() and notes == []


def test_no_repo_is_a_quiet_false(tmp_path):
    assert git_pull(tmp_path / "missing", PullGit(tmp_path)) is False
