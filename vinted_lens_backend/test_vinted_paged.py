import os, sys, time
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.dirname(__file__))
from integrations.vinted_client import VintedClient

# --- helpers robustes sur les champs de date ---
def get_epoch_s(it: dict) -> int | None:
    """
    Essaie plusieurs champs vus dans les réponses Vinted.
    Retourne un timestamp (secondes) ou None.
    """
    for k in ("created_at_ts", "updated_at_ts", "photo_highlighted_at_ts"):
        v = it.get(k)
        if isinstance(v, (int, float)) and v > 0:
            return int(v)
    # parfois c'est une ISO8601; on tente un parse simple
    for k in ("created_at", "updated_at"):
        v = it.get(k)
        if isinstance(v, str) and len(v) >= 10:
            try:
                # ex. "2025-08-31T09:31:22+00:00" ou "2025-08-31 09:31:22 UTC"
                dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
                return int(dt.timestamp())
            except Exception:
                pass
    return None

def main():
    client = VintedClient(base="https://www.vinted.fr", min_interval_s=0.9)

    query = "robe"  # on testera ensuite sans query en scannant des catalog_ids
    per_page = 40
    max_pages = 5   # on garde petit pour le test
    since_dt = datetime.now(timezone.utc) - timedelta(days=730)  # 2 ans
    since_epoch = int(since_dt.timestamp())

    total_seen = 0
    total_kept = 0
    kept_examples = []

    for page in range(1, max_pages + 1):
        data = client.search_items(query=query, page=page, per_page=per_page)
        items = data.get("items") or data.get("catalog_items") or []
        if not items:
            print(f"[PAGE {page}] 0 item -> stop.")
            break

        total_seen += len(items)
        for it in items:
            ts = get_epoch_s(it)
            if ts is None or ts >= since_epoch:
                total_kept += 1
                if len(kept_examples) < 5:
                    kept_examples.append({
                        "id": it.get("id"),
                        "title": it.get("title") or it.get("description"),
                        "price": it.get("price") or it.get("price_numeric"),
                        "ts": ts
                    })

        print(f"[PAGE {page}] reçus={len(items)} | cumul vus={total_seen} | cumul gardés≤2ans={total_kept}")
        # petite pause déjà gérée par client (rate limit)

    print("\n✅ RÉSUMÉ")
    print(f"Vus: {total_seen} | Gardés (≤ 2 ans ou date inconnue): {total_kept}")
    print("Exemples:")
    for ex in kept_examples:
        print(" -", ex)

if __name__ == "__main__":
    main()
