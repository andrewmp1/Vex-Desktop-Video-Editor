from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QWidget,
)

from vex_desktop.platform_support import (
    SECRET_ANTHROPIC,
    SECRET_GEMINI,
    SECRET_OPENAI,
    get_secret,
    set_secret,
)


class SettingsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, *, provider: str = "gemini", model: str = "gemini"):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self._provider = QComboBox()
        self._provider.addItems(["gemini", "claude", "ollama"])
        index = self._provider.findText(provider)
        self._provider.setCurrentIndex(max(index, 0))

        self._model = QLineEdit(model)
        self._model.setPlaceholderText("Model id")

        self._api_key = QLineEdit()
        self._api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key.setPlaceholderText("Leave blank to keep the stored key")

        form = QFormLayout(self)
        form.addRow("Provider", self._provider)
        form.addRow("Model", self._model)
        form.addRow("API key", self._api_key)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self) -> tuple[str, str]:
        return self._provider.currentText(), self._model.text().strip()

    def save_secrets(self) -> None:
        key = self._api_key.text().strip()
        if not key:
            return
        provider = self._provider.currentText()
        if provider == "claude":
            set_secret(SECRET_ANTHROPIC, key)
        elif provider == "ollama":
            set_secret(SECRET_OPENAI, key)
        else:
            set_secret(SECRET_GEMINI, key)

    @staticmethod
    def current_key(provider: str) -> str | None:
        if provider == "claude":
            return get_secret(SECRET_ANTHROPIC)
        if provider == "ollama":
            return get_secret(SECRET_OPENAI)
        return get_secret(SECRET_GEMINI)
