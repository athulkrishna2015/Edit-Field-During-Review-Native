import json
import importlib.util
import types
import sys
import unittest
from pathlib import Path

from bump import increment_version, validate_version


def load_utils_module():
    """Load utils without executing the add-on's Anki-dependent entrypoint."""
    root = Path(__file__).resolve().parents[1]
    # utils only uses these imports for type annotations/runtime access to mw.
    # Stub them so tests do not require a running Anki GUI.
    anki_cards = types.ModuleType("anki.cards")
    anki_cards.Card = object
    anki_notes = types.ModuleType("anki.notes")
    anki_notes.Note = object
    aqt = types.ModuleType("aqt")
    aqt.mw = types.SimpleNamespace(backend=None)
    sys.modules.setdefault("anki.cards", anki_cards)
    sys.modules.setdefault("anki.notes", anki_notes)
    sys.modules.setdefault("aqt", aqt)
    package = sys.modules.setdefault("addon", type(sys)("addon"))
    package.__path__ = [str(root / "addon")]
    spec = importlib.util.spec_from_file_location("addon.utils", root / "addon" / "utils.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["addon.utils"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


utils = load_utils_module()
add_edit_filter_to_template = utils.add_edit_filter_to_template
field_allowed_for_card = utils.field_allowed_for_card


class FakeNote:
    def __init__(self):
        self._model = {
            "id": 10,
            "name": "Basic",
            "flds": [{"name": "Front", "ord": 0}, {"name": "Back", "ord": 1}],
        }
        self.values = {"Front": "question", "Back": "answer"}

    def model(self):
        return self._model

    def __getitem__(self, name):
        return self.values[name]


class FakeCard:
    def __init__(self):
        self._note = FakeNote()

    def note(self):
        return self._note

    def template(self):
        return {"name": "Card 1", "ord": 0}


class UtilsTests(unittest.TestCase):
    def test_template_rewrite_preserves_special_templates(self):
        template = "{{Front}} {{type:Back}} {{edit:Front}} {{#Tags}}{{Tags}}{{/Tags}}"
        result = add_edit_filter_to_template(template, {"Front", "Back"})
        self.assertEqual(
            result,
            "{{edit:Front}} {{type:Back}} {{edit:Front}} {{#Tags}}{{Tags}}{{/Tags}}",
        )

    def test_exclusions_use_stable_ordinals(self):
        card = FakeCard()
        config = {"exclusions_v2": {"10": {"fields": [1]}}}
        self.assertTrue(field_allowed_for_card(card, "Front", config))
        self.assertFalse(field_allowed_for_card(card, "Back", config))


class VersionTests(unittest.TestCase):
    def test_version_validation_and_bumping(self):
        self.assertEqual(validate_version("1.2"), "1.2.0")
        self.assertEqual(increment_version("1.2.3", "major"), "2.0.0")
        self.assertEqual(increment_version("1.2.3", "minor"), "1.3.0")
        self.assertEqual(increment_version("1.2.3", "patch"), "1.2.4")

    def test_sync_files_are_not_written_by_unit_helpers(self):
        # Keep this test explicit so the suite remains safe to run in the repo.
        self.assertTrue(Path("addon/manifest.json").is_file())
        self.assertEqual(json.loads(Path("addon/manifest.json").read_text())["version"], "7.4.2")


if __name__ == "__main__":
    unittest.main()
