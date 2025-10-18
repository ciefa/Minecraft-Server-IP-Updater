# Minecraft Server IP Updater

Automatically updates your Minecraft client's server list with a dynamic IP address by fetching it from a webpage. Supports both static and JavaScript-rendered pages.

## Features

- Automatic IP extraction from any webpage (IPv4 with optional port)
- Playwright fallback for JavaScript-heavy sites
- Smart NBT format detection (handles both gzipped and uncompressed servers.dat)
- Automatic backup before modifications
- Preserves existing server entries
- Comprehensive test suite (19 tests)

## Requirements

- Python 3.8 or higher
- Playwright (for JavaScript-rendered pages)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/mc-server-ip.git
cd mc-server-ip
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install Playwright browser:
```bash
playwright install chromium
```

## Configuration

1. Copy the example configuration:
```bash
cp config.example.py config.py
```

2. Edit `config.py` with your settings:
```python
SITE_URL = "https://your-website.com/server-status"
INSTANCE_DIR = "/path/to/your/minecraft/instance/directory"
SERVER_NAME = "My Server Name"
```

### Finding Your Instance Directory

- **Vanilla Minecraft**: `~/.minecraft` (Linux/Mac) or `%APPDATA%\.minecraft` (Windows)
- **PrismLauncher**: `~/.local/share/PrismLauncher/instances/YourInstance/minecraft`
- **MultiMC**: `~/MultiMC/instances/YourInstance/minecraft`

## Usage

Run the script to update your server list:
```bash
python update_mc_server_ip.py
```

The script will:
1. Fetch the webpage containing your server IP
2. Extract the IP address using regex
3. Load your Minecraft servers.dat file
4. Update or insert the server entry
5. Save the file (with automatic backup)

Output example:
```
[update_mc_server_ip] Set 'My Server Name' to 192.168.1.100:25565 in /path/to/servers.dat (via playwright)
```

## How It Works

### Fetching Strategy

The script uses a smart fallback approach:
1. First attempts to fetch with `requests.get()` (fast, < 1 second)
2. If no IP found, falls back to Playwright headless browser (2-5 seconds)

This ensures compatibility with both static HTML and JavaScript-rendered pages.

### NBT Format Handling

The script automatically detects and preserves the NBT format:
- Tries gzipped format first
- Falls back to uncompressed if needed
- Saves in the same format as the original file

Minecraft typically uses uncompressed NBT for servers.dat, but both formats are supported.

## Launcher Integration

### Prism Launcher / MultiMC

To automatically update the server IP before launching Minecraft:

1. Open your instance settings (Edit Instance)
2. Go to Settings → Custom Commands
3. Enable "Custom Commands"
4. In the "Pre-launch command" field, enter:
```
/path/to/mc-server-ip/run_update.sh
```
Replace `/path/to/mc-server-ip/` with the actual path to this repository.

5. Click OK

Now the server IP will automatically update every time you launch the instance.

**Important:** Use `run_update.sh`, not `update_mc_server_ip.py` directly. The wrapper script ensures the virtual environment is activated.

### Other Launchers

For other launchers, use the wrapper script in any pre-launch hook or custom command field:
```bash
/path/to/mc-server-ip/run_update.sh
```

### Manual Execution

You can also run the wrapper script manually anytime:
```bash
./run_update.sh
```

Or use the Python script directly if your shell has the venv activated:
```bash
source venv/bin/activate
python update_mc_server_ip.py
```

## Testing

Run the test suite:
```bash
pytest test_update_mc_server_ip.py -v
```

All 19 tests should pass, covering:
- IP extraction (5 tests)
- NBT file loading (3 tests)
- Server upsert operations (4 tests)
- File saving and backup (3 tests)
- Playwright functionality (2 tests)
- Integration tests (2 tests)

## Troubleshooting

### "Playwright is not installed"
Run: `pip install playwright && playwright install chromium`

### "Could not find an IP on the page"
- Verify the SITE_URL is correct
- Check that the page actually displays an IP address
- Try viewing the page source to confirm IP format

### "Failed to read existing servers.dat"
- Verify INSTANCE_DIR points to the correct Minecraft directory
- Check that servers.dat exists and is readable
- The script handles both gzipped and uncompressed formats automatically

### Script runs but server doesn't appear in Minecraft
- Ensure Minecraft is closed when running the script
- Check that the IP was extracted correctly from the output
- Verify the backup file (servers.dat_backup) was created

## License

This project is licensed under the Viral Public License. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome. Please ensure all tests pass before submitting pull requests.
