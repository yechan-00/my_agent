"""my_agent: 로컬 Ollama(Qwen) 멀티턴·도구 연동 에이전트."""

from my_agent.agent import AUTO_MODEL, COURSE_MODEL, Agent, pick_installed_model
from my_agent.file_ops import (
    read_file_content,
    replace_in_file_content,
    resolve_safe_path,
    write_file_content,
)
from my_agent.namuwiki import fetch_namuwiki_raw, search_namuwiki
from my_agent.persona import DEFAULT_SYSTEM
from my_agent.tools import TOOL_DEFINITIONS, TOOL_NAMES, dispatch_tool

__all__ = [
    "Agent",
    "AUTO_MODEL",
    "COURSE_MODEL",
    "DEFAULT_SYSTEM",
    "fetch_namuwiki_raw",
    "search_namuwiki",
    "TOOL_DEFINITIONS",
    "TOOL_NAMES",
    "dispatch_tool",
    "pick_installed_model",
    "read_file_content",
    "replace_in_file_content",
    "resolve_safe_path",
    "write_file_content",
]
__version__ = "0.1.0"
