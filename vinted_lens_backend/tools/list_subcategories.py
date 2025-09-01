import os, sys
sys.path.append(os.path.dirname(__file__) + "/..")
from integrations.vinted_client import VintedClient

PARENT_ID = 10  # Robes (tous types)

def child_catalogs(client: VintedClient, parent_id: int) -> list[tuple[int, str]]:
    js = client.faceted_categories(str(parent_id))
    print("[DEBUG] keys:", list(js.keys()))
    out: list[tuple[int, str]] = []

    # Vinted varie : on balaie les endroits plausibles
    for key in ("children", "items", "breadcrumbs"):
        arr = js.get(key) or []
        if isinstance(arr, list):
            for it in arr:
                if isinstance(it, dict):
                    cid = it.get("id")
                    title = it.get("title") or it.get("name")
                    if isinstance(cid, int) and title and cid != parent_id:
                        out.append((cid, title))

    # dédoublon + tri
    seen = set()
    uniq = []
    for cid, t in out:
        if cid not in seen:
            seen.add(cid)
            uniq.append((cid, t))
    return sorted(uniq, key=lambda x: x[1].lower())

def main():
    client = VintedClient(base="https://www.vinted.fr", min_interval_s=0.9)
    kids = child_catalogs(client, PARENT_ID)
    print(f"[PARENT {PARENT_ID}] {len(kids)} sous-catégories trouvées :")
    for cid, title in kids:
        print(f"- {cid}\t{title}")

if __name__ == "__main__":
    main()  