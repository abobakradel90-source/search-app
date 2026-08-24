import os
import torch
import torch.nn.functional as F
import pickle
from PIL import Image
from transformers import CLIPProcessor, CLIPModel

print("🔄 جاري تحميل نموذج الذكاء الاصطناعي محلياً...")
processor = CLIPProcessor.from_pretrained('openai/clip-vit-base-patch32')
model = CLIPModel.from_pretrained('openai/clip-vit-base-patch32')

embeddings_db = {}
data_file = "embeddings.pkl"

# لو فيه ملف قديم نكمل عليه
if os.path.exists(data_file):
    with open(data_file, "rb") as f:
        embeddings_db = pickle.load(f)

files = [f for f in os.listdir('.') if f.lower().endswith(('.jpg', '.jpeg', '.png')) and f not in embeddings_db]
print(f"🚀 جاري معالجة واستخراج البصمات لـ {len(files)} صورة محلياً...")

for i, filename in enumerate(files):
    try:
        image = Image.open(filename).convert("RGB")
        inputs = processor(images=image, return_tensors="pt")
        
        with torch.no_grad():
            image_features = model.get_image_features(**inputs)
            embedding = image_features[0].tolist()
        
        embeddings_db[filename] = embedding
        
        # حفظ دُري كل 50 صورة لتجنب ضياع البيانات
        if i % 50 == 0:
            with open(data_file, "wb") as f:
                pickle.dump(embeddings_db, f)
                
        print(f"✅ تم معالجة: {filename} ({i+1}/{len(files)})")
    except Exception as e:
        print(f"⚠️ خطأ في {filename}: {e}")

# الحفظ النهائي
with open(data_file, "wb") as f:
    pickle.dump(embeddings_db, f)

print(f"\n🎉 تم الانتهاء بنجاح! إجمالي الصور المخزنة محلياً: {len(embeddings_db)}")