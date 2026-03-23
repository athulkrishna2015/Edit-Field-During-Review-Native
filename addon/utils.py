# -*- coding: utf-8 -*-

from typing import Optional

from anki.cards import Card
from anki.notes import Note
from aqt import mw


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


def field_allowed_for_card(card: Card, field_name: str, config: dict) -> bool:
    try:
        model = card.note().model()
        exclusions = config.get("exclusions", {}).get(model["name"], {})
        if exclusions.get("disabled"):
            return False
        if field_name in exclusions.get("fields", []):
            return False
        template_name = template_name_for_card(card)
        if template_name and template_name in exclusions.get("templates", []):
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
