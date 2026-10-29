"""
Offline mode: the backend must boot and verify logins with NO Firebase service account when it is
pointed at the local emulators (docker-compose.offline.yml) — and must not do that by accident.

Runs the real FirebaseService in a fresh interpreter (it initialises Firebase at import time).
The emulators themselves need Java, so they are not started here; the SDK-level behaviour is.

Run from backend/:  python -m pytest tests/test_offline_mode.py -q
"""

import json
import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent

PROBE = r"""
import asyncio, base64, json, sys, time
sys.path.insert(0, ".")
from app.services.firebase_service import firebase_service, emulator_mode

def b64(obj):
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()

project = "demo-flowmind"
now = int(time.time())
# what the Auth emulator hands out: an UNSIGNED token with the usual Firebase claims
token = ".".join([b64({"alg": "none", "typ": "JWT"}),
                  b64({"iss": f"https://securetoken.google.com/{project}", "aud": project, "auth_time": now,
                       "user_id": "emu-user", "sub": "emu-user", "iat": now, "exp": now + 3600,
                       "email": "emu@example.com", "firebase": {"identities": {}, "sign_in_provider": "password"}}),
                  ""])
claims = asyncio.run(firebase_service.verify_token(token))
print(json.dumps({"emulator": emulator_mode(), "has_db": firebase_service.db is not None,
                  "uid": (claims or {}).get("uid"), "email": (claims or {}).get("email")}))
"""


def run_probe(extra_env):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("FIREBASE", "FIRESTORE_EMULATOR", "GOOGLE_APPLICATION"))}
    env.update({"PYTHONWARNINGS": "ignore", **extra_env})
    return subprocess.run([sys.executable, "-c", PROBE], cwd=BACKEND, env=env, capture_output=True, text=True, timeout=120)


def test_backend_boots_and_verifies_logins_against_the_emulators_without_any_key():
    result = run_probe({
        "FIRESTORE_EMULATOR_HOST": "127.0.0.1:8080",
        "FIREBASE_AUTH_EMULATOR_HOST": "127.0.0.1:9099",
        "FIREBASE_PROJECT_ID": "demo-flowmind",
    })
    assert result.returncode == 0, result.stderr[-1500:]
    assert json.loads(result.stdout.strip().splitlines()[-1]) == {
        "emulator": True, "has_db": True, "uid": "emu-user", "email": "emu@example.com"}
    assert "LOCAL EMULATORS" in result.stderr + result.stdout             # loud, so it is never silent in production


def test_without_the_emulator_variables_real_credentials_are_still_required():
    """Offline mode must never switch itself on: no variables → the normal (strict) startup path."""
    result = run_probe({"FIREBASE_PROJECT_ID": "demo-flowmind"})
    assert result.returncode != 0
    assert "certificate" in result.stderr.lower() or "credential" in result.stderr.lower()
