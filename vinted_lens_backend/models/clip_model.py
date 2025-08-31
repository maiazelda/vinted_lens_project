# models/clip_model.py
# Service CLIP principal pour Vinted Lens

import torch
from transformers import CLIPProcessor, CLIPModel
import numpy as np
from PIL import Image
import io
import time
from typing import Union, List, Optional
import logging

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VintedLensCLIP:
    """
    Service CLIP optimisé pour Vinted Lens
    Gère l'encoding d'images en embeddings vectoriels
    """
    
    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        self.model_name = model_name
        self.model = None
        self.processor = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.is_loaded = False
        
        logger.info(f"🤖 VintedLensCLIP initialisé - Device: {self.device}")
    
    def load_model(self) -> bool:
        """Charge le modèle CLIP en mémoire"""
        if self.is_loaded:
            logger.info("✅ Modèle déjà chargé")
            return True
        
        try:
            start_time = time.time()
            logger.info(f"📥 Chargement {self.model_name}...")
            
            # Chargement modèle et processor
            self.model = CLIPModel.from_pretrained(self.model_name)
            self.processor = CLIPProcessor.from_pretrained(self.model_name)
            self.model.to(self.device)
            
            # Mode évaluation (pas d'entraînement)
            self.model.eval()
            
            load_time = time.time() - start_time
            self.is_loaded = True
            
            logger.info(f"✅ Modèle chargé en {load_time:.2f}s sur {self.device}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur chargement modèle: {e}")
            return False
    
    def encode_image(self, image: Union[Image.Image, bytes, io.BytesIO]) -> Optional[np.ndarray]:
        """
        Encode une image en embedding vectoriel
        
        Args:
            image: Image PIL, bytes, ou BytesIO
            
        Returns:
            np.ndarray: Embedding normalisé (512 dimensions) ou None si erreur
        """
        if not self.is_loaded:
            if not self.load_model():
                return None
        
        try:
            start_time = time.time()
            
            # Conversion vers PIL si nécessaire
            if isinstance(image, (bytes, io.BytesIO)):
                if isinstance(image, bytes):
                    image = io.BytesIO(image)
                image = Image.open(image)
            
            # Conversion RGB si nécessaire
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Traitement CLIP
            inputs = self.processor(images=image, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
                # Normalisation L2 pour similarité cosinus
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
            embedding = image_features.cpu().numpy().flatten()
            encode_time = time.time() - start_time
            
            logger.info(f"⚡ Embedding généré en {encode_time:.3f}s - Shape: {embedding.shape}")
            
            return embedding
            
        except Exception as e:
            logger.error(f"❌ Erreur encoding image: {e}")
            return None
    
    def encode_text(self, texts: Union[str, List[str]]) -> Optional[np.ndarray]:
        """
        Encode du texte en embedding vectoriel
        
        Args:
            texts: Texte ou liste de textes
            
        Returns:
            np.ndarray: Embeddings normalisés ou None si erreur
        """
        if not self.is_loaded:
            if not self.load_model():
                return None
        
        try:
            if isinstance(texts, str):
                texts = [texts]
            
            # Traitement CLIP
            inputs = self.processor(text=texts, return_tensors="pt", padding=True).to(self.device)
            
            with torch.no_grad():
                text_features = self.model.get_text_features(**inputs)
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            
            embeddings = text_features.cpu().numpy()
            
            logger.info(f"📝 {len(texts)} texte(s) encodé(s) - Shape: {embeddings.shape}")
            
            return embeddings if len(texts) > 1 else embeddings.flatten()
            
        except Exception as e:
            logger.error(f"❌ Erreur encoding texte: {e}")
            return None
    
    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calcule la similarité cosinus entre deux embeddings"""
        return float(np.dot(embedding1, embedding2))
    
    def batch_similarity(self, query_embedding: np.ndarray, embeddings: np.ndarray) -> np.ndarray:
        """
        Calcule la similarité entre un embedding de requête et un batch d'embeddings
        
        Args:
            query_embedding: Embedding de la requête (512,)
            embeddings: Batch d'embeddings (N, 512)
            
        Returns:
            np.ndarray: Scores de similarité (N,)
        """
        return np.dot(embeddings, query_embedding)
    
    def get_model_info(self) -> dict:
        """Retourne les informations du modèle"""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "is_loaded": self.is_loaded,
            "embedding_dim": 512,  # CLIP ViT-B/32
            "input_resolution": 224
        }

# Instance globale (Singleton pattern pour FastAPI)
_clip_service = None

def get_clip_service() -> VintedLensCLIP:
    """Retourne l'instance globale du service CLIP"""
    global _clip_service
    if _clip_service is None:
        _clip_service = VintedLensCLIP()
    return _clip_service

# Test du service
if __name__ == "__main__":
    # Test rapide du service
    clip = VintedLensCLIP()
    
    if clip.load_model():
        print("✅ Service CLIP opérationnel")
        info = clip.get_model_info()
        print(f"📊 Info: {info}")
    else:
        print("❌ Erreur initialisation service CLIP")