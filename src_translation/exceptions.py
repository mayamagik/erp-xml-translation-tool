from __future__ import annotations

import re
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable

from .models import TranslationItem
from .protect_text import Protector


SELECTION_HELP_UNIT_PATTERNS: list[str] = [
    "_XlsMsg_Resources*",
    "_FunctionNames*",
    "PythonEngine",
    "_FlxMsg_Resources*",
    "_FormulaMsg_Resources*",
    "__Flx*",
    "__U*",
    "System*",
    "Vcl*",
    "SynEditStrConst_SYNS",
    "OverbyteIcsCharsetUtils",
    "JclResources",
    "IdResourceStrings",
    "Hlp*",
    "FireDAC*",
    "dx*",
    "Data_DBConsts",
    "Data_Bind_Consts",
    "cx*",
]

PLAIN_PROTECT_PREFIXES: tuple[str, ...] = (
    "btn", "ac", "act", "cx", "dx", "lbl", "lb", "tb", "cb", "rb", "chk", "edt",
    "txt", "mnu", "grd", "pnl", "pg", "tab", "te", "ah", "jmp", "gc", "cp", "tsh",
    "rbtn", "ed", "chbx", "lcl", "fie", "lg", "gb", "fm", "lyi", "cbx", "dp", "pan",
    "chx", "tfrm", "lc", "lyg", "lys", "lsi", "cmb", "grp", "dlg", "wnd", "frm", "tv",
    "lv", "gv", "sv", "rv", "pb", "pm", "pop", "res", "str", "msg", "err", "warn",
    "hint", "tip", "sql", "qry", "conn", "cmd", "dm", "ds",
)

CAPITAL_AFTER_PREFIXES: tuple[str, ...] = ("li", "mi", "se", "a")

WHOLE_TOKEN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^ToolButton\d+$", re.IGNORECASE),
    re.compile(r"^Prop(?:GUID|ID|Name)$", re.IGNORECASE),
    re.compile(r"^Page(?:Background|Setup|Width)$", re.IGNORECASE),
    re.compile(r"^PrintDialog$", re.IGNORECASE),
    re.compile(r"^Jmp[A-Za-z0-9_]+$"),
)

ALL_CAPS_ABBREV = re.compile(r"^[A-Z]{2,8}(?:[0-9]{0,4})?(?:_[A-Z0-9]{2,8})*$")
NUMBER_ONLY = re.compile(r"^[0-9 .,:;/%+\-]+$")
IDENTIFIER_LIKE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def _is_identifier_like(text: str) -> bool:
    value = (text or "").strip()
    if not IDENTIFIER_LIKE_RE.match(value):
        return False
    return bool(re.search(r"[A-Z0-9_]", value[1:]))


def _matches_capital_after_prefix(text: str, prefix: str) -> bool:
    if len(text) <= len(prefix):
        return False
    if text[: len(prefix)].lower() != prefix:
        return False
    return text[len(prefix)].isupper()


def is_technical_identifier_text(text: str, source_text_prefixes: Iterable[str] | None = None) -> bool:
    value = (text or "").strip()
    if not value:
        return False
    if not _is_identifier_like(value):
        return False

    custom_prefixes = tuple(p.lower() for p in (source_text_prefixes or []))
    lower = value.lower()

    for prefix in CAPITAL_AFTER_PREFIXES:
        if _matches_capital_after_prefix(value, prefix):
            return True

    if any(lower.startswith(prefix) for prefix in PLAIN_PROTECT_PREFIXES):
        return True

    if custom_prefixes and any(lower.startswith(prefix) for prefix in custom_prefixes):
        return True

    if any(pattern.match(value) for pattern in WHOLE_TOKEN_PATTERNS):
        return True

    return False


class Filter:
    def __init__(self, unit_patterns: Iterable[str] | None = None, source_text_prefixes: Iterable[str] | None = None) -> None:
        self.unit_patterns = list(SELECTION_HELP_UNIT_PATTERNS if unit_patterns is None else unit_patterns)
        self.source_text_prefixes = list(source_text_prefixes or [])
        self.protector = Protector()

    def load_patterns(self, file_path: str) -> None:
        path = Path(file_path)
        if not file_path or not path.exists():
            return
        prefixes: list[str] = []
        units: list[str] = []
        for raw_line in path.read_text(encoding='utf-8').splitlines():
            line = raw_line.strip()
            if not line or line.startswith('#'):
                continue
            if line.lower().startswith('prefix:'):
                prefixes.append(line.split(':', 1)[1].strip())
            elif line.lower().startswith('unit:'):
                units.append(line.split(':', 1)[1].strip())
            else:
                units.append(line)
        if prefixes:
            self.source_text_prefixes.extend(prefixes)
        if units:
            self.unit_patterns.extend(units)

    def should_skip(self, item: TranslationItem) -> tuple[bool, str]:
        source = (item.source_text or '').strip()

        if item.owner_unit and any(
            fnmatch(item.owner_unit.lower(), pattern.lower())
            for pattern in self.unit_patterns
        ):
            return True, 'excluded_unit'

        if not source:
            return True, 'empty_source'
        if self.protector.is_rtf(item.source_text):
            return True, 'rtf_text'
        if is_technical_identifier_text(source, self.source_text_prefixes):
            return True, 'technical_identifier_source_text'
        if ALL_CAPS_ABBREV.match(source):
            return True, 'all_caps_abbrev'
        if NUMBER_ONLY.match(source):
            return True, 'numeric_or_symbolic_only'
        return False, ''
