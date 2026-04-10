import json
from pathlib import Path
from typing import Any

from .dedup import normalize_history_data


def _log(logger_obj: Any, level: str, message: str):
    log_func = getattr(logger_obj, level, None)
    if callable(log_func):
        log_func(message)


def load_json(path: Path, default: Any, logger_obj: Any = None):
    """Load JSON file with default fallback."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(default, ensure_ascii=False, indent=2), "utf-8")
        return default

    try:
        return json.loads(path.read_text("utf-8"))
    except json.JSONDecodeError:
        if logger_obj is not None:
            _log(logger_obj, "error", f"JSON文件解析失败，重置为默认值：{path}")
        path.write_text(json.dumps(default, ensure_ascii=False, indent=2), "utf-8")
        return default


def save_json(path: Path, data: Any):
    """Save JSON data to file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


def load_history_file(path: Path, logger_obj: Any = None) -> dict:
    """Load history JSON and normalize structure."""
    raw_history = load_json(path, {"users": {}}, logger_obj=logger_obj)
    return normalize_history_data(raw_history)
