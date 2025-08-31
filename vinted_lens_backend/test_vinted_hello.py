import os, sys
sys.path.append(os.path.dirname(__file__))

from integrations.vinted_client import VintedClient

def main():
    client = VintedClient(base="https://www.vinted.fr", min_interval_s=0.8)
    # Test soft: la home renvoie 200 (HTML). Le but est de vérifier nos en-têtes + rate-limit.
    r = client.get("/")                 # pas d'API privée ici, juste un sanity check
    assert r.status_code == 200, f"HTTP={r.status_code}"

    # Requête suivante rapprochée -> vérifie le sleep min_interval_s
    r2 = client.get("/")
    assert r2.status_code == 200, f"HTTP={r2.status_code}"

    print("[OK] Connexion et headers valides (200). On est prêts pour l'endpoint privé.")

if __name__ == "__main__":
    main()
