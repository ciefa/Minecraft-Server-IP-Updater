#!/bin/bash
# Wrapper script to run the Minecraft server IP updater with virtual environment

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if virtual environment exists
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "[run_update.sh] ERROR: Virtual environment not found at $SCRIPT_DIR/venv" >&2
    echo "[run_update.sh] Please run: cd $SCRIPT_DIR && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && playwright install chromium" >&2
    exit 1
fi

# Activate virtual environment and run the script
source "$SCRIPT_DIR/venv/bin/activate"
python "$SCRIPT_DIR/update_mc_server_ip.py"
EXIT_CODE=$?

# Deactivate is not strictly necessary since the script exits, but included for completeness
deactivate

exit $EXIT_CODE
