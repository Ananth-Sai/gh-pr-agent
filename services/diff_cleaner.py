import re

IGNORED_EXTENSIONS = {
    ".lock", ".min.js", ".min.css", ".map", ".svg", ".png",
    ".jpg", ".jpeg", ".gif", ".ico", ".pdf",
}

IGNORED_FILENAMES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    "pipfile.lock", "cargo.lock", "composer.lock", "go.sum",
}

MAX_DIFF_CHARACTERS = 25000


def clean_and_truncate_diff(raw_diff: str, max_chars: int = MAX_DIFF_CHARACTERS) -> str:
    """Filters out dependency lockfiles, assets, and truncates large diffs."""
    if not raw_diff:
        return ""

    file_diffs = re.split(r"(?=diff --git )", raw_diff)
    cleaned_sections = []

    for file_diff in file_diffs:
        if not file_diff.strip():
            continue

        match = re.search(r"diff --git a/.*? b/(.+)", file_diff)
        if match:
            file_path = match.group(1).strip()
            file_name = file_path.split("/")[-1].lower()

            if file_name in IGNORED_FILENAMES or any(file_name.endswith(ext) for ext in IGNORED_EXTENSIONS):
                continue

        cleaned_sections.append(file_diff)

    combined_diff = "".join(cleaned_sections)
    if len(combined_diff) > max_chars:
        combined_diff = combined_diff[:max_chars] + f"\n\n... [DIFF TRUNCATED: Exceeded {max_chars} limit] ..."

    return combined_diff


def get_valid_diff_lines_by_file(raw_diff: str) -> dict[str, set[int]]:
    """Extracts valid target line numbers on the 'RIGHT' side for each file from diff hunks."""
    valid_lines_map: dict[str, set[int]] = {}
    file_diffs = re.split(r"(?=diff --git )", raw_diff)

    for file_diff in file_diffs:
        if not file_diff.strip():
            continue

        match = re.search(r"diff --git a/.*? b/(.+)", file_diff)
        if not match:
            continue

        file_path = match.group(1).strip()
        valid_lines: set[int] = set()

        hunks = re.split(r"(?=@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@)", file_diff)
        for hunk in hunks:
            hunk_header = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", hunk)
            if not hunk_header:
                continue

            current_line = int(hunk_header.group(1))
            for line in hunk.split("\n")[1:]:
                if line.startswith("+") or line.startswith(" "):
                    valid_lines.add(current_line)
                    current_line += 1
                elif line.startswith("-"):
                    continue

        valid_lines_map[file_path] = valid_lines

    return valid_lines_map
