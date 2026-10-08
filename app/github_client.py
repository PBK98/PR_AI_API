"""확인 후 브랜치를 push하고 GitHub PR을 생성한다."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from .git_client import run_git


@dataclass(frozen=True)
class PRPlan:
    repo: str
    remote_url: str
    branch: str
    base: str
    head: str
    diff: str


def run_gh(*args: str) -> str:
    if not shutil.which('gh'):
        raise RuntimeError('GitHub CLI가 없습니다. brew install gh 후 gh auth login을 실행하세요.')
    result = subprocess.run(['gh', *args], capture_output=True, text=True,
                            env=dict(os.environ, GH_PROMPT_DISABLED='1'))
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or 'GitHub CLI 실행 실패: gh auth login을 확인하세요.')
    return result.stdout


def existing_pr(repo: str, branch: str, base: str) -> str | None:
    prs = json.loads(run_gh('pr', 'list', '--repo', repo, '--head', branch,
                           '--base', base, '--state', 'open', '--json', 'url'))
    return prs[0]['url'] if prs else None


def prepare_pr(base: str | None) -> PRPlan:
    if run_git('status', '--porcelain').strip():
        raise RuntimeError('PR을 올리기 전에 변경 파일을 모두 커밋하거나 정리하세요.')
    branch = run_git('branch', '--show-current').strip()
    if not branch:
        raise RuntimeError('detached HEAD에서는 PR을 만들 수 없습니다. 작업 브랜치로 이동하세요.')
    url = run_git('remote', 'get-url', '--push', 'origin').strip()
    match = re.fullmatch(r'(?:https://github\.com/|git@github\.com:)([^/]+/[^/]+?)(?:\.git)?', url)
    if not match:
        raise RuntimeError('origin의 push 주소는 github.com의 HTTPS 또는 SSH 저장소여야 합니다.')
    repo = match.group(1)
    info = json.loads(run_gh('repo', 'view', repo, '--json', 'defaultBranchRef'))
    base = base or (info.get('defaultBranchRef') or {}).get('name')
    if not base:
        raise RuntimeError('기준 브랜치를 찾을 수 없습니다. --base를 지정하세요.')
    run_git('check-ref-format', '--branch', base)
    if branch == base:
        raise RuntimeError('현재 브랜치와 기준 브랜치가 같습니다. 작업 브랜치에서 실행하세요.')
    found = existing_pr(repo, branch, base)
    if found:
        raise RuntimeError(f'이미 열린 PR이 있습니다: {found}')
    # 실제 push 대상에서 기준 브랜치를 읽어 온다. 로컬 작업 브랜치는 변경하지 않는다.
    run_git('fetch', '--no-tags', url, f'refs/heads/{base}')
    base_sha = run_git('rev-parse', 'FETCH_HEAD').strip()
    head = run_git('rev-parse', 'HEAD').strip()
    diff = run_git('diff', '--no-ext-diff', '--no-textconv', f'{base_sha}...{head}', '--')
    if not diff.strip():
        raise RuntimeError('기준 브랜치와 비교해 PR에 포함할 변경이 없습니다.')
    return PRPlan(repo, url, branch, base, head, diff)


def publish_pr(plan: PRPlan, title: str, body: str) -> str:
    if (run_git('branch', '--show-current').strip() != plan.branch
            or run_git('rev-parse', 'HEAD').strip() != plan.head
            or run_git('status', '--porcelain').strip()
            or run_git('remote', 'get-url', '--push', 'origin').strip() != plan.remote_url):
        raise RuntimeError('초안 생성 후 브랜치/커밋/작업 상태/원격 주소가 바뀌었습니다. 다시 실행하세요.')
    found = existing_pr(plan.repo, plan.branch, plan.base)
    if found:
        raise RuntimeError(f'이미 열린 PR이 있습니다: {found}')
    # 검토한 커밋만 명시한 브랜치로 push한다. force push는 하지 않는다.
    run_git('push', plan.remote_url, f'{plan.head}:refs/heads/{plan.branch}')
    with tempfile.TemporaryDirectory(prefix='ai-pr-') as directory:
        path = Path(directory, 'body.md')
        path.write_text(body, encoding='utf-8')
        try:
            return run_gh('pr', 'create', '--repo', plan.repo, '--base', plan.base,
                          '--head', plan.branch, '--title', title, '--body-file', str(path)).strip()
        except RuntimeError as exc:
            raise RuntimeError(f'브랜치는 push됐지만 PR 생성 확인에 실패했습니다. GitHub에서 생성 여부를 확인하세요. {exc}') from None
