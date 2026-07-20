from __future__ import annotations

import re


class Protector:
    TAG = "x-protect"

    PLACEHOLDER_RE = re.compile(
        r"%(?:\d+:)?[sdifuxX]"
        r"|%(?:\d+\$)?[sdifuxX]"
        r"|\{\d+(?::[^{}]+)?\}"
        r"|#(?:Ü|Ccl[A-Za-z0-9_]+)"
    )
    ACCELERATOR_RE = re.compile(r"&(?!amp;)(?!\s)(.)")
    NEWLINE_RE = re.compile(r"\\r\\n|\\n|\\r|\r\n|\n|\r")

    def protect_xtags(self, text: str) -> str:
        protected = text or ""
        protected = self._protect_pattern(protected, self.PLACEHOLDER_RE)
        protected = self._protect_pattern(protected, self.ACCELERATOR_RE, whole_match=True)
        return protected

    def _protect_pattern(self, text: str, pattern: re.Pattern[str], whole_match: bool = False) -> str:
        def repl(match: re.Match[str]) -> str:
            value = match.group(0) if whole_match else match.group(0)
            return f"<{self.TAG}>{value}</{self.TAG}>"

        return pattern.sub(repl, text)

    def restore(self, text: str) -> str:
        return re.sub(fr"</?{self.TAG}>", "", text or "")

    def count_placeholders(self, text: str) -> list[str]:
        return [m.group(0) for m in self.PLACEHOLDER_RE.finditer(text or "")]

    def accelerator_present(self, text: str) -> bool:
        return bool(self.ACCELERATOR_RE.search(text or ""))

    def extract_accelerators(self, text: str) -> list[str]:
        return [m.group(0) for m in self.ACCELERATOR_RE.finditer(text or "")]

    def newline_count(self, text: str) -> int:
        return len(self.NEWLINE_RE.findall(text or ""))

    def leading_space_count(self, text: str) -> int:
        match = re.match(r"^\s*", text or "")
        return len(match.group(0)) if match else 0

    def trailing_space_count(self, text: str) -> int:
        match = re.search(r"\s*$", text or "")
        return len(match.group(0)) if match else 0

    def is_rtf(self, text: str) -> bool:
        return (text or "").lstrip().startswith(r"{\rtf")
