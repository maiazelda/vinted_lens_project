# models/test_clip.py
# Test autonome du pipeline CLIP pour Vinted Lens

import torch
from transformers import CLIPProcessor, CLIPModel
import requests
from PIL import Image
from io import BytesIO
import numpy as np
import time
import sys
import os

def test_clip_pipeline():
    """Test complet du pipeline CLIP"""
    print("🚀 Test CLIP Pipeline - Vinted Lens")
    print("=" * 50)
    
    # 1️⃣ Vérification environnement
    print(f"🐍 Python: {sys.version}")
    print(f"🔥 PyTorch: {torch.__version__}")
    print(f"💻 Device: {'CUDA' if torch.cuda.is_available() else 'CPU'}")
    
    # 2️⃣ Chargement du modèle CLIP
    print("\n📥 Chargement CLIP model...")
    start_time = time.time()
    
    try:
        model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model.to(device)
        
        load_time = time.time() - start_time
        print(f"✅ Modèle chargé en {load_time:.2f}s sur {device}")
        
    except Exception as e:
        print(f"❌ Erreur chargement modèle: {e}")
        return False
    
    # 3️⃣ Test avec image de vêtement réelle
    print("\n👕 Test encoding image de vêtement...")
    
    # Image test : T-shirt Unsplash (free)
    image_url = "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400&h=400&fit=crop"
    
    try:
        # Télécharger et traiter image
        print(f"📥 Téléchargement: {image_url}")
        response = requests.get(image_url, timeout=15)
        response.raise_for_status()
        
        image = Image.open(BytesIO(response.content))
        print(f"📸 Image chargée: {image.size} ({image.mode})")
        
        # Encoder avec CLIP
        start_time = time.time()
        inputs = processor(images=image, return_tensors="pt").to(device)
        
        with torch.no_grad():
            image_features = model.get_image_features(**inputs)
            # Normalisation L2 pour similarité cosinus
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        
        encode_time = time.time() - start_time
        embedding = image_features.cpu().numpy().flatten()
        
        print(f"✅ Embedding généré en {encode_time:.3f}s")
        print(f"✅ Shape: {embedding.shape}")
        print(f"✅ Dtype: {embedding.dtype}")
        print(f"✅ Sample: [{embedding[0]:.4f}, {embedding[1]:.4f}, {embedding[2]:.4f}, ...]")
        print(f"✅ Norm: {np.linalg.norm(embedding):.6f} (doit être ~1.0)")
        
        # 4️⃣ Test similarité (doit être 1.0 avec elle-même)
        similarity = np.dot(embedding, embedding)
        print(f"✅ Auto-similarité: {similarity:.6f} (parfait si ~1.0)")
        
        # 5️⃣ Test avec texte (bonus)
        print("\n🔍 Test embedding texte...")
        text_inputs = processor(text=["a red t-shirt", "blue jeans", "white sneakers"], 
                               return_tensors="pt", padding=True).to(device)
        
        with torch.no_grad():
            text_features = model.get_text_features(**text_inputs)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        
        # Similarité image-texte
        text_similarities = []
        for i, text in enumerate(["red t-shirt", "blue jeans", "white sneakers"]):
            sim = np.dot(embedding, text_features[i].cpu().numpy())
            text_similarities.append((text, sim))
            print(f"📝 Similarité '{text}': {sim:.4f}")
        
        print("\n🎉 PIPELINE CLIP FONCTIONNEL - PRÊT POUR VINTED LENS!")
        print("=" * 50)
        
        return {
            'model_load_time': load_time,
            'encode_time': encode_time,
            'embedding_shape': embedding.shape,
            'embedding_norm': np.linalg.norm(embedding),
            'auto_similarity': similarity,
            'text_similarities': text_similarities,
            'device': device
        }
        
    except Exception as e:
        print(f"❌ Erreur test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🎯 Test CLIP Pipeline - Vinted Lens")
    print("Assurez-vous d'être dans le dossier backend avec l'env virtuel activé")
    print()
    
    result = test_clip_pipeline()
    
    if result:
        print(f"\n📊 Résumé Performance:")
        print(f"• Chargement modèle: {result['model_load_time']:.2f}s")
        print(f"• Encoding image: {result['encode_time']:.3f}s")
        print(f"• Device: {result['device']}")
        print(f"• Prêt pour intégration FastAPI! ✅")
    else:
        print("\n❌ Test échoué - Vérifiez les dépendances")
        sys.exit(1)