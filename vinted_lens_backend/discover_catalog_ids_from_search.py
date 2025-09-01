import os, sys, json
sys.path.append(os.path.dirname(__file__))
from integrations.vinted_client import VintedClient

def extract_catalog_id(item: dict) -> int | None:
    if isinstance(item.get("catalog_id"), int):
        return item["catalog_id"]
    if isinstance(item.get("category_id"), int):
        return item["category_id"]
    cat = item.get("category") or {}
    if isinstance(cat.get("id"), int):
        return cat["id"]
    return None

def main():
    client = VintedClient(base="https://www.vinted.fr", min_interval_s=0.9)

    search_text = "pull"
    data = client.search_items(query=search_text, page=1, per_page=20)
    items = data.get("items") or data.get("catalog_items") or []
    print(f"Items reçus: {len(items)}")
    if not items:
        return

    found = set()
    for it in items:
        cid = extract_catalog_id(it)
        if cid:
            found.add(cid)
    print("✅ catalog_ids détectés:", found)

    if found:
        cid = next(iter(found))
        params = {"catalog_ids": str(cid), "page": 1, "per_page": 20, "order": "newest_first"}
        data2 = client.search_by_params(params, referer_query=f"?catalog_ids={cid}")
        items2 = data2.get("items") or data2.get("catalog_items") or []
        print(f"Test avec catalog_ids={cid} → {len(items2)} articles")
        for it in items2[:5]:
            print("-", it.get("id"), "|", (it.get("title") or it.get("description")))

if __name__ == "__main__":
    main()
