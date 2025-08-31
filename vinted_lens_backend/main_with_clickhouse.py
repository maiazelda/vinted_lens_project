from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
from models.clip_model import CLIPService
from database.clickhouse_setup import ClickHouseVectorDB
import time
import io
from PIL import Image

# Initialisation
app = FastAPI(title="Vinted Lens API", version="2.0.0")
clip_service = CLIPService()
vector_db = ClickHouseVectorDB()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage"""
    print("🚀 Démarrage Vinted Lens API v2.0...")
    
    # Vérifier que ClickHouse fonctionne
    try:
        stats = vector_db.get_stats()
        print(f"✅ ClickHouse connecté - {stats['total_products']} produits en base")
        
        # Si pas de produits, ajouter des exemples
        if stats['total_products'] == 0:
            print("📦 Base vide, ajout de produits d'exemple...")
            vector_db.add_sample_products()
            
    except Exception as e:
        print(f"⚠️ ClickHouse non disponible: {e}")
        print("📝 L'API fonctionnera en mode dégradé")

@app.get("/health")
async def health_check():
    """Vérification santé API"""
    try:
        stats = vector_db.get_stats()
        return {
            "status": "healthy",
            "clip_model_loaded": clip_service.model is not None,
            "database_connected": True,
            "products_count": stats['total_products'],
            "timestamp": time.time()
        }
    except:
        return {
            "status": "degraded",
            "clip_model_loaded": clip_service.model is not None,
            "database_connected": False,
            "products_count": 0,
            "timestamp": time.time()
        }

@app.post("/api/search-similar")
async def search_similar_products(file: UploadFile = File(...)):
    """Recherche de produits similaires avec ClickHouse"""
    start_time = time.time()
    
    try:
        # Validation fichier
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Le fichier doit être une image")
        
        # Lire l'image
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        
        # Générer embedding avec CLIP
        embedding_time = time.time()
        embedding = clip_service.encode_image(image)
        embedding_duration = time.time() - embedding_time
        
        # Recherche dans ClickHouse
        search_time = time.time()
        try:
            similar_products = vector_db.search_similar(
                embedding, 
                limit=12,
                platform_filter=None  # Rechercher sur toutes les plateformes
            )
            search_duration = time.time() - search_time
            database_used = "clickhouse"
            
        except Exception as db_error:
            print(f"⚠️ Erreur ClickHouse: {db_error}")
            print("🔄 Fallback vers résultats simulés...")
            
            # Fallback : résultats simulés si ClickHouse indisponible
            similar_products = generate_fallback_results()
            search_duration = 0.050
            database_used = "fallback"
        
        total_duration = time.time() - start_time
        
        # Statistiques de performance
        performance_stats = {
            "total_time": round(total_duration, 3),
            "embedding_time": round(embedding_duration, 3),
            "search_time": round(search_duration, 3),
            "database_used": database_used,
            "results_count": len(similar_products)
        }
        
        return {
            "success": True,
            "results": similar_products,
            "performance": performance_stats,
            "query_id": f"query_{int(time.time())}"
        }
        
    except Exception as e:
        print(f"❌ Erreur API: {e}")
        return {
            "success": False,
            "error": str(e),
            "results": [],
            "performance": {
                "total_time": round(time.time() - start_time, 3),
                "error": True
            }
        }

def generate_fallback_results():
    """Résultats simulés en cas de problème ClickHouse"""
    return [
        {
            "id": 1,
            "title": "T-shirt vintage rouge (Simulé)",
            "price": 15.50,
            "platform": "vinted",
            "image_url": "https://via.placeholder.com/300x400/ff0000/ffffff?text=T-shirt+Rouge",
            "category": "tops",
            "color": "red",
            "similarity": 0.95
        },
        {
            "id": 2,
            "title": "Jean skinny bleu (Simulé)",
            "price": 25.00,
            "platform": "vinted",
            "image_url": "https://via.placeholder.com/300x400/0066cc/ffffff?text=Jean+Bleu",
            "category": "bottoms",
            "color": "blue",
            "similarity": 0.87
        },
        {
            "id": 3,
            "title": "Robe fleurie été (Simulé)",
            "price": 35.99,
            "platform": "amazon",
            "image_url": "https://via.placeholder.com/300x400/ff69b4/ffffff?text=Robe+Fleurie",
            "category": "dresses",
            "color": "multicolor",
            "similarity": 0.82
        }
    ]

@app.get("/api/stats")
async def get_database_stats():
    """Statistiques de la base de données"""
    try:
        stats = vector_db.get_stats()
        return {
            "success": True,
            "stats": stats,
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": time.time()
        }

@app.post("/api/add-product")
async def add_product_manually():
    """Endpoint pour ajouter des produits manuellement (développement)"""
    try:
        added = vector_db.add_sample_products()
        return {
            "success": True,
            "message": f"{added} produits ajoutés",
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": time.time()
        }

if __name__ == "__main__":
    import uvicorn
    print("🔥 Lancement Vinted Lens API avec ClickHouse...")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)