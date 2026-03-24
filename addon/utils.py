# -*- coding: utf-8 -*-

import re
from typing import Optional

from anki.cards import Card
from anki.notes import Note
from aqt import mw

_FIELD_REPLACEMENT_RE = re.compile(r"{{([^{}]+)}}")


def note_is_image_occlusion(note: Note) -> bool:
    kind = note.model().get("originalStockKind")
    if hasattr(kind, "name"):
        kind = kind.name
    if kind == "ORIGINAL_STOCK_KIND_IMAGE_OCCLUSION":
        return True
    try:
        return int(kind) == 6
    except (TypeError, ValueError):
        return False


def field_index_by_name(note: Note, field_name: str) -> Optional[int]:
    for idx, field in enumerate(note.model()["flds"]):
        if field["name"] == field_name:
            return idx
    return None


def template_name_for_card(card: Card) -> str:
    try:
        template = card.template()
        return template["name"] if template else ""
    except Exception:
        return ""


def _stable_model_exclusion(model: dict, config: dict) -> dict:
    exclusions = config.get("exclusions_v2", {})
    model_id = str(model.get("id", ""))
    entry = exclusions.get(model_id, {})
    return entry if isinstance(entry, dict) else {}


def _legacy_model_exclusion(model: dict, config: dict) -> dict:
    exclusions = config.get("exclusions", {})
    entry = exclusions.get(model.get("name", ""), {})
    return entry if isinstance(entry, dict) else {}


def note_type_disabled(model: dict, config: dict) -> bool:
    stable = _stable_model_exclusion(model, config)
    if stable:
        return bool(stable.get("disabled"))
    return bool(_legacy_model_exclusion(model, config).get("disabled"))


def template_disabled(model: dict, template: dict, config: dict) -> bool:
    stable = _stable_model_exclusion(model, config)
    if stable:
        return template.get("ord") in stable.get("templates", [])
    return template.get("name") in _legacy_model_exclusion(model, config).get(
        "templates", []
    )


def field_disabled(model: dict, field: dict, config: dict) -> bool:
    stable = _stable_model_exclusion(model, config)
    if stable:
        return field.get("ord") in stable.get("fields", [])
    return field.get("name") in _legacy_model_exclusion(model, config).get(
        "fields", []
    )


def field_allowed_for_card(card: Card, field_name: str, config: dict) -> bool:
    try:
        model = card.note().model()
        if note_type_disabled(model, config):
            return False
        field_idx = field_index_by_name(card.note(), field_name)
        if field_idx is not None and field_disabled(
            model, model["flds"][field_idx], config
        ):
            return False
        template = card.template()
        if template and template_disabled(model, template, config):
            return False
    except Exception:
        return True
    return True


def card_has_any_allowed_field(card: Card, config: dict) -> bool:
    for field in card.note().model()["flds"]:
        if field_allowed_for_card(card, field["name"], config):
            return True
    return False


def fallback_field_index_for_card(card: Card, config: dict) -> int:
    note = card.note()
    model_fields = note.model()["flds"]

    if note_is_image_occlusion(note):
        io_fields = None
        try:
            io_fields = mw.backend.get_image_occlusion_fields(note.mid)
        except Exception:
            io_fields = None

        preferred_indices = []
        if io_fields is not None:
            for attr in ("header", "back_extra", "comments"):
                idx = getattr(io_fields, attr, None)
                if idx is not None:
                    preferred_indices.append(int(idx))

        if not preferred_indices:
            for field_name in ("Header", "Back Extra", "Comments"):
                idx = field_index_by_name(note, field_name)
                if idx is not None:
                    preferred_indices.append(idx)

        skipped_indices = set()
        if io_fields is not None:
            for attr in ("occlusions", "image"):
                idx = getattr(io_fields, attr, None)
                if idx is not None:
                    skipped_indices.add(int(idx))

        for idx in preferred_indices:
            if 0 <= idx < len(model_fields):
                field_name = model_fields[idx]["name"]
                if field_allowed_for_card(card, field_name, config):
                    return idx

        for idx, field in enumerate(model_fields):
            if idx in skipped_indices:
                continue
            if field_allowed_for_card(card, field["name"], config):
                return idx

    for idx, field in enumerate(model_fields):
        if field_allowed_for_card(card, field["name"], config):
            return idx

    return 0


def add_edit_filter_to_template(template_html: str, field_names: set[str]) -> str:
    def replace(match: re.Match[str]) -> str:
        inner = match.group(1).strip()
        if not inner or inner[0] in "#/^":
            return match.group(0)

        parts = [part.strip() for part in inner.split(":")]
        if not parts:
            return match.group(0)

        field_name = parts[-1]
        filters = parts[:-1]
        if field_name not in field_names:
            return match.group(0)
        if any(filter_name.lower() == "edit" for filter_name in filters):
            return match.group(0)
        if any(filter_name.lower().startswith("type") for filter_name in filters):
            return match.group(0)

        return "{{" + ":".join(["edit", *parts]) + "}}"

    return _FIELD_REPLACEMENT_RE.sub(replace, template_html)
