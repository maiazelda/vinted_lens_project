from vinted import Vinted
import time
from typing import List, Dict, Optional

class VintedIntegration:
    def __init__(self):
        try:
            self.vinted_api = Vinted(domain='fr')
            self.api_available = True
            print("Service Vinted réel initialisé")
        except Exception as e:
            print(f"Erreur init Vinted API: {e}")
            self.api_available = False
    
    def search_products(self, query: str, limit: int = 20) -> Optional[List[Dict]]:
        """Recherche UNIQUEMENT avec vraie API Vinted - retourne None si indisponible"""
        if not self.api_available:
            print("API Vinted non disponible")
            return None
        
        try:
            print(f"Recherche Vinted réelle: '{query}'")
            raw_results = self.vinted_api.search(query)
            
            if not raw_results:
                print("Aucun résultat Vinted")
                return []
            
            # Formatage sécurisé
            formatted_results = []
            for i, item in enumerate(raw_results[:limit]):
                try:
                    formatted_item = {
                        'id': item.get('id', f"vinted_{i}"),
                        'title': item.get('title', ''),
                        'price': self._extract_price(item),
                        'platform': 'vinted',
                        'image_url': self._extract_image(item),
                        'category': self._map_category(item),
                        'color': item.get('color', ''),
                        'brand': self._extract_brand(item),
                        'size': self._extract_size(item),
                        'condition': item.get('status', ''),
                        'similarity': round(0.90 - (i * 0.02), 2)
                    }
                    formatted_results.append(formatted_item)
                except Exception as e:
                    print(f"Erreur formatage item {i}: {e}")
                    continue
            
            print(f"Vinted API: {len(formatted_results)} vrais produits")
            return formatted_results
            
        except Exception as e:
            print(f"Erreur API Vinted: {e}")
            return None
    
    # Méthodes d'extraction sécurisées...
    def _extract_price(self, item):
        try:
            price_data = item.get('price', {})
            if isinstance(price_data, dict):
                return float(price_data.get('amount', 0))
            return float(price_data) if price_data else 0.0
        except:
            return 0.0
    
    def _extract_image(self, item):
        try:
            photos = item.get('photos', [])
            if photos:
                return photos[0].get('full_size_url', photos[0].get('url', ''))
        except:
            pass
        return ''
    
    def _extract_brand(self, item):
        try:
            brand_data = item.get('brand', {})
            if isinstance(brand_data, dict):
                return brand_data.get('title', '')
            return str(brand_data) if brand_data else ''
        except:
            return ''
    
    def _extract_size(self, item):
        try:
            size_data = item.get('size', {})
            if isinstance(size_data, dict):
                return size_data.get('title', '')
            return str(size_data) if size_data else ''
        except:
            return ''
    
    def _map_category(self, item):
        try:
            category_data = item.get('category', {})
            if isinstance(category_data, dict):
                title = category_data.get('title', '').lower()
            else:
                title = str(category_data).lower()
            
            if any(word in title for word in ['t-shirt', 'top', 'pull']):
                return 'tops'
            elif any(word in title for word in ['jean', 'pantalon']):
                return 'bottoms'
            elif 'robe' in title:
                return 'dresses'
            elif 'chaussure' in title:
                return 'shoes'
        except:
            pass
        return 'other'