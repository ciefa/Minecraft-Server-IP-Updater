#!/usr/bin/env python3
import re
import sys
from pathlib import Path

import requests
from nbtlib import File, Compound, List, String

# === CONFIGURATION ===
# Copy config.example.py to config.py and edit your settings there.
# For quick testing, you can edit these values directly:

SITE_URL = "https://example.com/server-status"  # URL that displays the current IP
INSTANCE_DIR = "/path/to/minecraft/instance/directory"  # Path to your Minecraft instance
SERVER_NAME = "My Minecraft Server"  # Name to display in server list

# Optionally load from config.py if it exists
try:
    from config import SITE_URL, INSTANCE_DIR, SERVER_NAME
except ImportError:
    pass  # Use the default values above
# ===================

IP_REGEX = re.compile(r"\b(?:(?:\d{1,3}\.){3}\d{1,3})(?::\d{1,5})?\b")  # matches IPv4 and optional :port

def extract_ip(text: str) -> str:
    m = IP_REGEX.search(text)
    if not m:
        raise RuntimeError("Could not find an IP on the page.")
    return m.group(0)

def fetch_dynamic_html(url: str, timeout: int = 30000) -> str:
    """
    Fetch HTML from a URL using a headless browser to render JavaScript.
    Falls back when requests.get() doesn't find the IP (for dynamic sites).

    Args:
        url: The URL to fetch
        timeout: Timeout in milliseconds (default: 30000 = 30 seconds)

    Returns:
        Rendered HTML content with JavaScript executed

    Raises:
        RuntimeError: If Playwright is not installed or browser fails to load
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    except ImportError:
        raise RuntimeError(
            "Playwright is not installed. Install it with: "
            "pip install playwright && playwright install chromium"
        )

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=timeout)

            # Wait for the IPv4 section to load (dynamic content)
            try:
                page.wait_for_selector('text=IPv4', timeout=10000)
            except PlaywrightTimeout:
                # Content might still be there, just without "IPv4" label
                pass

            # Give a bit more time for any async content to load
            page.wait_for_timeout(2000)

            html = page.content()
            browser.close()
            return html
    except Exception as e:
        raise RuntimeError(f"Failed to fetch dynamic HTML with Playwright: {e}")

def load_servers_dat(path: Path):
    """
    Load servers.dat NBT file, automatically detecting gzipped or uncompressed format.

    Returns:
        tuple: (File object, is_gzipped: bool)
    """
    if path.exists():
        # Try gzipped first (less common for servers.dat)
        try:
            nbt = File.load(path, gzipped=True)
            return (nbt, True)
        except Exception as gzip_error:
            # If gzip fails, try uncompressed (standard Minecraft format)
            try:
                nbt = File.load(path, gzipped=False)
                return (nbt, False)
            except Exception as uncomp_error:
                raise RuntimeError(
                    f"Failed to read existing servers.dat. "
                    f"Tried gzipped: {gzip_error}. Tried uncompressed: {uncomp_error}"
                )
    # Create a new empty servers list if none (uncompressed by default)
    return (File({'': Compound({"servers": List[Compound]([])})}), False)
def save_servers_dat(nbt: File, path: Path, gzipped: bool = False):
    """
    Save servers.dat NBT file in the specified format.

    Args:
        nbt: The NBT File object to save
        path: Path to save to
        gzipped: Whether to save as gzipped (default: False, matches Minecraft)
    """
    # Make a backup
    if path.exists():
        path.with_suffix(".dat_backup").write_bytes(path.read_bytes())
    nbt.save(path, gzipped=gzipped)

def upsert_server(nbt: File, name: str, ip: str):
    # Handle both File structures:
    # - Created: File({'': Compound({...})}) - access via nbt['']
    # - Loaded from disk: access directly via nbt
    if '' in nbt:
        root = nbt['']
    else:
        root = nbt

    servers = root.get("servers")
    if servers is None:
        servers = List[Compound]([])
        root["servers"] = servers

    # Try to find by name first; if not, by old IP (fingerprint)
    idx = None
    for i, entry in enumerate(servers):
        if str(entry.get("name", "")) == name or str(entry.get("ip", "")) == ip:
            idx = i
            break

    new_entry = Compound({
        "name": String(name),
        "ip": String(ip),
        # You can add optional fields like "icon" (base64), "acceptTextures" (1b), etc.
    })

    if idx is None:
        servers.append(new_entry)
    else:
        servers[idx] = new_entry

def main():
    # Try fast method first (requests.get)
    server_ip = None
    method_used = "requests"

    try:
        html = requests.get(SITE_URL, timeout=10).text
        server_ip = extract_ip(html)
    except RuntimeError:
        # IP not found in static HTML, fall back to headless browser
        print("[update_mc_server_ip] IP not found in static HTML, using headless browser...", file=sys.stderr)
        method_used = "playwright"
        html = fetch_dynamic_html(SITE_URL)
        server_ip = extract_ip(html)

    mc_dir = Path(INSTANCE_DIR)
    servers_dat = mc_dir / "servers.dat"
    servers_nbt, is_gzipped = load_servers_dat(servers_dat)
    upsert_server(servers_nbt, SERVER_NAME, server_ip)
    save_servers_dat(servers_nbt, servers_dat, gzipped=is_gzipped)

    # Optional: also write to stdout so you can see what it set
    print(f"[update_mc_server_ip] Set '{SERVER_NAME}' to {server_ip} in {servers_dat} (via {method_used})")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[update_mc_server_ip] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
