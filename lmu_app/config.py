"""lmu_app/config.py — Configuration JSON persistante."""
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_PATH = Path.home() / ".lmuapp" / "config.json"

_DEFAULTS: dict = {
    "locked": False,
    "merge_calc": False,
    "widgets": {
        "speed":      {"enabled": True,  "x": 50,  "y": 50},
        "inputs":     {"enabled": True,  "x": 50,  "y": 190},
        "standings":  {"enabled": True,  "x": 350, "y": 50},
        "relative":   {"enabled": True,  "x": 350, "y": 310},
        "tyres":      {"enabled": True,  "x": 50,  "y": 390},
        "fuel_calc":  {"enabled": True,  "x": 50,  "y": 540},
        "ve_calc":    {"enabled": False, "x": 280, "y": 540},
    },
}


class AppConfig:
    def __init__(self) -> None:
        self._data: dict = {}
        self.load()

    def load(self) -> None:
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, encoding="utf-8") as f:
                    self._data = json.load(f)
                logger.info("Config chargée depuis %s", CONFIG_PATH)
                return
            except Exception as e:
                logger.warning("Erreur config: %s — valeurs par défaut", e)
        self._data = json.loads(json.dumps(_DEFAULTS))

    def save(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)
        logger.debug("Config sauvegardée dans %s", CONFIG_PATH)

    @property
    def locked(self) -> bool:
        return bool(self._data.get("locked", False))

    @locked.setter
    def locked(self, v: bool) -> None:
        self._data["locked"] = v

    @property
    def hide_in_garage(self) -> bool:
        return bool(self._data.get("hide_in_garage", False))

    @hide_in_garage.setter
    def hide_in_garage(self, v: bool) -> None:
        self._data["hide_in_garage"] = v

    def _w(self, key: str) -> dict:
        return self._data.setdefault("widgets", {}).setdefault(key, {})

    def widget_enabled(self, key: str) -> bool:
        return bool(self._w(key).get("enabled", True))

    def set_widget_enabled(self, key: str, enabled: bool) -> None:
        self._w(key)["enabled"] = enabled

    def widget_pos(self, key: str) -> tuple[int, int]:
        w = self._w(key)
        default = _DEFAULTS["widgets"].get(key, {"x": 100, "y": 100})
        return w.get("x", default["x"]), w.get("y", default["y"])

    def set_widget_pos(self, key: str, x: int, y: int) -> None:
        w = self._w(key)
        w["x"] = x
        w["y"] = y

    def class_colors(self) -> dict[str, str]:
        return dict(self._data.get("class_colors", {}))

    def set_class_colors(self, colors: dict[str, str]) -> None:
        self._data["class_colors"] = colors

    @property
    def merge_calc(self) -> bool:
        return bool(self._data.get("merge_calc", False))

    @merge_calc.setter
    def merge_calc(self, v: bool) -> None:
        self._data["merge_calc"] = v

    def widget_params(self, key: str) -> dict:
        return dict(self._w(key).get("params", {}))

    def set_widget_params(self, key: str, params: dict) -> None:
        self._w(key)["params"] = params

    # ------------------------------------------------------------------
    # Presets
    # ------------------------------------------------------------------

    def presets(self) -> list[dict]:
        return list(self._data.get("presets", []))

    def preset_names(self) -> list[str]:
        return [p["name"] for p in self._data.get("presets", [])]

    def preset_by_name(self, name: str) -> dict | None:
        return next((p for p in self._data.get("presets", []) if p.get("name") == name), None)

    def upsert_preset(self, name: str, data: dict) -> None:
        ps = self._data.setdefault("presets", [])
        for i, p in enumerate(ps):
            if p.get("name") == name:
                ps[i] = {"name": name, **data}
                return
        ps.append({"name": name, **data})

    def rename_preset(self, old_name: str, new_name: str) -> None:
        for p in self._data.get("presets", []):
            if p.get("name") == old_name:
                p["name"] = new_name
                break
        sp = self._data.get("session_presets", {})
        for k, v in list(sp.items()):
            if v == old_name:
                sp[k] = new_name

    def delete_preset(self, name: str) -> None:
        self._data["presets"] = [p for p in self._data.get("presets", []) if p.get("name") != name]
        sp = self._data.get("session_presets", {})
        for k in list(sp.keys()):
            if sp[k] == name:
                del sp[k]

    @property
    def session_presets(self) -> dict[str, str]:
        return dict(self._data.get("session_presets", {}))

    @session_presets.setter
    def session_presets(self, v: dict[str, str]) -> None:
        self._data["session_presets"] = v

    @property
    def auto_load_preset(self) -> bool:
        return bool(self._data.get("auto_load_preset", False))

    @auto_load_preset.setter
    def auto_load_preset(self, v: bool) -> None:
        self._data["auto_load_preset"] = v
