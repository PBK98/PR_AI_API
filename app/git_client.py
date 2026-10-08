"""Git 명령 실행과 결과 수집."""

import subprocess


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Git 명령 실행에 실패했습니다.")
    return result.stdout


def collect_file_diffs(staged: bool) -> dict[str, str]:
    """파일 경로를 NUL로 구분해 수집한다. 이동은 삭제/추가로 표시한다."""
    options = ["--cached"] if staged else []
    names = run_git("diff", *options, "--no-renames", "--name-only", "-z")
    return {
        name: run_git("diff", *options, "--no-renames", "--no-ext-diff", "--no-textconv",
                      "--", ":(literal)" + name)
        for name in names.split("\0") if name
    }
