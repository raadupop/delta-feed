"""Unwrap single-cell requirement tables into structured Markdown subsections.

Input pattern produced by docx_to_md.py:

    | [CLS-001]  [Must] The system shall ... Rationale: ... Verification: ... |
    | --- |

Output:

    ### CLS-001 [Must]

    The system shall ...

    **Rationale:** ...

    **Verification:** ...
"""

import re
import sys
from pathlib import Path

REQ_ID_PATTERN = r"(?:[A-Z]{3}|[A-Z]{2,4})-\d{3}"

# Matches the whole 2-line requirement table (cell line + separator line)
REQ_BLOCK = re.compile(
    r"^\|\s*\[(?P<id>" + REQ_ID_PATTERN + r")\]\s+\[(?P<prio>[^\]]+)\]\s*(?P<body>.*?)\s*\|\s*\n\|\s*---\s*\|\s*$",
    re.MULTILINE,
)


def split_body(body: str):
    """Split body at Rationale: and Verification: markers."""
    # Find Rationale: and Verification: positions; be liberal on leading whitespace
    rat_m = re.search(r"\bRationale:\s*", body)
    ver_m = re.search(r"\bVerification:\s*", body)

    statement = body
    rationale = None
    verification = None

    if rat_m and ver_m and rat_m.start() < ver_m.start():
        statement = body[: rat_m.start()].strip()
        rationale = body[rat_m.end() : ver_m.start()].strip()
        verification = body[ver_m.end() :].strip()
    elif rat_m and not ver_m:
        statement = body[: rat_m.start()].strip()
        rationale = body[rat_m.end() :].strip()
    elif ver_m and not rat_m:
        statement = body[: ver_m.start()].strip()
        verification = body[ver_m.end() :].strip()
    else:
        statement = body.strip()

    return statement, rationale, verification


def render(match: re.Match) -> str:
    req_id = match.group("id")
    prio = match.group("prio").strip()
    body = match.group("body")

    statement, rationale, verification = split_body(body)

    parts = [f"### {req_id} [{prio}]", "", statement]
    if rationale:
        parts.extend(["", f"**Rationale:** {rationale}"])
    if verification:
        parts.extend(["", f"**Verification:** {verification}"])
    return "\n".join(parts)


def main(path: Path):
    text = path.read_text(encoding="utf-8")
    new_text, n = REQ_BLOCK.subn(render, text)
    # Collapse excess blank lines introduced by replacements
    new_text = re.sub(r"\n{3,}", "\n\n", new_text)
    path.write_text(new_text, encoding="utf-8")
    print(f"unwrapped {n} requirement blocks in {path}")


def lint_cleanup(path: Path):
    """Safe markdownlint-ish cleanup. No cross-line whitespace regexes."""
    t = path.read_text(encoding="utf-8")
    # Strip leading blank lines
    t = t.lstrip("\n")
    # Fix '**INVEX**' emphasis-as-heading at file start → '# INVEX — ...'
    t = t.replace(
        "**INVEX**\n\nSoftware Requirements Specification\n",
        "# INVEX — Software Requirements Specification\n",
        1,
    )
    # Trailing space inside emphasis, within single line: '**xxx **' → '**xxx** '
    t = re.sub(r"\*\*([^*\n]+?)[ \t]+\*\*", r"**\1** ", t)
    # Leading space inside emphasis, within single line: '** xxx**' → ' **xxx**'
    t = re.sub(r"\*\*[ \t]+([^*\n]+?)\*\*", r" **\1**", t)
    # Collapse double spaces that may appear on the same line
    t = re.sub(r"(?m)[ \t]{2,}", " ", t)
    # Ensure blank line before headings
    t = re.sub(r"(?<=\n)(?=#{1,6} )", "\n", t)
    # Collapse >2 blank lines
    t = re.sub(r"\n{3,}", "\n\n", t)
    # Trailing newline
    if not t.endswith("\n"):
        t += "\n"
    path.write_text(t, encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
    lint_cleanup(Path(sys.argv[1]))
    print("cleanup pass done")
