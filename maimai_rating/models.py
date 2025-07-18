# pyright: basic

from dataclasses import dataclass
from functools import cache, cached_property
from pathlib import Path
from rich.text import Text

from maimai_rating import data


ranks = [
    # rank, color, acc threshold, rank constant
    ("SSS+", "#a6e3a1", 1.005, 22.4),
    ("SSS", "#a6e3a1", 1.000, 21.6),
    ("SS+", "#74c7ec", 0.995, 21.1),
    ("SS", "#74c7ec", 0.99, 20.8),
    ("S+", "#f9e2af", 0.98, 20.3),
    ("S", "#f9e2af", 0.97, 20.0),
    ("AAA", "#f38ba8", 0.94, 16.8),
    ("AA", "#f38ba8", 0.90, 15.2),
    ("A", "#f38ba8", 0.80, 13.6),
    ("BBB", "#74c7ec", 0.75, 0.0),  # RCs below A unknown
    ("BB", "#74c7ec", 0.70, 0.0),
    ("B", "#74c7ec", 0.60, 0.0),
    ("C", "#a0a0a0", 0.50, 0.0),
    ("D", "#a0a0a0", 0.00, 0.0),
]

diff_display = {diff: (name, color) for diff, name, color in data.diffs.rows()}


def calc_rating(int_level: float, accuracy: float) -> int:
    rc = next(x for _, _, a, x in ranks if accuracy >= a)
    return int(int_level * min(accuracy, 1.005) * rc)


def rank_for_rating(int_level: float, target: int) -> Text :
    for r, c, a, _ in ranks[::-1]:
        if (new_rating := calc_rating(int_level, a)) > target:
            return Text.assemble(
                (f"+{new_rating - target}", "yellow"),
                " for ",
                (r, c),
            )
    return Text("")


@dataclass
class Score:
    title: str
    dxmax: int
    difficulty: str
    dxscore: int
    accuracy: float
    topn: int = 999

    @cached_property
    def _chart_data(self) -> dict:
        found = data.sheets.filter(
            title=self.title,
            difficulty=self.difficulty,
            dxmax=self.dxmax,
        )
        assert len(found) == 1
        return found.row(0, named=True)

    @property
    def is_new(self) -> bool:
        return self._chart_data["isNew"]

    @property
    def internal_level(self) -> float:
        return self._chart_data["internalLevelValue"]

    @cached_property
    def rating(self) -> int:
        return calc_rating(self.internal_level, self.accuracy)

    @cached_property
    def star_count(self) -> int:
        dx_acc = self.dxscore / self.dxmax
        return sum(dx_acc >= i for i in [0.85, 0.90, 0.93, 0.95, 0.97])

    @cached_property
    def table_info(self):
        d = self._chart_data
        info_title = Text.assemble(
            ("[N] ", "green") if self.is_new else "",
            self.title,
            overflow="ellipsis",
        )
        info_title.truncate(30)
        info_title.append_text(Text(" DX", "yellow") if d["type"] == "dx" else Text(" STD", "blue"))

        info_diff = Text(
            f"{diff_display[self.difficulty][0]} {self.internal_level:.1f}",
            diff_display[self.difficulty][1],
        )

        info_acc = Text.assemble(
            f"{self.accuracy:.4%} ",
            next((r, c) for r, c, a, _ in ranks if self.accuracy >= a),
        )

        info_rating = Text(str(self.rating))
        if self.topn <= 15:
            info_rating.append(f" {self.topn}/15", "green")
        elif self.topn <= 50:
            info_rating.append(f" {self.topn-15}/35", "yellow")

        info_dx = Text.assemble(
            str(self.dxscore),
            ("/", "#808080"),
            str(self.dxmax),
            (f" {self.star_count}*", ["#808080", "green", "green", "red", "red", "yellow"][self.star_count]),
            (f" {self.dxscore/self.dxmax:.1%}", "#808080"),
        )

        return (info_title, info_diff, info_acc, info_dx, info_rating)


class PlayerScores:
    def __init__(self, scores: list[Score]) -> None:
        self.scores = scores
        # assign b50
        self.scores.sort(key=lambda s: s.rating, reverse=True)
        b15_count = 0
        b35_count = 0
        self.min_b35 = 999
        self.min_b15 = 999
        for s in self.scores:
            if b15_count == 15 and b35_count == 35:
                break
            if s.is_new and b15_count < 15:
                b15_count += 1
                s.topn = b15_count
                self.min_b15 = s.rating
                continue
            if b35_count < 35:
                b35_count += 1
                s.topn = b35_count + 15
                self.min_b35 = s.rating
                continue
        if b15_count < 15:
            self.min_b15 = 0
        if b35_count < 35:
            self.min_b35 = 0

    def __iter__(self):
        return iter(self.scores)

    def __len__(self):
        return len(self.scores)

    def __getitem__(self, index):
        return self.scores[index]

    def rating_totals(self):
        b15_total = 0
        b35_total = 0
        for score in self.scores:
            if score.topn <= 15:
                b15_total += score.rating
            elif score.topn <= 50:
                b35_total += score.rating
        b50_total = b15_total + b35_total
        return (b15_total, b35_total, b50_total)

    def rank_for_rating(self, score: Score | float, is_new: bool | None = None) -> Text | str:
        if is_new is not None:
            assert isinstance(score, float)
            level = score
            rating = 0
        else:
            assert isinstance(score, Score)
            level = score.internal_level
            is_new = score.is_new
            rating = score.rating

        target = self.min_b35
        if is_new:
            target = min(self.min_b15, self.min_b35)
        target = max(target, rating)

        return rank_for_rating(level, target)

    @classmethod
    def from_df(cls, df) -> "PlayerScores":
        cols = df.select("title", "dxmax", "difficulty", "dxscore", "accuracy")
        return cls([Score(**d) for d in cols.to_dicts()])
