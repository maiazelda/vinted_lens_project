import os, sys, io
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List

sys.path.append(os.path.dirname(__file__) + "/..")

import requests
from PIL import Image
import numpy as np
from clickhouse_driver import Client

from integrations.vinted_client import VintedClient
from models.clip_model import CLIPService

CLICKHOUSE_HOST = "localhost"
CLICKHOUSE_DB   = "vinted_lens"

# ---------- ClickHouse ----------
def ch() -> Client:
    return Client(host=CLICKHOUSE_HOST, database=CLICKHOUSE_DB)

# ---------- Helpers champs Vinted ----------
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
    return (it.get("status") or it.get("condition") or {}).get("title", "") if isinstance(it.get("condition"), dict) else (it.get("condition") or "")

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

# ---------- Image -> Embedding ----------
def download_image(url: str, session: Optional[requests.Session] = None) -> Image.Image:
    sess = session or requests.Session()
    headers = {"Referer": "https://www.vinted.fr/catalog"}
    r = sess.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGB")

def encode_image(url: str, clip: CLIPService, session: Optional[requests.Session] = None) -> List[float]:
    img = download_image(url, session=session)
    vec = clip.encode_image_pil(img)  # attendu: 512 floats
    v = np.asarray(vec, dtype=np.float32)
    # normalisation L2 pour que dot ≃ cosinus
    n = np.linalg.norm(v)
    if v.shape != (512,):
        raise RuntimeError(f"Embedding shape {v.shape}, attendu (512,)")
    if not np.isfinite(n) or n == 0:
        raise RuntimeError("Norme embedding invalide")
    v = (v / n).astype(np.float32)
    return v.tolist()

# ---------- Inserts alignés sur TON schéma ----------
def insert_products(db: Client, rows: List[tuple]):
    db.execute("""
        INSERT INTO vinted_lens.products
        (id, title, price, platform, image_url, embedding, category, color, brand, size, condition, created_at, updated_at)
        VALUES
    """, rows)

def insert_product_embeddings(db: Client, rows: List[tuple]):
    db.execute("""
        INSERT INTO vinted_lens.product_embeddings
        (product_id, embedding, norm)
        VALUES
    """, rows)

def main():
    client = VintedClient(base="https://www.vinted.fr", min_interval_s=0.9)
    clip   = CLIPService()
    db     = ch()

    # 1) on prend 1 page (robe), on gardera le 1er item pour test
    data = client.search_by_params(params, referer_query=f"?catalog_ids={CATALOG_ID}") or {}
    items = data.get("items") or data.get("catalog_items") or []
    assert items, "Aucun item"
    it = items[0]

    pid = int(it["id"])
    title = it.get("title") or it.get("description") or ""
    price = pick_price(it)
    platform = "vinted"
    image_url = pick_image_url(it)
    assert image_url, "image_url introuvable"

    category = pick_category(it)
    color = (it.get("colour") or it.get("color") or "")
    brand = pick_brand(it)
    size = pick_size(it)
    condition = pick_condition(it)
    created_at, updated_at = pick_created_updated(it)

    # 2) embedding
    emb = encode_image(image_url, clip, session=requests.Session())  # 512 floats normalisés
    norm = float(np.linalg.norm(np.asarray(emb, dtype=np.float32)))  # ~1.0 (après normalisation, par sécurité)

    # 3) counts avant
    before_p = db.execute("SELECT count() FROM vinted_lens.products")[0][0]
    before_e = db.execute("SELECT count() FROM vinted_lens.product_embeddings")[0][0]
    print(f"[BEFORE] products={before_p} embeddings={before_e}")

    # 4) insert dans TES colonnes
    insert_products(db, [(
        pid, title, float(price), platform, image_url, emb, category, str(color), brand, size, condition, created_at, updated_at
    )])
    insert_product_embeddings(db, [(
        pid, emb, norm
    )])

    # 5) counts après
    after_p = db.execute("SELECT count() FROM vinted_lens.products")[0][0]
    after_e = db.execute("SELECT count() FROM vinted_lens.product_embeddings")[0][0]
    print(f"[AFTER ] products={after_p} embeddings={after_e}")
    print(f"[DELTA ] +products={after_p - before_p}  +embeddings={after_e - before_e}")
    print(f"[OK] id={pid}  title={title[:60]!r}")

if __name__ == "__main__":
    main()
