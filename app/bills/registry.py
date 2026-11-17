"""Finds every adapter in `app/bills/adapters/` so adding a company is just adding a file."""

from __future__ import annotations

import importlib
import pkgutil
from typing import Optional

from app.bills import adapters
from app.bills.base import Adapter

_registry: dict[str, type[Adapter]] | None = None


def _load() -> dict[str, type[Adapter]]:
    found: dict[str, type[Adapter]] = {}
    for module_info in pkgutil.iter_modules(adapters.__path__):
        if module_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{adapters.__name__}.{module_info.name}")
        for obj in vars(module).values():
            if isinstance(obj, type) and issubclass(obj, Adapter) and obj is not Adapter and obj.id:
                if obj.id in found and found[obj.id] is not obj:
                    raise RuntimeError(f"Two bill adapters share the id {obj.id!r}")
                found[obj.id] = obj
    return found


def all_adapters() -> dict[str, type[Adapter]]:
    global _registry
    if _registry is None:
        _registry = _load()
    return _registry


def get_adapter(adapter_id: str) -> Optional[type[Adapter]]:
    return all_adapters().get(adapter_id)
