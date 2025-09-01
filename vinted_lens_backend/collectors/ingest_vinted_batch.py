import os, sys, io, time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple, List, Iterable

# rendre visibles les packages du backend
sys.path.append(os.path.dirname(__file__) + "/..")

import requests
from PIL import Image
import numpy as np
from clickhouse_driver import Client

from integrations.vinted_client import VintedClient
from models.clip_model import CLIPService

CLICKHOUSE_HOST = "localhost"
CLICKHOUSE_DB   = "vinted_lens"

# ----------- ClickHouse ----------
def ch() -> Client:
    return Client(host=CLICKHOUSE_HOST, database=CLICKHOUSE_DB)

def already_have_ids(db: Client, ids: Iterable[int]) -> set[int]:
    ids = list(set(int(x) for x in ids))
    if not ids:
        return set()
    # on construit une clause IN correcte avec tuple
    query = f"SELECT id FROM vinted_lens.products WHERE id IN {tuple(ids)}"
    rows = db.execute(query)
    return {int(r[0]) for r in rows}

def insert_products(db: Client, rows: List[tuple]):
    if rows:
        db.execute("""
            INSERT INTO vinted_lens.products
            (id, title, price, platform, image_url, embedding, category, color, brand, size, condition, created_at, updated_at)
            VALUES
        """, rows)

def insert_product_embeddings(db: Client, rows: List[tuple]):
    if rows:
        db.execute("""
            INSERT INTO vinted_lens.product_embeddings
            (product_id, embedding, norm)
            VALUES
        """, rows)

# ----------- Helpers champs Vinted ----------
def pick_image_url(it: Dict[str, Any]) -> Optional[str]:
    photo = it.get("photo") or {}
    for k in ("full_size_url", "url"):
        if isinstance(photo, dict) and photo.get(k):
            return photo[k]
    photos = it.get("photos")
    if isinstance(photos, list) and photos:
        for k in ("full_size_url", "url"):
            if photos[0].get(k):
                return photos[0][k]
    return None

def pick_price(it: Dict[str, Any]) -> float:
    p = it.get("price") or {}
    try:
        return float(p.get("amount")) if p.get("amount") is not None else 0.0
    except Exception:
        return 0.0

def pick_brand(it: Dict[str, Any]) -> str:
    if it.get("brand_title"):
        return it["brand_title"]
    b = it.get("brand") or {}
    return b.get("title") or ""

def pick_size(it: Dict[str, Any]) -> str:
    return (it.get("size_title") or (it.get("size") or {}).get("title") or "")

def pick_condition(it: Dict[str, Any]) -> str:
    if isinstance(it.get("condition"), dict):
        return it["condition"].get("title", "")
    return it.get("condition") or it.get("status") or ""

def pick_category(it: Dict[str, Any]) -> str:
    cat = it.get("category") or {}
    parts = []
    for k in ("parent_title", "title"):
        if cat.get(k):
            parts.append(cat[k])
    return " > ".join(parts) if parts else ""

def pick_created_updated(it: Dict[str, Any]) -> Tuple[datetime, datetime]:
    def as_dt(ts_key: str, iso_key: str) -> Optional[datetime]:
        ts = it.get(ts_key)
        if isinstance(ts, (int, float)) and ts > 0:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        v = it.get(iso_key)
        if isinstance(v, str) and len(v) >= 10:
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except Exception:
                return None
        return None
    created = as_dt("created_at_ts", "created_at") or datetime.now(timezone.utc)
    updated = as_dt("updated_at_ts", "updated_at") or created
    return created, updated

# ----------- Image -> Embedding ----------
def download_image(url: str, session: Optional[requests.Session] = None) -> Image.Image:
    sess = session or requests.Session()
    headers = {"Referer": "https://www.vinted.fr/catalog"}
    r = sess.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGB")

def encode_image(url: str, clip: CLIPService, session: Optional[requests.Session] = None) -> List[float]:
    img = download_image(url, session=session)
    vec = clip.encode_image_pil(img)  # 512 floats
    v = np.asarray(vec, dtype=np.float32)
    n = np.linalg.norm(v)
    if v.shape != (512,):
        raise RuntimeError(f"Embedding shape {v.shape}, attendu (512,)")
    if not np.isfinite(n) or n == 0:
        raise RuntimeError("Norme embedding invalide")
    v = (v / n).astype(np.float32)
    return v.tolist()

# ----------- Main (petite batch paginée) ----------
def main():
    client = VintedClient(base="https://www.vinted.fr", min_interval_s=0.9)
    clip   = CLIPService()
    db     = ch()

    query      = "robe"       # pour valider la pipeline; on passera ensuite à H/F via catalog_ids
    per_page   = 20
    max_pages  = 3            # petite batch pour validation
    since_dt   = datetime.now(timezone.utc) - timedelta(days=730)  # ≤ 2 ans

    total_seen = total_kept = total_inserted = 0
    img_session = requests.Session()

    for page in range(1, max_pages + 1):
        data  = client.search_items(query=query, page=page, per_page=per_page)
        items = data.get("items") or data.get("catalog_items") or []
        if not items:
            print(f"[PAGE {page}] 0 item -> stop.")
            break

        total_seen += len(items)

        # filtre ≤ 2 ans (sur created/updated)
        filtered: List[Dict[str, Any]] = []
        for it in items:
            created, updated = pick_created_updated(it)
            if (created >= since_dt) or (updated >= since_dt):
                filtered.append(it)

        total_kept += len(filtered)
        if not filtered:
            print(f"[PAGE {page}] rien à garder (≤2ans).")
            continue

        # dédoublonnage: on n'insère que les id inexistants
        ids_page = [int(it["id"]) for it in filtered if "id" in it]
        have = already_have_ids(db, ids_page)
        todo = [it for it in filtered if int(it["id"]) not in have]
        if not todo:
            print(f"[PAGE {page}] tous déjà en base, skip.")
            continue

        rows_products: List[tuple] = []
        rows_embs: List[tuple]     = []

        for it in todo:
            try:
                pid = int(it["id"])
                image_url = pick_image_url(it)
                if not image_url:
                    raise RuntimeError("image_url introuvable")

                emb = encode_image(image_url, clip, session=img_session)   # 512 Float32 normalisés
                norm = float(np.linalg.norm(np.asarray(emb, dtype=np.float32)))  # ~1.0

                title = it.get("title") or it.get("description") or ""
                price = pick_price(it)
                platform = "vinted"
                category = pick_category(it)
                color    = (it.get("colour") or it.get("color") or "")
                brand    = pick_brand(it)
                size     = pick_size(it)
                condition = pick_condition(it)
                created_at, updated_at = pick_created_updated(it)

                rows_products.append((
                    pid, title, float(price), platform, image_url, emb, category, str(color),
                    brand, size, condition, created_at, updated_at
                ))
                rows_embs.append((pid, emb, norm))
                # petit délai pour être sympa (download image)
                time.sleep(0.1)

            except Exception as e:
                print(f"  [!] skip id={it.get('id')} : {e}")

        insert_products(db, rows_products)
        insert_product_embeddings(db, rows_embs)
        total_inserted += len(rows_products)
        print(f"[PAGE {page}] vus={len(items)} gardés≤2ans={len(filtered)} insérés={len(rows_products)}")

    print(f"\n✅ RÉSUMÉ  vus={total_seen}  gardés≤2ans={total_kept}  insérés={total_inserted}")

if __name__ == "__main__":
    main()
