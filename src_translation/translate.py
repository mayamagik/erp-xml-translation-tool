from __future__ import annotations

from typing import Any, Dict

import requests


class Translator:
    def __init__(
        self,
        api_key: str = "",
        source_lang: str = "DE",
        target_lang: str = "FR",
        mode: str = "smoke",
        api_base: str = "https://api-free.deepl.com",
        timeout_seconds: int = 60,
    ) -> None:
        self.api_key = api_key
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.mode = mode
        self.api_base = api_base.rstrip("/") if api_base else ""
        self.timeout_seconds = timeout_seconds

    def get_usage(self) -> dict[str, Any]:
        if self.mode != "deepl":
            return {"available": False, "character_count": 0, "character_limit": 0}
        if not self.api_key:
            raise RuntimeError("A DeepL API key is required for mode='deepl'.")
        url = f"{self.api_base}/v2/usage"
        headers = {"Authorization": f"DeepL-Auth-Key {self.api_key}"}
        response = requests.get(url, headers=headers, timeout=self.timeout_seconds)
        response.raise_for_status()
        data = response.json()
        return {
            "available": True,
            "character_count": int(data.get("character_count", 0)),
            "character_limit": int(data.get("character_limit", 0)),
            "raw": data,
        }

    def translate_text(self, protected_text: str) -> tuple[str, int]:
        if self.mode == "smoke":
            return self._smoke_translate(protected_text), 0
        return self._deepl_translate(protected_text)

    def _smoke_translate(self, text: str) -> str:
        replacements: Dict[str, str] = {
            "Änderungen speichern?": "Enregistrer les modifications ?",
            "Die Datei ": "Le fichier ",
            " wurde nicht gefunden.": " est introuvable.",
            "Kundenverwaltung": "Gestion des clients",
            "Kundennummer": "Numéro de client",
            "Kundenname": "Nom du client",
            "Abbrechen": "Annuler",
            "Löschen": "Supprimer",
            "Optionen": "Options",
            "ptionen": "ptions",
            "Status": "Statut",
            "Bereit": "Prêt",
            " Einträge wurden verarbeitet.": " entrées ont été traitées.",
            "Datensatz ": "Supprimer l’enregistrement ",
            " löschen?": " ?",
            "Der Vorgang wurde abgeschlossen.": "L’opération est terminée.",
            "Bitte prüfen Sie den Bericht.": "Veuillez vérifier le rapport.",
            " für alle Benutzer löschen": " supprimer pour tous les utilisateurs",
        }
        out = text
        for src, tgt in replacements.items():
            out = out.replace(src, tgt)
        return out

    def _deepl_translate(self, protected_text: str) -> tuple[str, int]:
        if not self.api_key:
            raise RuntimeError("A DeepL API key is required for mode='deepl'.")
        url = f"{self.api_base}/v2/translate"
        payload = {
            "text": protected_text,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "tag_handling": "xml",
            "ignore_tags": "x-protect",
            "preserve_formatting": "1",
            "split_sentences": "nonewlines",
            "show_billed_characters": "1",
        }
        headers = {"Authorization": f"DeepL-Auth-Key {self.api_key}"}
        response = requests.post(url, data=payload, headers=headers, timeout=self.timeout_seconds)
        response.raise_for_status()
        data = response.json()
        translated = data["translations"][0]["text"]
        billed = int(data["translations"][0].get("billed_characters", data.get("billed_characters", 0) or 0))
        return translated, billed
