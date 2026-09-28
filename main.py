"""Git 변경 사항을 수집하는 CLI의 첫 단계."""

import argparse
import subprocess
import sys
from pathlib import Path


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Git 명령 실행에 실패했습니다.")
    return result.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description="Git 변경 확인 및 AI 커밋 메시지 생성")
    parser.add_argument("command", nargs="?", choices=["commit"], help="생략하면 Git 변경만 출력")
    parser.add_argument("--model", default="gpt-5-mini")
    parser.add_argument("--temperature", type=float, default=None, help="생략하면 모델 기본값 사용")
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--safe-mode", action="store_true", help="전송 diff를 최대 200줄/20,000자로 제한")
    args = parser.parse_args()
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
    except (OSError, RuntimeError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    if args.command == "commit":
        # 실제 다음 커밋에 들어가는 staged diff를 우선한다.
        diff = staged or unstaged
        if not diff.strip():
            print("[INFO] 생성할 diff가 없습니다. 새 파일은 git add 후 실행하세요.")
            return 0
        print("[INFO] 생성 대상: " + ("스테이징한 변경" if staged else "스테이징 전 변경"))
        try:
            from ai_client import generate_commit

            message = generate_commit(diff, args.model, args.temperature, args.max_tokens, args.safe_mode)
        except ImportError:
            print("[ERROR] python -m pip install -r requirements.txt 를 먼저 실행하세요.", file=sys.stderr)
            return 1
        except (OSError, RuntimeError) as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 1
        print("\n--- Commit Message ---")
        print(message)
        print("----------------------")
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


if __name__ == "__main__":
    sys.exit(main())
