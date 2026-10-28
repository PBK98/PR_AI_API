# AI Git 메시지 도우미

Git 변경 내용을 읽어 한국어 커밋 메시지와 PR 초안을 생성하는 Python CLI입니다.
교육기관의 OpenAI 호환 Chat Completions API를 사용합니다.
기본 실행은 초안만 출력합니다. `commit --apply`는 확인 후 로컬 커밋을 생성하며, push와 GitHub PR 등록은 사용자가 직접 수행합니다.

## 설치

Git과 curl이 필요합니다. 초기 설정 스크립트가 Python 3.14.7을 준비하므로 Python을 미리 설치하지 않아도 됩니다. 프로젝트 루트에서 실행하세요.

```bash
git clone https://github.com/PBK98/PR_AI_API.git
cd PR_AI_API
bash scripts/setup-venv.sh
cp -n .env.example .env
```

`setup-venv.sh`는 `prepare-python.sh`를 호출해 **Python 3.14.7** 가상환경을 준비하고, `requirements.txt`를 설치한 뒤 가상환경이 활성화된 새 Bash 셸을 엽니다. `python --version`으로 버전을 확인하고 `python -m app`으로 실행하세요. `exit`하면 원래 셸로 돌아갑니다.

준비 순서는 **Python 3.14.7 확보 → .venv 생성 → 패키지 설치 → 활성화**입니다. 이미 정확한 버전의 유효한 `.venv`가 있으면 재사용합니다. 다른 버전이거나 깨진 환경이면 `.venv-backup.임의문자/.venv`에 백업한 뒤 새로 만듭니다. 새 환경 생성에 실패하면 기존 환경을 원래 위치로 복구합니다. 패키지 설치에 실패한 경우에는 새 환경과 백업을 보존하며 활성화하지 않습니다. 백업된 가상환경을 다시 쓰려면 원래 `.venv` 경로로 복구해야 합니다.

관리자 권한이나 `sudo`는 사용하지 않습니다. 필요한 경우 uv 공식 설치 도구를 받아 `.tools/bin`에 설치하고, uv로 Python 3.14.7을 `.tools/python`에 다운로드합니다. 캐시는 `.tools/cache`, 패키지는 `.venv`에 저장합니다. 시스템 Python과 `.zshrc`·`.bashrc`는 변경하지 않습니다. `.tools/`와 가상환경 백업은 Git에서 제외합니다.

이 방식은 [uv의 사용자 지정 설치](https://docs.astral.sh/uv/reference/installer/)와 [Python 설치 기능](https://docs.astral.sh/uv/guides/install-python/)을 사용합니다. 프로젝트 폴더 쓰기 권한과 Astral·GitHub·패키지 저장소에 접근할 수 있는 네트워크가 필요합니다. 교육장 정책이나 해당 macOS·CPU용 배포 파일 제공 여부에 따라 다운로드가 실패할 수 있으며, 이 경우 다른 Python 버전으로 임의 대체하지 않습니다. `.tools/python`은 `.venv`가 참조하므로 사용 중에 삭제하지 마세요.

직접 실행한 스크립트는 부모 셸의 환경을 바꿀 수 없으므로 새 셸을 여는 방식입니다. 이 셸은 가상환경 PATH를 유지하도록 개인 셸 초기화 파일을 읽지 않아 사용자 별칭이나 테마는 적용되지 않습니다. 현재 Bash 또는 Zsh에서 그대로 활성화하려면 다음 명령을 사용하세요.

```bash
source scripts/setup-venv.sh
```

`source` 방식은 작업 디렉터리를 변경하지 않습니다. 설치에 실패하면 활성화 단계로 넘어가지 않습니다. 초기 설정 후 패키지 설치 확인 없이 활성화만 하려면 `source .venv/bin/activate`를 사용하세요. 이후 `.env`를 열어 키를 입력합니다.

```dotenv
AI_API_KEY="교육기관에서 발급받은 키"
AI_BASE_URL=...
```

`.env`는 자동으로 읽으며 셸 환경변수가 우선합니다. 실제 키를 Git에 넣지 마세요.
교육기관 키는 교육기관 서버에 사용하며, 주소 뒤에 `/chat/completions`를 붙이지 않습니다.
새 터미널에서는 가상환경을 다시 활성화하거나 `.venv/bin/python -m app`을 사용하세요.

## 실행

```bash
# 변경 목록과 staged/unstaged diff 확인: API 호출 없음
python -m app

# 커밋 제목 생성
python -m app commit --safe-mode

# 파일별 커밋 제목 생성
python -m app commit --per-file --safe-mode

# PR 제목과 본문 생성
python -m app pr --safe-mode
```

스테이징된 변경이 있으면 그 변경만, 없으면 스테이징 전 변경을 분석합니다.
새 미추적 파일은 `git add 파일명`으로 스테이징해야 diff에 포함됩니다.
변경이 없으면 안내 후 종료하며 API를 호출하지 않습니다.
커밋을 마친 브랜치의 이력은 분석하지 않으므로 커밋 전에 초안을 생성하세요.
생성된 문구를 검토한 뒤 직접 `git commit`과 GitHub PR 작성에 사용합니다.

## 출력 예시

아래는 형식 설명용 예시입니다. 실제 실행 증빙은 [실행 결과](docs/verification.md)를 확인하세요.

```text
--- Commit Message ---
feat: 이름 공백을 제거하는 인사 함수 추가
----------------------
```

```text
--- PR Title ---
feat: 인사 함수 추가

--- PR Body ---
## 📌 PR 개요
- **작업자**: 확인 필요
- **관련 기능**: 인사말 생성

## Why
- 변경 배경 확인 필요

## What
- 입력 이름의 앞뒤 공백을 제거하는 greet 함수 추가
- 추가 변경 사항 없음

## How to Test
- 제안(미실행): 앞뒤 공백이 있는 이름을 입력하여 반환 문자열 확인
```

실제 본문에는 저장소 템플릿의 테스트 검증 및 과제 체크리스트도 함께 출력됩니다.
작업자와 실제 검증 결과는 사용자가 수정합니다. 자동으로 체크하지 않습니다.
커밋 제목은 50자 이내 권장, 최대 72자입니다. PR 제목은 최대 80자입니다.

## PR 템플릿

[.github/pull_request_template.md](.github/pull_request_template.md)를 자동 적용합니다.
빈 불릿·빈 체크박스 및 굵은 라벨의 빈 값/예시 값을 채우고 고정 문구를 보존합니다.
`Why`, `What`, `How to Test` 헤더와 각 섹션의 불릿을 필수로 검증합니다.
템플릿이 없으면 동일한 필수 세 섹션을 기본 형식으로 생성합니다.
응답의 JSON이나 입력 항목이 잘못되면 오류로 안내하며 자동 재요청하지 않습니다.

## 옵션

| 옵션 | 기본값 | 설명 |
| --- | --- | --- |
| `--model` | `gpt-5-mini` | 교육기관이 제공하는 모델 ID |
| `--temperature` | 생략 | 0~2, 지원하는 모델에만 지정 |
| `--max-tokens` | 2048 | 최소 16, 출력 및 추론 토큰 한도 |
| `--safe-mode` | 꺼짐 | 전송할 diff 분량 제한 |
| `--per-file` | 꺼짐 | commit 전용, 파일별 메시지 생성 |
| `--apply` | 꺼짐 | commit 전용, 확인 후 실제 로컬 커밋 |
| `--help` | — | 도움말 |

```bash
python -m app commit --per-file --safe-mode --max-tokens 4096
```

## 안전 모드와 비용

생성 명령당 AI 요청은 최대 1회이며 자동 재시도하지 않습니다. 응답 대기 제한은 60초입니다.
모델과 토큰 사용량에 따라 교육기관 크레딧이 차감될 수 있습니다.
API 키 원문, 일반적인 `sk-` 패턴, 설정된 `AI_BASE_URL`과 일치하는 문자열은 전송할 diff에서 `[REDACTED]`로 마스킹합니다. 이 처리는 안전 모드 여부와 관계없이 적용하며, 실제 API 연결 주소는 유지합니다.

- 일반 안전 모드: 최대 200줄 및 20,000자까지 diff 전송
- 파일별 안전 모드: 최대 10개 파일, 200줄/20,000자 예산을 파일 수로 균등 분배
- 생략 표시·JSON 포장·PR 템플릿은 diff 제한과 별도로 포함

모든 개인정보나 비밀을 탐지하는 기능은 아니므로 전송할 diff와 템플릿을 확인하세요.
제한으로 잘린 변경은 요약에서 빠질 수 있습니다. 파일이 10개를 넘으면 스테이징 대상을 나누세요.
파일별 모드에서 이동은 삭제와 추가로 나누어 분석합니다.

## 문제 해결

| 증상 | 대응 |
| --- | --- |
| `python` 없음 / `externally-managed-environment` | 가상환경 활성화 후 설치·실행 |
| 키 누락 | `.env`의 `AI_API_KEY` 확인 |
| HTTP 401 | 교육기관 키·서버 주소 확인, 필요 시 `unset AI_API_KEY`로 기존 셸 키 해제 |
| HTTP 400 | 모델·temperature·토큰 옵션 지원 여부 확인 |
| HTTP 403/404 | 모델 이름·접근 권한 확인 |
| HTTP 429 | 요청 한도·사용 잔액 확인 |
| 응답 미완료 | `--max-tokens`를 늘려 재실행 |
| 변경 없음 / 새 파일 제외 | 미커밋 변경 확인, 필요한 파일을 `git add` |
| PR 템플릿 형식 오류 | 필수 세 헤더와 각 섹션의 불릿 확인 |

## 구조

```text
app/
  __init__.py       # app 패키지 표시
  __main__.py       # python -m app 진입점
  runner.py         # 실행 흐름·Git 상태 출력
  cli.py            # 명령어·옵션 정의와 검증
  generation.py       # 커밋 메시지·PR 초안 생성 및 출력
  commit_actions.py # 사용자 확인·스테이징 검증·실제 커밋
  git_client.py     # Git 명령·diff 수집·임시 인덱스 처리
  ai_client.py      # 환경설정·API 통신·생성 흐름 연결
  prompts.py        # 커밋·기본 PR·템플릿 PR의 고정 작성 규칙
  diff_processing.py # 키 마스킹·diff 제한·파일별 입력 구성
  response_format.py # JSON·제목·PR·파일별 결과 검증
  pr_template.py    # 템플릿 로딩·채우기·필수 섹션 검증
.github/pull_request_template.md
tests/
docs/
requirements.txt
.env.example
```

## 검증과 제출 자료

```bash
python -m unittest discover -s tests -v
```

단위 테스트는 모의 API로 실행하며 비용을 발생시키지 않습니다.
[실행 증빙](docs/verification.md), [요구사항 및 학습 정리](docs/submission.md)를 함께 확인하세요.

자동 커밋·push·PR 생성 확장 버전은 로컬 브랜치 `archive/apply-features-20261008`에 보관했습니다.
현재 버전에는 `commit --apply`가 복원되어 있으며, `--base`와 원격 반영 모듈은 없습니다.


## 확인 후 실제 커밋

커밋할 파일을 먼저 `git add 파일명`으로 스테이징한 뒤 실행합니다.

```bash
# 전체 스테이징 내용을 하나의 커밋으로 저장
python -m app commit --safe-mode --apply

# 파일별 메시지로 각각 별도 커밋
python -m app commit --safe-mode --per-file --apply
```

생성된 메시지와 파일 목록을 검토하고 확인 질문에 `y`를 입력하면 커밋합니다.
Enter, 다른 입력, 확인 질문에서의 Ctrl+C 또는 입력 종료는 취소입니다.
스테이징되지 않은 수정은 보존합니다. 자동 스테이징이나 push는 하지 않습니다.
파일별 커밋 중 오류가 발생하면 중단하며, 이미 완료된 커밋은 유지됩니다.
안전 모드의 파일별 제한은 최대 10개이므로 대상을 나누어 스테이징하세요.
이동이나 서로 의존하는 변경은 하나의 커밋으로 묶는 편이 좋습니다.


## 코드를 읽는 순서

처음에는 `runner.py`의 `main()`에서 전체 흐름을 보고, 호출하는 함수를 따라 읽으면 됩니다.

1. **실행 진입** — `__main__.py`가 `runner.main()`을 호출합니다.
2. **명령 해석** — `cli.py`의 `build_parser()`와 `validate_args()`가 명령과 옵션을 확인합니다.
3. **변경 조회** — `runner.py`가 Git 상태와 스테이징 전·후 diff를 읽습니다. 명령을 생략하면 상태만 출력합니다.
4. **분석 대상 선택** — `generation.py`의 `handle_generation()`이 스테이징한 변경을 우선 선택합니다.
5. **AI 요청** — `ai_client.py`가 설정을 읽고, `diff_processing.py`에서 입력을 정리한 뒤 요청합니다. 고정 작성 규칙은 `prompts.py`에 있습니다.
6. **응답 검증과 출력** — `response_format.py`가 응답 형식을 검증하고 `generation.py`가 결과를 출력합니다. 템플릿 PR은 `pr_template.py`가 빈 항목을 채워 Markdown 본문을 만듭니다.
7. **선택적 커밋** — `commit --apply`일 때만 `commit_actions.py`가 사용자 확인과 스테이징 재검증 후 커밋합니다. 실제 Git 명령과 임시 인덱스 처리는 `git_client.py`가 담당합니다.

### 변수 이름으로 데이터 구분하기

| 변수 | 담고 있는 내용 |
|---|---|
| `cli_args` | 터미널에서 입력한 명령과 옵션 |
| `git_status` | `git status --short` 결과 문자열 |
| `staged_diff` / `unstaged_diff` | 스테이징한 변경 / 아직 스테이징하지 않은 변경 |
| `selected_diff` | 이번 생성 작업에서 분석할 변경 내용 |
| `use_staged_diff` | 파일별 diff를 스테이징 기준으로 읽을지 정하는 참·거짓 값 |
| `staged_snapshot` | 생성 당시 보관한 전체 스테이징 변경. 실제 커밋 직전에 비교 |
| `file_diffs` | 파일 경로를 키로, 해당 파일의 diff를 값으로 가진 딕셔너리 |
| `commit_messages` | 파일 경로와 생성된 커밋 메시지를 연결한 딕셔너리 |
| `request_content` / `api_response` | API에 보낼 내용 / API가 반환한 응답 객체 |
| `response_text` / `response_data` | 응답의 텍스트 / JSON을 해석한 Python 데이터 |
| `editable_lines` | 템플릿에서 채울 줄 번호와 해당 줄의 접두사 |
| `field_descriptions` / `field_values` | AI에 전달할 원본 항목 / AI가 작성한 항목 값 |

`diff_text`는 diff 문자열, `file_id`는 응답을 원래 파일에 연결하는 번호,
`line_number`는 템플릿의 0부터 시작하는 줄 번호입니다.

### PR 템플릿 처리 흐름

`.github/pull_request_template.md`는 최종 Markdown 양식입니다.
`template_instructions()`는 `prompts.py`의 고정 규칙에 빈 항목 목록과 원본 템플릿을 붙입니다.
AI는 채울 내용을 JSON으로 반환하고, `render_template()`이 다음 순서로 처리합니다.

1. JSON과 PR 제목을 검증합니다.
2. 응답의 항목이 템플릿의 빈 줄과 정확히 대응하는지 확인합니다.
3. 지정된 줄을 채우고 필수 섹션을 검증해 Markdown으로 반환합니다.

템플릿이 없으면 기본 Why·What·How to Test 형식으로 생성합니다.

### 함수 안의 import

`generation.py`는 AI 생성 함수를 사용할 때 `ai_client.py`를 불러옵니다.
이 덕분에 `openai`나 `python-dotenv`가 설치되지 않아도 도움말과 Git 상태 조회는 사용할 수 있습니다.
AI 생성이 필요한 시점에 패키지가 없으면 설치 안내를 출력합니다.

변수 이름과 설명을 정리했으며 실행 명령, 출력 형식, API 요청 횟수, 안전 모드 제한과 커밋 확인 절차는 유지합니다.
ㅁㄴㅇㄹㅁㄴㅇㄹ
