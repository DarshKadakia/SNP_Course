"""Shared ProfileEditDialog — importable by any course gui/main_app.py."""

import os
import threading
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QApplication
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon

_ABSIX_ICON = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "resources", "Absix_logo.png"
)

_FIELD_SS = """
    QLineEdit {
        background: #1e1e1e; color: #e0e0e0;
        border: 1px solid #333; border-radius: 7px;
        padding: 8px 12px; font-size: 13px;
    }
    QLineEdit:focus { border-color: #666; }
"""
_BTN_SAVE = """
    QPushButton {
        background-color: #1e4a1e; color: #fff;
        border: 1px solid #2a7a2a; border-radius: 8px;
        padding: 8px 24px; font-weight: 600; font-size: 12px;
        min-width: 100px;
    }
    QPushButton:hover { background-color: #275527; border-color: #3a9a3a; }
    QPushButton:disabled { background-color: #1a1a1a; color: #555; border-color: #333; }
"""
_BTN_CANCEL = """
    QPushButton {
        background-color: #1a1a1a; color: #888;
        border: 1px solid #333; border-radius: 8px;
        padding: 8px 20px; font-size: 12px;
        min-width: 80px;
    }
    QPushButton:hover { background-color: #222; color: #ccc; border-color: #555; }
"""


class ProfileEditDialog(QDialog):
    """Dark-themed dialog to edit the user's profile (PATCH /users/me)."""

    def __init__(self, api_client, current_profile: dict, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.setWindowTitle("Edit Profile")
        if os.path.exists(_ABSIX_ICON):
            self.setWindowIcon(QIcon(_ABSIX_ICON))
        self.setWindowModality(Qt.ApplicationModal)
        self.setStyleSheet("QDialog { background: #111; } QLabel { color: #aaa; font-size: 12px; }")
        self.setFixedWidth(440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("Edit Profile")
        title.setStyleSheet("color: #fff; font-size: 17px; font-weight: bold;")
        layout.addWidget(title)

        fields_data = [
            ("Full Name",    current_profile.get("full_name", "") or ""),
            ("Organisation", current_profile.get("organization", "") or ""),
            ("Mobile",       current_profile.get("mobile_number", "") or ""),
        ]
        self._inputs = []
        for label_text, value in fields_data:
            lbl = QLabel(label_text)
            layout.addWidget(lbl)
            inp = QLineEdit(value)
            inp.setStyleSheet(_FIELD_SS)
            layout.addWidget(inp)
            self._inputs.append(inp)

        self._status = QLabel("")
        self._status.setStyleSheet("color: #f87171; font-size: 12px;")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self._save_btn = QPushButton("Save")
        self._save_btn.setStyleSheet(_BTN_SAVE)
        self._save_btn.setCursor(Qt.PointingHandCursor)
        self._save_btn.clicked.connect(self._on_save)
        cancel = QPushButton("Cancel")
        cancel.setStyleSheet(_BTN_CANCEL)
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(self._save_btn)
        btn_row.addStretch()
        btn_row.addWidget(cancel)
        layout.addLayout(btn_row)

        self.updated_profile = None

    def _on_save(self):
        name   = self._inputs[0].text().strip()
        org    = self._inputs[1].text().strip()
        mobile = self._inputs[2].text().strip()
        if not name:
            self._status.setText("Full name cannot be empty.")
            return
        self._save_btn.setEnabled(False)
        self._save_btn.setText("Saving…")
        self._status.setText("")
        QApplication.processEvents()

        def _do():
            ok, _, err = self.api_client.update_profile(
                full_name=name, organization=org, mobile_number=mobile
            )
            if ok:
                profile = None
                if hasattr(self.api_client, "get_user_profile"):
                    profile = self.api_client.get_user_profile() or {}
                elif hasattr(self.api_client, "get_profile"):
                    profile = self.api_client.get_profile() or {}
                if profile:
                    profile.setdefault("full_name", name)
                    self.updated_profile = profile
                else:
                    self.updated_profile = {"full_name": name, "organization": org, "mobile_number": mobile}
                QTimer.singleShot(0, self.accept)
            else:
                def _show_err():
                    self._status.setText(err or "Update failed. Please try again.")
                    self._save_btn.setEnabled(True)
                    self._save_btn.setText("Save")
                QTimer.singleShot(0, _show_err)

        threading.Thread(target=_do, daemon=True).start()
