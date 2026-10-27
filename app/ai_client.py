"""AI 요청을 구성하고 생성 목적에 맞는 결과 처리를 연결한다."""

from dataclasses import dataclass, field
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from .diff_processing import prepare_diff, prepare_file_records
from .pr_template import load_template, render_template, template_instructions
from .prompts import INSTRUCTIONS, PR_INSTRUCTIONS, FILE_COMMIT_INSTRUCTIONS
from .response_format import format_commit, format_pr, format_file_commits

API_TIMEOUT_SECONDS = 60.0


# frozen=True는 생성한 설정 객체의 필드를 이후에 바꾸지 못하게 한다.
@dataclass(frozen=True)
class APIConfig:
    """인증과 연결 설정. 키는 객체 출력에 포함하지 않는다."""
    api_key: str = field(repr=False)
    base_url: str


def load_api_config() -> APIConfig:
    """환경변수를 읽고 기존 우선순위와 검증 규칙을 적용한다."""
    # 실행 디렉터리의 .env를 읽는다. 기존 셸 변수는 유지하며 ${...} 치환은 하지 않는다.
    load_dotenv(Path.cwd() / ".env", override=False, interpolate=False)
    api_key = os.environ.get("AI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("AI_API_KEY가 없습니다. .env 또는 환경변수에 교육기관 API 키를 설정하세요.")
    # 주소 끝의 /를 정리한다. API 키와 주소는 읽기만 하며 화면에 출력하지 않는다.
    base_url = os.environ.get("AI_BASE_URL", "https://").strip().rstrip("/")
    if not base_url.startswith("https://"):
        raise RuntimeError("AI_BASE_URL이 없습니다. .env 또는 환경변수에 교육기관 API 키를 설정하세요.")
    return APIConfig(api_key=api_key, base_url=base_url)


def request_text(diff_text: str, model: str, temperature: float | None, max_tokens: int,
                 safe_mode: bool, instructions: str) -> str:
    """설정 → 입력 정리 → 요청 → 응답 추출을 연결하는 공통 진입점."""
    # 요청 전에는 설정과 전송 내용을 준비하고, 응답 후에는 사용할 텍스트만 꺼낸다.
    api_config = load_api_config()
    request_content = prepare_diff(diff_text, api_config.api_key, safe_mode)
    print("[INFO] AI API 요청 중... (요청 1회, 자동 재시도 없음)")
    api_response = send_request(api_config, request_content, model, temperature, max_tokens, instructions)
    return extract_response_text(api_response)


def send_request(api_config: APIConfig, request_content: str, model: str, temperature: float | None,
                 max_tokens: int, instructions: str):
    """API를 한 번 호출하고 통신 오류를 사용자 메시지로 바꾼다."""
    try:
        # None일 때 temperature 인자 자체를 생략해 서버의 모델 기본값을 사용한다.
        optional_parameters = {}
        if temperature is not None:
            optional_parameters["temperature"] = temperature
        # with 블록이 끝나면 연결 자원을 정리한다. 자동 재시도는 0회로 제한한다.
        with OpenAI(api_key=api_config.api_key, base_url=api_config.base_url,
                    timeout=API_TIMEOUT_SECONDS, max_retries=0) as api_client:
            return api_client.chat.completions.create(
                model=model,
                # 작성 규칙(system)과 분석할 변경 내용(user)을 구분해 보낸다.
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": request_content},
                ],
                max_completion_tokens=max_tokens,
                # 딕셔너리를 키워드 인자로 펼친다. 비어 있으면 추가 인자가 없다.
                **optional_parameters,
            )
    except APITimeoutError:
        raise RuntimeError("API 응답 시간이 초과되었습니다. 잠시 후 다시 실행하세요.") from None
    except APIConnectionError:
        raise RuntimeError("API 서버에 연결하지 못했습니다. 네트워크 연결을 확인하세요.") from None
    except APIStatusError as exc:
        # 서버 오류 본문에는 입력값이나 키가 포함될 수 있어 그대로 출력하지 않는다.
        status_messages = {
            400: "모델과 temperature/max-tokens 옵션이 지원되는지 확인하세요.",
            401: "인증에 실패했습니다. API 서버 주소와 교육기관 키를 확인하세요.",
            403: "API 또는 모델 접근 권한을 확인하세요.",
            404: "모델 이름과 사용 권한을 확인하세요.",
            429: "요청 한도 또는 사용 잔액을 확인하세요.",
        }
        error_message = status_messages.get(exc.status_code, "API 서버 오류입니다. 잠시 후 다시 실행하세요.")
        raise RuntimeError(f"HTTP {exc.status_code}: {error_message}") from None


def extract_response_text(api_response) -> str:
    """완료된 응답에서 비어 있지 않은 텍스트를 꺼낸다."""
    if not api_response.choices:
        raise RuntimeError("AI가 응답을 반환하지 않았습니다.")
    # 여러 후보 중 첫 번째를 사용한다. 이 코드는 정상 종료(stop)인 응답만 허용한다.
    first_choice = api_response.choices[0]
    if first_choice.finish_reason != "stop":
        raise RuntimeError("응답이 완료되지 않았습니다. --max-tokens 값을 늘려 다시 실행하세요.")
    response_text = (first_choice.message.content or "").strip()
    if not response_text:
        raise RuntimeError("AI가 텍스트를 반환하지 않았습니다.")
    return response_text


def generate_commit(diff_text: str, model: str, temperature: float | None, max_tokens: int, safe_mode: bool) -> str:
    """일반 커밋용 규칙으로 요청하고 검증된 제목 한 줄을 반환한다."""
    response_text = request_text(diff_text, model, temperature, max_tokens, safe_mode, INSTRUCTIONS)
    return format_commit(response_text)


def generate_pr(diff_text: str, model: str, temperature: float | None, max_tokens: int, safe_mode: bool) -> tuple[str, str]:
    """템플릿이 있으면 적용하고, 없으면 기본 세 섹션으로 (제목, 본문)을 만든다."""
    # 1. 템플릿 유무에 맞는 작성 규칙을 선택한다.
    pr_template = load_template()
    instructions = PR_INSTRUCTIONS
    if pr_template is not None:
        print("[INFO] .github/pull_request_template.md 양식을 적용합니다.")
        instructions = template_instructions(pr_template)
    # 2. 한 번 요청한 뒤, 선택한 양식에 맞게 응답을 검증하고 조립한다.
    response_text = request_text(diff_text, model, temperature, max_tokens, safe_mode, instructions)
    if pr_template is not None:
        return render_template(response_text, pr_template)
    return format_pr(response_text)


def generate_file_commits(file_diffs: dict[str, str], model: str, temperature: float | None,
                          max_tokens: int, safe_mode: bool) -> dict[str, str]:
    """파일 목록을 한 번에 요청해 {파일 경로: 커밋 제목}으로 반환한다."""
    if not file_diffs:
        return {}
    file_records = prepare_file_records(file_diffs, safe_mode)
    # ensure_ascii=False는 한글을 \uXXXX 표기 대신 읽을 수 있는 문자로 유지한다.
    request_content = json.dumps(file_records, ensure_ascii=False)
    # 파일별 제한은 이미 적용했으므로 JSON 전체를 다시 자르지 않는다.
    response_text = request_text(request_content, model, temperature, max_tokens, False, FILE_COMMIT_INSTRUCTIONS)
    return format_file_commits(response_text, file_diffs)
