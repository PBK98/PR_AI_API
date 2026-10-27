"""저장소 PR 템플릿의 빈 항목을 채우고 고정 문구를 보존한다."""

import json
from pathlib import Path
import re

from .prompts import PR_TEMPLATE_INSTRUCTIONS
from .response_format import (
    MAX_PR_TITLE_LENGTH, is_nonempty_text, parse_json_response, read_pr_title, shorten_title,
)


TEMPLATE_PATH = Path('.github/pull_request_template.md')


def load_template() -> str | None:
    """프로젝트 루트의 템플릿을 읽는다. 없으면 None, 비었거나 형식이 잘못되면 예외를 발생시킨다."""
    if not TEMPLATE_PATH.is_file():
        return None
    # utf-8-sig는 UTF-8 파일 앞의 BOM이 있는 경우에도 헤더를 올바르게 읽는다.
    template_text = TEMPLATE_PATH.read_text(encoding='utf-8-sig')
    if not template_text.strip():
        raise RuntimeError('PR 템플릿이 비어 있습니다. .github/pull_request_template.md를 확인하세요.')
    validate_sections(template_text)
    return template_text


def template_slots(template_text: str) -> dict[int, str]:
    """빈 체크박스와 빈/예시 값이 있는 굵은 라벨을 입력 항목으로 찾는다."""
    # 반환 예: {1: "- **작업자**: ", 5: "- "}. 키는 0부터 시작하는 줄 번호다.
    # 접두사는 코드가 보관하고 AI에게는 그 뒤에 들어갈 내용만 작성하게 한다.
    editable_lines = {}
    for line_number, template_line in enumerate(template_text.splitlines()):
        # fullmatch는 줄 전체가 양식과 일치할 때만 성공한다.
        # 내용이 이미 있는 체크리스트는 매칭하지 않아 원문을 그대로 보존한다.
        checkbox_match = re.fullmatch(r'(\s*- \[ \]\s*)', template_line)
        # 첫 번째 괄호 그룹은 "- **라벨**: ", 두 번째는 현재 입력된 값이다.
        label_match = re.fullmatch(r'(\s*- \*\*[^*]+\*\*:\s*)(.*)', template_line)
        if re.fullmatch(r"\s*-\s*", template_line):
            editable_lines[line_number] = "- "
        elif checkbox_match:
            editable_lines[line_number] = '- [ ] '
        elif label_match and (not label_match.group(2).strip() or label_match.group(2).strip().startswith('(예:')):
            editable_lines[line_number] = label_match.group(1).rstrip() + ' '
    return editable_lines


def template_instructions(template_text: str) -> str:
    """템플릿 원문과 수정 가능한 줄 목록을 포함한 작성 규칙을 만든다."""
    editable_lines = template_slots(template_text)
    template_lines = template_text.splitlines()
    # JSON 객체의 키는 문자열이므로 줄 번호를 str로 바꾼다.
    field_descriptions = {str(line_number): template_lines[line_number] for line_number in editable_lines}
    return (
        PR_TEMPLATE_INSTRUCTIONS
        + json.dumps(field_descriptions, ensure_ascii=False)
        + '\n템플릿:\n' + template_text
    )


def render_template(response_text: str, template_text: str) -> tuple[str, str]:
    """AI의 JSON 응답을 검증해 (PR 제목, 템플릿을 채운 본문)을 반환한다."""
    # 1. JSON과 제목을 검증한다.
    response_data = parse_json_response(response_text, 'PR 템플릿 응답이 올바른 JSON이 아닙니다.')
    pr_title = shorten_title(read_pr_title(response_data), MAX_PR_TITLE_LENGTH)
    # 2. 응답의 항목들이 실제로 채울 줄과 정확히 대응하는지 확인한다.
    editable_lines = template_slots(template_text)
    field_values = response_data.get('fields')
    # 키 집합을 비교해 누락된 줄과 AI가 임의로 추가한 줄을 모두 거부한다.
    if not isinstance(field_values, dict) or set(field_values) != {str(line_number) for line_number in editable_lines}:
        raise RuntimeError('PR 템플릿 응답의 입력 항목이 누락되거나 추가되었습니다.')
    template_lines = template_text.splitlines()
    # 3. 지정된 줄만 채운 뒤, 완성된 Markdown의 필수 섹션을 검증한다.
    for line_number, field_prefix in editable_lines.items():
        field_value = normalize_field(field_values[str(line_number)], field_prefix)
        template_lines[line_number] = field_prefix + field_value
    pr_body = "\n".join(template_lines)
    validate_sections(pr_body)
    if template_text.endswith("\n"):
        pr_body += "\n"
    return pr_title, pr_body


def validate_sections(pr_body: str) -> None:
    """과제 필수 헤더와 각 섹션의 불릿을 확인한다."""
    for heading in ('Why', 'What', 'How to Test'):
        # re.M: ^를 각 줄의 시작으로 해석. re.S: .이 줄바꿈까지 포함하도록 설정.
        # .*?로 최소한만 읽고, 다음 "## " 헤더 또는 문서 끝(\Z)에서 멈춘다.
        section_match = re.search(r'^## ' + re.escape(heading) + r'\s*\n(.*?)(?=^## |\Z)', pr_body, re.M | re.S)
        if not section_match or not re.search(r'^-($|\s)', section_match.group(1), re.M):
            raise RuntimeError(f'PR 템플릿에 {heading} 헤더와 불릿이 필요합니다.')


def normalize_field(value: object, field_prefix: str) -> str:
    """항목을 한 줄로 만들고 체크 여부와 작업자 정보는 직접 통제한다."""
    if not is_nonempty_text(value):
        raise RuntimeError('PR 템플릿 응답에 빈 항목이 있습니다.')
    field_text = ' '.join(value.split())
    # AI가 붙인 "- ", "* ", "- [x] " 등을 제거한다. 체크 여부는 원본 양식이 결정한다.
    field_text = re.sub(r'^[-*]\s*(?:\[[ xX]\]\s*)?', '', field_text).strip()
    if not field_text:
        raise RuntimeError('PR 템플릿 응답에 빈 항목이 있습니다.')
    # diff만으로 작성자 신원을 확정할 수 없으므로 AI의 추측을 사용하지 않는다.
    if '작업자' in field_prefix:
        return '확인 필요'
    return field_text
