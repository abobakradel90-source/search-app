import os
import chromadb
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import torch
import shutil

print("🚀 جاري تحميل Fashion-CLIP (الموديل المتخصص في الأحذية والملابس)...")
model_id = "patrickjohncyh/fashion-clip"
processor = CLIPProcessor.from_pretrained(model_id)
model = CLIPModel.from_pretrained(model_id)

if os.path.exists("./chroma_db"):
    shutil.rmtree("./chroma_db")
    
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.create_collection(
    name="products_collection",
    metadata={"hnsw:space": "cosine"}
)

image_folder = "compressed_images"
count = 0

print("🔍 جاري فحص الكوتشيات كخبير أزياء...")
for filename in os.listdir(image_folder):
    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        img_path = os.path.join(image_folder, filename)
        try:
            image = Image.open(img_path).convert('RGB')
            inputs = processor(images=image, return_tensors="pt")
            with torch.no_grad():
                features = model.get_image_features(**inputs)
                
                # السطرين اللي نسيناهم: فك شفرة الموديل 
                if not isinstance(features, torch.Tensor):
                    if hasattr(features, 'image_embeds'):
                        features = features.image_embeds
                    elif hasattr(features, 'pooler_output'):
                        features = features.pooler_output
                    else:
                        features = features[0]
                        
                embedding = features.squeeze().numpy().tolist()
            
            collection.add(
                embeddings=[embedding],
                metadatas=[{"filename": filename}],
                ids=[filename]
            )
            count += 1
            print(f"✅ تمت إضافة: {filename}")
        except Exception as e:
            print(f"❌ خطأ في صورة {filename}: {e}")

print(f"🎉 تم الانتهاء! إجمالي الصور: {count}")
print("📦 اضغط مجلد chroma_db إلى chroma_db.zip وارفعه على GitHub Releases.")