"""Run locally to authorize a hosted frontend. Restart the backend after changes."""
import argparse
import json
import secrets

from localvoiceai.config import Settings
from localvoiceai.pairing import validate_origin

parser = argparse.ArgumentParser(description=__doc__)
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--origin", help="Exact HTTPS frontend origin")
group.add_argument("--revoke", action="store_true")
args = parser.parse_args()
settings = Settings()
path = settings.data_dir / "workspace-pairing.json"
if args.revoke:
    path.unlink(missing_ok=True)
    print("Pairing revoked. Restart the backend to apply.")
else:
    origin = validate_origin(args.origin)
    settings.prepare()
    token = secrets.token_urlsafe(32)
    path.write_text(json.dumps({"origin": origin, "token": token}), encoding="utf-8")
    print(f"Authorized site: {origin}\nRestart the backend, then paste this token into that site:\n{token}")
