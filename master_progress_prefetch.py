"""
Master Progress Prefetcher
==========================
Runs as a single background daemon thread right after the user logs in.

For every course listed in the master COURSES table it:
  1. Reads the course's course_config.json (plain file I/O — no module imports).
  2. Calls GET /learning/courses/find  -> get course_id.
  3. Calls POST /learning/courses/{id}/initialize -> ensure user has progress rows.
  4. Calls GET /learning/courses/{id}/challenges -> challenge structure.
  5. Calls GET /users/progress?course_id={id} -> challenge-level progress only
     (scores + completed flags; NOT individual attempt rows).
  6. Saves the raw API responses to the course-specific encrypted local cache so
     ProgressSyncManager.load_progress() can convert them to the full UI format
     and return instantly without waiting for the backend.

Key design choices
------------------
- Single sequential thread: avoids concurrent Python import collisions (every
  course folder has its own backend_api_client / gui.data modules with the same
  names — importing them in parallel threads corrupts sys.modules).
- No course-module imports here: uses plain requests + file I/O only.
- Preserves any existing queue ops in the local file so in-flight offline work
  is never lost.
- Idempotent: safe to call on every login even if cache already exists.
"""

import os
import sys
import json
import threading
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import requests

# ── Storage key names (must match progress_sync.py) ──────────────────────────
_K_PREFETCHED_COURSE_ID = "_prefetched_course_id"
_K_PREFETCHED_AT        = "_prefetched_at"
_K_RAW_CHALLENGES       = "_raw_challenges"
_K_RAW_USER_PROGRESS    = "_raw_user_progress"
_K_COURSE_ID            = "_course_id"
_K_OP_QUEUE             = "_op_queue"


# ── Path helpers (must produce same result as get_user_course_data_dir) ───────

def _get_robox_app_dir() -> str:
    import sys as _sys
    if _sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    elif _sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    path = os.path.join(base, "ROBOX")
    os.makedirs(path, exist_ok=True)
    return path


def _course_storage_dir(
    event_name:      str,
    event_version:   Optional[str],
    course_name:     str,
    course_sequence: Optional[int],
    course_version:  Optional[str],
) -> str:
    """
    Returns the same directory that ProgressSyncManager / get_user_course_data_dir
    uses for this course.  All five course_config.json fields are used so that
    any field change is treated as a distinct course with its own cache.
    """
    ev  = str(event_version  or "1").replace(".", "_")
    cv  = str(course_version or "1").replace(".", "_")
    seq = str(course_sequence or 1)
    parts = [
        str(event_name).replace(" ", "_"),
        f"ev{ev}",
        str(course_name).replace(" ", "_"),
        f"seq{seq}",
        f"cv{cv}",
    ]
    course_key = "__".join(parts)
    path = os.path.join(_get_robox_app_dir(), "user_data", course_key)
    os.makedirs(path, exist_ok=True)
    return path


# ── EncryptedStorage import (identical across all course folders) ─────────────

def _load_encrypted_storage_class():
    """Import EncryptedStorage from the first available course src/utils."""
    root = os.path.dirname(os.path.abspath(__file__))
    for folder in ("Kinematics", "SNP_Kinematics", "SimToReal_Kinematics", "OMX_Kinematics"):
        src = os.path.join(root, folder, "src")
        if os.path.isdir(src):
            if src not in sys.path:
                sys.path.insert(0, src)
            try:
                # Remove any stale utils module before importing
                for _k in list(sys.modules.keys()):
                    if _k == "utils" or _k.startswith("utils."):
                        del sys.modules[_k]
                from utils.encrypted_storage import EncryptedStorage
                return EncryptedStorage
            except ImportError:
                continue
    raise ImportError("EncryptedStorage not found in any course src/utils folder")


# ── Main class ────────────────────────────────────────────────────────────────

class CourseProgressPrefetcher:
    """
    Starts one background daemon thread that sequentially prefetches challenge
    progress for every course and writes it to the local encrypted cache.

    Usage (called from master_main_app.py after login succeeds)::

        prefetcher = CourseProgressPrefetcher(
            access_token  = api_client.access_token,
            refresh_token = api_client.refresh_token,
            user_email    = email,
            courses       = COURSES,
            root_dir      = os.path.dirname(__file__),
        )
        prefetcher.start()   # non-blocking
    """

    def __init__(
        self,
        access_token:  str,
        refresh_token: str,
        user_email:    str,
        courses:       List[Dict],
        root_dir:      str,
        base_url:      str = "https://ab6exebackend-production-0c0a.up.railway.app",
    ):
        self.access_token  = access_token
        self.refresh_token = refresh_token
        self.user_email    = user_email.lower().strip()
        self.courses       = courses
        self.root_dir      = root_dir
        self.base_url      = base_url.rstrip("/")
        self._stop_evt     = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Kick off the background prefetch thread. Returns immediately."""
        if self._thread and self._thread.is_alive():
            return  # Already running
        self._stop_evt.clear()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="PREFETCH_AllCourses"
        )
        self._thread.start()
        print("[PREFETCH] Background prefetch thread started")

    def stop(self) -> None:
        """Signal the thread to stop at the next course boundary."""
        self._stop_evt.set()

    # ── Internal ─────────────────────────────────────────────────────────────

    def _try_refresh_token(self, session: requests.Session) -> bool:
        """POST /auth/refresh and update session Authorization header if successful."""
        if not self.refresh_token:
            return False
        try:
            r = session.post(
                f"{self.base_url}/auth/refresh",
                json={"refresh_token": self.refresh_token},
                headers={"Content-Type": "application/json"},
                timeout=20,
            )
            if r.status_code == 200:
                data = r.json()
                self.access_token = data["access_token"]
                if "refresh_token" in data:
                    self.refresh_token = data["refresh_token"]
                session.headers.update({"Authorization": f"Bearer {self.access_token}"})
                print("[PREFETCH] Token refreshed successfully")
                return True
            print(f"[PREFETCH] Token refresh failed (HTTP {r.status_code})")
            return False
        except Exception as exc:
            print(f"[PREFETCH] Token refresh error: {exc}")
            return False

    def _run(self) -> None:
        try:
            EncryptedStorage = _load_encrypted_storage_class()
        except ImportError as exc:
            print(f"[PREFETCH] Cannot load EncryptedStorage: {exc} — prefetch skipped")
            return

        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type":  "application/json",
        })

        for course in self.courses:
            if self._stop_evt.is_set():
                print("[PREFETCH] Stopped early")
                break
            try:
                self._prefetch_one(session, EncryptedStorage, course)
            except Exception as exc:
                name = course.get("name", "?")
                print(f"[PREFETCH] {name}: unhandled error — {exc}")

        session.close()
        print("[PREFETCH] All courses processed")

    def _prefetch_one(
        self,
        session,
        EncryptedStorage,
        course: Dict,
    ) -> None:
        folder      = course.get("folder", "")
        course_dir  = os.path.join(self.root_dir, folder)
        config_path = os.path.join(course_dir, "gui", "data", "course_config.json")

        if not os.path.isfile(config_path):
            print(f"[PREFETCH] Missing course_config.json: {config_path}")
            return

        with open(config_path, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)

        event_name      = cfg.get("event_name",      "DEFAULT")
        event_version   = cfg.get("event_version")
        course_name     = cfg.get("course_name",     "Course")
        course_sequence = cfg.get("course_sequence", 1)
        course_version  = cfg.get("course_version")

        print(f"[PREFETCH] >> {event_name} / {course_name} ...")

        # ── 1. Find course on backend ──────────────────────────────────────
        params: Dict[str, str] = {
            "event_name":  event_name,
            "course_name": course_name,
        }
        if event_version:
            params["event_version"] = event_version
        if course_version:
            params["course_version"] = course_version

        try:
            r = session.get(
                f"{self.base_url}/learning/courses/find",
                params=params,
                timeout=20,
            )
        except Exception as exc:
            print(f"[PREFETCH] find_course network error: {exc}")
            return

        if r.status_code == 401:
            print("[PREFETCH] 401 on find_course — attempting token refresh...")
            if not self._try_refresh_token(session):
                print("[PREFETCH] Token refresh failed — stopping prefetch")
                self._stop_evt.set()
                return
            try:
                r = session.get(
                    f"{self.base_url}/learning/courses/find",
                    params=params,
                    timeout=20,
                )
            except Exception as exc:
                print(f"[PREFETCH] find_course retry error: {exc}")
                return
            if r.status_code == 401:
                print("[PREFETCH] Still 401 after refresh — stopping prefetch")
                self._stop_evt.set()
                return
        if r.status_code != 200:
            print(f"[PREFETCH] Course not found (HTTP {r.status_code}) — skipping")
            return

        found = r.json() if r.text else {}
        course_id = str(found.get("course_id", "")) if found else ""
        if not course_id:
            print(f"[PREFETCH] Course not set up on backend yet — skipping {course_name}")
            return

        # ── 2. Initialize user's progress rows (non-fatal) ────────────────
        try:
            session.post(
                f"{self.base_url}/learning/courses/{course_id}/initialize",
                timeout=15,
            )
        except Exception:
            pass

        # ── 3. Fetch challenge structure ───────────────────────────────────
        try:
            r_ch = session.get(
                f"{self.base_url}/learning/courses/{course_id}/challenges",
                timeout=20,
            )
            if r_ch.status_code != 200:
                print(f"[PREFETCH] get_challenges HTTP {r_ch.status_code} — skipping")
                return
            raw_challenges: List[Dict] = r_ch.json() or []
        except Exception as exc:
            print(f"[PREFETCH] get_challenges error: {exc}")
            return

        # ── 4. Fetch challenge-level progress (no attempt details) ────────
        try:
            r_pr = session.get(
                f"{self.base_url}/users/progress",
                params={"course_id": course_id},
                timeout=20,
            )
            if r_pr.status_code != 200:
                print(f"[PREFETCH] get_user_progress HTTP {r_pr.status_code} — skipping")
                return
            raw_user_progress: List[Dict] = r_pr.json() or []
        except Exception as exc:
            print(f"[PREFETCH] get_user_progress error: {exc}")
            return

        # ── 5. Save to course-specific encrypted local storage ────────────
        storage_dir = _course_storage_dir(
            event_name, event_version, course_name, course_sequence, course_version
        )
        storage = EncryptedStorage(self.user_email, app_data_dir=storage_dir)

        # Preserve any existing queue ops so in-flight offline work is not lost.
        existing = storage.load() or {}
        data_to_save = dict(existing)
        data_to_save[_K_PREFETCHED_COURSE_ID] = course_id
        data_to_save[_K_PREFETCHED_AT]        = datetime.now(timezone.utc).isoformat()
        data_to_save[_K_RAW_CHALLENGES]       = raw_challenges
        data_to_save[_K_RAW_USER_PROGRESS]    = raw_user_progress
        if not data_to_save.get(_K_COURSE_ID):
            data_to_save[_K_COURSE_ID] = course_id

        ok = storage.save(data_to_save)
        if ok:
            print(
                f"[PREFETCH] ✓ {course_name}: "
                f"{len(raw_challenges)} challenges, "
                f"{len(raw_user_progress)} progress rows cached"
            )
        else:
            print(f"[PREFETCH] ✗ {course_name}: failed to write local cache")
