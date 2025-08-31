import os, sys
sys.path.append(os.path.dirname(__file__))

from integrations.vinted_client import VintedClient

def main():
    client = VintedClient(base="https://www.vinted.fr")

    data = client.search_items(query="robe", page=1, per_page=5)
    items = data.get("items") or data.get("catalog_items") or []
    print(f"Reçus {len(items)} articles")
    if not items:
        print("Clés disponibles dans la réponse:", list(data.keys()))
    for it in items:
        # champs robustes: id, title, price (peuvent varier)
        pid = it.get("id")
        title = it.get("title") or it.get("description") or ""
        price = it.get("price") or it.get("price_numeric") or it.get("total_item_price") or ""
        print(f"- {pid} | {title} | {price}")

if __name__ == "__main__":
    main()
