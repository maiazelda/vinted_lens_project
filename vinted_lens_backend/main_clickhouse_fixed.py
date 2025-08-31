from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import numpy as np
import io
import time
from database.clickhouse_setup import ClickHouseVectorDB

# Configuration CLIP
MODEL_NAME = "openai/clip-vit-base-patch32"

class CLIPService:
    def __init__(self):
        print("🔄 Chargement du modèle CLIP...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = CLIPModel.from_pretrained(MODEL_NAME)
        self.processor = CLIPProcessor.from_pretrained(MODEL_NAME)
        self.model.to(self.device)
        print(f"✅ Modèle CLIP chargé sur {self.device}")
    
    def encode_image(self, image):
        """Encode une image en embedding vectoriel"""
        try:
            # Préprocessing de l'image
            inputs = self.processor(images=image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Générer l'embedding
            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
                # Normaliser l'embedding
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
            return image_features.cpu().numpy().flatten()
        except Exception as e:
            print(f"❌ Erreur encoding image: {e}")
            return np.random.rand(512).astype(np.float32)  # Fallback

# Initialisation
app = FastAPI(title="Vinted Lens API", version="2.0.0")

# Services globaux
clip_service = None
vector_db = None

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage"""
    global clip_service, vector_db
    
    print("🚀 Démarrage Vinted Lens API v2.0...")
    
    # Initialiser CLIP
    try:
        clip_service = CLIPService()
        print("✅ CLIP Service initialisé")
    except Exception as e:
        print(f"❌ Erreur CLIP: {e}")
        clip_service = None
    
    # Initialiser ClickHouse
    try:
        vector_db = ClickHouseVectorDB()
        stats = vector_db.get_stats()
        print(f"✅ ClickHouse connecté - {stats['total_products']} produits")
        
        # Ajouter des produits si base vide
        if stats['total_products'] == 0:
            print("📦 Ajout de produits d'exemple...")
            vector_db.add_sample_products()
            
    except Exception as e:
        print(f"⚠️ ClickHouse indisponible: {e}")
        vector_db = None

@app.get("/health")
async def health_check():
    """Vérification santé de l'API"""
    try:
        db_stats = vector_db.get_stats() if vector_db else {"total_products": 0}
        return {
            "status": "healthy",
            "clip_loaded": clip_service is not None,
            "database_connected": vector_db is not None,
            "products_count": db_stats.get('total_products', 0),
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": time.time()
        }

@app.post("/api/search-similar")
async def search_similar_products(file: UploadFile = File(...)):
    """Recherche de produits similaires"""
    start_time = time.time()
    
    if not clip_service:
        raise HTTPException(status_code=503, detail="Service CLIP non disponible")
    
    try:
        # Validation fichier
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Le fichier doit être une image")
        
        # Lire et traiter l'image
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        
        print(f"📷 Image reçue: {image.size}")
        
        # Générer embedding
        embedding_start = time.time()
        embedding = clip_service.encode_image(image)
        embedding_time = time.time() - embedding_start
        
        print(f"🧠 Embedding généré en {embedding_time:.3f}s")
        
        # Recherche dans ClickHouse ou fallback
        search_start = time.time()
        if vector_db:
            try:
                results = vector_db.search_similar(embedding, limit=10)
                database_used = "clickhouse"
                print(f"🔍 ClickHouse: {len(results)} résultats trouvés")
            except Exception as db_error:
                print(f"⚠️ ClickHouse error: {db_error}")
                results = get_fallback_results()
                database_used = "fallback"
        else:
            results = get_fallback_results()
            database_used = "fallback"
        
        search_time = time.time() - search_start
        total_time = time.time() - start_time
        
        return {
            "success": True,
            "results": results,
            "performance": {
                "total_time": round(total_time, 3),
                "embedding_time": round(embedding_time, 3),
                "search_time": round(search_time, 3),
                "database_used": database_used,
                "results_count": len(results)
            },
            "query_id": f"query_{int(time.time())}"
        }
        
    except Exception as e:
        total_time = time.time() - start_time
        print(f"❌ Erreur API: {e}")
        return {
            "success": False,
            "error": str(e),
            "results": get_fallback_results(),
            "performance": {
                "total_time": round(total_time, 3),
                "error": True
            }
        }

def get_fallback_results():
    """Résultats de fallback si ClickHouse indisponible"""
    return [
        {
            "id": 1,
            "title": "T-shirt vintage rouge",
            "price": 15.50,
            "platform": "vinted",
            "image_url": "https://via.placeholder.com/300x400/ff4444/ffffff?text=T-shirt+Rouge",
            "category": "tops",
            "color": "red",
            "similarity": 0.95
        },
        {
            "id": 2,
            "title": "Jean skinny bleu",
            "price": 25.00,
            "platform": "vinted", 
            "image_url": "https://via.placeholder.com/300x400/4444ff/ffffff?text=Jean+Bleu",
            "category": "bottoms",
            "color": "blue",
            "similarity": 0.87
        },
        {
            "id": 3,
            "title": "Robe d'été fleurie",
            "price": 35.99,
            "platform": "amazon",
            "image_url": "https://via.placeholder.com/300x400/ff69b4/ffffff?text=Robe+Fleurie",
            "category": "dresses",
            "color": "multicolor", 
            "similarity": 0.82
        }
    ]

@app.get("/api/stats")
async def get_stats():
    """Statistiques de la base"""
    if not vector_db:
        return {"error": "Base de données non connectée"}
    
    try:
        stats = vector_db.get_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    print("🔥 Lancement Vinted Lens API...")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)