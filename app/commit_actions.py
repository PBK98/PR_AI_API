"""사용자 확인과 스테이징 검증을 거쳐 실제 커밋을 수행한다."""

import sys

from .git_client import (
    commit_staged_file,
    read_staged_file_patch,
    read_staged_snapshot,
    run_git,
)


def confirm_commit(commit_message: str, expected_staged_diff: str) -> int:
    """검토 후 명시적으로 확인한 경우에만 현재 인덱스를 커밋한다."""
    if not ask_confirmation("이 메시지로 스테이징된 변경을 커밋할까요? [y/N] "):
        return 0
    try:
        # AI 응답을 기다리는 동안 사용자가 git add를 다시 했을 수 있다.
        # 생성 당시의 변경과 비교해 메시지와 실제 커밋 내용이 달라지는 것을 막는다.
        verify_staged_changes(expected_staged_diff)
        commit_output = run_git("commit", "-m", commit_message)
    except (OSError, RuntimeError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    print("[DONE] 커밋을 완료했습니다.")
    print(commit_output, end="")
    return 0


def confirm_file_commits(commit_messages: dict[str, str], expected_staged_diff: str) -> int:
    """파일별 메시지를 확인받고 순서대로 커밋한다. 중단 시 완료된 커밋은 유지한다."""
    if not ask_confirmation(f"위 {len(commit_messages)}개 파일을 각각 별도 커밋할까요? [y/N] "):
        return 0
    completed_count = 0
    try:
        verify_staged_changes(expected_staged_diff)
        # 커밋마다 HEAD가 바뀌므로 파일별 patch를 미리 기록해 비교한다.
        expected_file_patches = {}
        for file_path in commit_messages:
            expected_file_patches[file_path] = read_staged_file_patch(file_path)
        for file_path, commit_message in commit_messages.items():
            current_file_patch = read_staged_file_patch(file_path)
            if current_file_patch != expected_file_patches[file_path]:
                raise RuntimeError(f"{file_path!r}: 스테이징 내용이 바뀌었습니다.")
            commit_output = commit_staged_file(file_path, commit_message)
            completed_count += 1
            print(f"[DONE] {file_path!r} 커밋 완료")
            print(commit_output, end="")
    except (OSError, RuntimeError, KeyboardInterrupt) as exc:
        print(f"[ERROR] 파일별 커밋 중단: {exc} (완료 {completed_count}/{len(commit_messages)})", file=sys.stderr)
        print("[INFO] 완료된 커밋은 유지됩니다. git status와 git log를 확인하세요.")
        return 1
    return 0


def ask_confirmation(question: str) -> bool:
    """명시적인 y만 승인으로 처리하며 입력 중단도 취소로 안내한다."""
    try:
        user_answer = input(question)
    except (EOFError, KeyboardInterrupt):
        print("\n[INFO] 커밋을 취소했습니다.")
        return False
    if user_answer.strip().lower() != "y":
        print("[INFO] 커밋을 취소했습니다.")
        return False
    return True


def verify_staged_changes(expected_staged_diff: str) -> None:
    """메시지 생성 당시와 스테이징 내용이 다르면 커밋을 중단한다."""
    if read_staged_snapshot() != expected_staged_diff:
        raise RuntimeError("메시지 생성 중 스테이징 내용이 바뀌었습니다. 다시 실행하세요.")
