"""Eklenti sistemi icin temel arayuz (v0.1 iskelet)."""
from abc import ABC, abstractmethod


class Plugin(ABC):
    """Tum AI Director eklentilerinin atasi."""

    name: str = "unnamed"
    version: str = "0.0.0"

    @abstractmethod
    def activate(self) -> None:
        """Eklenti yuklendiginde cagrilir."""

    def deactivate(self) -> None:
        """Eklenti kapatilirken cagrilir."""


class PluginManager:
    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}

    def register(self, plugin: Plugin) -> None:
        if plugin.name in self._plugins:
            raise ValueError(f"Eklenti zaten kayitli: {plugin.name}")
        self._plugins[plugin.name] = plugin
        plugin.activate()

    def unregister(self, name: str) -> None:
        plugin = self._plugins.pop(name, None)
        if plugin:
            plugin.deactivate()

    def names(self) -> list[str]:
        return sorted(self._plugins)
