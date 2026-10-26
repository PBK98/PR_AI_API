"""Git 변경 확인 및 커밋/PR 초안 생성 CLI."""

import argparse
import sys
from pathlib import Path

from .git_client import collect_file_diffs, commit_staged_file, run_git


def confirm_commit(message: str, expected_diff: str) -> int:
    """검토 후 명시적으로 확인한 경우에만 현재 인덱스를 커밋한다."""
    if not ask_confirmation("이 메시지로 스테이징된 변경을 커밋할까요? [y/N] "):
        return 0
    try:
        # AI 응답을 기다리는 동안 사용자가 git add를 다시 했을 수 있다.
        # 생성 당시의 변경과 비교해 메시지와 실제 커밋 내용이 달라지는 것을 막는다.
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
    """파일별 메시지를 확인받고 순서대로 커밋한다. 중단 시 완료된 커밋은 유지한다."""
    if not ask_confirmation(f"위 {len(messages)}개 파일을 각각 별도 커밋할까요? [y/N] "):
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


def build_parser() -> argparse.ArgumentParser:
    """명령어와 옵션을 역할별로 정의한다."""
    # 여기서는 허용할 명령과 옵션만 등록한다. 실제 해석은 main의 parse_args가 수행한다.
    # --safe-mode처럼 하이픈이 있는 옵션은 args.safe_mode처럼 밑줄 속성으로 읽는다.
    parser = argparse.ArgumentParser(
        description="Git 변경 확인 및 AI 커밋/PR 초안 생성"
    )
    parser.add_argument(
        "command",
        # nargs="?"는 명령 생략을 허용한다. 생략 시 command는 None이 된다.
        nargs="?",
        choices=["commit", "pr"],
        help="생략하면 Git 변경만 출력",
    )

    ai_options = parser.add_argument_group("AI 설정")
    ai_options.add_argument(
        "--model",
        default="gpt-5-mini",
        help="사용할 AI 모델",
    )
    ai_options.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="생략하면 모델 기본값 사용",
    )
    ai_options.add_argument(
        "--max-tokens",
        type=int,
        default=2048,
        help="출력 및 추론 토큰 한도",
    )

    safety_options = parser.add_argument_group("전송 설정")
    # store_true 옵션은 값을 따로 받지 않는다. 지정하면 True, 생략하면 False다.
    safety_options.add_argument(
        "--safe-mode",
        action="store_true",
        help="전송 diff를 최대 200줄/20,000자로 제한",
    )

    commit_options = parser.add_argument_group("커밋 전용")
    commit_options.add_argument(
        "--per-file",
        action="store_true",
        help="commit 메시지를 파일별로 생성",
    )
    commit_options.add_argument(
        "--apply",
        action="store_true",
        help="확인 후 스테이징된 변경을 실제 커밋",
    )
    return parser


def validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    """옵션의 사용 조건과 값의 범위를 확인한다."""
    if args.apply and args.command != "commit":
        parser.error("--apply는 commit 명령에서만 사용할 수 있습니다.")
    if args.per_file and args.command != "commit":
        parser.error("--per-file은 commit 명령에서만 사용할 수 있습니다.")
    if args.temperature is not None and not 0 <= args.temperature <= 2:
        parser.error("--temperature는 0~2 사이여야 합니다.")
    if args.max_tokens < 16:
        parser.error("--max-tokens는 16 이상이어야 합니다.")


def main() -> int:
    """인자 검증 → Git 상태 수집 → 명령 실행. 반환값 0은 정상 종료, 1은 처리 실패다."""
    parser = build_parser()
    args = parser.parse_args()
    validate_args(parser, args)

    # .git 파일을 사용하는 worktree도 허용한다.
    if not Path(".git").exists():
        print("[ERROR] Git 프로젝트의 루트 디렉터리에서 실행하세요.", file=sys.stderr)
        return 1

    snapshot = ""
    try:
        status = run_git("status", "--short", "--untracked-files=all")
        if not status.strip():
            print("[INFO] 변경 사항이 없습니다.")
            return 0

        # unstaged: 작업 파일과 인덱스의 차이. staged: 인덱스와 HEAD의 차이.
        # 인덱스는 git add로 다음 커밋에 포함할 내용을 모아 둔 영역이다.
        unstaged = run_git("diff", "--no-ext-diff", "--no-textconv")
        staged = run_git("diff", "--cached", "--no-ext-diff", "--no-textconv")
        if args.apply:
            if not staged.strip():
                print("[ERROR] 커밋할 파일을 먼저 git add로 스테이징하세요.", file=sys.stderr)
                return 1
            # 실제 적용 직전에 비교할 원본을 보관한다. 바이너리 변경 내용도 포함한다.
            snapshot = run_git("diff", "--cached", "--binary", "--no-ext-diff", "--no-textconv")
    except (OSError, RuntimeError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    if args.command in ("commit", "pr"):
        try:
            return handle_generation(args, status, staged, unstaged, snapshot)
        except ImportError:
            print("[ERROR] python -m pip install -r requirements.txt 를 먼저 실행하세요.", file=sys.stderr)
            return 1
        except (OSError, RuntimeError) as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 1

    show_changes(status, staged, unstaged)
    return 0


def show_changes(status: str, staged: str, unstaged: str) -> None:
    """수집한 Git 상태와 두 종류의 diff를 출력한다."""
    print("--- 변경된 파일 (git status) ---")
    print(status, end="")
    print("\n--- 스테이징 전 변경 (git diff) ---")
    print(unstaged or "변경 내용이 없습니다.")
    print("--- 스테이징한 변경 (git diff --cached) ---")
    print(staged or "변경 내용이 없습니다.")
    if any(line.startswith("?? ") for line in status.splitlines()):
        print("[INFO] 새 미추적 파일은 목록에만 표시됩니다. 내용을 확인하려면 해당 파일을 git add 하세요.")


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

    title, body = generate_pr(diff, args.model, args.temperature, args.max_tokens, args.safe_mode)
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
    from .ai_client import generate_commit, generate_file_commits

    if args.per_file:
        files = collect_file_diffs(staged=staged)
        messages = generate_file_commits(files, args.model, args.temperature, args.max_tokens, args.safe_mode)
        print("\n--- Commit Messages by File ---")
        for path, message in messages.items():
            print(f"\n파일: {path!r}\n{message}")
        print("----------------------")
        if args.apply:
            return confirm_file_commits(messages, snapshot)
        return 0

    message = generate_commit(diff, args.model, args.temperature, args.max_tokens, args.safe_mode)
    print("\n--- Commit Message ---")
    print(message)
    print("----------------------")
    if args.apply:
        return confirm_commit(message, snapshot)
    return 0


def ask_confirmation(question: str) -> bool:
    """명시적인 y만 승인으로 처리하며 입력 중단도 취소로 안내한다."""
    try:
        answer = input(question)
    except (EOFError, KeyboardInterrupt):
        print("\n[INFO] 커밋을 취소했습니다.")
        return False
    if answer.strip().lower() != "y":
        print("[INFO] 커밋을 취소했습니다.")
        return False
    return True
