#!/bin/zsh
# 앱은 이 프로젝트에서, Git 작업 대상은 전달받은 경로에서 찾는다.
project_dir="$(cd -- "$(dirname -- "$0")/.." && pwd)" || exit 1
repository_dir="${1:-$project_dir}"

python_path="$project_dir/.venv/bin/python"
if [[ ! -x "$python_path" ]]; then
    print -u2 -- "[ERROR] 프로젝트의 .venv/bin/python을 찾을 수 없습니다."
    print -u2 -- "프로젝트 폴더에서 가상환경과 requirements.txt의 패키지를 먼저 설치하세요."
    exit_code=1
else
    # 자동 스테이징 없이, 앱의 확인 질문을 거쳐 파일별로 커밋한다.
    "$python_path" "$project_dir/scripts/run_in_repository.py" "$repository_dir"
    exit_code=$?
fi

# Finder 또는 단축어로 실행해도 결과를 읽을 수 있도록 기다린다.
if [[ -t 0 ]]; then
    printf '\n종료하려면 Enter를 누르세요. '
    IFS= read -r reply
fi
exit "$exit_code"
