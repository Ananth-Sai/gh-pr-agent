import re
from typing import NamedTuple


class SecretMatch(NamedTuple):
    secret_type: str
    matched_snippet: str
    line_number: int | None


SECRET_PATTERNS = {
    "GitHub Personal Access Token": re.compile(
        r"(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82})"
    ),
    "OpenAI / Simulated API Key": re.compile(r"sk-[a-zA-Z0-9_-]{20,64}"),
    "AWS Access Key ID": re.compile(
        r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}"
    ),
    "Generic Private Key Block": re.compile(
        r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"
    ),
    "Slack Bot Token": re.compile(
        r"xoxb-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24}"
    ),
    "Generic Password Assignment": re.compile(
        r"""(?i)(?:password|passwd|pwd|secret|api_key|apikey)\s*=\s*['"][^'"]{8,}['"]"""
    ),
}


def scan_diff_for_secrets(raw_diff: str) -> list[SecretMatch]:
    """Locally pre-scans unified diff additions (+) for exposed credentials and secrets."""
    detected_secrets: list[SecretMatch] = []
    current_line_num = 0

    for line in raw_diff.split("\n"):
        if line.startswith("@@"):
            match = re.search(r"\+(\d+)", line)
            if match:
                current_line_num = int(match.group(1))
            continue

        if line.startswith("+") and not line.startswith("+++"):
            code_line = line[1:].strip()
            for secret_type, pattern in SECRET_PATTERNS.items():
                match = pattern.search(code_line)
                if match:
                    snippet = match.group(0)
                    masked = (
                        snippet[:4] + "*" * (len(snippet) - 8) + snippet[-4:]
                        if len(snippet) > 8
                        else "****"
                    )
                    detected_secrets.append(
                        SecretMatch(
                            secret_type=secret_type,
                            matched_snippet=masked,
                            line_number=current_line_num,
                        )
                    )
            current_line_num += 1
        elif line.startswith(" "):
            current_line_num += 1

    return detected_secrets
