"""사용자 명령을 읽고 Git 상태 확인과 생성 작업을 연결하는 진입점."""

import sys
from pathlib import Path

from .cli import build_parser, validate_args
from .commands import handle_generation
from .git_client import read_staged_snapshot, run_git


def main() -> int:
    """인자 검증 → Git 상태 수집 → 명령 실행. 반환값 0은 정상 종료, 1은 처리 실패다."""
    # 1. 명령과 옵션을 읽고 사용할 수 있는 조합인지 확인한다.
    parser = build_parser()
    cli_args = parser.parse_args()
    validate_args(parser, cli_args)

    # .git 파일을 사용하는 worktree도 허용한다.
    if not Path(".git").exists():
        print("[ERROR] Git 프로젝트의 루트 디렉터리에서 실행하세요.", file=sys.stderr)
        return 1

    # 2. Git 상태와 두 종류의 변경 내용을 읽는다.
    staged_snapshot = ""
    try:
        git_status = run_git("status", "--short", "--untracked-files=all")
        if not git_status.strip():
            print("[INFO] 변경 사항이 없습니다.")
            return 0

        # unstaged_diff: 작업 파일과 인덱스의 차이. staged_diff: 인덱스와 HEAD의 차이.
        # 인덱스는 git add로 다음 커밋에 포함할 내용을 모아 둔 영역이다.
        unstaged_diff = run_git("diff", "--no-ext-diff", "--no-textconv")
        staged_diff = run_git("diff", "--cached", "--no-ext-diff", "--no-textconv")
        # 3. 실제 커밋을 요청했다면 스테이징된 내용의 비교용 원본을 보관한다.
        if cli_args.apply:
            if not staged_diff.strip():
                print("[ERROR] 커밋할 파일을 먼저 git add로 스테이징하세요.", file=sys.stderr)
                return 1
            # 실제 적용 직전에 비교할 원본을 보관한다. 바이너리 변경 내용도 포함한다.
            staged_snapshot = read_staged_snapshot()

        # 4. 생성 명령이 있으면 해당 작업을 실행한다. 없으면 아래에서 상태만 출력한다.
        if cli_args.command in ("commit", "pr"):
            try:
                return handle_generation(cli_args, git_status, staged_diff, unstaged_diff, staged_snapshot)
            except ImportError:
                print("[ERROR] python -m pip install -r requirements.txt 를 먼저 실행하세요.", file=sys.stderr)
                return 1
    except (OSError, RuntimeError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    show_changes(git_status, staged_diff, unstaged_diff)
    return 0


def show_changes(git_status: str, staged_diff: str, unstaged_diff: str) -> None:
    """수집한 Git 상태와 두 종류의 diff를 출력한다."""
    print("--- 변경된 파일 (git status) ---")
    print(git_status, end="")
    print("\n--- 스테이징 전 변경 (git diff) ---")
    print(unstaged_diff or "변경 내용이 없습니다.")
    print("--- 스테이징한 변경 (git diff --cached) ---")
    print(staged_diff or "변경 내용이 없습니다.")
    if any(line.startswith("?? ") for line in git_status.splitlines()):
        print("[INFO] 새 미추적 파일은 목록에만 표시됩니다. 내용을 확인하려면 해당 파일을 git add 하세요.")
