import sys
import os
import numpy as np
import time

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    from database.clickhouse_setup import ClickHouseVectorDB
    DB_AVAILABLE = True
except Exception as e:
    print(f"ClickHouse non disponible: {e}")
    DB_AVAILABLE = False

class RobustProductCollector:
    def __init__(self):
        if DB_AVAILABLE:
            self.vector_db = ClickHouseVectorDB()
        else:
            self.vector_db = None
    
    def generate_products_robust(self, count=50):
        """Version robuste avec gestion d'erreur améliorée"""
        if not self.vector_db:
            print("Pas de base de données disponible")
            return 0
        
        print(f"Génération robuste de {count} produits...")
        
        added_count = 0
        error_count = 0
        
        for i in range(count):
            try:
                # Données simplifiées pour éviter erreurs SQL
                np.random.seed(i + 1000)  # Seed différent pour éviter doublons
                
                brands = ["Zara", "H&M", "Nike", "Adidas"]
                colors = ["noir", "blanc", "bleu", "rouge"]
                categories = ["tops", "bottoms", "shoes"]
                
                brand = np.random.choice(brands)
                color = np.random.choice(colors)
                category = np.random.choice(categories)
                
                # Prix simple
                price = round(np.random.uniform(10, 50), 2)
                
                # Embedding normalisé
                embedding = np.random.rand(512).astype(np.float32)
                embedding = embedding / np.linalg.norm(embedding)
                
                product_data = {
                    "title": f"{brand} {color} {category}",  # Titre simplifié
                    "price": price,
                    "platform": "batch",
                    "image_url": f"https://example.com/{i}.jpg",
                    "embedding": embedding,
                    "category": category,
                    "color": color,
                    "brand": brand,
                    "size": "M",
                    "condition": "bon"  # Condition simplifiée
                }
                
                product_id = self.vector_db.add_product(product_data)
                if product_id:
                    added_count += 1
                    if added_count % 25 == 0:
                        print(f"  {added_count}/{count} produits OK")
                else:
                    error_count += 1
                
                # Pause pour éviter surcharge ClickHouse
                time.sleep(0.05)
                
            except Exception as e:
                error_count += 1
                if error_count % 10 == 0:
                    print(f"  Erreurs: {error_count}")
                continue
        
        print(f"Terminé: {added_count} ajoutés, {error_count} erreurs")
        return added_count

if __name__ == "__main__":
    collector = RobustProductCollector()
    if DB_AVAILABLE:
        # Stats avant
        stats_before = collector.vector_db.get_stats()
        print(f"Avant: {stats_before['total_products']} produits")
        
        # Collection
        added = collector.generate_products_robust(200)
        
        # Stats après
        stats_after = collector.vector_db.get_stats()
        print(f"Après: {stats_after['total_products']} produits")
        print(f"Gain: +{added} produits")