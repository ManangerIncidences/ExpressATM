import os
import sys
import json
from pathlib import Path

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.driver_manager import (
    get_chromedriver_path,
    get_chrome_binary_path,
    get_chrome_and_driver_info,
)


def main():
    info = {
        "python": sys.version,
        "cwd": str(Path.cwd()),
        "env": {
            k: os.getenv(k)
            for k in [
                "CHROMEDRIVER_PATH",
                "CHROME_BINARY",
                "CHROME_HEADLESS",
                "PATH",
            ]
        },
        "paths": {
            "repo_root": str(ROOT),
            "chrome_binary": get_chrome_binary_path(),
        },
        "driver": {},
        "notes": [],
    }
    try:
        info["driver"]["chromedriver_path"] = get_chromedriver_path()
    except Exception as e:
        info["driver"]["chromedriver_error"] = str(e)

    try:
        info["driver"]["diag"] = get_chrome_and_driver_info()
    except Exception as e:
        info["driver"]["diag_error"] = str(e)

    print(json.dumps(info, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
