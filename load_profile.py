from pathlib import Path
import pyperclip

PROFILES_PATH = Path(__file__).parent / "profiles"


print("Existing profiles:")
for i in PROFILES_PATH.iterdir():
    if not i.is_dir():
        continue
    print(f"- {i.name}")
profile = input("Enter profile name: ")
(PROFILES_PATH / profile).mkdir(exist_ok=True)
print()


diffs = {
    "b": "basic",
    "a": "advanced",
    "e": "expert",
    "m": "master",
    "r": "remaster",
}

n = 0
while True:
    diff = input("Difficulty ([B]ASIC [A]DVANCED [E]XPERT [M]ASTER [R]EMASTER) or [Q]uit: ").lower()
    if not diff or diff == "q":
        break
    if diff not in diffs:
        print("Invalid option, try again")
        continue
    path = PROFILES_PATH / profile / f"{diffs[diff]}.txt"
    data = pyperclip.paste()
    length = path.write_text(data)
    n += 1
    print(f"{length} bytes written to {path}")
print(f"Wrote {n} total files")
