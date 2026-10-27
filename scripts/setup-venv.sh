#!/bin/bash
# 관리자 권한 없이 초기 설정을 하고 가상환경 셸을 연다.
# 직접 실행: bash scripts/setup-venv.sh
# 현재 셸에 적용: source scripts/setup-venv.sh

_pr_ai_sourced=false
if [ -n "${ZSH_VERSION:-}" ]; then
    case "$ZSH_EVAL_CONTEXT" in
        *:file) _pr_ai_sourced=true ;;
    esac
elif [ -n "${BASH_VERSION:-}" ]; then
    if [ "${BASH_SOURCE[0]}" != "$0" ]; then
        _pr_ai_sourced=true
    fi
else
    printf '%s\n' 'bash scripts/setup-venv.sh 로 실행하세요.' >&2
    return 1 2>/dev/null || exit 1
fi

_pr_ai_setup_venv() {
    local script_path project_dir python_path
    if [ -n "${ZSH_VERSION:-}" ]; then
        script_path="${(%):-%x}"
    else
        script_path="${BASH_SOURCE[0]}"
    fi
    project_dir="$(cd -- "$(dirname -- "$script_path")/.." && pwd)" || return 1
    python_path="$project_dir/.venv/bin/python"

    if [ "$_pr_ai_sourced" = false ] && [ ! -t 0 ]; then
        printf '%s\n' '[ERROR] 가상환경 셸을 열 수 있도록 터미널에서 직접 실행하세요.' >&2
        return 1
    fi

    if [ ! -f "$project_dir/requirements.txt" ]; then
        printf '%s\n' '[ERROR] requirements.txt를 찾을 수 없습니다.' >&2
        return 1
    fi

    # 먼저 정확한 Python 버전을 확보한 뒤 그 Python으로 가상환경을 만든다.
    bash "$project_dir/scripts/prepare-python.sh" || return 1
    "$python_path" --version || return 1

    # pip도 가상환경의 Python으로 실행해 시스템 Python에 설치하지 않는다.
    printf '%s\n' '[INFO] requirements.txt의 패키지를 설치·확인합니다.'
    # 사용자 pip 설정의 전역 설치 옵션을 피하고 설치 대상도 .venv로 고정한다.
    PIP_CONFIG_FILE=/dev/null "$python_path" -m pip --isolated install \
        --require-virtualenv --prefix "$project_dir/.venv" \
        -r "$project_dir/requirements.txt" || return 1

    # 설치가 성공한 경우에만 현재 터미널의 Python을 전환한다.
    source "$project_dir/.venv/bin/activate" || return 1
    printf '[DONE] 가상환경 활성화: %s\n' "$VIRTUAL_ENV"
    printf '%s\n' '프로젝트 폴더에서 python -m app 명령을 사용할 수 있습니다.'

    if [ "$_pr_ai_sourced" = false ]; then
        cd -- "$project_dir" || return 1
        printf '%s\n' '[INFO] 가상환경이 적용된 Bash 셸을 엽니다. exit로 원래 셸로 돌아갑니다.'
        # 시작 설정이 PATH를 덮어쓰지 않도록 초기화 파일 없이 셸을 연다.
        export PS1='(.venv) \w \$ '
        export BASH_SILENCE_DEPRECATION_WARNING=1
        exec /bin/bash --noprofile --norc -i
    fi
}

if _pr_ai_setup_venv; then
    unset -f _pr_ai_setup_venv
    unset _pr_ai_sourced
else
    unset -f _pr_ai_setup_venv
    if [ "$_pr_ai_sourced" = true ]; then
        unset _pr_ai_sourced
        return 1
    fi
    unset _pr_ai_sourced
    exit 1
fi
