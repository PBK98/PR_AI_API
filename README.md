# AI Git 메시지 도우미

Git 변경 사항을 확인하고 교육기관의 OpenAI 호환 API로 한국어 커밋 제목과 PR 초안을 생성하는 Python CLI입니다.

## 준비

Python 3.10 이상과 Git이 필요합니다. 프로젝트 루트에서 실행하세요.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

로컬 `.env`에 교육기관에서 발급받은 API 키를 입력하세요. 새 환경에서는 `.env.example`을
`.env`로 복사합니다. 기존 `.env`는 덮어쓰지 마세요.

```dotenv
AI_API_KEY="발급받은 실제 키"
AI_BASE_URL=https://copa.codyssey.kr/v1
```

`.env`는 자동으로 읽으며 이미 설정된 환경변수가 우선합니다.
키를 코드나 커밋에 넣지 마세요.

## 실행

```bash
# API 호출 없이 변경 파일 및 스테이징 전후 diff 확인
python main.py

# 커밋 제목 생성 (실제 커밋은 하지 않음)
python main.py commit --safe-mode

# PR 제목과 본문 생성 (실제 GitHub PR은 만들지 않음)
python main.py pr --safe-mode

# API 옵션 조정
python main.py commit --model gpt-5-mini --max-tokens 2048 --safe-mode
```

스테이징한 변경이 있으면 그 변경만 사용합니다. 없으면 스테이징 전 변경을 사용합니다.
새 미추적 파일은 diff에 포함되지 않으므로 `git add 파일명` 후 실행하세요.
변경이 없거나 미추적 파일만 있으면 API를 호출하지 않습니다.

출력 예시 (생성 문구는 달라질 수 있습니다):

```text
[INFO] 생성 대상: 스테이징한 변경
[INFO] AI API 요청 중... (요청 1회, 자동 재시도 없음)

--- Commit Message ---
chore: 테스트 텍스트 파일 추가
----------------------
```

커밋 제목은 50자 이내를 권장하도록 요청하고 최대 72자로 후처리합니다.
생성된 내용은 사용자가 검토한 뒤 직접 커밋하세요.

## PR 초안

`pr`도 스테이징한 변경을 우선 사용하고, 없으면 스테이징 전 변경을 사용합니다.
이미 커밋한 변경이나 브랜치 전체 이력은 수집하지 않습니다.
PR에 넣을 변경을 커밋하기 전에 초안을 생성해 복사해 두세요.

```text
--- PR Title ---
feat: PR 초안 생성 명령 추가

--- PR Body ---
## Why
- 변경 배경 확인 필요

## What
- Git 변경 내용을 바탕으로 PR 제목과 본문 생성

## How to Test
- 제안(미실행): python main.py pr --safe-mode 실행 후 출력 형식 확인
```

API에 JSON 형식의 초안을 요청한 뒤 제목을 한 줄, 최대 80자로 다듬습니다.
Why/What/How to Test 섹션과 각 섹션의 불릿을 생성하며, 필수 내용 누락이나
잘못된 JSON은 오류로 안내합니다. 자동으로 추가 API 요청을 보내지 않습니다.
변경 배경이 불명확하면 확인 필요로 표시하도록 요청하며, 테스트 방법은
미실행 제안으로 작성하도록 요청합니다. 생성 내용의 사실 여부는 직접 검토하세요.
초안을 복사해 GitHub에서 PR을 직접 작성합니다.

## API 옵션과 오류

- 기본 모델: `gpt-5-mini`
- `--temperature`: 기본 생략(모델 기본값), 범위 0~2. 지원하는 모델에만 지정하세요.
- `--max-tokens`: 기본 2048, 최소 16. `max_completion_tokens`로 전달하며 추론 토큰도 포함합니다.
- 다른 모델은 옵션 지원 여부가 다를 수 있습니다. HTTP 400이면 모델과 옵션을 확인하세요.
- 키 누락, 인증 실패, 권한 부족, 요청 한도/잔액 부족, 연결 실패, 타임아웃을 안내합니다.
- 실행당 API 요청은 1회이며 자동 재시도하지 않습니다. 실행 시 API 사용 비용이 발생할 수 있습니다.

## 민감정보 및 안전 모드

API에는 선택된 diff를 전송합니다. 사용 중인 API 키와 일반적인 `sk-` 키 패턴은
항상 마스킹합니다. `--safe-mode`는 diff를 최대 200줄 및 20,000자로 제한합니다.
이 제한은 모든 개인정보나 비밀을 제거하는 기능이 아니므로 전송할 변경을 먼저 확인하세요.
제한으로 잘린 경우 일부 변경이 요약에서 누락될 수 있습니다.

## 검증

```bash
python -m unittest discover -s tests -v
```

테스트는 가짜 키와 모의 API 응답을 사용하며 네트워크를 호출하지 않습니다.

## 참고

[OpenAI Chat Completions 공식 문서](https://developers.openai.com/api/reference/python/resources/chat/subresources/completions/methods/create)

교육기관 서버의 `/v1/chat/completions`를 사용합니다. `AI_BASE_URL`에는
`/chat/completions`를 붙이지 마세요. 기본 주소는 `https://copa.codyssey.kr/v1`입니다.

## 프로젝트 구조

```text
PR_AI_API/
├── main.py              # 기존 실행 명령을 위한 진입점
├── app/
│   ├── __init__.py       # Python 패키지 선언
│   ├── __main__.py       # python -m app 진입점
│   ├── cli.py            # 옵션 처리와 커밋/PR 출력
│   ├── git_client.py     # Git 명령 실행
│   └── ai_client.py      # API 호출, 프롬프트, 결과 검증
├── tests/               # 모의 API 및 CLI 테스트
├── requirements.txt
└── .env                 # 프로젝트 루트에서 읽는 로컬 설정
```

프로젝트 루트에서 기존 명령과 모듈 실행 방식 모두 사용할 수 있습니다.

```bash
python main.py commit --safe-mode
python -m app commit --safe-mode
python -m app pr --safe-mode
```

`app/` 안의 파일을 직접 실행하지 말고 위 진입점을 사용하세요.

## 파일별 커밋 메시지

```bash
python -m app commit --per-file --safe-mode
```

선택된 diff의 각 파일에 대해 제목 하나씩 출력합니다. 실제 커밋은 하지 않습니다.
스테이징한 변경이 있으면 그 파일들만, 없으면 스테이징 전 변경을 분석합니다.
새 파일은 먼저 `git add 파일명`으로 스테이징해야 합니다.
이동은 기존 경로 삭제와 새 경로 추가로 나누어 분석합니다.
모듈 이동처럼 서로 의존하는 변경은 실제 커밋 시 하나로 묶는 편이 좋습니다.

API 요청은 파일 수와 관계없이 1회입니다. `--safe-mode`에서는 최대 10개 파일을
허용하며, diff 총 200줄/20,000자 예산을 파일 수로 균등 분배합니다(JSON 포장 제외).
파일이 10개를 넘으면 오류로 안내하므로 스테이징할 파일을 나누어 실행하세요.
잘못된 파일 ID, 누락, 중복, 빈 제목은 오류로 처리합니다.
응답이 길어져 토큰 한도에 걸리면 `--max-tokens 4096` 등으로 조정할 수 있습니다.

## 확인 후 실제 커밋 (선택)

```bash
# 커밋할 파일을 명시적으로 선택
git add app/cli.py
python -m app commit --safe-mode --apply
```

`--apply`는 생성된 제목을 출력하고 `[y/N]` 확인 질문을 표시합니다.
`y`를 입력한 경우에만 스테이징된 변경 전체를 하나의 커밋으로 저장합니다.
Enter, 다른 입력, Ctrl+C, 입력 종료는 커밋을 취소합니다.
자동 `git add` 또는 push는 하지 않습니다. 스테이징되지 않은 변경은 포함하지 않습니다.
스테이징된 변경이 없으면 API 호출 전에 안내하고 종료합니다.
메시지 생성 후 스테이징 내용이 달라지면 커밋을 중단하고 재실행을 안내합니다.
Git 사용자 설정이나 커밋 훅 오류는 터미널에 표시합니다.

`commit --apply`는 `--per-file`과 함께 사용할 수 있습니다.
기본 실행은 과제 범위인 초안 출력만 수행합니다.


### 파일마다 별도 커밋

```bash
python -m app commit --per-file --safe-mode --apply
```

파일별 제목을 모두 검토하고 `y`를 입력하면 표시 순서대로 파일당 커밋을 하나씩 만듭니다.
각 커밋에는 해당 파일의 스테이징된 내용만 포함됩니다. 부분 스테이징한 파일의
나머지 수정과 다른 파일의 스테이징 상태는 유지됩니다. 자동 push는 하지 않습니다.
중간에 Git 훅 등으로 실패하면 즉시 중단하며, 앞서 완료한 커밋은 유지합니다.
`git status`와 `git log`를 확인한 뒤 남은 변경을 다시 실행하세요.
이동은 삭제/추가로 분리되므로, 원자적으로 적용해야 하는 모듈 이동 등은
`--per-file` 없이 하나의 커밋으로 적용하는 것을 권장합니다.


## GitHub PR 실제 생성 (선택)

GitHub CLI가 필요하며, AI API 키와 별도로 GitHub 로그인이 필요합니다.

```bash
brew install gh
gh auth login
```

기준 브랜치(main 등)와 다른 작업 브랜치에서 변경을 커밋한 뒤 실행하세요.
작업 파일과 인덱스는 깨끗해야 합니다.

```bash
python -m app pr --safe-mode --apply
# 기준 브랜치를 직접 지정하려면
python -m app pr --safe-mode --apply --base main
```

`pr`만 실행하면 기존처럼 미커밋 변경의 초안을 출력합니다.
`pr --apply`는 origin의 push 주소(GitHub HTTPS/SSH)를 대상으로 하며,
기준 브랜치를 fetch하고 공통 조상부터 현재 HEAD까지 커밋된 변경을 요약합니다.
기준 브랜치는 GitHub 기본 브랜치를 사용하거나 `--base`로 지정합니다.
원격과 작업 브랜치 이름, PR 제목 및 본문을 보여준 후 `y`로 확인하면
검토한 커밋을 해당 브랜치로 push하고 PR을 생성하여 링크를 출력합니다.
Enter, 다른 입력, Ctrl+C는 취소합니다. 자동 커밋, 강제 push, merge는 하지 않습니다.

동일한 head/base의 열린 PR이 있으면 링크를 안내하고 종료합니다.
push가 실패하면 PR을 만들지 않습니다. push 이후 PR 생성 확인에 실패하면
원격 브랜치는 남으므로 GitHub에서 PR 생성 여부를 확인한 뒤 다시 실행하세요.
이 기능은 과제의 기본 초안 출력 범위를 확장하는 선택 기능입니다.

[GitHub CLI PR 생성 공식 문서](https://cli.github.com/manual/gh_pr_create)
