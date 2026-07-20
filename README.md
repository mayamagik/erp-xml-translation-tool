# ERP XML Translation and Validation Tool

A Python command-line application for processing multilingual ERP language files in XML format. It extracts translatable text, filters technical content, protects placeholders and keyboard accelerators, translates the text locally or through the DeepL API, validates the result, and writes the translated values back into the original XML structure.

This repository is a simplified portfolio version of an application developed as an IHK final project in application development. The public version contains only synthetic demonstration data and no employer-owned production exports or credentials.

## What the project demonstrates

- object-oriented Python development;
- XML parsing, extraction, transformation, and reconstruction;
- REST API integration with DeepL;
- protection of technical content during translation;
- validation, error handling, and CSV reporting;
- resumable processing for larger files;
- configuration through CLI arguments, INI files, and environment variables;
- automated testing with `unittest` and GitHub Actions.

## Main features

- Extracts form properties, component properties, and constants from the supported XML structure.
- Skips empty values, RTF content, technical identifiers, uppercase abbreviations, numeric-only values, and excluded constant units.
- Protects placeholders such as `%s`, `%d`, and `{0}` with temporary XML tags.
- Protects keyboard accelerators such as the `&O` in `&Options`.
- Supports a deterministic local smoke mode that does not call an external service.
- Supports live translation through the DeepL REST API.
- Checks placeholders, accelerators, line breaks, outer whitespace, missing translations, and XML well-formedness.
- Produces a detailed semicolon-separated CSV report.
- Saves completed translations in `resume.jsonl` and safely ignores saved entries when their source text has changed.

## Processing workflow

```text
Input XML
   │
   ▼
Extract properties and constants
   │
   ▼
Filter non-translatable entries
   │
   ▼
Protect placeholders and accelerators
   │
   ▼
Translate in smoke or DeepL mode
   │
   ▼
Restore protected content
   │
   ▼
Validate technical consistency
   │
   ▼
Write output XML and CSV report
```

## Project structure

```text
.
├── .github/workflows/tests.yml       # Continuous integration
├── data/in/demo_de.xml                # Synthetic demonstration input
├── examples/
│   ├── output_demo_fr.xml             # Example smoke-mode result
│   └── report_demo.csv                # Example validation report
├── src_translation/
│   ├── config/
│   │   ├── config.ini                 # Default demo configuration
│   │   └── filter_patterns.example.txt
│   ├── exceptions.py                  # Filtering rules
│   ├── io_xml.py                      # XML extraction and reconstruction
│   ├── main.py                        # Command-line interface
│   ├── models.py                      # Data models
│   ├── pipeline.py                    # Workflow orchestration
│   ├── protect_text.py                # Technical marker protection
│   ├── resume.py                      # Incremental persistence
│   ├── translate.py                   # Smoke and DeepL translation
│   └── validate_report.py             # Validation and CSV reporting
├── tests/test_smoke.py
├── .env.example
├── .gitignore
└── requirements.txt
```

## Requirements

- Python 3.10 or later
- `requests`
- `python-dotenv`
- a DeepL API key only when using DeepL mode

## Installation

Clone the repository and open its root directory.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run the included demonstration

The default configuration points to the demo file `data/in/demo_de.xml` and uses smoke mode:

```bash
python -m src_translation.main
```

The command creates:

```text
data/out/demo_smoke/output.xml
data/out/demo_smoke/report.csv
data/out/demo_smoke/resume.jsonl
```

The demo processes examples containing ordinary interface text, placeholders, an accelerator, an actual line break, an empty value, RTF content, an identifier, an abbreviation, a numeric value, and a constant unit excluded by a wildcard rule.

Smoke mode uses a small deterministic replacement map. It exists to demonstrate the complete technical pipeline and is not intended as a general translation engine.

## Run the tests

```bash
python -m unittest discover -s tests -v
```

The smoke test verifies that:

- the output XML is well formed;
- placeholders and accelerators are preserved;
- RTF and technical identifiers are skipped;
- the XML and CSV output files are created.

The same test command runs automatically in GitHub Actions after pushes and pull requests.

## Use DeepL mode

Copy the environment template:

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

### macOS or Linux

```bash
cp .env.example .env
```

Add your own key to `.env`:

```dotenv
DEEPL_API_KEY=your-own-api-key
```

The application loads `.env` automatically. The populated file is excluded through `.gitignore` and must never be committed.

Run the tool in DeepL mode:

```bash
python -m src_translation.main --mode deepl --snapshot demo_deepl
```

The translation request uses XML tag handling and instructs DeepL to ignore the temporary `<x-protect>` tags. Formatting is preserved and sentence splitting at line breaks is disabled.

Two-key configuration is also supported through `DEEPL_API_KEY_1`, `DEEPL_API_KEY_2`, and `DEEPL_API_KEY_ACTIVE`.

## Command-line example

```bash
python -m src_translation.main \
  --input data/in/demo_de.xml \
  --output data/out/custom/output.xml \
  --report data/out/custom/report.csv \
  --source-lang DE \
  --target-lang FR \
  --mode smoke
```

Command-line values override values from `config.ini`.

## Supported XML structure

The processor is designed for language exports containing form properties, component properties, and constants grouped in units:

```xml
<langfile>
  <properties>
    <form name="DemoForm">
      <prop name="Caption" id="1">Form title</prop>
      <component name="btnSave">
        <prop name="Caption" id="2">Save</prop>
      </component>
    </form>
  </properties>
  <constants>
    <unit name="DemoMessages">
      <const name="FILE_NOT_FOUND" id="101" stringid="1001">
        The file "%s" was not found.
      </const>
    </unit>
  </constants>
</langfile>
```

Entries are mapped back to their original positions using their type, owner, name, ID, and string ID.

## Filtering

The application automatically skips:

- empty source text;
- RTF content;
- identifier-like technical strings such as `btnSave`;
- uppercase abbreviations such as `PDF`;
- values containing only numbers or symbols;
- constants belonging to excluded units such as `System*`, `dx*`, or `cx*`.

Additional rules can be loaded with `--exceptions-file`:

```text
unit: DemoTechnical*
prefix: internal
```

Example:

```bash
python -m src_translation.main \
  --exceptions-file src_translation/config/filter_patterns.example.txt
```

## Protection and validation

Before translation, sensitive markers are wrapped in temporary tags:

```text
%s für alle Benutzer löschen
```

becomes:

```xml
<x-protect>%s</x-protect> für alle Benutzer löschen
```

After translation, the tags are removed and the validator compares the source and final values.

The report checks:

- placeholder content and count;
- missing target text;
- accelerator presence and count;
- actual or escaped line-break counts;
- leading and trailing whitespace;
- final XML well-formedness.

The validator assesses technical consistency. It does not replace linguistic review.

## Generated report

The CSV report contains summary metrics followed by one row per extracted item. Its fields include:

- XML context and identifiers;
- processing status and skip reason;
- source, protected, translated, and final text;
- validation categories;
- placeholder and accelerator information;
- newline and outer-whitespace counts.

## Resume behaviour

The application writes completed translations to `resume.jsonl` every 25 translated items. A later run can reuse those entries. Resume records include the complete XML context and source text, preventing an old translation from being reused when the corresponding source value has changed.

Delete the snapshot directory when you intentionally want to start a completely new run:

```bash
rm -rf data/out/demo_smoke
```

In PowerShell:

```powershell
Remove-Item -Recurse -Force data/out/demo_smoke
```

## Scope and limitations

- The XML processor targets the demonstrated ERP language-export structure; it is not a universal XML translation framework.
- Filtering rules are heuristic and may need adjustment for another application.
- Smoke mode has only a small demonstration dictionary.
- DeepL availability, quotas, billing, and translation behaviour are controlled by the API provider.
- Generated XML should be reviewed and tested before import into another system.
- The synthetic sample represents the technical cases handled by the original application but contains no production ERP data.

## Security and repository hygiene

The repository intentionally excludes:

- real API keys and `.env` files;
- production ERP XML exports;
- generated production reports and resume files;
- virtual environments and Python caches;
- IDE configuration and nested archives.


