import asyncio
import requests
from PIL import Image
import io
import time
from datetime import datetime, timedelta
import numpy as np

# Imports locaux avec chemin corrigé
try:
    from database.clickhouse_setup import ClickHouseVectorDB
    CLICKHOUSE_AVAILABLE = True
except ImportError:
    print("ClickHouse non disponible")
    CLICKHOUSE_AVAILABLE = False
    
class ProductEmbeddingCollector:
    def __init__(self, clip_service=None, vector_db=None):
        self.clip_service = clip_service
        self.vector_db = vector_db
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Configuration collecte
        self.categories = {
            "femme": ["tops", "bottoms", "dresses", "shoes", "outerwear"],
            "homme": ["tops", "bottoms", "shoes", "outerwear"]
        }
        self.min_date = datetime.now() - timedelta(days=730)  # 2 ans
        
    def collect_products_batch(self, gender="femme", category="tops", limit=100):
        """Collecte un lot de produits avec leurs embeddings"""
        print(f"Collecte {gender}/{category}: {limit} produits...")
        
        collected_count = 0
        
        # Simulation de collecte avec données réalistes
        for i in range(limit):
            try:
                # Données produit simulées mais cohérentes
                product_data = self._generate_realistic_product(gender, category, i)
                
                # Générer embedding de l'image
                embedding = self._get_product_embedding(product_data['image_url'])
                if embedding is not None:
                    product_data['embedding'] = embedding
                    
                    # Stocker en base
                    product_id = self.vector_db.add_product(product_data)
                    if product_id:
                        collected_count += 1
                        if collected_count % 10 == 0:
                            print(f"  {collected_count}/{limit} produits traités...")
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Erreur produit {i}: {e}")
                continue
        
        print(f"✅ Collecte terminée: {collected_count} produits ajoutés")
        return collected_count
    
    def _generate_realistic_product(self, gender, category, index):
        """Génère des données produit réalistes"""
        brands = ["Zara", "H&M", "Uniqlo", "Nike", "Adidas", "Levi's", "Mango", "Bershka"]
        colors = ["noir", "blanc", "bleu", "rouge", "vert", "gris", "beige", "rose"]
        conditions = ["Neuf avec étiquettes", "Très bon état", "Bon état", "État satisfaisant"]
        
        # Génération déterministe basée sur l'index
        np.random.seed(index + hash(f"{gender}{category}"))
        
        brand = np.random.choice(brands)
        color = np.random.choice(colors)
        condition = np.random.choice(conditions)
        
        # Prix cohérents par catégorie
        price_ranges = {
            "tops": (8, 35),
            "bottoms": (15, 45), 
            "dresses": (12, 60),
            "shoes": (20, 80),
            "outerwear": (25, 100)
        }
        min_price, max_price = price_ranges.get(category, (10, 50))
        price = round(np.random.uniform(min_price, max_price), 2)
        
        # Tailles cohérentes par genre
        sizes = {
            "femme": ["XS", "S", "M", "L", "XL", "34", "36", "38", "40", "42"],
            "homme": ["S", "M", "L", "XL", "XXL", "38", "40", "42", "44"]
        }
        size = np.random.choice(sizes[gender])
        
        return {
            "title": f"{self._get_category_name(category)} {brand} {color} {gender}",
            "price": price,
            "platform": "vinted",
            "image_url": self._generate_image_url(brand, category, color),
            "category": category,
            "color": color,
            "brand": brand,
            "size": size,
            "condition": condition
        }
    
    def _get_category_name(self, category):
        names = {
            "tops": "T-shirt",
            "bottoms": "Jean",
            "dresses": "Robe",
            "shoes": "Baskets",
            "outerwear": "Veste"
        }
        return names.get(category, "Article")
    
    def _generate_image_url(self, brand, category, color):
        """URL d'image placeholder cohérente"""
        color_hex = {
            "noir": "333333", "blanc": "FFFFFF", "bleu": "0066CC",
            "rouge": "CC0000", "vert": "00CC00", "gris": "888888",
            "beige": "D2B48C", "rose": "FF69B4"
        }.get(color, "999999")
        
        return f"https://via.placeholder.com/400x500/{color_hex}/ffffff?text={brand}+{category}"
    
    def _get_product_embedding(self, image_url):
        """Génère embedding à partir d'URL image"""
        try:
            # Pour la simulation, on génère des embeddings cohérents
            # basés sur l'URL pour avoir des résultats reproductibles
            seed = hash(image_url) % 2147483647
            np.random.seed(seed)
            embedding = np.random.rand(512).astype(np.float32)
            
            # Normaliser l'embedding
            embedding = embedding / np.linalg.norm(embedding)
            
            # Simuler le temps de traitement CLIP
            time.sleep(0.05)
            
            return embedding
            
        except Exception as e:
            print(f"Erreur embedding: {e}")
            return None
    
    def collect_all_categories(self, products_per_category=50):
        """Collecte complète pour toutes les catégories"""
        total_collected = 0
        
        print("🚀 Début collecte massive d'embeddings...")
        start_time = time.time()
        
        for gender in self.categories:
            for category in self.categories[gender]:
                print(f"\n--- {gender.upper()} / {category.upper()} ---")
                collected = self.collect_products_batch(gender, category, products_per_category)
                total_collected += collected
        
        duration = time.time() - start_time
        print(f"\n✅ COLLECTE TERMINÉE")
        print(f"Total produits: {total_collected}")
        print(f"Temps total: {duration:.1f}s")
        print(f"Vitesse: {total_collected/duration:.1f} produits/seconde")
        
        return total_collected

# Script de lancement
if __name__ == "__main__":
    from models.clip_model import CLIPService
    from database.clickhouse_setup import ClickHouseVectorDB
    
    print("Initialisation du collecteur...")
    clip_service = CLIPService()
    vector_db = ClickHouseVectorDB()
    
    collector = ProductEmbeddingCollector(clip_service, vector_db)
    
    # Lancer collecte test
    total = collector.collect_all_categories(products_per_category=20)
    
    # Vérifier les stats finales
    stats = vector_db.get_stats()
    print(f"\nBase finale: {stats['total_products']} produits")