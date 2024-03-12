import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.request import urlretrieve
from zipfile import ZipFile, is_zipfile


class DownloadCache:
    CACHE_DIR = Path(".cache")
    METADATA_FILE = CACHE_DIR / "metadata.json"

    def __init__(self) -> None:
        self.__metadata = None

    def download(self, sources: dict[str, str]) -> None:
        sources = self._check_metadata(sources)

        if sources:
            self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

        for name, url in sources.items():
            tmpfile, _ = urlretrieve(url)

            if is_zipfile(tmpfile):
                with ZipFile(tmpfile) as f:
                    dest_dir = self.CACHE_DIR / name
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    f.extractall(dest_dir)
            else:
                shutil.copyfile(tmpfile, self.CACHE_DIR / name)

        self._update_metadata(sources)

    def get_path(self, *parts: str | Path) -> Path:
        return self.CACHE_DIR.joinpath(*parts)

    @property
    def _metadata(self) -> dict[str, Any]:
        if self.__metadata is None:
            if self.METADATA_FILE.exists():
                self.__metadata = json.loads(self.METADATA_FILE.read_text())
            else:
                self.__metadata = {"sources": {}, "last_modified": None}

        return self.__metadata

    def _check_metadata(self, sources: dict[str, str]) -> dict[str, str]:
        if self._metadata["last_modified"] is None or datetime.now() - datetime.fromisoformat(
            self._metadata["last_modified"]
        ) >= timedelta(1):
            return sources
        else:
            return {k: sources[k] for k in sources if k not in self._metadata["sources"]}

    def _update_metadata(self, sources: dict[str, str]) -> None:
        if set(sources) - set(self._metadata["sources"]):
            self.METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
            self.METADATA_FILE.write_text(
                json.dumps(
                    {
                        "sources": self._metadata["sources"] | sources,
                        "last_modified": datetime.now().isoformat(),
                    }
                )
            )
