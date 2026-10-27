"""AI 응답의 JSON, 제목, PR 및 파일별 결과 형식 검증."""

import json
import re

MAX_COMMIT_TITLE_LENGTH = 72
MAX_PR_TITLE_LENGTH = 80
# JSON의 키와 사람이 읽는 Markdown 헤더를 연결한다.
PR_SECTIONS = (("why", "Why"), ("what", "What"), ("how_to_test", "How to Test"))


def is_nonempty_text(value: object) -> bool:
    """비어 있지 않은 문자열인지 확인한다."""
    # and는 앞 조건이 거짓이면 뒤를 실행하지 않아 숫자/None에 strip()을 호출하지 않는다.
    return isinstance(value, str) and bool(value.strip())


def parse_json_response(response_text: str, error_message: str):
    """코드 블록 포장을 제거한 뒤 JSON을 해석한다."""
    response_text = response_text.strip()
    if response_text.startswith("```") and response_text.endswith("```"):
        # 모델이 ```json ... ```으로 감싸면 첫 줄과 마지막 줄을 제외한다.
        response_text = "\n".join(response_text.splitlines()[1:-1])
    try:
        # JSON 문법만 해석한다. 객체/목록 여부와 필수 키 검증은 호출자가 담당한다.
        return json.loads(response_text)
    except json.JSONDecodeError:
        raise RuntimeError(error_message) from None


def shorten_title(title: str, max_length: int) -> str:
    """긴 제목에 말줄임표를 붙여 최대 길이를 지킨다."""
    if len(title) <= max_length:
        return title
    # 뒤에 붙일 점 세 개의 길이를 먼저 확보한다.
    return title[:max_length - 3].rstrip() + "..."


def format_commit(response_text: str) -> str:
    """응답 첫 줄을 커밋 제목으로 정리한다."""
    # 공통 API 응답 검사에서 빈 문자열을 거른 후 호출한다. 제목은 첫 줄만 사용한다.
    commit_title = response_text.splitlines()[0].strip().strip('`"')
    if not commit_title:
        raise RuntimeError("AI 응답에서 커밋 제목을 찾지 못했습니다.")
    if len(commit_title) > MAX_COMMIT_TITLE_LENGTH:
        commit_title = shorten_title(commit_title, MAX_COMMIT_TITLE_LENGTH)
        print("[INFO] 커밋 제목을 최대 72자로 줄였습니다.")
    return commit_title


def format_pr(response_text: str) -> tuple[str, str]:
    """JSON을 검증하고 제목/섹션/불릿을 일정한 형식으로 출력한다."""
    response_data = parse_json_response(response_text, "PR 응답이 올바른 JSON이 아닙니다. 다시 실행하세요.")
    pr_title = read_pr_title(response_data)
    if len(pr_title) > MAX_PR_TITLE_LENGTH:
        pr_title = shorten_title(pr_title, MAX_PR_TITLE_LENGTH)
        print("[INFO] PR 제목을 최대 80자로 줄였습니다.")
    markdown_sections = []
    for section_key, section_heading in PR_SECTIONS:
        section_items = response_data.get(section_key)
        if not is_nonempty_text_list(section_items):
            raise RuntimeError(f"PR 응답의 {section_heading}에는 내용이 있는 항목이 하나 이상 필요합니다.")
        bullets = []
        for section_item in section_items:
            bullet_text = " ".join(section_item.split()).lstrip("-* ")
            if not bullet_text:
                raise RuntimeError(f"PR 응답의 {section_heading}에 빈 항목이 있습니다.")
            bullets.append("- " + bullet_text)
        markdown_sections.append("## " + section_heading + "\n" + "\n".join(bullets))
    return pr_title, "\n\n".join(markdown_sections)


def format_file_commits(response_text: str, file_diffs: dict[str, str]) -> dict[str, str]:
    """모든 파일 ID를 검증하고 입력 순서대로 제목을 연결한다."""
    response_data = parse_json_response(response_text, "파일별 커밋 응답이 올바른 JSON이 아닙니다.")
    if not isinstance(response_data, dict) or not isinstance(response_data.get("commits"), list):
        raise RuntimeError("파일별 커밋 응답 형식이 잘못되었습니다.")
    titles_by_file_id = {}
    for commit_item in response_data["commits"]:
        if not isinstance(commit_item, dict):
            raise RuntimeError("파일별 커밋 항목 형식이 잘못되었습니다.")
        file_id, commit_title = commit_item.get("id"), commit_item.get("title")
        # bool은 int의 하위 타입이므로 isinstance 대신 type을 비교해 True/False를 거부한다.
        is_valid_file_id = type(file_id) is int and file_id in range(len(file_diffs))
        if not is_valid_file_id or file_id in titles_by_file_id:
            raise RuntimeError("파일별 커밋 응답에 중복되거나 잘못된 파일 ID가 있습니다.")
        if not is_nonempty_text(commit_title):
            raise RuntimeError("파일별 커밋 응답에 빈 제목이 있습니다.")
        commit_title = " ".join(commit_title.split())
        # ^는 문자열 시작, \s+는 공백 하나 이상, \S는 공백이 아닌 실제 제목 문자다.
        if not re.match(r"^(feat|fix|docs|refactor|test|chore):\s+\S", commit_title):
            raise RuntimeError("파일별 커밋 제목의 접두사 형식이 잘못되었습니다.")
        titles_by_file_id[file_id] = shorten_title(commit_title, MAX_COMMIT_TITLE_LENGTH)
    if len(titles_by_file_id) != len(file_diffs):
        raise RuntimeError("일부 파일의 커밋 메시지가 누락되었습니다. --max-tokens를 늘려 다시 실행하세요.")
    # AI 응답 순서 대신 입력 딕셔너리의 순서로 결과를 구성한다.
    return {file_path: titles_by_file_id[file_id] for file_id, file_path in enumerate(file_diffs)}


def is_nonempty_text_list(value: object) -> bool:
    """내용이 있는 문자열을 하나 이상 가진 목록인지 확인한다."""
    if not isinstance(value, list) or not value:
        return False
    return all(is_nonempty_text(item) for item in value)


def read_pr_title(response_data: object) -> str:
    """기본 PR과 템플릿 PR에 공통인 제목 검증·공백 정리를 수행한다."""
    if not isinstance(response_data, dict) or not is_nonempty_text(response_data.get("title")):
        raise RuntimeError("PR 응답에 유효한 제목이 없습니다.")
    # 연속 공백과 줄바꿈을 단일 공백으로 합쳐 제목을 반드시 한 줄로 만든다.
    pr_title = " ".join(response_data["title"].split())
    return pr_title
