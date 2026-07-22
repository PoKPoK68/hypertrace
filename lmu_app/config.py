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
        "ve_calc":    {"enabled": True,  "x": 280, "y": 540},
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
        cp = self._data.get("class_presets", {})
        for k, v in list(cp.items()):
            if v == old_name:
                cp[k] = new_name

    def delete_preset(self, name: str) -> None:
        self._data["presets"] = [p for p in self._data.get("presets", []) if p.get("name") != name]
        cp = self._data.get("class_presets", {})
        for k in list(cp.keys()):
            if cp[k] == name:
                del cp[k]

    @property
    def class_presets(self) -> dict[str, str]:
        return dict(self._data.get("class_presets", {}))

    @class_presets.setter
    def class_presets(self, v: dict[str, str]) -> None:
        self._data["class_presets"] = v

    @property
    def current_preset(self) -> str:
        return str(self._data.get("current_preset", ""))

    @current_preset.setter
    def current_preset(self, v: str) -> None:
        self._data["current_preset"] = v

    # ------------------------------------------------------------------
    # Stream mode
    # ------------------------------------------------------------------

    def _s(self) -> dict:
        return self._data.setdefault("stream", {})

    def _sw(self, key: str) -> dict:
        return self._s().setdefault("widgets", {}).setdefault(key, {})

    @property
    def stream_port(self) -> int:
        return int(self._s().get("port", 8765))

    @stream_port.setter
    def stream_port(self, v: int) -> None:
        self._s()["port"] = int(v)

    @property
    def stream_active(self) -> bool:
        return bool(self._s().get("active", False))

    @stream_active.setter
    def stream_active(self, v: bool) -> None:
        self._s()["active"] = bool(v)

    @property
    def stream_hide_in_garage(self) -> bool:
        return bool(self._s().get("hide_in_garage", False))

    @stream_hide_in_garage.setter
    def stream_hide_in_garage(self, v: bool) -> None:
        self._s()["hide_in_garage"] = bool(v)

    def stream_widget_enabled(self, key: str) -> bool:
        return bool(self._sw(key).get("enabled", False))

    def set_stream_widget_enabled(self, key: str, enabled: bool) -> None:
        self._sw(key)["enabled"] = bool(enabled)

    def stream_widget_params(self, key: str) -> dict:
        return dict(self._sw(key).get("params", {}))

    def set_stream_widget_params(self, key: str, params: dict) -> None:
        self._sw(key)["params"] = params

    # ------------------------------------------------------------------
    # Broadcast mode
    # ------------------------------------------------------------------

    def _bc(self) -> dict:
        return self._s().setdefault("broadcast", {})

    @property
    def broadcast_active(self) -> bool:
        return bool(self._bc().get("active", False))

    @broadcast_active.setter
    def broadcast_active(self, v: bool) -> None:
        self._bc()["active"] = bool(v)

    @property
    def bc_tower_enabled(self) -> bool:
        return bool(self._bc().get("tower_enabled", True))

    @bc_tower_enabled.setter
    def bc_tower_enabled(self, v: bool) -> None:
        self._bc()["tower_enabled"] = bool(v)

    @property
    def bc_battle_enabled(self) -> bool:
        return bool(self._bc().get("battle_enabled", False))

    @bc_battle_enabled.setter
    def bc_battle_enabled(self, v: bool) -> None:
        self._bc()["battle_enabled"] = bool(v)

    @property
    def bc_driver_enabled(self) -> bool:
        return bool(self._bc().get("driver_enabled", False))

    @bc_driver_enabled.setter
    def bc_driver_enabled(self, v: bool) -> None:
        self._bc()["driver_enabled"] = bool(v)

    @property
    def bc_sectors_enabled(self) -> bool:
        return bool(self._bc().get("sectors_enabled", False))

    @bc_sectors_enabled.setter
    def bc_sectors_enabled(self, v: bool) -> None:
        self._bc()["sectors_enabled"] = bool(v)

    @property
    def bc_tower_count_overall(self) -> int:
        bc = self._bc()
        return int(bc.get("tower_count_overall", bc.get("tower_count", 10)))

    @bc_tower_count_overall.setter
    def bc_tower_count_overall(self, v: int) -> None:
        self._bc()["tower_count_overall"] = int(v)

    @property
    def bc_tower_count_multiclass(self) -> int:
        return int(self._bc().get("tower_count_multiclass", 5))

    @bc_tower_count_multiclass.setter
    def bc_tower_count_multiclass(self, v: int) -> None:
        self._bc()["tower_count_multiclass"] = int(v)

    @property
    def bc_tower_count_ourclass(self) -> int:
        return int(self._bc().get("tower_count_ourclass", 10))

    @bc_tower_count_ourclass.setter
    def bc_tower_count_ourclass(self, v: int) -> None:
        self._bc()["tower_count_ourclass"] = int(v)

    @property
    def bc_tower_parade_count(self) -> int:
        return int(self._bc().get("tower_parade_count", 5))

    @bc_tower_parade_count.setter
    def bc_tower_parade_count(self, v: int) -> None:
        self._bc()["tower_parade_count"] = int(v)

    @property
    def bc_tower_mode(self) -> int:
        bc = self._bc()
        if "tower_mode" in bc:
            return int(bc["tower_mode"])
        return 1 if bc.get("tower_class_mode", False) else 0

    @bc_tower_mode.setter
    def bc_tower_mode(self, v: int) -> None:
        self._bc()["tower_mode"] = int(v)

    @property
    def bc_tower_filter_class(self) -> str:
        return str(self._bc().get("tower_filter_class", ""))

    @bc_tower_filter_class.setter
    def bc_tower_filter_class(self, v: str) -> None:
        self._bc()["tower_filter_class"] = str(v)

    @property
    def bc_tower_show_team(self) -> bool:
        return bool(self._bc().get("tower_show_team", False))

    @bc_tower_show_team.setter
    def bc_tower_show_team(self, v: bool) -> None:
        self._bc()["tower_show_team"] = bool(v)
