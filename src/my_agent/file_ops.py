"""파일 읽기·쓰기·치환 (워크스페이스 제한).

모든 경로는 workspace 루트 이하의 상대 경로만 허용합니다.
"""

from __future__ import annotations

from pathlib import Path

READ_MAX_CHARS = 200_000


def resolve_safe_path(workspace: Path, relative: str) -> Path:
    """작업 폴더 밖으로 나가지 않는 절대 경로를 반환합니다."""
    rel = (relative or "").strip().replace("\\", "/")
    if not rel or rel == ".":
        raise ValueError("파일 상대 경로는 비울 수 없습니다.")
    base = workspace.resolve()
    resolved = (base / rel).resolve()
    try:
        resolved.relative_to(base)
    except ValueError as e:
        raise PermissionError(
            f"작업 폴더 밖 경로는 사용할 수 없습니다: {relative!r}"
        ) from e
    return resolved


def read_file_content(workspace: Path, relative_path: str) -> str:
    """UTF-8로 파일을 읽습니다. 길면 앞부분만 잘라 반환합니다."""
    path = resolve_safe_path(workspace, relative_path)
    if not path.is_file():
        raise FileNotFoundError(f"파일이 없습니다: {relative_path!r}")
    raw = path.read_text(encoding="utf-8", errors="replace")
    if len(raw) > READ_MAX_CHARS:
        return (
            raw[:READ_MAX_CHARS]
            + f"\n\n… (앞 {READ_MAX_CHARS}자만 표시, 전체 {len(raw)}자)"
        )
    return raw


def write_file_content(workspace: Path, relative_path: str, content: str) -> str:
    """파일 전체를 덮어씁니다. 부모 디렉터리가 없으면 생성합니다."""
    path = resolve_safe_path(workspace, relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    return f"저장 완료: {relative_path} ({len(content)}자)"


def replace_in_file_content(
    workspace: Path,
    relative_path: str,
    old_string: str,
    new_string: str,
) -> str:
    """old_string이 처음 나타나는 한 곳만 new_string으로 바꿉니다."""
    if old_string == "":
        raise ValueError("old_string은 비울 수 없습니다.")
    path = resolve_safe_path(workspace, relative_path)
    if not path.is_file():
        raise FileNotFoundError(f"파일이 없습니다: {relative_path!r}")
    text = path.read_text(encoding="utf-8", errors="replace")
    if old_string not in text:
        raise ValueError(f"old_string이 파일에 없습니다: {relative_path!r}")
    updated = text.replace(old_string, new_string, 1)
    path.write_text(updated, encoding="utf-8", newline="\n")
    return f"치환 1회 적용: {relative_path}"
