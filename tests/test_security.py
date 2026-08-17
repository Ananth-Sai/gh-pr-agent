from services.security import scan_diff_for_secrets


def test_scan_diff_detects_github_pat():
    diff = """
diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,3 +1,4 @@
+GITHUB_KEY = "ghp_123456789012345678901234567890123456"
"""
    secrets = scan_diff_for_secrets(diff)
    assert len(secrets) == 1
    assert secrets[0].secret_type == "GitHub Personal Access Token"
    assert "ghp_" in secrets[0].matched_snippet


def test_scan_diff_detects_aws_key():
    diff = """
diff --git a/config.py b/config.py
--- a/config.py
+++ b/config.py
@@ -1,2 +1,3 @@
+AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
"""
    secrets = scan_diff_for_secrets(diff)
    assert len(secrets) == 1
    assert secrets[0].secret_type == "AWS Access Key ID"


def test_scan_diff_detects_openai_key():
    diff = """
diff --git a/ai.py b/ai.py
--- a/ai.py
+++ b/ai.py
@@ -1,2 +1,3 @@
+OPENAI_KEY = "sk-1234567890abcdef1234567890abcdef"
"""
    secrets = scan_diff_for_secrets(diff)
    assert len(secrets) == 1
    assert secrets[0].secret_type == "OpenAI / Simulated API Key"


def test_scan_diff_clean_code():
    diff = """
diff --git a/calculator.py b/calculator.py
--- a/calculator.py
+++ b/calculator.py
@@ -1,2 +1,3 @@
+def add(a: int, b: int) -> int:
+    return a + b
"""
    secrets = scan_diff_for_secrets(diff)
    assert len(secrets) == 0