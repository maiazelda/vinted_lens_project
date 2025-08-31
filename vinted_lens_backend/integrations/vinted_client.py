import time
import requests
from typing import Optional, Dict, Any

class VintedClient:
    """
    Client HTTP pour endpoints privés Vinted.
    - Gère session, en-têtes réalistes, rate-limit
    - Récupère le token CSRF via un GET initial sur la home
    - Ajoute les en-têtes XHR attendus (X-Requested-With, Referer, X-CSRF-Token)
    """

    def __init__(self, base="https://www.vinted.fr", min_interval_s: float = 0.8):
        self.base = base.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/118.0.0.0 Safari/537.36"),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
        })
        self._last_call = 0.0
        self.min_interval_s = min_interval_s
        self._csrf_token: Optional[str] = None

    # --- utils ---
    def _sleep_if_needed(self):
        elapsed = time.time() - self._last_call
        if elapsed < self.min_interval_s:
            time.sleep(self.min_interval_s - elapsed)
        self._last_call = time.time()

    def _ensure_csrf(self):
        """Charge la home pour obtenir les cookies (dont vinted_csrf) puis mémorise le token."""
        if self._csrf_token:
            return
        # 1) un GET sur la home pour récupérer les Set-Cookie
        resp = self.session.get(self.base + "/", timeout=12)
        # 2) extraire le cookie vinted_csrf (nom fréquemment utilisé côté Vinted)
        csrf = (self.session.cookies.get("vinted_csrf")
                or self.session.cookies.get("csrf_token")
                or self.session.cookies.get("secure_vinted_csrf"))
        if csrf:
            self._csrf_token = csrf
        # Pas d'exception si pas trouvé: certains GET passent sans CSRF ; on l'ajoutera si dispo.

    def _with_xhr_headers(self, extra_ref: Optional[str] = None) -> Dict[str, str]:
        """En-têtes utilisés pour les appels XHR de l'app web Vinted."""
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Referer": extra_ref or (self.base + "/catalog"),
        }
        if self._csrf_token:
            headers["X-CSRF-Token"] = self._csrf_token
        # Certaines installations exigent ce header (plateforme applicative front)
        headers["App-Platform"] = "web"
        return headers

    # --- requêtes ---
    def get(self, path: str, params: Optional[Dict[str, Any]] = None,
            referer: Optional[str] = None) -> requests.Response:
        self._sleep_if_needed()
        url = path if path.startswith("http") else f"{self.base}{path}"
        self._ensure_csrf()
        headers = self._with_xhr_headers(extra_ref=referer)
        print(f"[VINTED] GET {url} params={params or {}}")
        resp = self.session.get(url, params=params, headers=headers, timeout=12)
        print(f"[VINTED] -> {resp.status_code} {len(resp.content)} bytes")
        return resp

    # --- API de recherche ---
    def search_items(self, query: str, page: int = 1, per_page: int = 20) -> dict:
        """
        Appelle l'API privée Vinted pour récupérer une page JSON d'articles.
        """
        params = {
            "search_text": query,
            "order": "newest_first",
            "page": page,
            "per_page": per_page,
        }
        # référer proche de ce que fait l'app web (utile pour certains contrôles côté serveur)
        r = self.get("/api/v2/catalog/items", params=params,
                     referer=f"{self.base}/catalog?search_text={query}")
        r.raise_for_status()
        return r.json()
