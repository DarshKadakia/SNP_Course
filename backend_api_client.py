"""
BackendAPIClient — Kinematics course
Routes used:

  Auth (login system):
    POST /auth/signup
    POST /auth/verification-email
    POST /auth/resend-verification-email
    POST /auth/login
    POST /auth/refresh          (internal token refresh)
    POST /auth/forgot-password
    POST /auth/resend-password-reset-email
    POST /auth/reset-password
    POST /auth/logout
    POST /auth/accept-terms

  User:
    GET  /users/me
    GET  /users/progress                    (filtered by course_id)
    GET  /users/progress/{challenge_id}
    GET  /users/course-summary/{course_id}

  Learning (progress sync setup):
    GET  /learning/courses/find          (fast path: check if course already exists)
    POST /learning/courses/{id}/initialize (fast path: init user_progress rows only)
    POST /learning/setup                 (slow path: first-time course creation)
    GET  /learning/courses/{course_id}/challenges

  Attempts (progress sync):
    POST  /attempts/{challenge_id}/start
    POST  /attempts/{challenge_id}/run
    POST  /attempts/{challenge_id}/submit
    POST  /attempts/{challenge_id}/abandon
    GET   /attempts/{challenge_id}/all
    PATCH /attempts/{challenge_id}/progress
"""

import os
import json
import time
import concurrent.futures
import requests
from typing import Optional, Dict, Any, Tuple, List
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_BACKEND_URLS = [
    # "https://ab6exebackend-production.up.railway.app/", # Production
    "https://ab6exebackend-production-0c0a.up.railway.app/", # Development
    # "https://ab6-exe-backend.onrender.com",
    # "http://127.0.0.1:8000/",
]


def _pick_fastest_url() -> str:
    def _probe(url):
        requests.get(f"{url}/", timeout=5)
        return url
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(_BACKEND_URLS)) as ex:
        futures = {ex.submit(_probe, u): u for u in _BACKEND_URLS}
        for f in concurrent.futures.as_completed(futures):
            try:
                return f.result()
            except Exception:
                continue
    return _BACKEND_URLS[0]


BASE_URL = _pick_fastest_url()


def _load_course_config() -> Dict[str, Any]:
    try:
        import sys as _sys
        if getattr(_sys, 'frozen', False) and hasattr(_sys, '_MEIPASS'):
            path = os.path.join(_sys._MEIPASS, "gui", "data", "course_config.json")
        else:
            path = os.path.join(os.path.dirname(__file__), "gui", "data", "course_config.json")
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {
            "event_name":      "DEFAULT",
            "event_version":   "1.0",
            "course_name":     "Course",
            "course_sequence": 1,
        }


COURSE_CONFIG = _load_course_config()


class BackendAPIClient:

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.access_token:  Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.email:         Optional[str] = None
        self.on_session_expired = None

        self._token_valid_cache:      Optional[bool] = None
        self._token_valid_cache_time: float          = 0
        self._TOKEN_CACHE_TTL:        float          = 43_200   # 12 h

        self.session = requests.Session()
        retry = Retry(
            total=3, connect=3, read=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "PATCH"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=2, pool_maxsize=4)
        self.session.mount("https://", adapter)
        self.session.mount("http://",  adapter)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _headers(self, auth: bool = True) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if auth and self.access_token:
            h["Authorization"] = f"Bearer {self.access_token}"
        return h

    def _parse_error(self, r) -> str:
        try:
            detail = r.json().get("detail", f"Error {r.status_code}")
            return "; ".join(str(x) for x in detail) if isinstance(detail, list) else str(detail)
        except Exception:
            return f"Error {r.status_code}"

    def _save_tokens(self, access: str, refresh: str, email: str) -> None:
        self.access_token            = access
        self.refresh_token           = refresh
        self.email                   = email
        self._token_valid_cache      = True
        self._token_valid_cache_time = time.time()

    def _clear_tokens(self) -> None:
        self.access_token            = None
        self.refresh_token           = None
        self.email                   = None
        self._token_valid_cache      = None
        self._token_valid_cache_time = 0

    def _do_refresh(self) -> bool:
        if not self.refresh_token:
            return False
        try:
            r = self.session.post(
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
                self._token_valid_cache      = True
                self._token_valid_cache_time = time.time()
                return True
            return False
        except Exception:
            return False

    def _request(
        self,
        method:   str,
        endpoint: str,
        body:     Optional[Dict] = None,
        auth:     bool           = True,
        timeout:  int            = 25,
    ) -> Tuple[bool, Optional[Any], str]:
        url = f"{self.base_url}{endpoint}"

        def _do(h):
            if method == "GET":
                return self.session.get(url, headers=h, timeout=timeout)
            if method == "POST":
                return self.session.post(url, json=body or {}, headers=h, timeout=timeout)
            if method == "PATCH":
                return self.session.patch(url, json=body or {}, headers=h, timeout=timeout)
            raise ValueError(f"Unsupported method: {method}")

        try:
            r = _do(self._headers(auth))

            if r.status_code == 401 and auth:
                self._token_valid_cache = None
                if self._do_refresh():
                    r = _do(self._headers(True))
                    if r.status_code == 401:
                        if self.on_session_expired:
                            self.on_session_expired()
                        return False, None, "Session expired. Please login again."
                else:
                    if self.on_session_expired:
                        self.on_session_expired()
                    return False, None, "Session expired. Please login again."

            if r.status_code in (200, 201):
                try:
                    return True, r.json(), ""
                except ValueError:
                    return True, {}, ""

            return False, None, self._parse_error(r)

        except requests.exceptions.Timeout:
            return False, None, "Request timed out. Please try again."
        except requests.exceptions.ConnectionError:
            return False, None, "Cannot connect to server. Check your internet connection."
        except Exception as e:
            return False, None, f"Unexpected error: {e}"

    # ── Auth ──────────────────────────────────────────────────────────────────

    def signup(self, email: str, password: str, full_name: str,
               organization: str, mobile_number: str) -> Tuple[bool, str]:
        ok, data, err = self._request(
            "POST", "/auth/signup",
            body={
                "email":         email.strip().lower(),
                "password":      password,
                "full_name":     full_name.strip(),
                "organization":  organization.strip(),
                "mobile_number": mobile_number.strip(),
            },
            auth=False,
        )
        if ok:
            return True, data.get("message", "Signup successful. Please verify your email.")
        if err and ("already" in err.lower() or "exists" in err.lower()):
            return False, "An account with this email already exists."
        return False, err or "Signup failed"

    def login(self, email: str, password: str) -> Tuple[bool, Optional[Dict], str]:
        normalized = email.strip().lower()
        ok, data, err = self._request(
            "POST", "/auth/login",
            body={"email": normalized, "password": password},
            auth=False, timeout=35,
        )
        if ok and data:
            access  = data.get("access_token")
            refresh = data.get("refresh_token")
            if not access or not refresh:
                return False, None, "Login response missing tokens. Please try again."
            self._save_tokens(access, refresh, normalized)
            profile = self.get_profile()
            return True, profile, "Login successful"
        if err:
            low = err.lower()
            if "verify" in low:
                return False, None, err
            if "not found" in low or "404" in low:
                err = "No account found with that email. Please sign up."
            elif "invalid" in low or "incorrect" in low or "401" in low:
                err = "Invalid email or password."
        return False, None, err or "Login failed"

    def verify_email(self, email: str, token: str) -> Tuple[bool, str]:
        ok, data, err = self._request(
            "POST", "/auth/verification-email",
            body={"email": email.strip().lower(), "token": token.strip()},
            auth=False,
        )
        if ok:
            return True, data.get("message", "Email verified successfully!")
        return False, err or "Verification failed"

    def resend_verification(self, email: str) -> Tuple[bool, str]:
        ok, data, err = self._request(
            "POST", "/auth/resend-verification-email",
            body={"email": email.strip().lower()},
            auth=False,
        )
        if ok:
            return True, data.get("message", "Verification email sent.")
        return False, err or "Failed to resend verification"

    def forgot_password(self, email: str) -> Tuple[bool, str]:
        ok, data, err = self._request(
            "POST", "/auth/forgot-password",
            body={"email": email.strip().lower()},
            auth=False,
        )
        if ok:
            return True, data.get("message", "If an account exists, a reset code has been sent.")
        return False, err or "Failed to send reset email"

    def resend_password_reset(self, email: str) -> Tuple[bool, str]:
        ok, data, err = self._request(
            "POST", "/auth/resend-password-reset-email",
            body={"email": email.strip().lower()},
            auth=False,
        )
        if ok:
            return True, data.get("message", "Reset code resent.")
        return False, err or "Failed to resend reset email"

    def reset_password(self, email: str, token: str, new_password: str) -> Tuple[bool, str]:
        ok, data, err = self._request(
            "POST", "/auth/reset-password",
            body={"email": email.strip().lower(), "token": token.strip(), "new_password": new_password},
            auth=False,
        )
        if ok:
            return True, data.get("message", "Password reset successfully.")
        return False, err or "Failed to reset password"

    def accept_terms(self) -> Tuple[bool, str]:
        ok, data, err = self._request("POST", "/auth/accept-terms")
        if ok:
            return True, data.get("message", "Terms accepted.")
        return False, err or "Failed to accept terms"

    def logout(self) -> None:
        try:
            if self.refresh_token:
                self.session.post(
                    f"{self.base_url}/auth/logout",
                    json={"refresh_token": self.refresh_token},
                    headers={"Content-Type": "application/json"},
                    timeout=8,
                )
        except Exception:
            pass
        finally:
            self._clear_tokens()
            try:
                self.session.close()
            except Exception:
                pass

    # ── User ──────────────────────────────────────────────────────────────────

    def get_profile(self) -> Optional[Dict]:
        """GET /users/me"""
        ok, data, _ = self._request("GET", "/users/me")
        if ok and data:
            name = data.get("name") or data.get("full_name", "")
            return {
                "email":         data.get("email"),
                "full_name":     name,
                "name":          name,
                "organization":  data.get("organization"),
                "mobile_number": data.get("mobile_number"),
                "is_admin":      False,
                "created_at":    data.get("created_at"),
                "last_login":    data.get("last_login"),
            }
        return None

    def update_profile(
        self,
        full_name: str = None,
        organization: str = None,
        mobile_number: str = None,
    ) -> Tuple[bool, Optional[Dict], str]:
        """PATCH /users/me"""
        body: Dict[str, str] = {}
        if full_name is not None:
            body["full_name"] = full_name.strip()
        if organization is not None:
            body["organization"] = organization.strip()
        if mobile_number is not None:
            body["mobile_number"] = mobile_number.strip()
        if not body:
            return False, None, "No fields to update."
        ok, data, err = self._request("PATCH", "/users/me", body=body)
        if ok:
            return True, data, ""
        return False, None, err or "Failed to update profile."

    def get_user_progress(
        self,
        course_id: Optional[str] = None,
        event_id:  Optional[str] = None,
    ) -> Tuple[bool, Optional[List], str]:
        """GET /users/progress  (optionally filtered by course_id or event_id)"""
        params = []
        if course_id:
            params.append(f"course_id={course_id}")
        if event_id:
            params.append(f"event_id={event_id}")
        endpoint = "/users/progress" + ("?" + "&".join(params) if params else "")
        ok, data, err = self._request("GET", endpoint)
        if ok:
            return True, data or [], ""
        return False, None, err or "Failed to fetch progress"

    def get_challenge_progress(self, challenge_id: str) -> Tuple[bool, Optional[Dict], str]:
        """GET /users/progress/{challenge_id}"""
        ok, data, err = self._request("GET", f"/users/progress/{challenge_id}")
        if ok:
            return True, data, ""
        return False, None, err or "Not found"

    def get_course_summary(self, course_id: str) -> Tuple[bool, Optional[Dict], str]:
        """GET /users/course-summary/{course_id}"""
        ok, data, err = self._request("GET", f"/users/course-summary/{course_id}")
        if ok:
            return True, data, ""
        return False, None, err or "Failed to fetch course summary"

    # ── Learning ──────────────────────────────────────────────────────────────

    def setup_course(
        self,
        event_name:      str,
        event_version:   Optional[str],
        course_name:     str,
        course_sequence: int,
        challenges:      List[Dict],
        course_version:  Optional[str] = None,
    ) -> Tuple[bool, Optional[Dict], str]:
        """POST /learning/setup"""
        ok, data, err = self._request(
            "POST", "/learning/setup",
            body={
                "event":      {"name": event_name, "version": event_version},
                "course":     {"name": course_name, "sequence": course_sequence, "version": course_version},
                "challenges": challenges,
            },
            timeout=90,
        )
        if ok:
            return True, data, "Course setup complete"
        return False, None, err or "Course setup failed"

    def find_course(
        self,
        event_name:     str,
        course_name:    str,
        event_version:  Optional[str] = None,
        course_version: Optional[str] = None,
    ) -> Tuple[bool, Optional[Dict], str]:
        """GET /learning/courses/find?event_name=...&course_name=...&event_version=...&course_version=..."""
        from urllib.parse import urlencode
        params: Dict[str, str] = {"event_name": event_name, "course_name": course_name}
        if event_version is not None:
            params["event_version"] = event_version
        if course_version is not None:
            params["course_version"] = course_version
        ok, data, err = self._request("GET", f"/learning/courses/find?{urlencode(params)}")
        if ok:
            return True, data, ""
        return False, None, err or "Course not found"

    def initialize_course_progress(self, course_id: str) -> Tuple[bool, Optional[Dict], str]:
        """POST /learning/courses/{course_id}/initialize — creates missing user_progress rows."""
        ok, data, err = self._request("POST", f"/learning/courses/{course_id}/initialize")
        if ok:
            return True, data, ""
        return False, None, err or "Failed to initialize course progress"

    def get_course_challenges(self, course_id: str) -> Tuple[bool, Optional[List], str]:
        """GET /learning/courses/{course_id}/challenges"""
        ok, data, err = self._request("GET", f"/learning/courses/{course_id}/challenges")
        if ok:
            return True, data or [], ""
        return False, None, err or "Failed to fetch challenges"

    # ── Attempts ──────────────────────────────────────────────────────────────

    def start_attempt(self, challenge_id: str) -> Tuple[bool, Optional[Dict], str]:
        """POST /attempts/{challenge_id}/start"""
        ok, data, err = self._request("POST", f"/attempts/{challenge_id}/start")
        if ok:
            return True, data, "Attempt started"
        return False, None, err or "Failed to start attempt"

    def run_attempt(self, challenge_id: str, code_file: str) -> Tuple[bool, Optional[Dict], str]:
        """POST /attempts/{challenge_id}/run"""
        ok, data, err = self._request(
            "POST", f"/attempts/{challenge_id}/run",
            body={"code_file": code_file},
        )
        if ok:
            return True, data, "Run saved"
        return False, None, err or "Failed to save run"

    def submit_attempt(
        self,
        challenge_id: str,
        final_code: Optional[str] = None,
        score: Optional[int] = None,
    ) -> Tuple[bool, Optional[Dict], str]:
        """
        POST /attempts/{challenge_id}/submit — closes attempt (end_time, total_time, submission_type).

        Quiz: no source code — send empty string so strict APIs that require ``str`` (not JSON
        null) still accept the body. Prefer ``PATCH …/progress`` for score (ProgressSyncManager).
        Optional ``score`` kept for older callers that combine in one request.
        """
        # Deployed servers may use ``final_code: str`` (rejects null) or ``Optional[str]`` (accepts null).
        # Empty string satisfies strict validators; backend can normalize to NULL for storage.
        body: Dict[str, Any] = {"final_code": "" if final_code is None else final_code}
        if score is not None:
            body["score"] = int(score)
        ok, data, err = self._request(
            "POST", f"/attempts/{challenge_id}/submit",
            body=body,
        )
        if ok:
            return True, data, "Submitted"
        return False, None, err or "Failed to submit"

    def abandon_attempt(self, challenge_id: str) -> Tuple[bool, Optional[Dict], str]:
        """POST /attempts/{challenge_id}/abandon"""
        ok, data, err = self._request("POST", f"/attempts/{challenge_id}/abandon")
        if ok:
            return True, data, "Attempt abandoned"
        return False, None, err or "Failed to abandon attempt"

    def get_attempts(self, challenge_id: str) -> Tuple[bool, Optional[List], str]:
        """GET /attempts/{challenge_id}/all"""
        ok, data, err = self._request("GET", f"/attempts/{challenge_id}/all")
        if ok:
            return True, data or [], ""
        return False, None, err or "Failed to fetch attempts"

    def update_challenge_progress(self, challenge_id: str, score: int) -> Tuple[bool, Optional[Dict], str]:
        """PATCH /attempts/{challenge_id}/progress"""
        ok, data, err = self._request(
            "PATCH", f"/attempts/{challenge_id}/progress",
            body={"score": score},
        )
        if ok:
            return True, data, "Progress updated"
        return False, None, err or "Failed to update progress"

    # ── Session ───────────────────────────────────────────────────────────────

    def is_authenticated(self) -> bool:
        if not self.access_token:
            return False
        now = time.time()
        if (self._token_valid_cache is not None and
                now - self._token_valid_cache_time < self._TOKEN_CACHE_TTL):
            return self._token_valid_cache
        self._token_valid_cache      = True
        self._token_valid_cache_time = now
        return True

    def close_session(self) -> None:
        try:
            self.session.close()
        except Exception:
            pass

    def __del__(self):
        self.close_session()
