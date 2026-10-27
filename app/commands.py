"""분석할 변경을 선택하고 커밋 메시지·PR 초안을 생성해 출력한다."""

import argparse

from .commit_actions import confirm_commit, confirm_file_commits
from .git_client import collect_file_diffs


def handle_generation(args: argparse.Namespace, status: str, staged: str,
                      unstaged: str, snapshot: str) -> int:
    """분석할 변경을 선택하고 명령별 처리로 전달한다."""
    # 스테이징한 변경을 우선 사용하고, 없을 때만 스테이징 전 변경을 사용한다.
    # 두 diff를 합치지 않으므로 메시지가 어느 변경을 설명하는지 명확해진다.
    diff = staged or unstaged
    if not diff.strip():
        print("[INFO] 생성할 diff가 없습니다. 새 파일은 git add 후 실행하세요.")
        return 0
    if any(line.startswith("?? ") for line in status.splitlines()):
        print("[INFO] 미추적 파일은 제외됩니다. 새 파일은 git add 후 실행하세요.")
    source = "스테이징한 변경" if staged else "스테이징 전 변경"
    print("[INFO] 생성 대상: " + source)
    if args.command == "pr":
        return handle_pr(args, diff)
    return handle_commit(args, diff, bool(staged), snapshot)


def handle_pr(args: argparse.Namespace, diff: str) -> int:
    """PR 초안을 생성하고 제목과 본문을 출력한다."""
    # AI 기능을 사용할 때만 불러와 단순 Git 상태 확인에는 API 의존성이 필요 없게 한다.
    from .ai_client import generate_pr

    title, body = generate_pr(diff, **ai_options(args))
    print("\n--- PR Title ---")
    print(title)
    print("\n--- PR Body ---")
    print(body)
    print("----------------------")
    return 0


def handle_commit(args: argparse.Namespace, diff: str, staged: bool, snapshot: str) -> int:
    """커밋 메시지를 생성하고 선택적으로 확인 후 적용한다."""
    # diff는 전체 변경 문자열이고 staged는 파일별 diff를 읽을 기준을 지정하는 bool이다.
    # snapshot은 --apply에서 생성 당시 스테이징 상태를 재검증할 때만 사용한다.
    if args.per_file:
        return handle_file_commits(args, staged, snapshot)

    from .ai_client import generate_commit

    message = generate_commit(diff, **ai_options(args))
    print("\n--- Commit Message ---")
    print(message)
    print("----------------------")
    if args.apply:
        return confirm_commit(message, snapshot)
    return 0


def handle_file_commits(args: argparse.Namespace, staged: bool, snapshot: str) -> int:
    """파일별 diff로 메시지를 생성하고, --apply가 있으면 확인 후 각각 커밋한다."""
    from .ai_client import generate_file_commits

    files = collect_file_diffs(staged=staged)
    messages = generate_file_commits(files, **ai_options(args))
    print("\n--- Commit Messages by File ---")
    for path, message in messages.items():
        print(f"\n파일: {path!r}\n{message}")
    print("----------------------")
    if args.apply:
        return confirm_file_commits(messages, snapshot)
    return 0


def ai_options(args: argparse.Namespace) -> dict:
    """세 생성 함수가 공유하는 AI 설정만 추린다. **로 펼쳐 이름 있는 인자로 전달한다."""
    return {
        "model": args.model,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "safe_mode": args.safe_mode,
    }
