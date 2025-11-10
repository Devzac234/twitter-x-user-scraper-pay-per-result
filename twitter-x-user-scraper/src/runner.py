thonimport json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

from extractors.twitter_parser import TwitterUserScraper
from extractors.utils_network import NetworkClient
from outputs.exporters import JsonExporter

DEFAULT_CONFIG: Dict[str, Any] = {
    "mode": "followers",  # currently only followers mode is simulated
    "max_items": 50,
    "include_unavailable_users": False,
    "output": {
        "directory": "data",
        "filename": "output_users.json",
    },
    "network": {
        "timeout": 10,
        "max_retries": 3,
        "enable_live": False,  # by default the scraper runs in offline/simulated mode
        "user_agent": "TwitterUserScraper/1.0 (+https://bitbash.dev)",
    },
}

def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent

def _load_json_file(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def _load_config() -> Dict[str, Any]:
    src_dir = Path(__file__).resolve().parent
    config_path = src_dir / "config" / "settings.example.json"

    if not config_path.exists():
        logging.warning(
            "Config file %s not found. Falling back to DEFAULT_CONFIG.", config_path
        )
        return DEFAULT_CONFIG.copy()

    try:
        config_data = _load_json_file(config_path)
        # Merge with defaults to ensure all keys are present
        merged = DEFAULT_CONFIG.copy()
        for key, value in config_data.items():
            if isinstance(value, dict) and key in merged and isinstance(
                merged[key], dict
            ):
                inner = merged[key].copy()
                inner.update(value)
                merged[key] = inner
            else:
                merged[key] = value
        return merged
    except Exception as exc:
        logging.exception("Unable to load config file. Using defaults. Error: %s", exc)
        return DEFAULT_CONFIG.copy()

def _load_input_items() -> List[Dict[str, Any]]:
    root = _project_root()
    input_path = root / "data" / "input.json"
    try:
        items = _load_json_file(input_path)
        if not isinstance(items, list):
            raise ValueError("Input JSON must be a list of items.")
        return items
    except Exception as exc:
        logging.exception("Failed to load input items from %s: %s", input_path, exc)
        return []

def main() -> None:
    _setup_logging()
    logger = logging.getLogger("runner")

    logger.info("Starting Twitter (X) user scraper (simulated).")

    config = _load_config()
    input_items = _load_input_items()

    if not input_items:
        logger.error(
            "No input items found. Please populate data/input.json with input records."
        )
        sys.exit(1)

    network_config = config.get("network", {})
    network_client = NetworkClient(
        timeout=network_config.get("timeout", 10),
        max_retries=network_config.get("max_retries", 3),
        user_agent=network_config.get("user_agent", "TwitterUserScraper/1.0"),
        enable_live=network_config.get("enable_live", False),
    )

    scraper = TwitterUserScraper(network_client=network_client, config=config)

    try:
        users = scraper.scrape_from_input_items(input_items)
    except Exception as exc:
        logger.exception("Unexpected error while scraping users: %s", exc)
        sys.exit(1)

    if not users:
        logger.warning("No users were generated from the provided inputs.")
        sys.exit(0)

    user_dicts = [u.to_dict() for u in users]

    root = _project_root()
    output_cfg = config.get("output", {})
    output_dir = root / output_cfg.get("directory", "data")
    output_filename = output_cfg.get("filename", "output_users.json")
    output_path = output_dir / output_filename

    try:
        JsonExporter.export_to_file(user_dicts, output_path)
    except Exception as exc:
        logger.exception("Failed to export results to %s: %s", output_path, exc)
        sys.exit(1)

    logger.info("Scraping completed successfully.")
    logger.info("Total users generated: %d", len(users))
    logger.info("Results written to: %s", output_path)

if __name__ == "__main__":
    main()