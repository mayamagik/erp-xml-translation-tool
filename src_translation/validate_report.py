from __future__ import annotations

import csv
from pathlib import Path
import xml.etree.ElementTree as ET

from .models import TranslationItem, ValidationIssue
from .protect_text import Protector


class Validator:
    def __init__(self) -> None:
        self.protector = Protector()

    def validate_item(self, item: TranslationItem) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        if item.skipped:
            return issues

        source = item.source_text or ''
        final = item.final_text or ''

        source_placeholders = self.protector.count_placeholders(source)
        final_placeholders = self.protector.count_placeholders(final)
        item.placeholder_source_count = len(source_placeholders)
        item.placeholder_final_count = len(final_placeholders)
        if source_placeholders != final_placeholders:
            issues.append(ValidationIssue(item_id=item.item_id, severity='ERROR', category='placeholder_diff', message='Placeholders differ between the source and final text.'))

        item.missing_translation = int(bool(source.strip() and not final.strip()))
        if item.missing_translation:
            issues.append(ValidationIssue(item_id=item.item_id, severity='ERROR', category='missing_translation', message='The final text is empty although the source text is not.'))

        source_hotkeys = self.protector.extract_accelerators(source)
        final_hotkeys = self.protector.extract_accelerators(final)
        item.hotkey_source_has = int(bool(source_hotkeys))
        item.hotkey_final_has = int(bool(final_hotkeys))
        item.hotkey_inserted = int((not source_hotkeys) and bool(final_hotkeys))
        item.hotkeys_source = '|'.join(source_hotkeys)
        item.hotkeys_final = '|'.join(final_hotkeys)
        item.hotkey_count_diff = len(final_hotkeys) - len(source_hotkeys)

        if item.hotkey_source_has and not item.hotkey_final_has:
            issues.append(ValidationIssue(item_id=item.item_id, severity='WARN', category='hotkey_missing', message='A keyboard accelerator from the source is missing in the final text.'))
        elif len(source_hotkeys) != len(final_hotkeys):
            issues.append(ValidationIssue(item_id=item.item_id, severity='WARN', category='hotkey_count_diff', message='The number of keyboard accelerators differs.'))

        item.newline_source_count = self.protector.newline_count(source)
        item.newline_final_count = self.protector.newline_count(final)
        if item.newline_source_count != item.newline_final_count:
            issues.append(ValidationIssue(item_id=item.item_id, severity='WARN', category='newline_diff', message='The number of line breaks differs.'))

        item.leading_space_source = self.protector.leading_space_count(source)
        item.leading_space_final = self.protector.leading_space_count(final)
        item.trailing_space_source = self.protector.trailing_space_count(source)
        item.trailing_space_final = self.protector.trailing_space_count(final)
        if item.leading_space_source != item.leading_space_final or item.trailing_space_source != item.trailing_space_final:
            issues.append(ValidationIssue(item_id=item.item_id, severity='WARN', category='outer_whitespace_diff', message='Leading or trailing whitespace differs.'))
        return issues

    def validate_file(self, file_path: str) -> list[ValidationIssue]:
        try:
            ET.parse(file_path)
            return []
        except ET.ParseError as exc:
            return [ValidationIssue(item_id='__file__', severity='ERROR', category='xml_not_well_formed', message=str(exc))]


class Reporter:
    HEADERS = [
        'item_id', 'kind', 'stringid', 'owner_form', 'owner_component', 'owner_unit', 'status', 'skip_reason',
        'issues', 'source_text', 'protected_text', 'translated_protected_text', 'final_text',
        'hotkey_source_has', 'hotkey_final_has', 'hotkey_inserted', 'hotkeys_source', 'hotkeys_final',
        'hotkey_count_diff', 'missing_translation', 'placeholder_source_count', 'placeholder_final_count',
        'newline_source_count', 'newline_final_count', 'leading_space_source', 'leading_space_final',
        'trailing_space_source', 'trailing_space_final',
    ]

    def write_detailed_report(self, items: list[TranslationItem], report_csv: str) -> None:
        Path(report_csv).parent.mkdir(parents=True, exist_ok=True)
        total_items = len(items)
        translated_total = sum(1 for item in items if item.status == 'translated')
        skipped_total = sum(1 for item in items if item.skipped)
        identical_to_source_total = sum(1 for item in items if (item.final_text or '') == (item.source_text or '') and (item.source_text or '').strip())

        with open(report_csv, 'w', encoding='utf-8-sig', newline='') as file_handle:
            writer = csv.writer(file_handle, delimiter=';')
            writer.writerow(['metric', 'value'])
            writer.writerow(['total_items', total_items])
            writer.writerow(['translated_total', translated_total])
            writer.writerow(['skipped_total', skipped_total])
            writer.writerow(['identical_to_source_total', identical_to_source_total])
            writer.writerow([])
            writer.writerow(self.HEADERS)
            for item in items:
                writer.writerow([
                    item.item_id, item.kind, item.stringid, item.owner_form, item.owner_component, item.owner_unit,
                    item.status, item.skip_reason, '|'.join(item.issues), item.source_text, item.protected_text,
                    item.translated_protected_text, item.final_text, item.hotkey_source_has, item.hotkey_final_has,
                    item.hotkey_inserted, item.hotkeys_source, item.hotkeys_final, item.hotkey_count_diff,
                    item.missing_translation, item.placeholder_source_count, item.placeholder_final_count,
                    item.newline_source_count, item.newline_final_count, item.leading_space_source,
                    item.leading_space_final, item.trailing_space_source, item.trailing_space_final,
                ])
