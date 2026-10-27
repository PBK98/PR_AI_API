"""분석할 변경을 선택하고 커밋 메시지·PR 초안을 생성해 출력한다."""

import argparse

from .commit_actions import confirm_commit, confirm_file_commits
from .git_client import collect_file_diffs


def handle_generation(cli_args: argparse.Namespace, git_status: str, staged_diff: str,
                      unstaged_diff: str, staged_snapshot: str) -> int:
    """분석할 변경을 선택하고 명령별 처리로 전달한다."""
    # 스테이징한 변경을 우선 사용하고, 없을 때만 스테이징 전 변경을 사용한다.
    # 두 diff를 합치지 않으므로 메시지가 어느 변경을 설명하는지 명확해진다.
    if staged_diff:
        selected_diff = staged_diff
        change_source = "스테이징한 변경"
    else:
        selected_diff = unstaged_diff
        change_source = "스테이징 전 변경"
    if not selected_diff.strip():
        print("[INFO] 생성할 diff가 없습니다. 새 파일은 git add 후 실행하세요.")
        return 0
    if any(line.startswith("?? ") for line in git_status.splitlines()):
        print("[INFO] 미추적 파일은 제외됩니다. 새 파일은 git add 후 실행하세요.")
    print("[INFO] 생성 대상: " + change_source)
    if cli_args.command == "pr":
        return handle_pr(cli_args, selected_diff)
    return handle_commit(cli_args, selected_diff, bool(staged_diff), staged_snapshot)


def handle_pr(cli_args: argparse.Namespace, selected_diff: str) -> int:
    """PR 초안을 생성하고 제목과 본문을 출력한다."""
    # AI 기능을 사용할 때만 불러와 단순 Git 상태 확인에는 API 의존성이 필요 없게 한다.
    from .ai_client import generate_pr

    pr_title, pr_body = generate_pr(
        selected_diff,
        model=cli_args.model,
        temperature=cli_args.temperature,
        max_tokens=cli_args.max_tokens,
        safe_mode=cli_args.safe_mode,
    )
    print("\n--- PR Title ---")
    print(pr_title)
    print("\n--- PR Body ---")
    print(pr_body)
    print("----------------------")
    return 0


def handle_commit(cli_args: argparse.Namespace, selected_diff: str, use_staged_diff: bool, staged_snapshot: str) -> int:
    """커밋 메시지를 생성하고 선택적으로 확인 후 적용한다."""
    # selected_diff는 분석할 변경 내용, use_staged_diff는 파일별 조회 기준이다.
    # staged_snapshot은 --apply에서 생성 당시 스테이징 상태를 재검증할 때 사용한다.
    if cli_args.per_file:
        return handle_file_commits(cli_args, use_staged_diff, staged_snapshot)

    from .ai_client import generate_commit

    commit_message = generate_commit(
        selected_diff,
        model=cli_args.model,
        temperature=cli_args.temperature,
        max_tokens=cli_args.max_tokens,
        safe_mode=cli_args.safe_mode,
    )
    # 생성된 메시지를 먼저 보여 주고, --apply가 있을 때만 커밋 확인 단계로 넘어간다.
    print("\n--- Commit Message ---")
    print(commit_message)
    print("----------------------")
    if cli_args.apply:
        return confirm_commit(commit_message, staged_snapshot)
    return 0


def handle_file_commits(cli_args: argparse.Namespace, use_staged_diff: bool, staged_snapshot: str) -> int:
    """파일별 diff로 메시지를 생성하고, --apply가 있으면 확인 후 각각 커밋한다."""
    from .ai_client import generate_file_commits

    file_diffs = collect_file_diffs(staged=use_staged_diff)
    commit_messages = generate_file_commits(
        file_diffs,
        model=cli_args.model,
        temperature=cli_args.temperature,
        max_tokens=cli_args.max_tokens,
        safe_mode=cli_args.safe_mode,
    )
    print("\n--- Commit Messages by File ---")
    for file_path, commit_message in commit_messages.items():
        print(f"\n파일: {file_path!r}\n{commit_message}")
    print("----------------------")
    if cli_args.apply:
        return confirm_file_commits(commit_messages, staged_snapshot)
    return 0
