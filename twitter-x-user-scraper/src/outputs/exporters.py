thonimport json
import logging
from pathlib import Path
from typing import Any, Iterable, Mapping

logger = logging.getLogger(__name__)

class JsonExporter:
    """
    Handles exporting scraper results into JSON files.

    The exporter creates parent directories if needed, writes the JSON atomically
    through a temporary file, and then replaces the final target. This reduces
    the chance of corrupted files if a process is interrupted mid-write.
    """

    @staticmethod
    def export_to_file(records: Iterable[Mapping[str, Any]], path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        records_list = list(records)
        logger.info(
            "Exporting %d records to JSON at %s", len(records_list), path.as_posix()
        )

        tmp_path = path.with_suffix(path.suffix + ".tmp")

        try:
            with tmp_path.open("w", encoding="utf-8") as f:
                json.dump(records_list, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.exception("Failed to write temporary JSON file %s: %s", tmp_path, exc)
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    logger.warning("Failed to remove temporary file %s", tmp_path)
            raise

        try:
            tmp_path.replace(path)
        except Exception as exc:
            logger.exception(
                "Failed to move temporary JSON file from %s to %s: %s",
                tmp_path,
                path,
                exc,
            )
            raise