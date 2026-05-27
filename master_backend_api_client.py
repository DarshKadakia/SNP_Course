"""
MasterBackendAPIClient — master login layer
Routes used:

  Auth:
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
    GET   /users/me
    PATCH /users/me
"""

import time
import concurrent.futures
import requests
from typing import Optional, Dict, Any, Tuple
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


class MasterBackendAPIClient:

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
        timeout:  int            = 30,
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

    def signup(
        self,
        email:         str,
        password:      str,
        full_name:     str,
        organization:  str,
        mobile_number: str,
    ) -> Tuple[bool, str]:
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
        return False, err or "Signup failed."

    def register(
        self,
        email:         str,
        password:      str,
        full_name:     str,
        college_name:  str,
        mobile_number: str,
    ) -> Tuple[bool, str]:
        """Alias for signup — college_name maps to organization."""
        return self.signup(email, password, full_name, college_name, mobile_number)

    def login(self, email: str, password: str) -> Tuple[bool, Optional[Dict], str, Optional[bool]]:
        ok, data, err = self._request(
            "POST", "/auth/login",
            body={"email": email.strip().lower(), "password": password},
            auth=False, timeout=35,
        )
        if ok and data:
            access  = data.get("access_token")
            refresh = data.get("refresh_token")
            if not access or not refresh:
                return False, None, "Login response missing tokens. Please try again.", None
            self._save_tokens(access, refresh, email.strip().lower())
            profile        = self.get_user_profile()
            terms_accepted = data.get("terms_accepted", None)
            return True, profile, "Login successful.", terms_accepted
        if err:
            low = err.lower()
            if "verify" in low:
                return False, None, err, None
            if "not found" in low or "404" in low:
                return False, None, "No account found with that email. Please sign up.", None
            if "invalid" in low or "incorrect" in low or "401" in low:
                return False, None, "Invalid email or password.", None
        return False, None, err or "Login failed.", None

    def verify_email(self, email: str, token: str) -> Tuple[bool, str]:
        ok, data, err = self._request(
            "POST", "/auth/verification-email",
            body={"email": email.strip().lower(), "token": token.strip()},
            auth=False,
        )
        if ok:
            return True, data.get("message", "Email verified successfully!")
        return False, err or "Verification failed."

    def resend_verification(self, email: str) -> Tuple[bool, str]:
        ok, data, err = self._request(
            "POST", "/auth/resend-verification-email",
            body={"email": email.strip().lower()},
            auth=False,
        )
        if ok:
            return True, data.get("message", "Verification email sent.")
        return False, err or "Failed to resend verification email."

    def forgot_password(self, email: str) -> Tuple[bool, str]:
        ok, data, err = self._request(
            "POST", "/auth/forgot-password",
            body={"email": email.strip().lower()},
            auth=False,
        )
        if ok:
            return True, data.get("message", "Password reset email sent.")
        return False, err or "Failed to send reset email."

    def request_password_reset(self, email: str) -> Tuple[bool, str]:
        """Alias for forgot_password."""
        return self.forgot_password(email)

    def resend_password_reset(self, email: str) -> Tuple[bool, str]:
        ok, data, err = self._request(
            "POST", "/auth/resend-password-reset-email",
            body={"email": email.strip().lower()},
            auth=False,
        )
        if ok:
            return True, data.get("message", "Password reset email resent.")
        return False, err or "Failed to resend reset email."

    def reset_password(self, email: str, token: str, new_password: str) -> Tuple[bool, str]:
        ok, data, err = self._request(
            "POST", "/auth/reset-password",
            body={"email": email.strip().lower(), "token": token.strip(), "new_password": new_password},
            auth=False,
        )
        if ok:
            return True, data.get("message", "Password reset successfully.")
        return False, err or "Failed to reset password."

    def accept_terms(self) -> Tuple[bool, str]:
        ok, data, err = self._request("POST", "/auth/accept-terms")
        if ok:
            return True, data.get("message", "Terms accepted.")
        return False, err or "Failed to accept terms."

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

    def get_user_profile(self) -> Optional[Dict]:
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
