# backend/registry.py
import os, hashlib, httpx
from pathlib import Path

async def fetch_package_info(ecosystem: str, name: str, version: str = "latest") -> dict:
    """Fetches README, version, and SHA256 from PyPI, npm, or a local demo directory."""
    # Case 1: Local folder path (e.g., ./frontend/demo_packages/evil_left_pad)
    if os.path.exists(name):
        path = Path(name)
        readme_path = path / "README.md"
        readme = readme_path.read_text(encoding="utf-8") if readme_path.exists() else "Local utility package."
        sha256 = hashlib.sha256(f"{path.name}:{readme}".encode()).hexdigest()
        return {
            "name": path.name,
            "version": "1.0.0-local",
            "sha256": sha256,
            "readme": readme,
            "metadata": {"source": "local", "path": str(path.resolve())}
        }

    # Case 2: Live PyPI Registry
    async with httpx.AsyncClient(timeout=15.0) as client:
        if ecosystem.lower() == "pypi":
            url = f"https://pypi.org/pypi/{name}/json" if version == "latest" else f"https://pypi.org/pypi/{name}/{version}/json"
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            info = data.get("info", {})
            resolved_ver = info.get("version", version)
            urls = data.get("urls", [])
            sha256 = urls[0]["digests"]["sha256"] if urls else hashlib.sha256(f"pypi:{name}:{resolved_ver}".encode()).hexdigest()
            return {
                "name": name,
                "version": resolved_ver,
                "sha256": sha256,
                "readme": info.get("description") or info.get("summary") or "",
                "metadata": {"summary": info.get("summary"), "home_page": info.get("home_page")}
            }

        # Case 3: Live npm Registry
        elif ecosystem.lower() == "npm":
            resp = await client.get(f"https://registry.npmjs.org/{name}")
            resp.raise_for_status()
            data = resp.json()
            resolved_ver = data.get("dist-tags", {}).get("latest", "1.0.0") if version == "latest" else version
            ver_data = data.get("versions", {}).get(resolved_ver, {})
            shasum = ver_data.get("dist", {}).get("shasum", hashlib.sha256(f"npm:{name}:{resolved_ver}".encode()).hexdigest())
            return {
                "name": name,
                "version": resolved_ver,
                "sha256": shasum,
                "readme": data.get("readme") or ver_data.get("description") or "",
                "metadata": {"description": ver_data.get("description"), "scripts": ver_data.get("scripts", {})}
            }
