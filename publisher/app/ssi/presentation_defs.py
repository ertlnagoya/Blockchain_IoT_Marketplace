from __future__ import annotations

import json
from pathlib import Path


class PresentationDefinitionStore:
    def __init__(self, directory: str) -> None:
        self._dir = Path(directory)

    def get(self, pd_id: str) -> dict | None:
        path = self._dir / f"{pd_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_ids(self) -> list[str]:
        if not self._dir.exists():
            return []
        return sorted(p.stem for p in self._dir.glob("*.json"))

    def find_for_dataset(
        self,
        dataset_id: str,
        vc_kind: str = "ConsentVC",
    ) -> tuple[str, dict] | None:
        """Pick the PD matching dataset_id and vc_kind.

        PD JSON may include `iw3ip_vc_kind` (defaults to ConsentVC) so the same
        dataset can have separate PDs for write (ConsentVC) and read (ViewerVC).
        """
        for pd_id in self.list_ids():
            pd = self.get(pd_id)
            if not pd:
                continue
            if pd.get("iw3ip_dataset_id") != dataset_id:
                continue
            if pd.get("iw3ip_vc_kind", "ConsentVC") != vc_kind:
                continue
            return pd_id, pd
        return None
