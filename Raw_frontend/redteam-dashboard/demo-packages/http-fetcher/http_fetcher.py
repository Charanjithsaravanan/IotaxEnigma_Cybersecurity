import json
from urllib.request import urlopen


def fetch_json(url: str) -> object:
    """Fetch and decode a JSON response from the provided URL."""
    with urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))
