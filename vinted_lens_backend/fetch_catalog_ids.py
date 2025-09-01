# fetch_catalog_ids.py
# Objectif : récupérer *tous* les catalog_id de Vinted en crawlant les pages /catalog.
# Principe :
#  - on part de la home et on collecte tous les liens /catalog/<id>-<slug>
#  - pour chaque page /catalog trouvée, on :
#       * extrait l'ID courant, le nom (depuis le dernier breadcrumb), le path complet,
#       * détecte le parent_id (avant-dernier breadcrumb s'il existe),
#       * découvre d'autres /catalog/... à visiter.
#  - on écrit un CSV final (id, slug, name, url, parent_id, path, level)
#
# Remarques :
#  - On reste côté HTML => pas d'API interne ni de cookies Datadome.
#  - Respecte la charte du site : rate-limit doux, UA propre.
#  - Ajoute --base si tu veux un autre portail (.de, .it, .com…).

import re, time, csv, sys
from collections import deque
from urllib.parse import urljoin, urlparse
import argparse
import requests
from bs4 import BeautifulSoup

CAT_HREF_RE = re.compile(r"^/catalog/(\d+)-([a-z0-9-]+)$", re.IGNORECASE)
BREADCRUMB_RE = re.compile(r"/catalog/(\d+)-[a-z0-9-]+", re.IGNORECASE)

def make_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": "VintedLens/1.0 (+research; contact: you@example.com)",
        "Accept-Language": "fr,fr-FR;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml"
    })
    return s

def extract_catalog_links(html):
    """Renvoie une liste d'hrefs '/catalog/<id>-<slug>' trouvés dans la page."""
    soup = BeautifulSoup(html, "html.parser")
    hrefs = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if CAT_HREF_RE.match(href):
            hrefs.add(href.split("?")[0])  # normalise (sans query)
    return list(hrefs)

def parse_breadcrumbs(html):
    """
    Tente d'extraire la hiérarchie à partir des breadcrumbs.
    Retourne (path_titles, path_ids), ex:
      (["Femmes","Robes","Robes mini"], [1904, 178, 1775])
    """
    soup = BeautifulSoup(html, "html.parser")
    # Heuristique générique : prendre tous les <a> des breadcrumbs s'ils existent
    crumbs = []
    # Essais sur éléments habituels : nav, ol[aria-label=breadcrumb], etc.
    for sel in ["nav", "ol", "ul", "div"]:
        for node in soup.select(f"{sel} a[href*='/catalog/']"):
            href = node.get("href", "")
            m = BREADCRUMB_RE.search(href)
            if m:
                cid = int(m.group(1))
                title = node.get_text(strip=True)
                if title:
                    crumbs.append((title, cid))
        if crumbs:
            break

    if not crumbs:
        # fallback brut : toutes les ancres au-dessus du H1
        h1 = soup.find("h1")
        anchor_candidates = soup.find_all("a", href=True) if not h1 else h1.find_all_previous("a", href=True)
        tmp = []
        for a in anchor_candidates:
            m = BREADCRUMB_RE.search(a["href"])
            if m:
                tmp.append((a.get_text(strip=True), int(m.group(1))))
        # on prend les derniers uniques comme approximation
        if tmp:
            # déduplique en conservant l'ordre d'apparition
            seen = set()
            crumbs = [(t, i) for t, i in tmp if not (i in seen or seen.add(i))][-5:]

    titles = [t for t, _ in crumbs]
    ids = [i for _, i in crumbs]
    return titles, ids

def current_category_from_page(url, html):
    """Déduit (id, slug) de l'URL, puis 'name' depuis breadcrumb last, path et parent_id."""
    m = CAT_HREF_RE.search(urlparse(url).path)
    if not m:
        return None

    curr_id = int(m.group(1))
    slug = m.group(2)

    titles, ids = parse_breadcrumbs(html)
    name = titles[-1] if titles else slug.replace("-", " ").title()
    parent_id = ids[-2] if len(ids) >= 2 and ids[-1] == curr_id else 0
    path = " > ".join(titles) if titles else name
    level = len(ids) if ids else 1

    return {
        "id": curr_id,
        "slug": slug,
        "name": name,
        "parent_id": parent_id,
        "path": path,
        "level": level
    }

def crawl_all_catalogs(base="https://www.vinted.fr", max_pages=5000, delay=0.2):
    s = make_session()
    start = base  # on part de la home
    seen_urls = set()
    to_visit = deque([start])
    found_ids = {}  # id -> record
    visited_pages = 0

    while to_visit and visited_pages < max_pages:
        url = to_visit.popleft()
        if url in seen_urls:
            continue
        seen_urls.add(url)

        try:
            r = s.get(url, timeout=20)
            if r.status_code >= 400:
                continue
        except Exception:
            continue

        html = r.text
        visited_pages += 1

        # Découverte des pages /catalog
        for href in extract_catalog_links(html):
            abs_url = urljoin(base, href)
            # Ajoute dans la file si pas vu
            if abs_url not in seen_urls:
                to_visit.append(abs_url)

        # Si cette page est elle-même une page /catalog/<id>-<slug>, on l’enregistre
        if CAT_HREF_RE.search(urlparse(url).path):
            rec = current_category_from_page(url, html)
            if rec and rec["id"] not in found_ids:
                found_ids[rec["id"]] = {
                    **rec,
                    "url": url
                }

        time.sleep(delay)

    return list(found_ids.values())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://www.vinted.fr", help="Portail Vinted (ex: https://www.vinted.de)")
    ap.add_argument("--out", default="catalog_ids.csv", help="Fichier CSV de sortie")
    ap.add_argument("--max-pages", type=int, default=5000, help="Limite de pages à visiter (sécurité)")
    ap.add_argument("--delay", type=float, default=0.2, help="Délai (s) entre requêtes")
    args = ap.parse_args()

    rows = crawl_all_catalogs(base=args.base, max_pages=args.max_pages, delay=args.delay)
    rows.sort(key=lambda r: (r["level"], r["parent_id"], r["id"]))

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "slug", "name", "url", "parent_id", "path", "level"])
        for r in rows:
            w.writerow([r["id"], r["slug"], r["name"], r["url"], r["parent_id"], r["path"], r["level"]])

    print(f"OK -> {args.out} ({len(rows)} catégories)")

if __name__ == "__main__":
    main()
