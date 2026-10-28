"""スキルをClaudeにアップロードできる zip（release/bank-journal.zip）にまとめる。

jev_config.json があれば一緒に入る（APIキーを含むので、その zip は人に渡さない）。
"""

import zipfile
from pathlib import Path

SKILL = Path(__file__).resolve().parent
OUTPUT = SKILL.parent.parent / "release" / "bank-journal.zip"
FILES = ["SKILL.md", "jev_config.json.example", "jev_config.json",
         "scripts/common.py", "scripts/build_rules.py", "scripts/journalize.py", "scripts/jev_client.py"]


def main() -> None:
    OUTPUT.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as z:
        for name in FILES:
            path = SKILL / name
            if path.exists():
                z.write(path, f"bank-journal/{name}")
                print("追加:", name)
    print("作成しました:", OUTPUT)


if __name__ == "__main__":
    main()
