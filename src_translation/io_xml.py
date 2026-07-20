from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List

from .models import TranslationItem


class XMLProcessor:
    def load_xml(self, file_path: str) -> ET.ElementTree:
        return ET.parse(file_path)

    def extract_items(self, tree: ET.ElementTree) -> List[TranslationItem]:
        root = tree.getroot()
        items: List[TranslationItem] = []

        properties = root.find('properties')
        if properties is not None:
            for form in properties.findall('form'):
                form_name = form.attrib.get('name', '')
                for prop in form.findall('prop'):
                    items.append(
                        TranslationItem(
                            item_id=prop.attrib.get('id', ''),
                            kind='prop',
                            stringid='',
                            owner_form=form_name,
                            owner_component='',
                            owner_unit='',
                            name=prop.attrib.get('name', ''),
                            source_text=prop.text or '',
                        )
                    )
                for component in form.findall('component'):
                    component_name = component.attrib.get('name', '')
                    for prop in component.findall('prop'):
                        items.append(
                            TranslationItem(
                                item_id=prop.attrib.get('id', ''),
                                kind='prop',
                                stringid='',
                                owner_form=form_name,
                                owner_component=component_name,
                                owner_unit='',
                                name=prop.attrib.get('name', ''),
                                source_text=prop.text or '',
                            )
                        )

        constants = root.find('constants')
        if constants is not None:
            for unit in constants.findall('unit'):
                unit_name = unit.attrib.get('name', '')
                for const in unit.findall('const'):
                    items.append(
                        TranslationItem(
                            item_id=const.attrib.get('id', ''),
                            kind='const',
                            stringid=const.attrib.get('stringid', ''),
                            owner_form='',
                            owner_component='',
                            owner_unit=unit_name,
                            name=const.attrib.get('name', ''),
                            source_text=const.text or '',
                        )
                    )
        return items

    def write_final_texts(self, tree: ET.ElementTree, items: List[TranslationItem], output_xml: str) -> None:
        root = tree.getroot()
        prop_map: Dict[tuple[str, str, str, str], str] = {}
        const_map: Dict[tuple[str, str, str, str], str] = {}

        for item in items:
            final_value = item.final_text if item.final_text != '' else item.source_text
            if item.kind == 'prop':
                prop_map[(item.owner_form, item.owner_component, item.name, item.item_id)] = final_value
            else:
                const_map[(item.owner_unit, item.name, item.item_id, item.stringid)] = final_value

        properties = root.find('properties')
        if properties is not None:
            for form in properties.findall('form'):
                form_name = form.attrib.get('name', '')
                for prop in form.findall('prop'):
                    key = (form_name, '', prop.attrib.get('name', ''), prop.attrib.get('id', ''))
                    if key in prop_map:
                        prop.text = prop_map[key]
                for component in form.findall('component'):
                    component_name = component.attrib.get('name', '')
                    for prop in component.findall('prop'):
                        key = (form_name, component_name, prop.attrib.get('name', ''), prop.attrib.get('id', ''))
                        if key in prop_map:
                            prop.text = prop_map[key]

        constants = root.find('constants')
        if constants is not None:
            for unit in constants.findall('unit'):
                unit_name = unit.attrib.get('name', '')
                for const in unit.findall('const'):
                    key = (unit_name, const.attrib.get('name', ''), const.attrib.get('id', ''), const.attrib.get('stringid', ''))
                    if key in const_map:
                        const.text = const_map[key]

        Path(output_xml).parent.mkdir(parents=True, exist_ok=True)
        tree.write(output_xml, encoding='utf-8', xml_declaration=True)
