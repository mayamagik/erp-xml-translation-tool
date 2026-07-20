from __future__ import annotations

import csv
import tempfile
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from src_translation.models import Config
from src_translation.pipeline import TranslationPipeline


SAMPLE_XML = """<?xml version=\"1.0\" encoding=\"utf-8\"?>
<langfile>
  <properties>
    <form name=\"DemoForm\">
      <component name=\"btnOptions\">
        <prop id=\"1\" name=\"Caption\">&amp;Optionen %s</prop>
      </component>
      <component name=\"rtfText\">
        <prop id=\"2\" name=\"Description.Text\">{\\rtf1\\ansi Demo %s}</prop>
      </component>
      <component name=\"technicalText\">
        <prop id=\"3\" name=\"Caption\">btnSave</prop>
      </component>
    </form>
  </properties>
  <constants>
    <unit name=\"DemoMessages\">
      <const id=\"4\" name=\"DEMO_DELETE\" stringid=\"40\">%s für alle Benutzer löschen</const>
    </unit>
  </constants>
</langfile>
"""


class SmokePipelineTest(unittest.TestCase):
    def test_smoke_pipeline_preserves_technical_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_xml = tmp_path / "input.xml"
            output_xml = tmp_path / "output.xml"
            report_csv = tmp_path / "report.csv"
            input_xml.write_text(SAMPLE_XML, encoding="utf-8")

            cfg = Config(
                input_xml=str(input_xml),
                output_xml=str(output_xml),
                report_csv=str(report_csv),
                mode="smoke",
            )
            items, summary = TranslationPipeline(cfg).run()

            self.assertTrue(summary["file_well_formed"])
            self.assertTrue(output_xml.exists())
            self.assertTrue(report_csv.exists())
            ET.parse(output_xml)

            translated = items[0]
            self.assertIn("&", translated.final_text)
            self.assertIn("%s", translated.final_text)
            self.assertEqual(translated.hotkey_source_has, 1)
            self.assertEqual(translated.hotkey_final_has, 1)
            self.assertEqual(translated.placeholder_source_count, 1)
            self.assertEqual(translated.placeholder_final_count, 1)

            rtf_item = items[1]
            self.assertTrue(rtf_item.skipped)
            self.assertEqual(rtf_item.skip_reason, "rtf_text")

            technical_item = items[2]
            self.assertTrue(technical_item.skipped)
            self.assertEqual(
                technical_item.skip_reason,
                "technical_identifier_source_text",
            )

            with report_csv.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.reader(handle, delimiter=";"))
            self.assertIn(["metric", "value"], rows)


if __name__ == "__main__":
    unittest.main()
