# pyright: basic

from collections.abc import Callable
from itertools import groupby
from typing import Any

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import DataTable, Label, Select

from maimai_rating.models import PlayerScores, Score, calc_rating, rank_for_rating

class RatingTable(Widget):
    b50_min: reactive[tuple[int, int] | None] = reactive(None)

    DEFAULT_CSS = """
    RatingTable {
        padding: 0 3;
    }

    RatingTable Label {
        padding-top: 1;
    }
    """

    def compose(self):
        table = DataTable()
        table.add_columns("Level", "New chart", "Old chart")

        yield Label("Baseline improvements:")
        yield table

    def watch_b50_min(self, _, new_min: tuple[int, int] | None):
        table = self.query_exactly_one(DataTable)
        table.clear()

        if new_min is None:
            return
        b15, b35 = new_min

        for l in range(100, 151):
            level = l / 10
            if calc_rating(level, 100.5) <= min(b15, b35):
                continue
            table.add_row(
                f"{level:.1f}",
                rank_for_rating(level, min(b15, b35)),
                rank_for_rating(level, b35),
            )
        table.refresh()


class SortFilterSelector(Widget):
    DEFAULT_CSS = """
    SortFilterSelector {
        layout: horizontal;
        height: auto;
        padding: 0;
    }

    SortFilterSelector Select {
        width: 30;
    }
    """

    def compose(self):
        yield Label("Sort: ")
        yield Select.from_values(ScoreTable.sorts.keys(), compact=True, id="sort", allow_blank=False)
        yield Label("Filter: ")
        yield Select.from_values(ScoreTable.filters.keys(), compact=True, id="filter", allow_blank=False)

    def on_select_changed(self, message: Select.Changed):
        table = self.query_ancestor(ScoreTable)
        if message.select.id == "sort":
            table.sort = message.value  # pyright: ignore
        elif message.select.id == "filter":
            table.filter = message.value  # pyright: ignore


class RatingLabel(Label):
    rating: reactive[tuple[int, int, int] | None] = reactive(None)

    def render(self) -> str:
        if self.rating is None:
            return "Rating: N/A"
        b15, b35, b50 = self.rating
        return f"Rating: {b50} ({b15} + {b35}; avg {b50/50:.1f})"


class ScoreTable(Widget):
    data: reactive[PlayerScores | None] = reactive(None)
    filter: reactive[str] = reactive("all")
    sort: reactive[str] = reactive("rating")

    filters: dict[str, Callable[[Score], Any]] = {
        "all": lambda _: True,
        "new": lambda s: s.is_new,
        "old": lambda s: not s.is_new,
        "b50": lambda s: s.topn <= 50,
    }

    sorts: dict[str, Callable[[Score], Any]] = {
        "rating": lambda s: s.rating,
        "accuracy": lambda s: s.accuracy,
        "dx": lambda s: s.dxscore / s.dxmax,
        "internalLevel": lambda s: s.internal_level,
    }

    DEFAULT_CSS = """
    ScoreTable {
        height: auto;
    }

    ScoreTable RatingLabel {
        margin-bottom: 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()

    def compose(self) -> ComposeResult:
        table = DataTable(
            cursor_type="row",
            cursor_foreground_priority="renderable",
            show_row_labels=True,
        )
        table.add_columns("Song", "Difficulty", "Score", "DX Score", "Rating", "Improvement")

        yield RatingLabel()
        yield SortFilterSelector()
        yield table

    def refill_table(self):
        if self.data is None:
            return
        sort_fn = self.sorts[self.sort]
        filter_fn = self.filters[self.filter]

        table = self.query_exactly_one(DataTable)
        table.clear()
        i = 1
        data = sorted(filter(filter_fn, self.data), key=sort_fn, reverse=True)
        for _, plays in groupby(data, key=sort_fn):
            k = 0
            for play in plays:
                r = self.data.rank_for_rating(play)
                table.add_row(*play.table_info, r, label=str(i))
                k += 1
            i += k
        self.styles.height = i + 3
        table.refresh(layout=True)

    def watch_data(self, _, new_data: PlayerScores | None):
        if new_data is None:
            self.query_one(RatingLabel).rating = None
            self.query_exactly_one(DataTable).clear()
        else:
            self.query_one(RatingLabel).rating = new_data.rating_totals()
            self.refill_table()

    def watch_filter(self, *_):
        self.refill_table()

    def watch_sort(self, *_):
        self.refill_table()
