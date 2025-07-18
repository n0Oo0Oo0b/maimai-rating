# pyright: basic

from textual.app import App

from maimai_rating.tui.score_table import RatingTable, ScoreTable
from maimai_rating.tui.profiles import ProfileSelector


class MaimaiRatingApp(App):
    # CSS_PATH = "styles.tcss"
    CSS = """
    ScoreTable {
        padding: 0 3;
    }
    """

    def compose(self):
        yield ProfileSelector()
        yield ScoreTable()
        yield RatingTable()
