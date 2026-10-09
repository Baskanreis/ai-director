from pathlib import Path
import importlib.util
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def test_api_contract_audit_runs_in_clean_process():
    script = ROOT / "installer" / "api_contract_audit.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_proxy_cache_uses_canonical_project_import():
    source = (ROOT / "app" / "proxy" / "test_cache.py").read_text(encoding="utf-8")
    assert "from app.proxy.cache import ProxyCache" in source
    assert "from proxy.cache import ProxyCache" not in source


def test_provider_model_is_not_stale_placeholder():
    source = (ROOT / "app" / "agents" / "provider_config.py").read_text(encoding="utf-8")
    assert '"model": "gpt-5.6-sol"' in source
    assert '"model": "gpt-5.6",' not in source
