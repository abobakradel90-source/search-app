import os
from PIL import Image
import torch
from transformers import AutoImageProcessor, AutoModel
import chromadb
import logging

logging.getLogger("transformers").setLevel(logging.ERROR)
print("جاري تجهيز قاعدة البيانات الصارمة (DINOv2)...")

chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(
    name="products_collection",
    metadata={"hnsw:space": "cosine"}
)

existing_ids = set(collection.get(include=[])['ids'])

# تحميل عقل DINOv2 المخصص للتفاصيل الدقيقة
processor = AutoImageProcessor.from_pretrained('facebook/dinov2-base')
model = AutoModel.from_pretrained('facebook/dinov2-base')

image_folder = "images"

if not os.path.exists(image_folder):
    print(f"❌ لم أجد مجلد '{image_folder}'")
else:
    images_found = False
    print("يبدأ الآن فحص الصور... (سيتم التخطي الذكي للصور المحفوظة)")
    
    for filename in os.listdir(image_folder):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            images_found = True
            if filename in existing_ids:
                print(f"⏩ تخطي: {filename}")
                continue
                
            img_path = os.path.join(image_folder, filename)
            try:
                image = Image.open(img_path).convert("RGB")
                inputs = processor(images=image, return_tensors="pt")
                
                with torch.no_grad():
                    outputs = model(**inputs)
                    # استخراج البصمة من النقطة المركزية للصورة (CLS Token)
                    embedding = outputs.last_hidden_state[0, 0].tolist()
                
                collection.upsert(
                    embeddings=[embedding],
                    metadatas=[{"filename": filename}],
                    ids=[filename]
                )
                print(f"✅ تم الحفظ بنجاح: {filename}")
            except Exception as e:
                print(f"❌ خطأ في {filename}: {e}")
    
    if images_found:
        print("🎉 اكتمل بناء قاعدة البيانات الصارمة بنجاح!")