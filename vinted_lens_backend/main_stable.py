from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import numpy as np
import io
import time

# Tentative d'import ClickHouse (optionnel)
try:
    from database.clickhouse_setup import ClickHouseVectorDB
    CLICKHOUSE_AVAILABLE = True
except ImportError:
    CLICKHOUSE_AVAILABLE = False
    print("ClickHouse non disponible, utilisation du fallback")

# Configuration CLIP
MODEL_NAME = "openai/clip-vit-base-patch32"

class CLIPService:
    def __init__(self):
        print("Chargement du modèle CLIP...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = CLIPModel.from_pretrained(MODEL_NAME)
        self.processor = CLIPProcessor.from_pretrained(MODEL_NAME)
        self.model.to(self.device)
        print(f"Modèle CLIP chargé sur {self.device}")
    
    def encode_image(self, image):
        try:
            inputs = self.processor(images=image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
            return image_features.cpu().numpy().flatten()
        except Exception as e:
            print(f"Erreur encoding image: {e}")
            return np.random.rand(512).astype(np.float32)

# Initialisation
app = FastAPI(title="Vinted Lens API", version="2.0.0")

# Variables globales
clip_service = None
vector_db = None

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialisation des services (sans @app.on_event)
def init_services():
    global clip_service, vector_db
    
    print("Initialisation des services...")
    
    # CLIP
    try:
        clip_service = CLIPService()
        print("CLIP Service initialisé")
    except Exception as e:
        print(f"Erreur CLIP: {e}")
    
    # ClickHouse
    if CLICKHOUSE_AVAILABLE:
        try:
            vector_db = ClickHouseVectorDB()
            stats = vector_db.get_stats()
            print(f"ClickHouse connecté - {stats['total_products']} produits")
            
            if stats['total_products'] == 0:
                print("Ajout de produits d'exemple...")
                vector_db.add_sample_products()
                
        except Exception as e:
            print(f"ClickHouse indisponible: {e}")
            vector_db = None

# Initialiser au chargement du module
init_services()

@app.get("/health")
async def health_check():
    try:
        db_stats = vector_db.get_stats() if vector_db else {"total_products": 0}
        return {
            "status": "healthy",
            "clip_loaded": clip_service is not None,
            "database_connected": vector_db is not None,
            "products_count": db_stats.get('total_products', 0),
            "clickhouse_available": CLICKHOUSE_AVAILABLE,
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
    start_time = time.time()
    
    if not clip_service:
        raise HTTPException(status_code=503, detail="Service CLIP non disponible")
    
    try:
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Le fichier doit être une image")
        
        # Traitement image
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        
        # Embedding
        embedding_start = time.time()
        embedding = clip_service.encode_image(image)
        embedding_time = time.time() - embedding_start
        
        # Recherche
        search_start = time.time()
        if vector_db and CLICKHOUSE_AVAILABLE:
            try:
                results = vector_db.search_similar(embedding, limit=10)
                database_used = "clickhouse"
                print(f"ClickHouse: {len(results)} résultats")
            except Exception as db_error:
                print(f"Erreur ClickHouse: {db_error}")
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
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "results": get_fallback_results(),
            "performance": {
                "total_time": round(time.time() - start_time, 3),
                "error": True
            }
        }

def get_fallback_results():
    return [
        {
            "id": 1,
            "title": "T-shirt vintage rouge",
            "price": 15.50,
            "platform": "vinted",
            "image_url": "https://via.placeholder.com/300x400/ff4444/ffffff?text=T-shirt",
            "category": "tops",
            "color": "red",
            "similarity": 0.95
        },
        {
            "id": 2,
            "title": "Jean skinny bleu",
            "price": 25.00,
            "platform": "vinted",
            "image_url": "https://via.placeholder.com/300x400/4444ff/ffffff?text=Jean",
            "category": "bottoms",
            "color": "blue",
            "similarity": 0.87
        }
    ]

@app.get("/api/stats")
async def get_stats():
    if not vector_db:
        return {"error": "Base de données non connectée"}
    
    try:
        stats = vector_db.get_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    # Version stable sans reload
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)