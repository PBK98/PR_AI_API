# 실행 증빙

2026-10-08 실행. 임시 Git 저장소의 예제 변경을 사용했다. 실제 키는 출력하지 않았다.

## 변경 없음 — 실제 CLI, API 호출 없음

명령: `python -m app commit` / 종료 코드: 0

```text
[INFO] 변경 사항이 없습니다.
```

## Git 상태 및 diff — 실제 CLI

명령: `python -m app ` / 종료 코드: 0

```text
--- 변경된 파일 (git status) ---
A  greeting.py

--- 스테이징 전 변경 (git diff) ---
변경 내용이 없습니다.
--- 스테이징한 변경 (git diff --cached) ---
diff --git a/greeting.py b/greeting.py
new file mode 100644
index 0000000..83ebfb9
--- /dev/null
+++ b/greeting.py
@@ -0,0 +1,3 @@
+def greet(name):
+    """이름 앞뒤 공백을 제거하여 인사말을 반환한다."""
+    return f"안녕하세요, {name.strip()}님!"
```

## 키 누락 — 테스트 환경에서 키 제거, API 호출 없음

명령: `python -m app commit` / 종료 코드: 1

```text
[INFO] 생성 대상: 스테이징한 변경
[ERROR] AI_API_KEY가 없습니다. .env 또는 환경변수에 교육기관 API 키를 설정하세요.
```

## 커밋 생성 — 실제 교육기관 API 1회

명령: `python -m app commit --safe-mode` / 종료 코드: 0

```text
[INFO] 미추적 파일은 제외됩니다. 새 파일은 git add 후 실행하세요.
[INFO] 생성 대상: 스테이징한 변경
[INFO] AI API 요청 중... (요청 1회, 자동 재시도 없음)

--- Commit Message ---
feat: 공백 제거 후 인사 문자열 반환하는 greet 함수 추가
----------------------
```

## PR 생성 — 실제 교육기관 API 1회

명령: `python -m app pr --safe-mode` / 종료 코드: 0

```text
[INFO] 미추적 파일은 제외됩니다. 새 파일은 git add 후 실행하세요.
[INFO] 생성 대상: 스테이징한 변경
[INFO] .github/pull_request_template.md 양식을 적용합니다.
[INFO] AI API 요청 중... (요청 1회, 자동 재시도 없음)

--- PR Title ---
greeting.py 추가 — greet(name) 함수로 공백 제거한 한글 인사 반환

--- PR Body ---
## 📌 PR 개요
- **작업자**: 확인 필요
- **관련 기능**: greeting.py의 greet(name) 함수 추가 — 입력 이름의 앞뒤 공백을 제거하고 한글 인사 문자열을 반환

## Why
- 변경 배경 확인 필요

## What
- greeting.py 신규 파일 추가 및 greet(name) 정의: name.strip()을 사용해 공백 제거 후 문자열 반환
- 추가 변경 사항 없음

## How to Test
- 제안(미실행): greet(' Alice ') 호출 시 '안녕하세요, Alice님!' 반환 확인; 빈 문자열 및 공백만 입력에 대한 동작 확인

## 🧪 테스트 및 동작 검증 결과
- [ ] 로컬 실행 및 정상 동작 확인
- [ ] 비정상 입력(공백 등) 예외 처리 확인

## 📋 과제 필수 체크리스트
- [ ] 코드 주석 및 docstring이 한국어로 작성되었는가?
- [ ] API Key, 비밀번호 등 민감정보가 하드코딩되지 않고 `.env`로 격리되었는가?
- [ ] Why/What/How to Test 섹션과 각 섹션의 불릿이 포함되었는가?

----------------------
```

## 안전 모드 비교 — 합성 입력, API 호출 없음

입력 251줄. OFF: 251줄, ON: 201줄(생략 안내 1줄 포함).
가짜 키는 두 모드 모두 마스킹됨: True.

## 자동 테스트 — 모의 API

인증·연결 실패, 응답 형식, 길이, 누락, 템플릿, 안전 모드를 검사한다. 실제 실패 API를 호출한 증빙과 구분한다.

```text
----------------------------------------------------------------------
Ran 26 tests in 0.006s

OK
```
