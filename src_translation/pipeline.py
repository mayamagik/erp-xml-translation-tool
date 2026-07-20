from __future__ import annotations

from pathlib import Path

from .exceptions import Filter
from .io_xml import XMLProcessor
from .models import Config, TranslationItem
from .protect_text import Protector
from .resume import ResumeManager
from .translate import Translator
from .validate_report import Reporter, Validator


class TranslationPipeline:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.xml_processor = XMLProcessor()
        self.filter = Filter()
        if config.exceptions_file:
            self.filter.load_patterns(config.exceptions_file)
        self.protector = Protector()
        self.translator = Translator(
            api_key=config.api_key,
            source_lang=config.source_lang,
            target_lang=config.target_lang,
            mode=config.mode,
            api_base=config.api_base,
            timeout_seconds=config.timeout_seconds,
        )
        self.validator = Validator()
        self.reporter = Reporter()

    def run(self) -> tuple[list[TranslationItem], dict]:
        print(f"LOAD xml={self.config.input_xml}")
        tree = self.xml_processor.load_xml(self.config.input_xml)
        print("LOAD done")

        print("EXTRACT items ...")
        items = self.xml_processor.extract_items(tree)
        print(f"EXTRACT done items_total={len(items)}")

        usage_before = {"available": False, "character_count": 0, "character_limit": 0}
        usage_after = {"available": False, "character_count": 0, "character_limit": 0}
        if self.config.mode == "deepl":
            print("DEEPL usage_before request ...")
            usage_before = self.translator.get_usage()
            print(
                "DEEPL usage_before "
                f"count={usage_before.get('character_count', 0)} "
                f"limit={usage_before.get('character_limit', 0)}"
            )

        billed_total = 0
        items_skipped = 0
        items_to_translate = 0
        translated_done = 0
        progress_step = 25

        print("FILTER: classify entries and count translatable values ...")
        for item in items:
            skip, reason = self.filter.should_skip(item)
            if skip:
                item.skipped = True
                item.skip_reason = reason
                item.final_text = item.source_text
                item.status = "empty" if not (item.source_text or "").strip() else "skipped"
                items_skipped += 1
            else:
                items_to_translate += 1

        print(
            "FILTER done "
            f"items_total={len(items)} "
            f"skipped={items_skipped} "
            f"to_translate={items_to_translate}"
        )

        resume_path = str(Path(self.config.output_xml).with_name("resume.jsonl"))
        resume_manager = ResumeManager(resume_path, save_interval=25)
        print(f"RESUME file={resume_path}")
        resume_loaded = resume_manager.load()
        print(f"RESUME loaded items={resume_loaded}")
        print("RESUME save every 25 translated items")

        for item in items:
            if resume_manager.contains(item):
                saved = resume_manager.get(item)
                item.translated_protected_text = str(saved.get("translated_protected_text", ""))
                item.final_text = str(saved.get("final_text", ""))
                item.status = str(saved.get("status", "translated"))
                item.skipped = False

        if items_to_translate == 0:
            print("TRANSLATE skipped: no translatable entries found")

        for item in items:
            if item.skipped:
                continue

            if resume_manager.contains(item):
                translated_done += 1
                if (
                    translated_done == 1
                    or translated_done % progress_step == 0
                    or translated_done == items_to_translate
                ):
                    print(
                        "RESUME progress "
                        f"{translated_done}/{items_to_translate} "
                        f"item_id={item.item_id}"
                    )
                continue

            translated_done += 1
            if (
                translated_done == 1
                or translated_done % progress_step == 0
                or translated_done == items_to_translate
            ):
                print(
                    "TRANSLATE progress "
                    f"{translated_done}/{items_to_translate} "
                    f"item_id={item.item_id}"
                )

            item.protected_text = self.protector.protect_xtags(item.source_text)
            translated, billed = self.translator.translate_text(item.protected_text)
            item.translated_protected_text = translated
            billed_total += billed
            item.final_text = self.protector.restore(item.translated_protected_text)

            issues = self.validator.validate_item(item)
            item.issues = [issue.category for issue in issues]

            if item.missing_translation:
                item.status = "error"
            elif not item.source_text.strip():
                item.status = "empty"
            elif item.final_text == item.source_text:
                item.status = "unchanged"
            else:
                item.status = "translated"

            saved_now = resume_manager.add_entry(item)
            if saved_now:
                print(f"RESUME save count={saved_now}")

        final_saved = resume_manager.flush()
        if final_saved:
            print(f"RESUME final save count={final_saved}")

        print(f"WRITE xml={self.config.output_xml}")
        self.xml_processor.write_final_texts(tree, items, self.config.output_xml)
        print("WRITE xml done")

        print("VALIDATE file ...")
        validation_issues = self.validator.validate_file(self.config.output_xml)
        file_well_formed = len(validation_issues) == 0
        print(f"VALIDATE done well_formed={file_well_formed}")

        print(f"REPORT detail={self.config.report_csv}")
        self.reporter.write_detailed_report(items, self.config.report_csv)
        print("REPORT detail done")

        if self.config.mode == "deepl":
            print("DEEPL usage_after request ...")
            usage_after = self.translator.get_usage()
            print(
                "DEEPL usage_after "
                f"count={usage_after.get('character_count', 0)} "
                f"limit={usage_after.get('character_limit', 0)}"
            )

        usage_delta = int(usage_after.get("character_count", 0)) - int(
            usage_before.get("character_count", 0)
        )

        summary = {
            "mode": self.config.mode,
            "endpoint": self.translator.api_base if self.config.mode == "deepl" else "smoke-local",
            "items_total": len(items),
            "items_skipped": items_skipped,
            "items_to_translate": items_to_translate,
            "output_xml": self.config.output_xml,
            "report_csv": self.config.report_csv,
            "file_well_formed": file_well_formed,
            "validation_issue_count": len(validation_issues),
            "usage_before_character_count": usage_before.get("character_count", 0),
            "usage_after_character_count": usage_after.get("character_count", 0),
            "usage_character_limit": usage_after.get(
                "character_limit", usage_before.get("character_limit", 0)
            ),
            "usage_delta": usage_delta,
            "billed_characters_total": billed_total,
            "active_key_index": self.config.active_key_index,
            "resume_path": resume_path,
            "resume_loaded_items": resume_loaded,
        }
        return items, summary
