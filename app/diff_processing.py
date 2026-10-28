"""API로 보낼 diff의 마스킹과 전송량 제한."""

import re

# 제한 단위는 토큰이 아니라 줄 수와 Python 문자열의 문자 수다.
MAX_DIFF_LINES = 200
MAX_DIFF_CHARS = 20_000
MAX_SAFE_FILES = 10


def limit_diff(diff_text: str, max_lines: int, max_chars: int) -> str:
    """줄 수를 먼저 제한하고 문자 수 한도를 적용한다."""
    selected_lines = diff_text.splitlines()[:max_lines]
    # 줄을 합친 후 문자 수도 제한하므로 한 줄이 매우 길어도 상한을 지킨다.
    return "\n".join(selected_lines)[:max_chars]


def prepare_diff(diff_text: str, api_key: str, safe_mode: bool, base_url: str = "") -> str:
    """diff의 키와 서버 주소를 가리고, 안전 모드일 때 분량을 제한한다.

    api_key는 호출자가 비어 있지 않음을 확인한 값이다.
    이 함수는 모든 비밀정보를 탐지하지 않으며 파일 자체는 수정하지 않는다.
    """
    # 주소 안에 키가 포함되어 있어도 전체 주소를 먼저 가릴 수 있도록 처리한다.
    # 빈 문자열을 replace에 전달하면 문자 사이마다 표시가 삽입되므로 제외한다.
    if base_url:
        diff_text = diff_text.replace(base_url, "[REDACTED]")
    # 사용 중인 키와 흔한 OpenAI 키 패턴은 모드와 관계없이 제거한다.
    diff_text = diff_text.replace(api_key, "[REDACTED]")
    # sk- 뒤의 영문자·숫자·밑줄·하이픈이 한 개 이상 이어지는 패턴을 치환한다.
    diff_text = re.sub(r"sk-[A-Za-z0-9_-]+", "[REDACTED]", diff_text)
    if not safe_mode:
        return diff_text
    limited_diff = limit_diff(diff_text, MAX_DIFF_LINES, MAX_DIFF_CHARS)
    # splitlines/join으로 끝 줄바꿈만 사라진 경우는 내용 생략으로 판단하지 않는다.
    if len(limited_diff) < len(diff_text.rstrip("\n")):
        print("[INFO] 안전 모드: diff 일부만 전송합니다.")
        limited_diff += "\n[입력 제한으로 나머지 diff 생략]"
    return limited_diff


def prepare_file_records(file_diffs: dict[str, str], safe_mode: bool) -> list[dict]:
    """파일별 입력 예산을 나누고 원래 순서를 식별할 ID를 붙인다."""
    if not file_diffs:
        return []
    if safe_mode and len(file_diffs) > MAX_SAFE_FILES:
        raise RuntimeError("파일별 안전 모드는 최대 10개 파일입니다. 스테이징할 파일을 나누어 실행하세요.")
    file_count = len(file_diffs)
    # //는 정수 나눗셈이다. 예를 들어 10개 파일이면 각 파일에 20줄을 배정한다.
    # 위의 빈 입력 반환으로 0으로 나누는 경우를 방지한다.
    lines_per_file = MAX_DIFF_LINES // file_count
    chars_per_file = MAX_DIFF_CHARS // file_count
    file_records = []
    for file_id, (file_path, diff_text) in enumerate(file_diffs.items()):
        if safe_mode:
            # JSON 전체를 자르면 뒤쪽 파일이 누락되므로 파일별로 예산을 배분한다.
            limited_diff = limit_diff(diff_text, lines_per_file, chars_per_file)
            if len(limited_diff) < len(diff_text.rstrip("\n")):
                print(f"[INFO] {file_path!r}: diff 일부만 전송합니다.")
                limited_diff += "\n[나머지 diff 생략]"
            diff_text = limited_diff
        # 응답 순서가 달라져도 id를 통해 원래 파일에 제목을 연결할 수 있다.
        file_records.append({"id": file_id, "path": file_path, "diff": diff_text})
    return file_records
