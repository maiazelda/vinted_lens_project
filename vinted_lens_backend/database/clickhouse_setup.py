import requests
import json
import numpy as np
from typing import List, Dict, Optional
import time

class ClickHouseVectorDB:
    def __init__(self, host="http://localhost:8123", database="vinted_lens"):
        self.host = host
        self.database = database
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
        
    def execute_query(self, query: str, params: List = None):
        """Exécute une requête ClickHouse"""
        try:
            url = f"{self.host}/?database={self.database}"
            if params:
                # Pour les requêtes avec paramètres
                response = self.session.post(url, data=query, params={'param_' + str(i): p for i, p in enumerate(params)})
            else:
                response = self.session.post(url, data=query)
            
            response.raise_for_status()
            return response.text.strip()
        except Exception as e:
            print(f"❌ Erreur requête: {e}")
            return None
    
    def init_database(self):
        """Initialise la base et les tables"""
        print("🚀 Initialisation ClickHouse...")
        
        # 1. Créer la base de données
        create_db = f"CREATE DATABASE IF NOT EXISTS {self.database}"
        result = self.execute_query(create_db)
        print("✅ Base de données créée")
        
        # 2. Créer la table principale des produits
        create_table = f"""
        CREATE TABLE IF NOT EXISTS {self.database}.products (
            id UInt64,
            title String,
            price Float32,
            platform String,
            image_url String,
            embedding Array(Float32),
            category String,
            color String,
            brand String,
            size String,
            condition String,
            created_at DateTime DEFAULT now(),
            updated_at DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY (platform, category, id)
        PARTITION BY platform
        SETTINGS index_granularity = 8192
        """
        
        result = self.execute_query(create_table)
        print("✅ Table products créée")
        
        # 3. Créer index pour recherche rapide
        create_index = f"""
        CREATE TABLE IF NOT EXISTS {self.database}.product_embeddings (
            product_id UInt64,
            embedding Array(Float32),
            norm Float32
        ) ENGINE = MergeTree()
        ORDER BY product_id
        SETTINGS index_granularity = 1024
        """
        
        result = self.execute_query(create_index)
        print("✅ Table embeddings créée")
        
        return True
    
    def add_product(self, product_data: Dict):
        """Ajoute un produit avec son embedding"""
        try:
            # Générer ID unique basé sur timestamp
            product_id = int(time.time() * 1000000) + np.random.randint(0, 1000)
            
            # Calculer la norme de l'embedding pour optimiser la recherche
            embedding = product_data['embedding']
            if isinstance(embedding, np.ndarray):
                embedding = embedding.tolist()
            
            norm = float(np.linalg.norm(embedding))
            
            # Insérer dans la table principale
            insert_product = f"""
            INSERT INTO {self.database}.products 
            (id, title, price, platform, image_url, embedding, category, color, brand, size, condition)
            VALUES 
            ({product_id}, '{product_data.get('title', '').replace("'", "''")}', 
             {product_data.get('price', 0)}, '{product_data.get('platform', '')}',
             '{product_data.get('image_url', '')}', {embedding},
             '{product_data.get('category', '')}', '{product_data.get('color', '')}',
             '{product_data.get('brand', '')}', '{product_data.get('size', '')}',
             '{product_data.get('condition', '')}')
            """
            
            result1 = self.execute_query(insert_product)
            
            # Insérer dans la table des embeddings
            insert_embedding = f"""
            INSERT INTO {self.database}.product_embeddings 
            (product_id, embedding, norm)
            VALUES ({product_id}, {embedding}, {norm})
            """
            
            result2 = self.execute_query(insert_embedding)
            
            return product_id
        except Exception as e:
            print(f"❌ Erreur ajout produit: {e}")
            return None
    
    def search_similar(self, query_embedding: np.ndarray, limit: int = 10, 
                      platform_filter: Optional[str] = None, 
                      category_filter: Optional[str] = None):
        """Recherche par similarité cosinus optimisée"""
        try:
            start_time = time.time()
            
            # Convertir embedding en liste
            if isinstance(query_embedding, np.ndarray):
                query_embedding = query_embedding.tolist()
            
            query_norm = float(np.linalg.norm(query_embedding))
            
            # Construire les filtres
            filters = []
            if platform_filter:
                filters.append(f"p.platform = '{platform_filter}'")
            if category_filter:
                filters.append(f"p.category = '{category_filter}'")
            
            where_clause = " AND " + " AND ".join(filters) if filters else ""
            
            # Requête optimisée avec similarité cosinus
            search_query = f"""
            SELECT 
                p.id,
                p.title,
                p.price,
                p.platform,
                p.image_url,
                p.category,
                p.color,
                p.brand,
                p.size,
                p.condition,
                dotProduct(e.embedding, {query_embedding}) / (e.norm * {query_norm}) as similarity
            FROM {self.database}.products p
            JOIN {self.database}.product_embeddings e ON p.id = e.product_id
            WHERE e.norm > 0 {where_clause}
            ORDER BY similarity DESC
            LIMIT {limit}
            """
            
            result = self.execute_query(search_query)
            
            if not result:
                return []
            
            # Parser les résultats
            lines = result.strip().split('\n')
            products = []
            
            for line in lines:
                if line:
                    parts = line.split('\t')
                    if len(parts) >= 11:
                        products.append({
                            'id': int(parts[0]),
                            'title': parts[1],
                            'price': float(parts[2]),
                            'platform': parts[3],
                            'image_url': parts[4],
                            'category': parts[5],
                            'color': parts[6],
                            'brand': parts[7],
                            'size': parts[8],
                            'condition': parts[9],
                            'similarity': float(parts[10])
                        })
            
            search_time = time.time() - start_time
            print(f"🔍 Recherche ClickHouse: {len(products)} résultats en {search_time:.3f}s")
            
            return products
            
        except Exception as e:
            print(f"❌ Erreur recherche: {e}")
            return []
        
    def get_stats(self):
        """Statistiques de la base"""
        try:
            stats_query = f"""
            SELECT 
                platform,
                category,
                count() as count
            FROM {self.database}.products 
            GROUP BY platform, category
            ORDER BY count DESC
            """
            
            result = self.execute_query(stats_query)
            
            total_query = f"SELECT count() FROM {self.database}.products"
            total_result = self.execute_query(total_query)
            
            return {
                'total_products': int(total_result) if total_result else 0,
                'details': result
            }
        except Exception as e:
            print(f"❌ Erreur stats: {e}")
            return {'total_products': 0, 'details': ''}

# Script de test
if __name__ == "__main__":
    print("🚀 Configuration ClickHouse pour Vinted Lens...")
    
    # Initialiser la base
    db = ClickHouseVectorDB()
    
    # Créer les tables
    if db.init_database():
        print("✅ Base initialisée")
        
        # Ajouter des produits d'exemple
        
        # Afficher stats
        stats = db.get_stats()
        print(f"📊 Total produits: {stats['total_products']}")
        
        # Test de recherche
        print("\n🔍 Test de recherche...")
        test_embedding = np.random.rand(512).astype(np.float32)
        results = db.search_similar(test_embedding, limit=3)
        
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['title']} - {result['platform']} - Similarité: {result['similarity']:.3f}")
        
        print("✅ ClickHouse opérationnel !")
    else:
        print("❌ Erreur initialisation")