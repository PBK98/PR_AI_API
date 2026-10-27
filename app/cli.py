"""CLI 명령과 옵션의 정의 및 유효성 검사. Git이나 API를 실행하지 않는다."""

import argparse


def build_parser() -> argparse.ArgumentParser:
    """명령어와 옵션을 역할별로 정의한다."""
    # 여기서는 허용할 명령과 옵션만 등록한다. 실제 해석은 main의 parse_args가 수행한다.
    # --safe-mode처럼 하이픈이 있는 옵션은 args.safe_mode처럼 밑줄 속성으로 읽는다.
    parser = argparse.ArgumentParser(description="Git 변경 확인 및 AI 커밋/PR 초안 생성")
    parser.add_argument(
        "command",
        # nargs="?"는 명령 생략을 허용한다. 생략 시 command는 None이 된다.
        nargs="?",
        choices=["commit", "pr"],
        help="생략하면 Git 변경만 출력",
    )

    ai_options = parser.add_argument_group("AI 설정")
    ai_options.add_argument("--model", default="gpt-5-mini", help="사용할 AI 모델")
    ai_options.add_argument("--temperature", type=float, default=None, help="생략하면 모델 기본값 사용")
    ai_options.add_argument("--max-tokens", type=int, default=2048, help="출력 및 추론 토큰 한도")

    safety_options = parser.add_argument_group("전송 설정")
    # store_true 옵션은 값을 따로 받지 않는다. 지정하면 True, 생략하면 False다.
    safety_options.add_argument(
        "--safe-mode",
        action="store_true",
        help="전송 diff를 최대 200줄/20,000자로 제한",
    )

    commit_options = parser.add_argument_group("커밋 전용")
    commit_options.add_argument("--per-file", action="store_true", help="commit 메시지를 파일별로 생성")
    commit_options.add_argument("--apply", action="store_true", help="확인 후 스테이징된 변경을 실제 커밋")
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
