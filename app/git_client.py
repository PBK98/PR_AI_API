"""Git 명령 실행과 결과 수집."""

import os
import subprocess
import tempfile
from pathlib import Path


def run_git(*args: str, env: dict[str, str] | None = None, input_text: str | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env=env,
        input=input_text,
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


def commit_staged_file(path: str, message: str) -> str:
    """임시 인덱스에 한 파일의 staged diff만 적용해 커밋한다.

    실제 인덱스와 작업 파일은 그대로 두므로 나머지 staged 변경과
    같은 파일의 unstaged 변경이 보존된다.
    """
    patch = run_git("diff", "--cached", "--binary", "--no-renames",
                    "--no-ext-diff", "--no-textconv", "--", ":(literal)" + path)
    if not patch.strip():
        raise RuntimeError(f"{path!r}: 스테이징된 변경이 없습니다.")
    with tempfile.TemporaryDirectory(prefix="ai-git-index-") as directory:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(directory) / "index"))
        # 최초 커밋 전 HEAD가 없으면 빈 tree로 시작한다.
        head = subprocess.run(["git", "rev-parse", "--verify", "--quiet", "HEAD"],
                              capture_output=True, text=True)
        if head.returncode == 0:
            run_git("read-tree", head.stdout.strip(), env=env)
        elif head.returncode == 1:
            run_git("read-tree", "--empty", env=env)
        else:
            raise RuntimeError("현재 HEAD를 확인할 수 없습니다.")
        run_git("apply", "--cached", "--binary", "--whitespace=nowarn", env=env, input_text=patch)
        return run_git("commit", "-m", message, env=env)
