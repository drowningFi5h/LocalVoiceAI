"""An explicit grant for one hosted frontend; never expose the model server."""
import json
import secrets
from urllib.parse import urlsplit


def validate_origin(value):
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or
            parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
        raise ValueError("Use an exact HTTPS site origin, without a path or credentials.")
    return value.rstrip("/")


class Pairing:
    def __init__(self, data_dir):
        path = data_dir / "workspace-pairing.json"
        self.origin = None
        self.token = None
        if path.exists():
            value = json.loads(path.read_text())
            self.origin = validate_origin(value["origin"])
            self.token = value["token"]
            if not isinstance(self.token, str) or len(self.token) < 32:
                raise ValueError("Invalid workspace pairing token. Generate a new pairing.")

    def authorized(self, origin, token):
        return bool(self.token and origin == self.origin and
                    secrets.compare_digest(token.encode(), self.token.encode()))
