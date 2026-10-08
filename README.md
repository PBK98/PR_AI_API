# AI Git 메시지 도우미

Git 변경 내용을 읽어 한국어 커밋 메시지와 PR 초안을 생성하는 Python CLI입니다.
교육기관의 OpenAI 호환 Chat Completions API를 사용합니다.
기본 실행은 초안만 출력합니다. `commit --apply`는 확인 후 로컬 커밋을 생성하며, push와 GitHub PR 등록은 사용자가 직접 수행합니다.

## 설치

Python 3.10 이상과 Git이 필요합니다. 프로젝트 루트에서 실행하세요.

```bash
git clone https://github.com/PBK98/PR_AI_API.git
cd PR_AI_API
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp -n .env.example .env
```

이미 저장소와 가상환경이 있으면 활성화부터 실행하세요. `.env`를 열어 키를 입력합니다.

```dotenv
AI_API_KEY="교육기관에서 발급받은 키"
AI_BASE_URL=https://copa.codyssey.kr/v1
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
API 키 원문과 일반적인 `sk-` 패턴은 diff에서 마스킹합니다.

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
  __main__.py       # python -m app 진입점
  cli.py            # 명령 및 출력
  git_client.py     # Git 상태·diff 수집
  ai_client.py      # API 연결·프롬프트·결과 검증
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
