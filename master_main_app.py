import os
import sys
import time
import traceback

# Force UTF-8 stdout/stderr on Windows to prevent UnicodeEncodeError on
# special characters like ✓ (\u2713) when the console uses cp1252.
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
os.environ.setdefault('PYTHONIOENCODING', 'utf-8:replace')

# ── MUST be first: multiprocessing freeze_support prevents infinite spawning
# when the app is packaged as a PyInstaller .exe (frozen). Without this,
# importing multiprocessing in any thread causes the exe to re-launch itself.
import multiprocessing
multiprocessing.freeze_support()

# ── Frozen-exe: point Qt/WebEngine at bundled resources before any DLL loads ──
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    _base = sys._MEIPASS
    os.environ.setdefault("QTWEBENGINE_RESOURCES_PATH", _base)
    os.environ.setdefault("QTWEBENGINE_LOCALES_PATH",
                          os.path.join(_base, "qtwebengine_locales"))
    # Ensure Qt finds its plugins (platforms, imageformats, etc.)
    os.environ.setdefault("QT_PLUGIN_PATH",
                          os.path.join(_base, "PyQt5", "Qt5", "plugins"))

# ── GPU / WebEngine flags — set before any Qt DLL is loaded ───────────────────
# AGGRESSIVE flags to prevent ANY GPU/driver crashes on broken Windows machines.
# These flags force Chromium to run in the safest possible mode with zero GPU usage.
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
    "--disable-gpu "
    "--disable-gpu-compositing "
    "--disable-gpu-shader-disk-cache "
    "--disable-gpu-program-cache "
    "--disable-software-rasterizer "
    "--disable-webgl "
    "--disable-webgl2 "
    "--disable-3d-apis "
    "--disable-accelerated-2d-canvas "
    "--disable-accelerated-video-decode "
    "--num-raster-threads=1 "
    "--in-process-gpu "
    "--no-sandbox "
    "--disable-dev-shm-usage "
    "--disable-background-networking "
    "--disable-extensions "
    "--disable-features=VizDisplayCompositor "
    "--use-gl=swiftshader "
    "--ignore-gpu-blocklist"
)
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
os.environ["QT_OPENGL"] = "software"

def _global_except_hook(exc_type, exc_value, exc_tb):
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print("[CRASH]\n" + msg, flush=True, file=sys.__stdout__)
    try:
        _log = os.path.join(os.path.dirname(os.path.abspath(
            sys.executable if getattr(sys, 'frozen', False) else __file__
        )), "crash.log")
        with open(_log, "a", encoding="utf-8") as f:
            import datetime
            f.write(f"\n--- {datetime.datetime.now().isoformat()} ---\n")
            f.write(msg)
    except Exception:
        pass

sys.excepthook = _global_except_hook
from PyQt5.QtWidgets import (
    QApplication, QSplashScreen, QLabel, QProgressBar, QWidget, QVBoxLayout,
    QMessageBox, QDesktopWidget, QMainWindow, QFrame, QLineEdit, QPushButton,
    QDialog, QHBoxLayout, QGridLayout, QScrollArea, QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt5.QtGui import (
    QPixmap, QColor, QCursor, QIcon,
    QPainter, QBrush, QPen, QLinearGradient, QPainterPath, QRadialGradient, QFont,
)

_SHARED_RESOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")
_ABSIX_ICON  = os.path.join(_SHARED_RESOURCES, "Absix_logo.png")
_AB6_LOGO    = os.path.join(_SHARED_RESOURCES, "AB6_Logo.png")
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QTextCursor  # register QTextCursor so queued-connection warning is suppressed

# Import master authentication components
from master_backend_api_client import MasterBackendAPIClient
from master_enhanced_login import MasterEnhancedLoginDialog

# Kinematics shared card dialogs (same design as mentor score UI)
_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
_KIN_DIR = os.path.join(_ROOT_DIR, "Kinematics")
if os.path.isdir(_KIN_DIR) and _KIN_DIR not in sys.path:
    sys.path.insert(0, _KIN_DIR)
try:
    from gui.dialog_utils import exec_dark_critical, exec_dark_warning_card
except ImportError:
    exec_dark_critical = None
    exec_dark_warning_card = None

# Course definitions: id, display name, description, access code, folder/module to launch
COURSES = [
    {
        "id": "kinematics",
        "name": "Kinematics",
        "description": "Learn robot kinematics, forward and inverse kinematics, and motion planning. Master the math behind robotic movement.",
        "code": "KIN",
        "icon": "⚙",
        "folder": "Kinematics",
        "launch_module": "main_app",
        "launch_class": "MainWindow",
        "difficulty": "Intermediate",
    },
    {
        "id": "snp_kinematics",
        "name": "Sensing and Perception",
        "description": "Explore robot sensing, sensor data interpretation, signal filtering, and perception algorithms using the ROBOX-SNP robot.",
        "code": "SNP",
        "icon": "📡",
        "folder": "SNP_Kinematics",
        "launch_module": "main_app",
        "launch_class": "MainWindow",
        "difficulty": "Beginner",
    },
    {
        "id": "sim_to_real",
        "name": "Sim to Real Kinematics",
        "description": "Bridge the gap between simulation and real hardware. Transfer trained kinematics models from virtual environments to physical robots.",
        "code": "STR",
        "icon": "🔄",
        "folder": "SimToReal_Kinematics",
        "launch_module": "main_app",
        "launch_class": "MainWindow",
        "difficulty": "Intermediate",
    },
    {
        "id": "omx_kinematics",
        "name": "OMX Kinematics",
        "description": "Deep dive into OMX robot arm kinematics — joint control, workspace analysis, trajectory generation, and real-time motion execution.",
        "code": "OMX",
        "icon": "🦾",
        "folder": "OMX_Kinematics",
        "launch_module": "main_app",
        "launch_class": "MainWindow",
        "difficulty": "Intermediate",
    },
]

class SplashScreen(QSplashScreen):
    """Custom splash screen for the application."""
    
    def __init__(self):
        # Create a blank pixmap for the splash screen
        splash_pix = QPixmap(700, 400)
        splash_pix.fill(Qt.transparent)
        super().__init__(splash_pix, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        
        # Set up the splash screen UI
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        
        # Create layout for splash screen content
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(40, 40, 40, 40)
        
        # Create widget to hold the content
        self.content = QWidget(self)
        self.content.setGeometry(0, 0, 700, 400)
        self.content.setLayout(self.layout)
        self.content.setStyleSheet("""
            background-color: #111111;
            border-radius: 20px;
        """)
        
        # Title
        title = QLabel("ROBOX UI")
        title.setStyleSheet("color: white; font-size: 36px; font-weight: bold; letter-spacing: 2px;")
        title.setAlignment(Qt.AlignCenter)

        # Subtitle
        subtitle = QLabel("Your Launchpad Into the Future of Robotics")
        subtitle.setStyleSheet("color: #aaaaaa; font-size: 20px;")
        subtitle.setAlignment(Qt.AlignCenter)
        
        # Loading indicator
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: #2a2a2a;
                border-radius: 4px;
                height: 6px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(
                    spread:pad, x1:0, y1:0, x2:1, y2:0,
                    stop:0 #666666, stop:1 #cccccc
                );
                border-radius: 4px;
            }
        """)
        
        # Loading text
        self.loading_text = QLabel("Initializing...")
        self.loading_text.setStyleSheet("color: #888888; font-size: 15px;")
        self.loading_text.setAlignment(Qt.AlignCenter)

        # Version info
        version = QLabel("v1.0.0")
        version.setStyleSheet("color: rgba(255, 255, 255, 0.3); font-size: 13px;")
        version.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        
        # Add widgets to layout
        self.layout.addStretch(1)
        self.layout.addWidget(title, 0, Qt.AlignCenter)
        self.layout.addWidget(subtitle, 0, Qt.AlignCenter)
        self.layout.addStretch(1)
        self.layout.addWidget(self.progress)
        self.layout.addWidget(self.loading_text, 0, Qt.AlignCenter)
        self.layout.addStretch(1)
        self.layout.addWidget(version, 0, Qt.AlignRight)
    
    def updateProgress(self, value, text="Loading..."):
        """Update the progress bar and loading text."""
        self.progress.setValue(value)
        self.loading_text.setText(text)

        # Process events to update the UI
        QApplication.processEvents()


class CourseLoadingSplash(QSplashScreen):
    """Minimal loading screen shown while a course dashboard is initialising."""

    def __init__(self):
        pix = QPixmap(700, 400)
        pix.fill(Qt.transparent)
        super().__init__(pix, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)

        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)

        self.content = QWidget(self)
        self.content.setGeometry(0, 0, 700, 400)
        self.content.setLayout(layout)
        self.content.setStyleSheet("""
            background-color: #111111;
            border-radius: 20px;
        """)

        title = QLabel("Course Loading")
        title.setStyleSheet("color: white; font-size: 36px; font-weight: bold; letter-spacing: 2px;")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("Connecting to backend...")
        subtitle.setStyleSheet("color: #aaaaaa; font-size: 20px;")
        subtitle.setAlignment(Qt.AlignCenter)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # indeterminate marquee
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: #2a2a2a;
                border-radius: 4px;
                height: 6px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(
                    spread:pad, x1:0, y1:0, x2:1, y2:0,
                    stop:0 #666666, stop:1 #cccccc
                );
                border-radius: 4px;
            }
        """)

        layout.addStretch(1)
        layout.addWidget(title, 0, Qt.AlignCenter)
        layout.addSpacing(8)
        layout.addWidget(subtitle, 0, Qt.AlignCenter)
        layout.addStretch(1)
        layout.addWidget(self.progress)
        layout.addStretch(1)


class CourseCodeDialog(QDialog):
    """Dialog to enter course access code."""
    
    def __init__(self, course_name, parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.course_name = course_name
        self.setWindowTitle(f"Enter code — {course_name}")
        if os.path.exists(_ABSIX_ICON):
            self.setWindowIcon(QIcon(_ABSIX_ICON))
        self.setMinimumWidth(380)
        self.setModal(True)
        self.code_edit = None
        self.setup_ui()
        self.apply_style()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        label = QLabel(f"Enter the access code for <b>{self.course_name}</b>:")
        label.setWordWrap(True)
        label.setObjectName("prompt")
        layout.addWidget(label)
        
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("Course code")
        self.code_edit.setEchoMode(QLineEdit.Password)
        self.code_edit.setObjectName("code_field")
        self.code_edit.returnPressed.connect(self.accept_code)
        layout.addWidget(self.code_edit)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancel_btn")
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QPushButton("Verify")
        ok_btn.setObjectName("ok_btn")
        ok_btn.clicked.connect(self.accept_code)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)
    
    def accept_code(self):
        self.accept()
    
    def get_code(self):
        return self.code_edit.text().strip() if self.code_edit else ""
    
    def apply_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #111111;
                border-radius: 12px;
            }
            QLabel#prompt { color: #cccccc; font-size: 15px; }
            QLineEdit#code_field {
                background-color: #141414;
                color: #e0e0e0;
                border: 1.5px solid #3a3a3a;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 15px;
            }
            QLineEdit#code_field:focus { border-color: #888888; }
            QPushButton#ok_btn {
                background-color: qlineargradient(
                    spread:pad, x1:0, y1:0, x2:0, y2:1,
                    stop:0 #555555, stop:1 #333333
                );
                color: #ffffff;
                border: 1px solid #666666;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton#ok_btn:hover {
                background-color: qlineargradient(
                    spread:pad, x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6a6a6a, stop:1 #444444
                );
                border-color: #888888;
            }
            QPushButton#cancel_btn {
                background-color: #1a1a1a;
                color: #888888;
                border: 1px solid #2e2e2e;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 13px;
            }
            QPushButton#cancel_btn:hover { background-color: #222222; color: #cccccc; border-color: #444444; }
        """)


class CourseCard(QFrame):
    """Clean minimal course card — icon, name, one-line desc, difficulty, arrow."""

    clicked = pyqtSignal(object)

    def __init__(self, course, parent=None):
        super().__init__(parent)
        self.course = course
        self._hovered = False
        self._cta = None
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setObjectName("courseCard")
        self.setFixedSize(400, 185)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(22, 18, 22, 16)

        # Icon + course name
        top = QHBoxLayout()
        top.setSpacing(10)
        icon_lbl = QLabel(self.course.get("icon", "●"))
        icon_lbl.setObjectName("courseIcon")
        name_lbl = QLabel(self.course["name"])
        name_lbl.setObjectName("courseTitle")
        top.addWidget(icon_lbl)
        top.addWidget(name_lbl)
        top.addStretch()
        layout.addLayout(top)

        # Short description — first sentence only
        raw = self.course.get("description", "")
        short = (raw.split(".")[0] + ".") if "." in raw else raw
        desc_lbl = QLabel(short)
        desc_lbl.setObjectName("courseDesc")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)

        layout.addStretch()

        # Footer: difficulty pill + Open arrow
        foot = QHBoxLayout()
        foot.setSpacing(0)
        if self.course.get("difficulty"):
            diff_lbl = QLabel(self.course["difficulty"])
            diff_lbl.setObjectName("diffTag")
            foot.addWidget(diff_lbl)
        foot.addStretch()
        self._cta = QLabel("Open  →")
        self._cta.setObjectName("courseCTA")
        foot.addWidget(self._cta)
        layout.addLayout(foot)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        path = QPainterPath()
        path.addRoundedRect(0.5, 0.5, w - 1, h - 1, 14, 14)

        # Transparent green background (matches completed challenge card style)
        painter.fillPath(path, QBrush(QColor(15, 55, 15) if self._hovered else QColor(10, 42, 10)))

        # Border
        painter.setPen(QPen(QColor(55, 155, 55) if self._hovered else QColor(42, 122, 42), 1.0))
        painter.drawPath(path)

    def enterEvent(self, event):
        self._hovered = True
        if self._cta:
            self._cta.setStyleSheet("color:#ffffff; background:transparent; font-size:13px; font-weight:600; border:none;")
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        if self._cta:
            self._cta.setStyleSheet("color:rgba(255,255,255,0.40); background:transparent; font-size:13px; font-weight:600; border:none;")
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.course)
        super().mousePressEvent(event)


class ProfileEditDialog(QDialog):
    """Dark-themed dialog to edit the user's profile (PATCH /users/me)."""

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
            inp.setStyleSheet(self._FIELD_SS)
            layout.addWidget(inp)
            self._inputs.append(inp)

        self._status = QLabel("")
        self._status.setStyleSheet("color: #f87171; font-size: 12px;")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self._save_btn = QPushButton("Save")
        self._save_btn.setStyleSheet(self._BTN_SAVE)
        self._save_btn.setCursor(Qt.PointingHandCursor)
        self._save_btn.clicked.connect(self._on_save)
        cancel = QPushButton("Cancel")
        cancel.setStyleSheet(self._BTN_CANCEL)
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(self._save_btn)
        btn_row.addStretch()
        btn_row.addWidget(cancel)
        layout.addLayout(btn_row)

        self.updated_profile = None  # set on successful save

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

        import threading
        def _do():
            ok, _, err = self.api_client.update_profile(
                full_name=name, organization=org, mobile_number=mobile
            )
            if ok:
                new_profile = self.api_client.get_user_profile() or {}
                new_profile.setdefault("full_name", name)
                self.updated_profile = new_profile
                QTimer.singleShot(0, self.accept)
            else:
                def _show_err():
                    self._status.setText(err or "Update failed. Please try again.")
                    self._save_btn.setEnabled(True)
                    self._save_btn.setText("Save")
                QTimer.singleShot(0, _show_err)
        threading.Thread(target=_do, daemon=True).start()


class CourseSelectionWindow(QMainWindow):
    """Window showing available courses after login."""

    def __init__(self, master_app, profile: dict = None, parent=None):
        super().__init__(parent)
        self.master_app = master_app
        self._profile = profile or {}
        self.setWindowTitle("ROBOX — Select a course")
        if os.path.exists(_ABSIX_ICON):
            self.setWindowIcon(QIcon(_ABSIX_ICON))
        self.setMinimumSize(920, 580)
        self.resize(1060, 680)
        self.setup_ui()
        self.apply_style()
        self.center_on_screen()
    
    def closeEvent(self, event):
        """If user closes window without selecting a course, quit the app. Do not quit when closing to launch dashboard."""
        if getattr(self.master_app, "_launching_course", False):
            event.accept()
            return
        QApplication.quit()
        event.accept()
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(40, 32, 40, 32)

        # ── Logo pill ─────────────────────────────────────────────────────────
        _logo_path = _AB6_LOGO
        pill = QFrame()
        pill.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                border-radius: 18px;
            }
        """)
        pill_layout = QHBoxLayout(pill)
        pill_layout.setContentsMargins(24, 10, 24, 10)
        pill_layout.setAlignment(Qt.AlignCenter)

        logo_lbl = QLabel()
        logo_lbl.setAttribute(Qt.WA_TranslucentBackground)
        logo_lbl.setStyleSheet("background: transparent; border: none;")
        logo_lbl.setAlignment(Qt.AlignCenter)
        _pix = QPixmap(_logo_path)
        if not _pix.isNull():
            logo_lbl.setPixmap(_pix.scaledToHeight(52, Qt.SmoothTransformation))

        from PyQt5.QtWidgets import QGraphicsDropShadowEffect
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(28)
        glow.setColor(QColor(255, 255, 255, 55))
        glow.setOffset(0, 0)
        logo_lbl.setGraphicsEffect(glow)
        pill_layout.addWidget(logo_lbl)

        # ── User info bar (right-aligned) ─────────────────────────────────────
        _name  = self._profile.get("full_name") or self._profile.get("name") or ""
        _email = self._profile.get("email") or ""
        _initials = "".join(p[0].upper() for p in _name.split() if p)[:2] or "?"

        user_bar = QWidget()
        user_bar.setStyleSheet("background: transparent;")
        user_bar_layout = QHBoxLayout(user_bar)
        user_bar_layout.setContentsMargins(0, 0, 0, 0)
        user_bar_layout.setSpacing(10)

        # Avatar circle
        avatar_lbl = QLabel(_initials)
        avatar_lbl.setFixedSize(36, 36)
        avatar_lbl.setAlignment(Qt.AlignCenter)
        avatar_lbl.setStyleSheet("""
            QLabel {
                background: #2a2a2a; color: #e0e0e0;
                border-radius: 18px; font-size: 13px; font-weight: bold;
                border: 1px solid #444;
            }
        """)

        # Name + email column
        info_col = QVBoxLayout()
        info_col.setSpacing(1)
        name_lbl = QLabel(_name or "User")
        name_lbl.setStyleSheet("color: #e0e0e0; font-size: 12px; font-weight: 600; background: transparent;")
        email_lbl = QLabel(_email)
        email_lbl.setStyleSheet("color: #666; font-size: 10px; background: transparent;")
        info_col.addWidget(name_lbl)
        info_col.addWidget(email_lbl)

        # Edit Profile button
        edit_btn = QPushButton("Edit Profile")
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setStyleSheet("""
            QPushButton {
                background: #1a1a1a; color: #aaa;
                border: 1px solid #333; border-radius: 6px;
                padding: 5px 12px; font-size: 11px;
            }
            QPushButton:hover { background: #222; color: #ddd; border-color: #555; }
        """)

        def _open_edit_dialog():
            edit_btn.setEnabled(False)
            edit_btn.setText("Loading…")
            api_client = self.master_app.api_client

            from PyQt5.QtCore import QObject, pyqtSignal as _Signal, Qt as _Qt

            class _Sig(QObject):
                ready = _Signal(object)

            _sig = _Sig()

            def _on_ready(fresh):
                edit_btn.setEnabled(True)
                edit_btn.setText("Edit Profile")
                dlg = ProfileEditDialog(api_client, fresh, self)
                if dlg.exec_() == QDialog.Accepted and dlg.updated_profile:
                    p = dlg.updated_profile
                    self._profile = p
                    self.master_app.current_user_profile = p
                    n = p.get("full_name") or p.get("name") or _name
                    e = p.get("email") or _email
                    ini = "".join(w[0].upper() for w in n.split() if w)[:2] or "?"
                    avatar_lbl.setText(ini)
                    name_lbl.setText(n or "User")
                    email_lbl.setText(e)
                _sig.deleteLater()

            _sig.ready.connect(_on_ready, _Qt.QueuedConnection)

            import threading
            def _fetch():
                fresh = api_client.get_user_profile() or self._profile
                _sig.ready.emit(fresh)

            threading.Thread(target=_fetch, daemon=True).start()

        edit_btn.clicked.connect(_open_edit_dialog)

        user_bar_layout.addStretch()
        user_bar_layout.addWidget(avatar_lbl)
        user_bar_layout.addLayout(info_col)
        user_bar_layout.addWidget(edit_btn)

        pill_row = QHBoxLayout()
        pill_row.setContentsMargins(0, 0, 0, 0)
        pill_row.addStretch()
        pill_row.addWidget(pill)
        pill_row.addStretch()
        main_layout.addLayout(pill_row)
        main_layout.addWidget(user_bar)

        main_layout.addSpacing(8)

        divider_top = QFrame()
        divider_top.setFixedHeight(3)
        divider_top.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0    rgba(255,255,255,0),
                    stop:0.18 rgba(255,255,255,0.12),
                    stop:0.35 rgba(255,255,255,0.70),
                    stop:0.50 rgba(255,255,255,0.95),
                    stop:0.65 rgba(255,255,255,0.70),
                    stop:0.82 rgba(255,255,255,0.12),
                    stop:1    rgba(255,255,255,0));
                border: none;
                border-radius: 1px;
            }
        """)
        main_layout.addWidget(divider_top)
        main_layout.addSpacing(22)

        # ── Page heading ──────────────────────────────────────────────────────
        header = QLabel("Choose Your Course")
        header.setObjectName("pageTitle")
        header.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header)

        main_layout.addSpacing(6)

        sub = QLabel("Select a course and enter the access code to begin your journey.")
        sub.setObjectName("pageSubtitle")
        sub.setAlignment(Qt.AlignCenter)
        sub.setWordWrap(True)
        main_layout.addWidget(sub)

        main_layout.addSpacing(26)

        # ── Scrollable centered card grid ─────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical { background: #1a1a1a; width: 6px; border-radius: 3px; margin: 0; }
            QScrollBar::handle:vertical { background: #444; border-radius: 3px; min-height: 20px; }
            QScrollBar::handle:vertical:hover { background: #666; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")

        outer_v = QVBoxLayout(scroll_content)
        outer_v.setContentsMargins(0, 4, 0, 24)
        outer_v.setSpacing(0)
        outer_v.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        # Grid widget — fixed width forces true centering
        _CARD_W, _GAP = 400, 20
        _COLS = 2
        grid_widget = QWidget()
        grid_widget.setFixedWidth(_COLS * _CARD_W + (_COLS - 1) * _GAP)
        grid_widget.setStyleSheet("background: transparent;")
        grid = QGridLayout(grid_widget)
        grid.setSpacing(_GAP)
        grid.setContentsMargins(0, 0, 0, 0)

        for i, course in enumerate(COURSES):
            # Skip courses whose folder doesn't exist
            folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), course.get("folder", ""))
            if not os.path.isdir(folder_path):
                continue
            
            card = CourseCard(course)
            card.clicked.connect(self.on_course_clicked)
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(36)
            shadow.setColor(QColor(0, 0, 0, 120))
            shadow.setOffset(0, 10)
            card.setGraphicsEffect(shadow)
            row, col = i // 2, i % 2
            grid.addWidget(card, row, col)

        outer_v.addWidget(grid_widget, 0, Qt.AlignHCenter | Qt.AlignTop)
        outer_v.addStretch()

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
    
    def on_course_clicked(self, course):
        print(f"[MASTER] on_course_clicked: course={course['name']}, id={course.get('id')}, folder={course.get('folder')}")
        dialog = CourseCodeDialog(course["name"], self)
        if dialog.exec_() != QDialog.Accepted:
            print("[MASTER] CourseCodeDialog cancelled")
            return
        entered = dialog.get_code()
        print(f"[MASTER] Code entered (matches: {entered == course['code']})")
        if entered != course["code"]:
            self._show_invalid_code_message()
            return
        self.master_app._launching_course = True
        app = QApplication.instance()
        app.setQuitOnLastWindowClosed(False)
        self.close()
        QApplication.processEvents()

        loading = CourseLoadingSplash()
        loading.show()
        app.processEvents()

        # Keep splash alive — it is closed by the course window once ready.
        self.master_app._course_loading_splash = loading
        print("[MASTER] Launching course dashboard...")
        self.master_app.launch_course_dashboard(course)

        app.setQuitOnLastWindowClosed(True)
        self.master_app._launching_course = False
    
    def _show_invalid_code_message(self):
        """Show a visible error dialog for wrong course code."""
        if exec_dark_warning_card:
            exec_dark_warning_card(
                self,
                "Invalid code",
                "The code you entered is incorrect. Please try again.",
                ok_text="OK",
            )
            return
        QMessageBox.warning(
            self,
            "Invalid code",
            "The code you entered is incorrect. Please try again.",
        )
    
    def center_on_screen(self):
        screen = QDesktopWidget().screenGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
    
    def apply_style(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #111111; }
            QWidget { background-color: transparent; }

            QLabel#pageTitle {
                color: #ffffff;
                font-size: 26px;
                font-weight: bold;
            }
            QLabel#pageSubtitle {
                color: #ffffff;
                font-size: 16px;
            }

            QLabel#courseIcon {
                background: transparent;
                color: #ffffff;
                font-size: 22px;
                border: none;
            }
            QLabel#courseTitle {
                background: transparent;
                color: #ffffff;
                font-size: 17px;
                font-weight: bold;
                border: none;
            }
            QLabel#courseDesc {
                background: transparent;
                color: #ffffff;
                font-size: 13px;
                border: none;
            }
            QLabel#diffTag {
                background: rgba(42, 122, 42, 0.25);
                color: #ffffff;
                font-size: 12px;
                font-weight: bold;
                border: 1px solid rgba(55, 155, 55, 0.40);
                border-radius: 4px;
                padding: 2px 10px;
            }
            QLabel#courseCTA {
                background: transparent;
                color: rgba(255, 255, 255, 0.40);
                font-size: 13px;
                font-weight: 600;
                border: none;
            }
        """)


class MasterMainApp:
    """Master application that handles authentication before launching dashboard."""
    
    def __init__(self):
        self.api_client = MasterBackendAPIClient()
        self.current_user_email = None
        self.current_user_profile = None
        self._prefetcher = None
        
    def show_login_dialog(self):
        """Show enhanced login dialog and handle authentication."""
        try:
            print("[MASTER] show_login_dialog: creating MasterEnhancedLoginDialog")
            login_dialog = MasterEnhancedLoginDialog(None)

            login_dialog.setWindowFlags(
                Qt.Dialog |
                Qt.WindowTitleHint |
                Qt.WindowCloseButtonHint |
                Qt.WindowMinimizeButtonHint
            )
            login_dialog.setWindowModality(Qt.ApplicationModal)
            login_dialog.raise_()
            login_dialog.activateWindow()

            login_dialog.login_success.connect(self.on_login_success)
            print("[MASTER] show_login_dialog: calling exec_() — blocking until dialog closes")
            result = login_dialog.exec_()
            print(f"[MASTER] show_login_dialog: exec_() returned, result={result} (Accepted={login_dialog.Accepted})")

            if result != login_dialog.Accepted:
                print("[MASTER] Login cancelled by user")
                sys.exit(0)

            print(f"[MASTER] Copying api_client from login_dialog (access_token set: {bool(login_dialog.api_client.access_token)})")
            self.api_client = login_dialog.api_client
            print("[MASTER] show_login_dialog: done")
                
        except Exception as e:
            # Handle any errors in login dialog
            print(f"Error in login dialog: {e}")
            import traceback
            traceback.print_exc()
            if exec_dark_critical:
                exec_dark_critical(
                    None,
                    "Login Error",
                    f"Failed to initialize login system:\n{str(e)}",
                )
            else:
                QMessageBox.critical(
                    None,
                    "Login Error",
                    f"Failed to initialize login system:\n{str(e)}",
                )
            sys.exit(1)
    
    def on_login_success(self, email, user_profile):
        """Handle successful user login: store data; course selection is shown after exec_() returns."""
        print(f"[MASTER] on_login_success called: email={email}, profile={user_profile}")
        self.current_user_email = email
        self.current_user_profile = user_profile

        # Kick off background prefetch for all courses so the dashboard loads instantly.
        # Small delay so the master api_client has time to complete any token refresh
        # before the prefetcher copies the tokens.
        try:
            from master_progress_prefetch import CourseProgressPrefetcher
            self._prefetcher = CourseProgressPrefetcher(
                access_token  = self.api_client.access_token  or "",
                refresh_token = self.api_client.refresh_token or "",
                user_email    = email,
                courses       = COURSES,
                root_dir      = os.path.dirname(os.path.abspath(__file__)),
                base_url      = self.api_client.base_url,
            )
            # Delay start by 2s so login token refresh completes first.
            # Re-copy tokens right before start() to pick up any refresh that
            # happened between construction and the timer firing.
            def _start_prefetch():
                self._prefetcher.access_token  = self.api_client.access_token  or ""
                self._prefetcher.refresh_token = self.api_client.refresh_token or ""
                self._prefetcher.start()
            QTimer.singleShot(2000, _start_prefetch)
        except Exception as _pf_err:
            print(f"[MASTER] Prefetch start failed (non-fatal): {_pf_err}")
            self._prefetcher = None

        print("[MASTER] on_login_success: scheduling show_course_selection via QTimer.singleShot(0)")
        QTimer.singleShot(0, self.show_course_selection)
        print("[MASTER] on_login_success: returning")

    def show_course_selection(self):
        """Show the course selection window (after login or after leaving a course)."""
        print("[MASTER] show_course_selection: creating CourseSelectionWindow")
        # Ensure Qt doesn't quit just because no windows are open during the transition
        app = QApplication.instance()
        if app:
            app.setQuitOnLastWindowClosed(True)
        self.course_selection_window = CourseSelectionWindow(self, profile=self.current_user_profile)
        print("[MASTER] show_course_selection: calling .show()")
        self.course_selection_window.show()
        self.course_selection_window.raise_()
        self.course_selection_window.activateWindow()
        print("[MASTER] show_course_selection: window shown")

    def on_course_left(self, old_dashboard):
        """User chose to switch course — tear down old dashboard and show course selection."""
        print("[MASTER] on_course_left: user leaving course")
        # Prevent Qt from quitting when the last window (the dashboard) closes
        app = QApplication.instance()
        if app:
            app.setQuitOnLastWindowClosed(False)
        try:
            old_dashboard.close()
        except Exception as e:
            print(f"[MASTER] on_course_left close error: {e}")
        self.dashboard_window = None

        # Explicitly close any open robot serial connections before purging modules.
        # Without this the OS-level COM port handle lingers (GC is non-deterministic),
        # causing PermissionError when the next course tries to open the same port.
        _robot_closers = [
            ('src.esp_bridge.esp_bridge_controller', 'close_shared_esp_actuator'),
            ('src.esp_bridge',                       'close_shared_esp_actuator'),
            ('src.omx_bridge.omx_bridge_controller', 'close_shared_omx_actuator'),
            ('src.omx_bridge',                       'close_shared_omx_actuator'),
            ('src.snp_bridge.snp_esp_bridge',        'close_shared_snp_actuator'),
            ('src.snp_bridge',                       'close_shared_snp_actuator'),
        ]
        _closed_any = False
        for _mod_name, _fn_name in _robot_closers:
            _mod = sys.modules.get(_mod_name)
            if _mod and hasattr(_mod, _fn_name):
                try:
                    print(f"[MASTER] on_course_left: calling {_fn_name}()")
                    getattr(_mod, _fn_name)()
                    _closed_any = True
                except Exception as _ce:
                    print(f"[MASTER] {_fn_name} error: {_ce}")
        if _closed_any:
            import time as _t
            _t.sleep(0.3)  # Allow Windows to release the COM port handle

        # Purge stale course-module imports so the next course loads from a clean slate
        for key in list(sys.modules.keys()):
            if (key == 'gui' or key.startswith('gui.') or
                    key == 'src' or key.startswith('src.') or
                    key in ('backend_api_client', 'course_utils', 'challenge_mapping',
                            'course_backend_api_client')):
                del sys.modules[key]
        print("[MASTER] on_course_left: showing course selection")
        QTimer.singleShot(0, self.show_course_selection)
    
    def launch_course_dashboard(self, course):
        """Launch the dashboard for the selected course."""
        try:
            print(f"[MASTER] launch_course_dashboard: course={course['name']}, id={course.get('id')}, folder={course.get('folder')}, module={course.get('launch_module')}, class={course.get('launch_class')}")
            print(f"[MASTER] api_client.access_token set: {bool(self.api_client.access_token)}")
            print(f"[MASTER] api_client.email: {self.api_client.email}")
            folder = course.get("folder", "Kinematics")
            course_id = course.get("id", folder.lower())
            launch_module = course.get("launch_module", "main_app")
            launch_class = course.get("launch_class", "MainWindow")
            root = os.path.dirname(os.path.abspath(__file__))
            gui_dir = os.path.join(root, folder, "gui")
            folder_path = os.path.join(root, folder)
            src_path = os.path.join(folder_path, "src")

            import importlib
            import importlib.util
            import types as _types

            # ── Validate course folder exists before doing anything ───────────────
            if not os.path.isdir(folder_path):
                raise ImportError(
                    f"Course folder '{folder}' not found at {folder_path}."
                )

            # ── Purge ALL stale course-specific modules from sys.modules ─────────
            # Must wipe 'gui' itself (not just gui.*) so Python doesn't reuse the
            # old package object whose __path__ still points to the previous course.
            _purge_prefixes = ('gui', 'src', 'sim_to_real', 'robox_parameters',
                               'esp_bridge', 'operating_modes', 'robot_core',
                               'challenges', 'scoring', 'visualization', 'wrappers',
                               'utils', 'gui_handler', 'control_tables', 'config')
            _purge_exact = {'backend_api_client', 'course_utils', 'course_main_app',
                            'course_backend_api_client', 'challenge_mapping',
                            'challenge_runner', 'challenge_manager', 'challenge_widgets',
                            'control_visualizer'}
            for key in list(sys.modules.keys()):
                if key in _purge_exact or any(
                    key == p or key.startswith(p + '.') for p in _purge_prefixes
                ):
                    del sys.modules[key]

            # ── Rebuild sys.path: remove ALL course folders, insert this course ──
            _all_course_paths = set()
            for c in COURSES:
                _cf = os.path.join(root, c["folder"])
                _all_course_paths.update([_cf, os.path.join(_cf, "gui"), os.path.join(_cf, "src")])
            sys.path[:] = [p for p in sys.path if p not in _all_course_paths]
            # folder_path MUST come before gui_dir so that top-level modules like
            # challenge_runner.py (at Kinematics/challenge_runner.py) are found
            # when GUI files do `from challenge_runner import ChallengeRunner`.
            for p in (folder_path, gui_dir, src_path):
                sys.path.insert(0, p)

            # ── Register a fresh 'gui' package pointing at this course's gui dir ─
            gui_pkg = _types.ModuleType('gui')
            gui_pkg.__path__ = [gui_dir]
            gui_pkg.__package__ = 'gui'
            gui_pkg.__spec__ = None
            sys.modules['gui'] = gui_pkg

            # ── Import gui.<launch_module> fresh ─────────────────────────────────
            try:
                mod = importlib.import_module(f"gui.{launch_module}")
            except ModuleNotFoundError as exc:
                raise ImportError(
                    f"Dashboard module 'gui.{launch_module}' not found. "
                    f"Ensure {folder}/gui/{launch_module}.py exists."
                ) from exc
            cls = getattr(mod, launch_class)
            dashboard_window = cls()

            # Use the course-specific BackendAPIClient (not MasterBackendAPIClient) so
            # that get_progress/save_progress/upload_code_submission all use the correct
            # course default and accept the slot_map parameter that ProgressSyncManager passes.
            try:
                bc_mod = importlib.import_module("backend_api_client")
                print(f"[MASTER] Loaded course BackendAPIClient via import")
                course_api_client = bc_mod.BackendAPIClient()
                course_api_client.access_token = self.api_client.access_token
                course_api_client.refresh_token = self.api_client.refresh_token
                course_api_client.email = self.api_client.email
                dashboard_window.api_client = course_api_client
                print(f"[MASTER] course_api_client tokens transferred: access_token set={bool(course_api_client.access_token)}, email={course_api_client.email}")
            except (ModuleNotFoundError, AttributeError):
                print(f"[MASTER] No course backend_api_client found, using master api_client")
                dashboard_window.api_client = self.api_client

            print(f"[MASTER] Calling dashboard_window.on_login_success({self.current_user_email}, ...)")
            dashboard_window.current_user_email = self.current_user_email
            dashboard_window.current_user_profile = self.current_user_profile
            dashboard_window.username = self.current_user_email
            if hasattr(dashboard_window.api_client, "on_session_expired"):
                dashboard_window.api_client.on_session_expired = dashboard_window.handle_session_expired
            # Connect leave-course signal so the user can switch courses without restarting.
            if hasattr(dashboard_window, 'leave_course'):
                dashboard_window.leave_course.connect(
                    lambda dw=dashboard_window: self.on_course_left(dw)
                )
            # Hand the splash reference to the course window so it can close
            # it once the home page is built and showMaximized() has been called.
            dashboard_window._master_loading_splash = getattr(self, '_course_loading_splash', None)
            dashboard_window.on_login_success(self.current_user_email, self.current_user_profile)
            print("[MASTER] dashboard_window.on_login_success returned")
            # Keep a reference so the window is not garbage-collected.
            self.dashboard_window = dashboard_window

            # Auto-connect the robot in the background so it's ready before the
            # user clicks their first challenge.  Runs in a daemon thread — no UI
            # calls, only serial I/O — so it's safe to do outside the Qt main thread.
            if hasattr(dashboard_window, '_try_robot_connection_silent'):
                import threading as _th
                _dw_ref = dashboard_window
                def _auto_connect_robot():
                    try:
                        connected = _dw_ref._try_robot_connection_silent()
                        status = "connected" if connected else "not detected"
                        print(f"[MASTER] Auto-connect robot: {status} for course '{course.get('name')}'")
                    except Exception as _ae:
                        print(f"[MASTER] Auto-connect robot error: {_ae}")
                _th.Thread(target=_auto_connect_robot, daemon=True).start()

            print("Dashboard launched successfully")
        except Exception as e:
            import traceback
            traceback.print_exc()
            if exec_dark_critical:
                exec_dark_critical(
                    None,
                    "Error",
                    f"Failed to launch course:\n{str(e)}",
                )
            else:
                QMessageBox.critical(None, "Error", f"Failed to launch course: {str(e)}")
            sys.exit(1)


def main():
    """Main entry point for the master application."""
    # ── Frozen-exe: resources already set at module top; nothing extra needed here ──

    # Required for Qt WebEngine before creating QApplication
    from PyQt5.QtCore import QCoreApplication
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    # Disable High-DPI scaling quirks that cause blurry text on some Windows machines
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("ROBOX")
    app.setOrganizationName("ABSix")
    
    # Configure WebEngine for video playback (needed for dashboard)
    # NOTE: Do NOT clear cache/cookies — forces YouTube re-auth every launch (video lag).
    try:
        import platform as _plat
        from PyQt5.QtWebEngineWidgets import QWebEngineProfile, QWebEngineSettings
        
        # CRITICAL: Delay profile access until after event loop starts to avoid subprocess crash
        def _configure_webengine():
            try:
                profile = QWebEngineProfile.defaultProfile()
                if _plat.system() == 'Darwin':
                    _ua = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
                else:
                    _ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
                profile.setHttpUserAgent(_ua)
                profile.setPersistentCookiesPolicy(QWebEngineProfile.AllowPersistentCookies)
                s = profile.settings()
                s.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
                s.setAttribute(QWebEngineSettings.PluginsEnabled, True)
                s.setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)
                s.setAttribute(QWebEngineSettings.PlaybackRequiresUserGesture, False)
                s.setAttribute(QWebEngineSettings.WebGLEnabled, False)
                s.setAttribute(QWebEngineSettings.Accelerated2dCanvasEnabled, False)
                print("WebEngine configured for video playback (software rendering)")
            except Exception as e:
                print(f"WARNING: WebEngine configuration failed: {e}")
        
        # Defer WebEngine init until after QApplication event loop starts
        QTimer.singleShot(100, _configure_webengine)
        
    except ImportError:
        print("WARNING: QtWebEngineWidgets not found. Videos will not be displayed.")
    except Exception as e:
        print(f"WARNING: WebEngine setup failed: {e}")
    
    # Set application style using Kinematics/gui/style.py.
    try:
        import importlib
        import types as _style_types
        _kin_gui = os.path.join(_KIN_DIR, "gui")
        # Register a fresh 'gui' package pointing at Kinematics/gui so that
        # gui.style resolves correctly regardless of any prior sys.modules state.
        _gui_pkg = _style_types.ModuleType("gui")
        _gui_pkg.__path__ = [_kin_gui]
        _gui_pkg.__package__ = "gui"
        sys.modules["gui"] = _gui_pkg
        if _kin_gui not in sys.path:
            sys.path.insert(0, _kin_gui)
        style_mod = importlib.import_module("gui.style")
        style_mod.set_app_style(app)
    except Exception as e:
        print(f"Warning: Could not set app style: {e}")
    
    # user_data and user_submission are created per-course inside Kinematics/ and Control/ folders
    
    # Show splash screen
    splash = SplashScreen()
    splash.show()
    
    # Simulate loading process
    def simulate_loading():
        steps = [
            (10, "Initializing systems..."),
            (20, "Loading robot parameters..."),
            (35, "Calibrating actuators..."),
            (50, "Setting up challenges..."),
            (70, "Configuring user interface..."),
            (85, "Performing final checks..."),
            (100, "Ready for launch!")
        ]
        
        for progress, text in steps:
            splash.updateProgress(progress, text)
            app.processEvents()
            time.sleep(0.4)  # Simulate work being done
    
    simulate_loading()
    
    # Create master app instance
    master_app = MasterMainApp()
    
    # IMPORTANT: Close splash screen BEFORE showing login dialog
    def handle_after_splash():
        splash.close()  # Close splash screen first
        app.processEvents()  # Process events to ensure splash is closed
        
        # Small delay to ensure splash is fully closed
        QTimer.singleShot(100, lambda: master_app.show_login_dialog())
    
    # Close splash and show login after a brief delay
    QTimer.singleShot(500, handle_after_splash)
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
