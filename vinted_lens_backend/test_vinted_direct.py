import sys
import traceback

def test_vinted_api():
    print("Test direct de l'API Vinted...")
    
    try:
        print("1. Import du wrapper...")
        from vinted import Vinted
        print("   Import OK")
        
        print("2. Initialisation...")
        vinted = Vinted(domain='fr')
        print("   Initialisation OK")
        
        print("3. Test de recherche...")
        results = vinted.search('t-shirt', limit=2)
        print(f"   Recherche OK - {len(results)} résultats")
        
        if results:
            print("4. Premier résultat:")
            first_result = results[0]
            print(f"   ID: {first_result.get('id')}")
            print(f"   Titre: {first_result.get('title')}")
            print(f"   Prix: {first_result.get('price')}")
            print(f"   Structure complète: {list(first_result.keys())}")
            
            return True
        else:
            print("   Aucun résultat retourné")
            return False
            
    except ImportError as e:
        print(f"Erreur d'import: {e}")
        return False
    except Exception as e:
        print(f"Erreur API: {e}")
        print(f"Type: {type(e).__name__}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_vinted_api()
    print(f"\nTest {'réussi' if success else 'échoué'}")