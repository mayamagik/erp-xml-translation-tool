from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Config:
    input_xml: str
    output_xml: str
    report_csv: str
    source_lang: str = "DE"
    target_lang: str = "FR"
    mode: str = "smoke"
    api_key: str = ""
    api_key_1: str = ""
    api_key_2: str = ""
    active_key_index: int = 1
    api_base: str = "https://api-free.deepl.com"
    timeout_seconds: int = 60
    exceptions_file: str = ""


@dataclass
class TranslationItem:
    item_id: str
    kind: str
    stringid: str
    owner_form: str
    owner_component: str
    owner_unit: str
    name: str
    source_text: str
    protected_text: str = ""
    translated_protected_text: str = ""
    final_text: str = ""
    skipped: bool = False
    skip_reason: str = ""
    status: str = ""
    issues: List[str] = field(default_factory=list)
    hotkey_source_has: int = 0
    hotkey_final_has: int = 0
    hotkey_inserted: int = 0
    hotkeys_source: str = ""
    hotkeys_final: str = ""
    hotkey_count_diff: int = 0
    missing_translation: int = 0
    placeholder_source_count: int = 0
    placeholder_final_count: int = 0
    newline_source_count: int = 0
    newline_final_count: int = 0
    leading_space_source: int = 0
    leading_space_final: int = 0
    trailing_space_source: int = 0
    trailing_space_final: int = 0


@dataclass
class ValidationIssue:
    item_id: str
    severity: str
    category: str
    message: str
