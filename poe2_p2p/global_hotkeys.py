from __future__ import annotations

from collections.abc import Callable


class GlobalHotkeyManager:
    def __init__(
        self,
        hotkeys: dict[str, str],
        callbacks: dict[str, Callable[[], None]],
        status_callback: Callable[[str], None] | None = None,
    ) -> None:
        self.hotkeys = hotkeys
        self.callbacks = callbacks
        self.status_callback = status_callback
        self._keyboard = None
        self._registered: list[str] = []

    def start(self) -> bool:
        try:
            import keyboard
        except ImportError:
            self._notify("Глобальные бинды недоступны: не установлен пакет keyboard.")
            return False

        self._keyboard = keyboard
        for action, hotkey in self.hotkeys.items():
            callback = self.callbacks.get(action)
            if not callback or not hotkey:
                continue
            try:
                keyboard.add_hotkey(hotkey, callback)
                self._registered.append(hotkey)
            except Exception as error:
                self._notify(f"Не удалось назначить бинд {hotkey}: {error}")
        if self._registered:
            self._notify("Глобальные бинды включены.")
        return bool(self._registered)

    def stop(self) -> None:
        if not self._keyboard:
            return
        for hotkey in self._registered:
            try:
                self._keyboard.remove_hotkey(hotkey)
            except Exception:
                pass
        self._registered.clear()

    def restart(self, hotkeys: dict[str, str]) -> bool:
        self.stop()
        self.hotkeys = hotkeys
        return self.start()

    def _notify(self, message: str) -> None:
        if self.status_callback:
            self.status_callback(message)
