# demo-http-fetcher

A lightweight HTTP client for fetching JSON APIs.

Network access occurs only when `fetch_json(url)` is called; importing this
module does not make a request. The package uses Python's standard library.

## Usage

```python
from http_fetcher import fetch_json

result = fetch_json("https://httpbin.org/get")
```
