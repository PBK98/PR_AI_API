"""설치된 앱과 설정을 사용해 지정한 Git 프로젝트에서 실행한다."""

import os
from pathlib import Path
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("[ERROR] 실행할 프로젝트 경로를 하나 지정하세요.", file=sys.stderr)
        return 1

    repository_dir = Path(sys.argv[1]).resolve()
    if not (repository_dir / ".git").exists():
        print("[ERROR] Git 프로젝트의 루트 폴더를 편집기로 열어주세요.", file=sys.stderr)
        return 1

    app_dir = Path(__file__).resolve().parent.parent
    # 대상 프로젝트에 app 패키지가 있어도 이 도구의 app을 사용한다.
    sys.path.insert(0, str(app_dir))
    try:
        from dotenv import dotenv_values
    except ImportError:
        print("[ERROR] PR_AI_API의 가상환경에 requirements.txt를 설치하세요.", file=sys.stderr)
        return 1

    # 도구의 API 설정만 가져온다. 기존 셸 설정이 있으면 우선한다.
    settings = dotenv_values(app_dir / ".env", interpolate=False)
    for name in ("AI_API_KEY", "AI_BASE_URL"):
        value = settings.get(name)
        if value is not None:
            os.environ.setdefault(name, value)

    os.chdir(repository_dir)
    print(f"[INFO] 실행 대상 프로젝트: {repository_dir}", flush=True)
    from app.runner import main as run_app

    sys.argv = ["app", "commit", "--safe-mode", "--per-file", "--apply"]
    return run_app()


if __name__ == "__main__":
    raise SystemExit(main())
