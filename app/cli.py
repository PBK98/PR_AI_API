"""Git 변경 확인 및 커밋/PR 초안 생성 CLI."""

import argparse
import sys
from pathlib import Path

from .git_client import collect_file_diffs, commit_staged_file, run_git


def confirm_commit(message: str, expected_diff: str) -> int:
    """검토 후 명시적으로 확인한 경우에만 현재 인덱스를 커밋한다."""
    try:
        answer = input("이 메시지로 스테이징된 변경을 커밋할까요? [y/N] ")
    except (EOFError, KeyboardInterrupt):
        print("\n[INFO] 커밋을 취소했습니다.")
        return 0
    if answer.strip().lower() != "y":
        print("[INFO] 커밋을 취소했습니다.")
        return 0
    try:
        current = run_git("diff", "--cached", "--binary", "--no-ext-diff", "--no-textconv")
        if current != expected_diff:
            raise RuntimeError("메시지 생성 중 스테이징 내용이 바뀌었습니다. 다시 실행하세요.")
        output = run_git("commit", "-m", message)
    except (OSError, RuntimeError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    print("[DONE] 커밋을 완료했습니다.")
    print(output, end="")
    return 0


def confirm_file_commits(messages: dict[str, str], expected_diff: str) -> int:
    try:
        answer = input(f"위 {len(messages)}개 파일을 각각 별도 커밋할까요? [y/N] ")
    except (EOFError, KeyboardInterrupt):
        print("\n[INFO] 커밋을 취소했습니다.")
        return 0
    if answer.strip().lower() != "y":
        print("[INFO] 커밋을 취소했습니다.")
        return 0
    completed = 0
    try:
        current = run_git("diff", "--cached", "--binary", "--no-ext-diff", "--no-textconv")
        if current != expected_diff:
            raise RuntimeError("메시지 생성 중 스테이징 내용이 바뀌었습니다. 다시 실행하세요.")
        # 커밋마다 HEAD가 바뀌므로 파일별 patch를 미리 기록해 비교한다.
        patches = {path: run_git("diff", "--cached", "--binary", "--no-renames",
                                "--no-ext-diff", "--no-textconv", "--", ":(literal)" + path)
                   for path in messages}
        for path, message in messages.items():
            current = run_git("diff", "--cached", "--binary", "--no-renames",
                              "--no-ext-diff", "--no-textconv", "--", ":(literal)" + path)
            if current != patches[path]:
                raise RuntimeError(f"{path!r}: 스테이징 내용이 바뀌었습니다.")
            output = commit_staged_file(path, message)
            completed += 1
            print(f"[DONE] {path!r} 커밋 완료")
            print(output, end="")
    except (OSError, RuntimeError, KeyboardInterrupt) as exc:
        print(f"[ERROR] 파일별 커밋 중단: {exc} (완료 {completed}/{len(messages)})", file=sys.stderr)
        print("[INFO] 완료된 커밋은 유지됩니다. git status와 git log를 확인하세요.")
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Git 변경 확인 및 AI 커밋/PR 초안 생성")
    parser.add_argument("command", nargs="?", choices=["commit", "pr"], help="생략하면 Git 변경만 출력")
    parser.add_argument("--model", default="gpt-5-mini")
    parser.add_argument("--temperature", type=float, default=None, help="생략하면 모델 기본값 사용")
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--safe-mode", action="store_true", help="전송 diff를 최대 200줄/20,000자로 제한")
    parser.add_argument("--per-file", action="store_true", help="commit 메시지를 파일별로 생성")
    parser.add_argument("--apply", action="store_true", help="메시지 검토 및 확인 후 스테이징된 변경을 실제 커밋")
    args = parser.parse_args()
    if args.per_file and args.command != "commit":
        parser.error("--per-file은 commit 명령에서만 사용할 수 있습니다.")
    if args.apply and args.command != "commit":
        parser.error("--apply는 commit 명령에서만 사용할 수 있습니다.")
    if args.temperature is not None and not 0 <= args.temperature <= 2:
        parser.error("--temperature는 0~2 사이여야 합니다.")
    if args.max_tokens < 16:
        parser.error("--max-tokens는 16 이상이어야 합니다.")
    # .git 파일을 사용하는 worktree도 허용한다.
    if not Path(".git").exists():
        print("[ERROR] Git 프로젝트의 루트 디렉터리에서 실행하세요.", file=sys.stderr)
        return 1

    try:
        status = run_git("status", "--short", "--untracked-files=all")
        if not status.strip():
            print("[INFO] 변경 사항이 없습니다.")
            return 0

        unstaged = run_git("diff", "--no-ext-diff", "--no-textconv")
        staged = run_git("diff", "--cached", "--no-ext-diff", "--no-textconv")
        if args.apply:
            if not staged.strip():
                print("[ERROR] 커밋할 파일을 먼저 git add로 스테이징하세요.", file=sys.stderr)
                return 1
            snapshot = run_git("diff", "--cached", "--binary", "--no-ext-diff", "--no-textconv")
    except (OSError, RuntimeError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    if args.command in ("commit", "pr"):
        # 실제 다음 커밋에 들어가는 staged diff를 우선한다.
        diff = staged or unstaged
        if not diff.strip():
            print("[INFO] 생성할 diff가 없습니다. 새 파일은 git add 후 실행하세요.")
            return 0
        if any(line.startswith("?? ") for line in status.splitlines()):
            print("[INFO] 미추적 파일은 제외됩니다. 새 파일은 git add 후 실행하세요.")
        print("[INFO] 생성 대상: " + ("스테이징한 변경" if staged else "스테이징 전 변경"))
        try:
            from .ai_client import generate_commit, generate_file_commits, generate_pr

            if args.command == "pr":
                title, body = generate_pr(diff, args.model, args.temperature, args.max_tokens, args.safe_mode)
            elif args.per_file:
                files = collect_file_diffs(staged=bool(staged))
                messages = generate_file_commits(files, args.model, args.temperature, args.max_tokens, args.safe_mode)
            else:
                message = generate_commit(diff, args.model, args.temperature, args.max_tokens, args.safe_mode)
        except ImportError:
            print("[ERROR] python -m pip install -r requirements.txt 를 먼저 실행하세요.", file=sys.stderr)
            return 1
        except (OSError, RuntimeError) as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 1
        if args.command == "pr":
            print("\n--- PR Title ---")
            print(title)
            print("\n--- PR Body ---")
            print(body)
        elif args.per_file:
            print("\n--- Commit Messages by File ---")
            for path, message in messages.items():
                print(f"\n파일: {path!r}\n{message}")
        else:
            print("\n--- Commit Message ---")
            print(message)
        print("----------------------")
        if args.apply and args.per_file:
            return confirm_file_commits(messages, snapshot)
        if args.apply:
            return confirm_commit(message, snapshot)
        return 0

    print("--- 변경된 파일 (git status) ---")
    print(status, end="")
    print("\n--- 스테이징 전 변경 (git diff) ---")
    print(unstaged or "변경 내용이 없습니다.")
    print("--- 스테이징한 변경 (git diff --cached) ---")
    print(staged or "변경 내용이 없습니다.")
    if any(line.startswith("?? ") for line in status.splitlines()):
        print("[INFO] 새 미추적 파일은 목록에만 표시됩니다. 내용을 확인하려면 해당 파일을 git add 하세요.")
    return 0
