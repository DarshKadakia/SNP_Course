"""
ROBOX UI — application entry point.

Used by both:
  • Development:  python main.py
  • Frozen exe:   PyInstaller uses this as the Analysis script.

Do NOT import any challenge / hardware modules at the top level here.
All heavy imports happen inside main() so that PyInstaller's hook discovery
runs cleanly and startup errors produce a readable traceback.
"""

import multiprocessing
import os
import sys


def _bootstrap_path() -> None:
    """Add the Kinematics root to sys.path when run as a script in dev mode.

    In a frozen exe sys._MEIPASS is already on sys.path; this is a no-op there.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)


def _configure_qt_env() -> None:
    """Apply Qt environment knobs before QApplication is created."""
    # Prevent Qt WebEngine from writing its disk cache inside the frozen bundle
    # (which is read-only in one-file mode).  Use a platform-appropriate path.
    if getattr(sys, 'frozen', False):
        if sys.platform == 'win32':
            app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
        elif sys.platform == 'darwin':
            app_data = os.path.expanduser('~/Library/Application Support')
        else:
            app_data = os.environ.get('XDG_DATA_HOME', os.path.expanduser('~/.local/share'))
        cache_dir = os.path.join(app_data, 'ROBOX', 'qt_cache')
        os.makedirs(cache_dir, exist_ok=True)
        os.environ.setdefault('QTWEBENGINE_DISK_CACHE_PATH', cache_dir)
        # macOS frozen .app bundles need --no-sandbox in addition to disabling
        # the GPU sandbox; without it QtWebEngineProcess exits immediately.
        if sys.platform == 'darwin':
            flags = '--disable-gpu-sandbox --disable-dev-shm-usage --no-sandbox'
        else:
            flags = '--disable-gpu-sandbox'
        os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS', flags)


def main() -> None:
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication

    # High-DPI support — must be set before QApplication is created
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("ROBOX UI")
    app.setOrganizationName("ABSix")

    # Import MainWindow lazily so any import error appears AFTER the app is
    # running and can be shown in a dialog rather than silently crashing.
    try:
        from gui.main_app import MainWindow
    except Exception as exc:
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(
            None,
            "Startup Error",
            f"Failed to load the main window:\n\n{exc}\n\n"
            "Please check your installation.",
        )
        sys.exit(1)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    # Required so that multiprocessing works correctly inside a frozen exe.
    # Must be called before any other code that might spawn child processes.
    multiprocessing.freeze_support()

    _bootstrap_path()
    _configure_qt_env()
    main()
