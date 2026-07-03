"""
One-time local utility: writes a freshly-downloaded Firebase service-account
JSON file into backend/.env, and prints a single-line FIREBASE_CREDENTIALS
value ready to paste into Render's dashboard.

Usage:
    python update_firebase_env.py path\to\downloaded-service-account.json

This script contains no secrets itself and is safe to keep in the repo -
it only reads whatever file path you pass it at runtime.
"""
import json
import re
import sys
from pathlib import Path

FIELDS = [
    "project_id",
    "private_key_id",
    "private_key",
    "client_email",
    "client_id",
    "auth_uri",
    "token_uri",
    "auth_provider_x509_cert_url",
    "client_x509_cert_url",
]

ENV_KEY_MAP = {
    "project_id": "FIREBASE_PROJECT_ID",
    "private_key_id": "FIREBASE_PRIVATE_KEY_ID",
    "private_key": "FIREBASE_PRIVATE_KEY",
    "client_email": "FIREBASE_CLIENT_EMAIL",
    "client_id": "FIREBASE_CLIENT_ID",
    "auth_uri": "FIREBASE_AUTH_URI",
    "token_uri": "FIREBASE_TOKEN_URI",
    "auth_provider_x509_cert_url": "FIREBASE_AUTH_PROVIDER_CERT_URL",
    "client_x509_cert_url": "FIREBASE_CLIENT_CERT_URL",
}


def main():
    if len(sys.argv) != 2:
        print("Usage: python update_firebase_env.py path\\to\\service-account.json")
        sys.exit(1)

    json_path = Path(sys.argv[1])
    if not json_path.exists():
        print(f"File not found: {json_path}")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        creds = json.load(f)

    missing = [f for f in FIELDS if f not in creds]
    if missing:
        print(f"Warning: JSON is missing fields: {missing}")

    env_path = Path("backend/.env")
    text = env_path.read_text(encoding="utf-8") if env_path.exists() else ""

    for field in FIELDS:
        if field not in creds:
            continue
        env_key = ENV_KEY_MAP[field]
        value = creds[field]
        if field == "private_key":
            value = value.replace("\n", "\\n")
            line = f'{env_key}="{value}"'
        else:
            line = f"{env_key}={value}"

        pattern = re.compile(rf"^{env_key}=.*$", re.MULTILINE)
        if pattern.search(text):
            text = pattern.sub(line, text, count=1)
        else:
            text = text.rstrip("\n") + "\n" + line + "\n"

    env_path.write_text(text, encoding="utf-8")
    print(f"Updated {env_path} with new Firebase service account credentials.")

    minified = json.dumps(creds, separators=(",", ":"))
    render_env_path = Path("render_firebase_credentials.txt")
    render_env_path.write_text(minified, encoding="utf-8")
    print(f"Wrote single-line JSON for Render's FIREBASE_CREDENTIALS var to: {render_env_path}")
    print("Open that file locally, copy its contents into Render's dashboard, then delete the file.")
    print("Do NOT paste its contents into chat.")


if __name__ == "__main__":
    main()
