#!/bin/bash
# Python이 설치되어 있지 않아도 실행 가능한 가상환경 준비 단계.
# setup-venv.sh에서 호출하며 셸 설정이나 시스템 Python은 수정하지 않는다.
set -e

project_dir="$(cd -- "$(dirname -- "$0")/.." && pwd)"
python_version="3.14.7"
python_path="$project_dir/.venv/bin/python"

has_required_python() {
    [ -x "$python_path" ] && [ -f "$project_dir/.venv/bin/activate" ] &&
        "$python_path" -c 'import sys; sys.exit(0 if sys.version_info[:3] == (3, 14, 7) and sys.prefix != sys.base_prefix else 1)'
}

if has_required_python; then
    printf '[INFO] 기존 Python %s 가상환경을 재사용합니다.\n' "$python_version"
    exit 0
fi

tools_dir="$project_dir/.tools"
uv_path="$tools_dir/bin/uv"
mkdir -p "$tools_dir"

# uv와 Python, 다운로드 캐시 모두 프로젝트 안에 보관한다.
export UV_PYTHON_INSTALL_DIR="$tools_dir/python"
export UV_CACHE_DIR="$tools_dir/cache"
export UV_NO_CONFIG=1
export UV_NO_MODIFY_PATH=1

if [ ! -x "$uv_path" ]; then
    if ! command -v curl >/dev/null 2>&1; then
        printf '%s\n' '[ERROR] Python 설치 파일을 받으려면 curl이 필요합니다.' >&2
        exit 1
    fi
    printf '%s\n' '[INFO] 프로젝트 내부에 Python 설치 도구 uv를 준비합니다.'
    installer_path="$(mktemp "$tools_dir/uv-installer.XXXXXX")"
    trap 'rm -f -- "$installer_path"' EXIT
    curl --proto '=https' --tlsv1.2 -fLsS https://astral.sh/uv/install.sh -o "$installer_path"
    UV_UNMANAGED_INSTALL="$tools_dir/bin" sh "$installer_path"
fi

# 다운로드 실패 시 기존 .venv는 아직 이동하지 않은 상태로 보존된다.
printf '[INFO] Python %s를 프로젝트 내부에 설치합니다.\n' "$python_version"
"$uv_path" python install "$python_version" --no-bin

backup_dir=""
if [ -e "$project_dir/.venv" ] || [ -L "$project_dir/.venv" ]; then
    backup_dir="$(mktemp -d "$project_dir/.venv-backup.XXXXXX")"
    mv -- "$project_dir/.venv" "$backup_dir/.venv"
    printf '[INFO] 기존 가상환경 백업: %s/.venv\n' "$backup_dir"
fi

printf '[INFO] Python %s로 .venv를 생성합니다.\n' "$python_version"
if "$uv_path" venv --python "$python_version" --managed-python --seed "$project_dir/.venv" && has_required_python; then
    exit 0
fi

printf '%s\n' '[ERROR] Python 3.14.7 가상환경을 만들지 못했습니다.' >&2
if [ -n "$backup_dir" ]; then
    # 실패한 파일도 삭제하지 않고 보관한 뒤 기존 환경을 원래 위치로 복구한다.
    if [ -e "$project_dir/.venv" ] || [ -L "$project_dir/.venv" ]; then
        mv -- "$project_dir/.venv" "$backup_dir/failed-venv"
    fi
    mv -- "$backup_dir/.venv" "$project_dir/.venv"
    printf '%s\n' '[INFO] 기존 .venv를 복구했습니다.'
fi
exit 1
