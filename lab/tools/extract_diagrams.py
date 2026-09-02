"""Extract mermaid blocks from the lab file into individual .mmd files for rendering."""
import re
import pathlib

SRC = pathlib.Path("lab/SE_LAB_FILE.md")
OUT = pathlib.Path("lab/tools/diagrams")
OUT.mkdir(parents=True, exist_ok=True)

text = SRC.read_text(encoding="utf-8")
blocks = re.findall(r"```mermaid\n(.*?)\n```", text, re.DOTALL)

for i, body in enumerate(blocks, 1):
    (OUT / f"diagram_{i:02d}.mmd").write_text(body.strip() + "\n", encoding="utf-8")

print(f"extracted {len(blocks)} mermaid diagrams -> {OUT}")
for i, body in enumerate(blocks, 1):
    kind = body.strip().split("\n")[0].split()[0]
    print(f"  diagram_{i:02d}.mmd  ({kind})")
