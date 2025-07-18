# pyright: basic

from functools import cache
import re
from pathlib import Path

import polars as pl


PROFILES_PATH = Path("profiles")


replacements = {
    "Help me, ERINNNNNN!!（Band ver.）": "Help me, ERINNNNNN!!",
    "Bad Apple!! feat.nomico": "Bad Apple!! feat nomico",
}


# Song data
data = pl.read_json("songdata.json")
unwrap = lambda col: data.select(pl.col(col).explode().struct.unnest())
songs = unwrap("songs")
diffs = unwrap("difficulties")

sheets = songs.lazy().explode("sheets").select(
    *(pl.col(col) for col in ["songId", "category", "title", "artist", "bpm"]),
    *(pl.col("sheets").struct.field(field) for field in ["type", "difficulty", "level", "internalLevelValue", "noteCounts", "regions", "isSpecial", "version"]),
).with_columns(
    pl.col("title").replace(replacements),
    dxmax=pl.col("noteCounts").struct.field("total") * 3,
    isNew=pl.col("version").is_in(["PRiSM", "PRiSM PLUS", "BUDDiES PLUS"]),
).collect()


@cache
def read_profile(profile) -> pl.DataFrame:
    # Score data
    profile_fp = PROFILES_PATH / profile
    play_data: list[tuple[str, str, float, int, int]] = []
    for diff in diffs["difficulty"]:
        if not (fp := profile_fp / f"{diff}.txt").exists():
            continue
        for m in re.finditer(r"(.*)\n([\d.]+)% ?([\d,]+) / ([\d,]+)", fp.read_text()):
            title, acc, dx1, dx2 = m.groups()
            play_data.append((
                title, diff,
                round(float(acc) / 100, 6),
                int(dx1.replace(",", "")),
                int(dx2.replace(",", "")),
            ))
    plays = pl.DataFrame(play_data, ["title", "difficulty", "accuracy", "dxscore", "dxmax"], orient="row")
    return plays


if __name__ == "__main__":
    from models import PlayerScores

    f = Path(__file__).parent / "profiles/cherry/other_calc_b50_full.txt"
    dat2 = f.read_text().splitlines()

    a = read_profile("cherry")
    a = sheets.join(a, on=["title", "difficulty", "dxmax"])

    for title, _, typ, acc, _, rat, _, level, _ in zip(*[iter(dat2)]*9):
        x = a.filter((pl.col("accuracy") - float(acc[:-1])/100).abs() < 1e-8, title=title)
        [d] = PlayerScores.from_df(x)
        if d.internal_level != float(level):
            print(f"{title} {d.difficulty} {d.internal_level} -> {level}")
        if d.rating != (r := int(rat.split(":")[1])):
            print(f"{title} {d.difficulty} {d.rating} -> {r}")
