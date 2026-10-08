# AI Git 메시지 도우미

Git 변경 내용을 분석해 한국어 커밋 메시지와 PR 초안을 만드는 Python CLI입니다.
교육기관의 OpenAI 호환 API를 사용하며, `--apply`를 지정하면 생성 결과를 검토한 뒤 실제 커밋 또는 GitHub PR 생성까지 진행할 수 있습니다.

## 주요 기능

- 변경 파일 목록과 스테이징 전후 diff 확인
- 전체 변경 또는 파일별 커밋 제목 생성
- 확인 후 전체 변경을 한 번에 커밋하거나 파일별로 별도 커밋
- 저장소 PR 템플릿을 적용한 제목·본문 생성
- 커밋된 브랜치 변경을 바탕으로 push 및 GitHub PR 생성
- 제목 길이·출력 형식 검증, API 오류 처리, 키 마스킹과 전송량 제한

기본 명령은 초안을 출력합니다. 실제 Git 변경이나 GitHub 등록은 `--apply` 실행 후 확인 질문에 `y`를 입력했을 때 진행합니다.

## 프로젝트 구조

```text
PR_AI_API/
├── .github/
│   └── pull_request_template.md  # PR 본문 양식
├── app/
│   ├── __init__.py
│   ├── __main__.py              # python -m app 진입점
│   ├── cli.py                   # 옵션, 출력, 사용자 확인
│   ├── git_client.py            # Git 실행과 파일별 커밋
│   ├── ai_client.py             # API 요청과 생성 결과 검증
│   ├── pr_template.py           # PR 템플릿 로딩과 빈 항목 채우기
│   └── github_client.py         # 브랜치 비교, push, GitHub PR 생성
├── tests/                      # 단위 테스트 및 임시 Git 저장소 테스트
├── .env.example                # 환경변수 설정 예시
├── .gitignore
├── requirements.txt
├── LICENSE.txt
└── README.md
```

실행할 때는 프로젝트 루트에서 `python -m app`을 사용합니다. 루트의 `main.py`는 사용하지 않습니다.

## 설치 및 설정

Python 3.10 이상과 Git이 필요합니다. 실제 PR 생성 기능에는 GitHub CLI(`gh`)도 필요합니다.

### 1. 저장소와 가상환경 준비

```bash
git clone https://github.com/PBK98/PR_AI_API.git
cd PR_AI_API

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

이미 저장소를 가지고 있다면 프로젝트 폴더에서 가상환경 설정부터 진행하세요.
새 터미널을 열 때마다 `source .venv/bin/activate`를 실행합니다.
활성화 없이 `.venv/bin/python -m app`으로 실행해도 됩니다.

### 2. API 키 설정

`.env`가 없는 경우에만 예시 파일을 복사합니다.

```bash
cp -n .env.example .env
```

`.env`를 열어 교육기관에서 발급받은 키를 입력하세요.

```dotenv
AI_API_KEY="교육기관에서 발급받은 키"
AI_BASE_URL=https://copa.codyssey.kr/v1
```

- 코드가 프로젝트 루트의 `.env`를 자동으로 읽습니다. 기존 셸 환경변수가 `.env`보다 우선합니다.
- `AI_BASE_URL`에는 `/chat/completions`를 붙이지 않습니다. 클라이언트가 해당 경로로 요청합니다.
- 기본 모델은 `gpt-5-mini`입니다. 교육기관에서 허용한 모델 ID를 사용하세요.
- `.env`는 Git에서 제외됩니다. `.env.example`에는 실제 키를 넣지 않습니다.

### 3. GitHub 로그인 — 실제 PR 생성 시

macOS/Homebrew 환경에서는 다음과 같이 준비합니다.

```bash
brew install gh
gh auth login
```

GitHub 인증은 교육기관 AI API 키와 별개입니다. `origin` 저장소에 push하고 PR을 생성할 권한이 필요합니다.

## 명령별 동작

| 명령 | 분석 대상 | 결과 |
| --- | --- | --- |
| `python -m app` | 현재 Git 상태와 diff | 터미널 출력, AI 호출 없음 |
| `python -m app commit` | 스테이징한 변경 우선, 없으면 스테이징 전 변경 | 커밋 제목 출력 |
| `python -m app commit --per-file` | 위와 동일 | 파일별 커밋 제목 출력 |
| `python -m app commit --apply` | 스테이징한 변경만 | 확인 후 하나의 커밋 생성 |
| `python -m app commit --per-file --apply` | 스테이징한 변경만 | 확인 후 파일당 별도 커밋 생성 |
| `python -m app pr` | 스테이징한 변경 우선, 없으면 스테이징 전 변경 | PR 제목·본문 출력 |
| `python -m app pr --apply` | 기준 브랜치와 공통 조상부터 현재 HEAD까지 커밋된 변경 | 확인 후 push 및 PR 생성 |

새 미추적 파일은 기본 diff에 포함되지 않습니다. 먼저 `git add 파일명`으로 스테이징하세요.
스테이징한 변경이 있으면 스테이징하지 않은 다른 변경은 생성 대상에서 제외됩니다.
초안 생성 시 변경이 없거나 미추적 파일만 있으면 AI를 호출하지 않습니다.

## 커밋 메시지 생성

```bash
# Git 변경 내용 확인
python -m app

# 전체 변경을 요약하는 제목
python -m app commit --safe-mode

# 파일별 제목
python -m app commit --per-file --safe-mode
```

출력 예시이며, 생성 문구는 실행마다 달라질 수 있습니다.

```text
--- Commit Message ---
feat: PR 템플릿 기반 초안 생성 추가
----------------------
```

파일별 출력 예시:

```text
--- Commit Messages by File ---

파일: 'app/pr_template.py'
feat: PR 템플릿 로딩 및 빈 항목 채우기 추가

파일: 'README.md'
docs: PR 템플릿 사용 방법 안내
----------------------
```

커밋 제목은 50자 이내를 권장하도록 요청하고, 최대 72자로 후처리합니다.

### 실제 커밋

```bash
# 포함할 파일을 선택해 스테이징
git add app/pr_template.py README.md

# 둘 중 원하는 방식을 실행
python -m app commit --safe-mode --apply
# 또는 파일마다 별도 커밋
python -m app commit --per-file --safe-mode --apply
```

출력된 메시지를 검토하고 `[y/N]` 질문에 `y`를 입력하면 커밋합니다.
Enter, 다른 입력, 확인 질문에서의 Ctrl+C 또는 입력 종료는 취소로 처리합니다.

자동 스테이징이나 push는 하지 않습니다. 부분 스테이징한 파일의 나머지 수정은 보존합니다.
생성 중 스테이징 내용이 바뀌면 중단하며, Git 사용자 설정이나 커밋 훅 오류를 안내합니다.
파일별 커밋 도중 실패하면 앞서 완료한 커밋은 유지됩니다. `git status`와 `git log`를 확인한 뒤 남은 변경을 처리하세요.

파일별 모드에서 이동은 이전 경로 삭제와 새 경로 추가로 나뉩니다.
모듈 이동처럼 함께 적용해야 하는 변경은 `--per-file` 없이 한 커밋으로 묶는 편이 좋습니다.

## PR 초안과 템플릿

커밋 전 변경으로 본문만 확인하려면 다음을 실행합니다.

```bash
python -m app pr --safe-mode
```

현재 저장소의 [.github/pull_request_template.md](.github/pull_request_template.md)를 자동 적용합니다.

- 헤더, 고정 문구, 기존 체크리스트는 유지합니다.
- 빈 체크박스 항목과 `- **라벨**:`의 빈 값 또는 `(예: ...)` 예시 값을 채웁니다.
- 관련 기능과 주요 변경 사항은 diff를 바탕으로 작성합니다.
- 작업자는 `확인 필요`로 표시합니다.
- 테스트 결과와 과제 체크리스트는 자동 체크하지 않습니다. 실제 확인 후 직접 수정하세요.

현재 템플릿을 적용한 본문 예시:

```markdown
## 📌 PR 개요
- **작업자**: 확인 필요
- **관련 기능**: PR 템플릿 기반 초안 생성

## 🛠️ 주요 변경 사항
- [ ] 저장소 PR 템플릿 자동 로딩
- [ ] 템플릿의 빈 항목 작성 및 결과 검증

## 🧪 테스트 및 동작 검증 결과
- [ ] 로컬 실행 및 정상 동작 확인
- [ ] 비정상 입력(공백 등) 예외 처리 확인

## 📋 과제 필수 체크리스트
- [ ] 코드 주석 및 docstring이 100% 한국어로 작성되었는가?
- [ ] API Key, 비밀번호 등 민감정보가 하드코딩되지 않고 `.env`로 격리되었는가?
- [ ] 절대 경로(`file:///`) 없이 상대 경로로 작성되었는가?
```

PR 제목은 한 줄, 최대 80자로 처리합니다.
템플릿이 없으면 `Why`, `What`, `How to Test`와 각 섹션의 불릿을 생성합니다.
빈 템플릿, 잘못된 JSON, 필수 항목 누락은 오류로 안내합니다. 자동 재생성은 하지 않습니다.

## GitHub에 실제 PR 생성

`pr --apply`는 **커밋을 마친 작업 브랜치**에서 실행합니다.
기준 브랜치와 현재 브랜치가 달라야 하며, 미추적 파일을 포함한 미커밋 변경이 없어야 합니다.

작업 흐름 예시:

```bash
# 새 작업을 시작할 때 브랜치 생성
git switch -c feature/my-change

# 파일을 수정한 뒤 원하는 파일을 스테이징하고 커밋
git add README.md
python -m app commit --safe-mode --apply

# 작업 파일이 정리됐는지 확인
git status

# 커밋된 브랜치 변경으로 PR 생성
python -m app pr --safe-mode --apply
```

기준 브랜치는 GitHub 저장소의 기본 브랜치를 사용합니다. 직접 지정하려면:

```bash
python -m app pr --safe-mode --apply --base main
```

실행 과정은 다음과 같습니다.

1. `origin`의 push 주소, 작업 상태, 브랜치, 기존 열린 PR을 확인합니다.
2. 기준 브랜치를 fetch하고 커밋된 변경으로 AI 초안을 생성합니다.
3. 대상 저장소·브랜치·제목·본문을 출력합니다.
4. `y`로 확인하면 검토한 커밋을 원격 브랜치로 push합니다.
5. GitHub PR을 생성하고 URL을 출력합니다.

`origin`은 `https://github.com/소유자/저장소.git` 또는 `git@github.com:소유자/저장소.git` 형식을 지원합니다.
자동 커밋, 강제 push, merge는 하지 않습니다. 생성 후 GitHub에서 작업자와 검증 결과를 검토·수정하세요.

같은 head/base의 열린 PR이 있으면 링크를 안내하고 종료합니다.
push 실패 시 PR을 만들지 않습니다. push 이후 PR 생성 확인에 실패하면 원격 브랜치는 남습니다.
GitHub에서 실제 PR 생성 여부를 확인한 뒤 재실행하세요.

## 옵션

| 옵션 | 기본값 | 설명 |
| --- | --- | --- |
| `--model` | `gpt-5-mini` | 교육기관에서 제공하는 모델 ID |
| `--temperature` | 생략 | 0~2. 지원하는 모델에만 지정 |
| `--max-tokens` | `2048` | 최소 16. `max_completion_tokens`로 전달하며 추론 토큰 포함 |
| `--safe-mode` | 꺼짐 | API에 보낼 diff 분량 제한 |
| `--per-file` | 꺼짐 | `commit` 전용. 파일별 제목 생성 및 선택적 커밋 |
| `--apply` | 꺼짐 | 확인 후 실제 커밋 또는 PR 생성 |
| `--base` | GitHub 기본 브랜치 | `pr --apply` 전용 기준 브랜치 |
| `-h`, `--help` | — | 도움말 출력 |

```bash
python -m app --help
python -m app commit --per-file --safe-mode --max-tokens 4096
```

모델마다 지원하는 옵션이 다를 수 있습니다. `temperature`를 생략하면 모델 기본값을 사용합니다.

## API 사용과 안전 모드

AI 요청은 생성 명령당 최대 1회이며, 파일별 모드에서도 한 번에 요청합니다.
자동 재시도는 하지 않고 응답 대기 제한은 60초입니다. 실제 사용량에 따라 교육기관의 크레딧이 차감될 수 있습니다.
GitHub 조회·fetch·push·PR 등록은 AI 요청 횟수와 별개입니다.

diff에 포함된 현재 API 키와 일반적인 `sk-` 패턴은 항상 마스킹합니다.
`--safe-mode`는 기본적으로 꺼져 있으므로 필요한 명령에 직접 붙이세요.

| 모드 | 안전 모드 제한 |
| --- | --- |
| 일반 커밋 / PR | diff 최대 200줄 및 20,000자 |
| 파일별 커밋 | 최대 10개 파일. 총 200줄/20,000자 예산을 파일 수로 균등 분배 |

생략 안내 문구와 파일별 JSON 포장은 제한 분량 외에 추가됩니다.
PR 템플릿 전체도 diff 제한과 별도로 전송됩니다.
파일별 안전 모드에서 10개를 넘으면 스테이징할 파일을 나누어 실행해야 합니다.

안전 모드는 모든 비밀번호·개인정보를 탐지하는 기능이 아닙니다. 전송할 diff와 템플릿을 확인하세요.
분량 제한으로 잘린 변경은 요약에서 빠질 수 있으며, 생성된 내용은 적용 전에 검토해야 합니다.

## 문제 해결

| 증상 | 확인할 내용 |
| --- | --- |
| `python: command not found` / `externally-managed-environment` | `source .venv/bin/activate` 후 설치·실행하거나 `.venv/bin/python` 사용 |
| 의존성 설치 안내 | 가상환경에서 `python -m pip install -r requirements.txt` 실행 |
| `AI_API_KEY` 누락 | 프로젝트 루트의 `.env`와 변수명 확인 |
| HTTP 401 | 교육기관 키와 `AI_BASE_URL` 확인. 이전 셸 키가 있으면 `unset AI_API_KEY` 후 재실행 |
| HTTP 400 | 모델과 옵션 지원 여부 확인 |
| HTTP 403 / 404 | 모델 이름 및 접근 권한 확인 |
| HTTP 429 | 교육기관 요청 한도·잔액 확인 |
| 응답 미완료 | `--max-tokens`를 늘려 재실행 |
| 변경 사항 없음 | 초안 모드는 미커밋 diff가 필요. 커밋된 브랜치의 PR 등록에는 `pr --apply` 사용 |
| 새 파일이 분석에서 빠짐 | `git add 파일명`으로 스테이징 |
| `--apply`에서 스테이징 안내 | 커밋할 파일을 먼저 `git add` |
| PR 생성 전 작업 상태 오류 | 미커밋·미추적 파일을 정리하고 기준 브랜치와 다른 작업 브랜치에서 실행 |
| GitHub CLI 인증 / push 실패 | `gh auth login`, Git 인증과 원격 저장소 권한 확인 |

## 테스트

프로젝트 루트에서 실행합니다.

```bash
python -m unittest discover -s tests -v
```

API 응답과 GitHub 등록은 모의 호출로 검증합니다.
실제 Git 커밋 동작은 임시 저장소에서 검증하므로 프로젝트의 커밋 이력을 바꾸지 않습니다.
테스트 실행은 AI API 비용을 발생시키거나 GitHub PR을 등록하지 않습니다.
