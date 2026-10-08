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
