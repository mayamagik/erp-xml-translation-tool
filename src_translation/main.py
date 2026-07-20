from __future__ import annotations

import argparse
import configparser
import os
from pathlib import Path

from dotenv import load_dotenv

from .models import Config
from .pipeline import TranslationPipeline

DEFAULT_FREE_BASE = 'https://api-free.deepl.com'
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / 'config' / 'config.ini'


def _load_ini(path_str: str) -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    if path_str:
        parser.read(path_str, encoding='utf-8')
    return parser


def _cfg_get(parser: configparser.ConfigParser, section: str, option: str, fallback: str = '') -> str:
    if parser.has_option(section, option):
        return parser.get(section, option)
    return fallback


def _resolve_config_path(cli_value: str) -> str:
    if cli_value:
        return cli_value
    if DEFAULT_CONFIG_PATH.exists():
        return str(DEFAULT_CONFIG_PATH)
    return ''


def _resolve_value(cli_value: str | None, ini_value: str, default: str = '') -> str:
    if cli_value not in (None, ''):
        return cli_value
    if ini_value != '':
        return ini_value
    return default


def _resolve_api_key(active_key: int, direct_key: str, key_1: str, key_2: str) -> tuple[str, int]:
    if direct_key:
        return direct_key, active_key
    if active_key == 2 and key_2:
        return key_2, 2
    if key_1:
        return key_1, 1
    if key_2:
        return key_2, 2
    return '', active_key


def _default_snapshot_name() -> str:
    from datetime import datetime
    return f"snap_{datetime.now().strftime('%Y-%m-%d')}_xtags_v1"


def _build_snapshot_paths(snapshot_name: str, output_base_dir: str) -> tuple[str, str]:
    out_dir = Path(output_base_dir) / snapshot_name
    output_xml = out_dir / 'output.xml'
    report_csv = out_dir / 'report.csv'
    return str(output_xml), str(report_csv)


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description='Translate and validate XML language files')
    parser.add_argument('--config', default='', help='Optional path to config.ini')
    parser.add_argument('--input', default='', help='Path to the input XML file')
    parser.add_argument('--output', default='', help='Path to the output XML file (overrides snapshot paths)')
    parser.add_argument('--report', default='', help='Path to the CSV validation report (overrides snapshot paths)')
    parser.add_argument('--snapshot', default='', help='Snapshot name used to build output paths')
    parser.add_argument('--output-base-dir', default='', help='Base directory for snapshot outputs')
    parser.add_argument('--source-lang', default='')
    parser.add_argument('--target-lang', default='')
    parser.add_argument('--mode', default='', choices=['', 'smoke', 'deepl'])
    parser.add_argument('--api-key', default='')
    parser.add_argument('--api-key-1', default='')
    parser.add_argument('--api-key-2', default='')
    parser.add_argument('--active-key', default='', choices=['', '1', '2'], help='Select which configured API key to use')
    parser.add_argument('--api-base', default='')
    parser.add_argument('--timeout', type=int, default=None)
    parser.add_argument('--exceptions-file', default='', help='Optional file containing additional filter patterns')
    args = parser.parse_args()

    config_path = _resolve_config_path(args.config)
    ini = _load_ini(config_path)
    input_xml = _resolve_value(args.input, _cfg_get(ini, 'paths', 'input_xml'))
    if not input_xml:
        parser.error('--input is missing and config.ini does not define input_xml.')

    source_lang = _resolve_value(args.source_lang, _cfg_get(ini, 'general', 'source_lang'), 'DE')
    target_lang = _resolve_value(args.target_lang, _cfg_get(ini, 'general', 'target_lang'), 'FR')
    mode = _resolve_value(args.mode, _cfg_get(ini, 'translation', 'mode'), 'smoke')
    active_key_str = _resolve_value(args.active_key, _cfg_get(ini, 'deepl', 'active_key'), os.getenv('DEEPL_API_KEY_ACTIVE', '1'))
    api_base = _resolve_value(args.api_base, _cfg_get(ini, 'deepl', 'api_base'), os.getenv('DEEPL_API_BASE', DEFAULT_FREE_BASE))
    timeout_ini = _cfg_get(ini, 'deepl', 'timeout_seconds', '60')
    timeout_seconds = args.timeout if args.timeout is not None else int(timeout_ini or '60')
    direct_key = _resolve_value(args.api_key, _cfg_get(ini, 'deepl', 'api_key'), os.getenv('DEEPL_API_KEY', ''))
    key_1 = _resolve_value(args.api_key_1, _cfg_get(ini, 'deepl', 'api_key_1'), os.getenv('DEEPL_API_KEY_1', ''))
    key_2 = _resolve_value(args.api_key_2, _cfg_get(ini, 'deepl', 'api_key_2'), os.getenv('DEEPL_API_KEY_2', ''))
    snapshot_name = _resolve_value(args.snapshot, _cfg_get(ini, 'paths', 'snapshot_name'), _default_snapshot_name())
    output_base_dir = _resolve_value(args.output_base_dir, _cfg_get(ini, 'paths', 'output_base_dir'), 'data/out')
    snapshot_output_xml, snapshot_report_csv = _build_snapshot_paths(snapshot_name=snapshot_name, output_base_dir=output_base_dir)
    output_xml = _resolve_value(args.output, _cfg_get(ini, 'paths', 'output_xml'), snapshot_output_xml)
    report_csv = _resolve_value(args.report, _cfg_get(ini, 'paths', 'report_csv'), snapshot_report_csv)
    exceptions_file = _resolve_value(args.exceptions_file, _cfg_get(ini, 'paths', 'exceptions_file'), '')

    active_key = int(active_key_str)
    selected_key, selected_index = _resolve_api_key(active_key, direct_key, key_1, key_2)

    cfg = Config(
        input_xml=input_xml,
        output_xml=output_xml,
        report_csv=report_csv,
        source_lang=source_lang,
        target_lang=target_lang,
        api_key=selected_key,
        api_key_1=key_1,
        api_key_2=key_2,
        active_key_index=selected_index,
        mode=mode,
        api_base=api_base,
        timeout_seconds=timeout_seconds,
        exceptions_file=exceptions_file,
    )

    print(f"CONFIG path={config_path or 'none'}")
    print(f"START mode={cfg.mode} source={cfg.source_lang} target={cfg.target_lang}")
    print(f"KEY active_index={cfg.active_key_index} configured={int(bool(cfg.api_key))}")
    print(f"SNAPSHOT name={snapshot_name}")
    print(f"PATHS output_xml={cfg.output_xml} report_csv={cfg.report_csv}")
    pipeline = TranslationPipeline(cfg)
    _, summary = pipeline.run()

    print(f"ENDPOINT {summary['endpoint']}")
    print(f"ITEMS total={summary['items_total']} skipped={summary['items_skipped']} to_translate={summary['items_to_translate']}")
    print(f"FILE well_formed={summary['file_well_formed']}")
    if cfg.mode == 'deepl':
        print('USAGE ' f"before={summary['usage_before_character_count']} " f"after={summary['usage_after_character_count']} " f"delta={summary['usage_delta']} " f"limit={summary['usage_character_limit']}")
        print(f"BILLED billed_characters_total={summary['billed_characters_total']}")
    print(f"OUTPUT xml={summary['output_xml']}")
    print(f"OUTPUT report={summary['report_csv']}")
    print('DONE')


if __name__ == '__main__':
    main()
