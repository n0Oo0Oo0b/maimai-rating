# pyright: basic

from pathlib import Path

from textual import on
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Button, Label, Select, Static
import pyperclip

from maimai_rating import data
from maimai_rating.models import PlayerScores
from maimai_rating.tui.score_table import RatingTable, ScoreTable


class ProfileSelector(Widget):
    DEFAULT_CSS = """
    ProfileSelector {
        layout: horizontal;
        height: auto;
        padding: 1;
    }

    ProfileSelector Select {
        width: 30;
    }
    """

    def __init__(self, path="profiles") -> None:
        super().__init__()
        self.profiles = [p.stem for p in Path(path).iterdir() if p.is_dir()]

    def compose(self) -> ComposeResult:
        yield Label("Profile ")
        yield Select.from_values(self.profiles, compact=True, type_to_search=True)
        yield Button("Import data", compact=True)

    def on_select_changed(self, message: Select.Changed):
        if message.value == Select.BLANK:
            self.data = None
            return
        df = data.read_profile(message.value)

        scores = PlayerScores.from_df(df)
        self.app.query_one(ScoreTable).data = scores
        self.app.query_one(RatingTable).b50_min = (scores.min_b15, scores.min_b35)

    def on_button_pressed(self, _: Button.Pressed):
        profile = self.query_one(Select).value
        if profile == Select.BLANK:
            return
        self.app.push_screen(ProfileImportDialog(profile))  # pyright: ignore


class ClipboardSaveButton(Widget):
    DEFAULT_CSS = """
    ClipboardSaveButton {
        layout: horizontal;
        width: auto;
        height: auto;
    }
    """

    def __init__(self, label: str, file: Path) -> None:
        super().__init__()
        self.label = label
        self.file = file

    def compose(self) -> ComposeResult:
        yield Button(self.label, compact=True)
        yield Label("")

    @on(Button.Pressed)
    def pressed(self):
        data = pyperclip.paste()
        pasted_len = self.file.write_text(data)
        self.query_one(Label).update(f"{pasted_len} bytes written")


class ProfileImportDialog(Screen):
    DEFAULT_CSS = """
    ProfileImportDialog {
        width: auto;
        height: auto;
        align: center middle;
        padding: 3 1;
        background: $primary 20%;
    }

    ProfileImportDialog>* {
        width: auto;
        height: auto;
        background: $background;
    }

    ProfileImportDialog>Button {
        padding-top: 1;
    }
    """

    BINDINGS = [("escape", "app.pop_screen", "Exit import menu")]

    difficulties = [
        ("Basic", "basic"),
        ("Advanced", "advanced"),
        ("Expert", "expert"),
        ("Master", "master"),
        ("Re:Master", "remaster"),
    ]

    def __init__(self, profile: str) -> None:
        super().__init__()
        self.profile = profile

    def compose(self) -> ComposeResult:
        yield Static(f"Import from clipboard to profile {self.profile}")
        for label, name in self.difficulties:
            yield ClipboardSaveButton(label, data.PROFILES_PATH / self.profile / f"{name}.txt")
        yield Button("Close menu", compact=True, id="exit-button")

    @on(Button.Pressed, "#exit-button")
    def exit(self):
        self.dismiss()
