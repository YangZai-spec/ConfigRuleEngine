from pathlib import Path

MARKERS = ("run_checks.py", "requirements.txt")

def find_project_root(start: Path | None = None) -> Path:
    """从 start 向上回溯, 找到包含任一标记文件的目录作为项目根。"""
    current = (start or Path(__file__)).resolve()
    for parent in [current, *current.parents]:
        if any((parent / m).exists() for m in MARKERS):
            return parent
    raise FileNotFoundError(f"未在 {current} 的任何上级目录中找到项目标记 {MARKERS}")


PROJECT_ROOT = find_project_root()
