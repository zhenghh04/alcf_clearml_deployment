"""Shared utilities used by both iri_launcher and submit_iri_job."""
from typing import Any, List, Optional

FACILITY_BASE_URLS = {
    "alcf": "https://api.alcf.anl.gov",
    "nersc": "https://api.nersc.gov",
    "olcf": "https://s3m.olcf.ornl.gov",
}


def clean_str(value: Any) -> str:
    """Return a stripped string, treating None/'none'/'null' as empty."""
    if value is None:
        return ""
    normalized = str(value).strip()
    if normalized.lower() in {"", "none", "null"}:
        return ""
    return normalized


def _escape_graphql_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _normalize_script_text(script_text: str) -> str:
    lines = []
    for raw_line in script_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#!"):
            continue
        lines.append(line)
    return "; ".join(lines)


def _combine_shell_text(prelude: str, main: str) -> str:
    parts = [part for part in (prelude, main) if part]
    return "; ".join(parts)


def _normalize_precommands(
    precommand: str = "",
    precommands: Optional[List[str]] = None,
) -> str:
    commands = []
    normalized_precommand = clean_str(precommand)
    if normalized_precommand:
        commands.append(normalized_precommand)
    if precommands:
        for item in precommands:
            normalized = clean_str(item)
            if normalized:
                commands.append(normalized)
    normalized_commands = []
    for command in commands:
        text = _normalize_script_text(command)
        if text:
            normalized_commands.append(text)
    return "; ".join(normalized_commands)
