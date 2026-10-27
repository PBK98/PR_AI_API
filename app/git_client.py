"""Git 명령 실행과 결과 수집."""

import os
import subprocess
import tempfile
from pathlib import Path


def run_git(*args: str, env: dict[str, str] | None = None, input_text: str | None = None) -> str:
    """Git을 실행해 표준출력을 반환하고 실패 시 RuntimeError를 발생시킨다.

    args는 Git 명령과 인자, env는 자식 프로세스의 환경변수다.
    input_text는 파일별 커밋의 patch처럼 표준입력으로 전달할 문자열이다.
    """
    # 문자열을 셸에 넘기지 않고 인자 목록을 전달해 공백과 특수문자가 있는 경로를 보존한다.
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
    # 성공 코드는 0이다. check=False로 받은 결과를 여기서 공통 예외로 변환한다.
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Git 명령 실행에 실패했습니다.")
    return result.stdout


def collect_file_diffs(staged: bool) -> dict[str, str]:
    """파일 경로를 NUL로 구분해 수집한다. 이동은 삭제/추가로 표시한다."""
    options = ["--cached"] if staged else []
    # -z는 파일명 구분자를 NUL로 만든다. 파일명에 공백/줄바꿈이 있어도 분리할 수 있다.
    # --no-renames는 이동을 삭제와 추가로 나누어 파일마다 독립적으로 다룬다.
    names = run_git("diff", *options, "--no-renames", "--name-only", "-z")
    # -- 뒤는 경로다. :(literal)은 [abc] 같은 문자를 실제 파일명으로 처리한다.
    return {
        name: run_git(
            "diff", *options, "--no-renames", "--no-ext-diff", "--no-textconv",
            "--", ":(literal)" + name,
        )
        for name in names.split("\0") if name
    }


def commit_staged_file(path: str, message: str) -> str:
    """임시 인덱스에 한 파일의 staged diff만 적용해 커밋한다.

    실제 인덱스와 작업 파일은 그대로 두므로 나머지 staged 변경과
    같은 파일의 unstaged 변경이 보존된다.
    """
    # 작업 파일이 아니라 인덱스에 올라간 변경만 읽는다. --binary는 바이너리 변경도 담는다.
    patch = read_staged_file_patch(path)
    if not patch.strip():
        raise RuntimeError(f"{path!r}: 스테이징된 변경이 없습니다.")
    with tempfile.TemporaryDirectory(prefix="ai-git-index-") as directory:
        # GIT_INDEX_FILE은 이 함수의 자식 Git 명령에만 임시 인덱스를 지정한다.
        # 실제 인덱스를 초기화하거나 작업 파일을 덮어쓰지 않는다.
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(directory) / "index"))
        initialize_commit_index(env)
        # HEAD 상태에 선택한 파일의 patch만 더한 인덱스를 커밋한다.
        # 커밋으로 HEAD가 바뀌면 실제 인덱스의 나머지 변경은 그대로 staged 상태로 남는다.
        run_git("apply", "--cached", "--binary", "--whitespace=nowarn", env=env, input_text=patch)
        return run_git("commit", "-m", message, env=env)


def initialize_commit_index(env: dict[str, str]) -> None:
    """임시 인덱스를 HEAD로 채우고 최초 커밋이면 빈 tree로 준비한다."""
    # 최초 커밋 전 HEAD가 없으면 빈 tree로 시작한다.
    head = subprocess.run(["git", "rev-parse", "--verify", "--quiet", "HEAD"],
                          capture_output=True, text=True)
    if head.returncode == 0:
        run_git("read-tree", head.stdout.strip(), env=env)
    elif head.returncode == 1:
        run_git("read-tree", "--empty", env=env)
    else:
        raise RuntimeError("현재 HEAD를 확인할 수 없습니다.")


def read_staged_snapshot() -> str:
    """커밋 직전 검증에 사용할 전체 스테이징 변경을 바이너리 내용까지 읽는다."""
    return run_git("diff", "--cached", "--binary", "--no-ext-diff", "--no-textconv")


def read_staged_file_patch(path: str) -> str:
    """한 파일의 스테이징 변경을 읽는다. 특수문자가 있는 경로도 그대로 취급한다."""
    return run_git(
        "diff", "--cached", "--binary", "--no-renames",
        "--no-ext-diff", "--no-textconv", "--", ":(literal)" + path,
    )
