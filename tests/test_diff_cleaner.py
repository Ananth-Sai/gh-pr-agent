from services.diff_cleaner import (
    clean_and_truncate_diff,
    get_valid_diff_lines_by_file,
)


def test_clean_diff_removes_lockfiles():
    sample_diff = """diff --git a/package-lock.json b/package-lock.json
index 1234567..89abcdef 100644
--- a/package-lock.json
+++ b/package-lock.json
@@ -1,3 +1,3 @@
-"version": "1.0.0"
+"version": "1.0.1"
diff --git a/main.py b/main.py
index abcdef1..2345678 100644
--- a/main.py
+++ b/main.py
@@ -1,2 +1,3 @@
+import os
"""
    cleaned = clean_and_truncate_diff(sample_diff)
    assert "package-lock.json" not in cleaned
    assert "main.py" in cleaned


def test_clean_diff_truncates_large_payloads():
    huge_diff = "diff --git a/big.py b/big.py\n" + ("+line\n" * 1000)
    cleaned = clean_and_truncate_diff(huge_diff, max_chars=500)
    assert len(cleaned) < 700
    assert "[DIFF TRUNCATED" in cleaned


def test_get_valid_diff_lines_by_file():
    diff = """diff --git a/calculator.py b/calculator.py
--- a/calculator.py
+++ b/calculator.py
@@ -1,3 +1,5 @@
 def initial():
+    x = 10
+    y = 20
     return None
"""
    valid_lines = get_valid_diff_lines_by_file(diff)
    assert "calculator.py" in valid_lines
    # Target right-side additions and context lines start at line 1
    assert {1, 2, 3, 4} <= valid_lines["calculator.py"]