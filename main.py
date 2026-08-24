import os
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel
import chromadb

print("جاري تجهيز قاعدة البيانات والذكاء الاصطناعي...")

# 1. إعداد قاعدة البيانات المحلية ChromaDB
# سيقوم بإنشاء مجلد مخفي لحفظ البيانات حتى لا تضيع عند إغلاق البرنامج
chroma_client = chromadb.PersistentClient(path="./chroma_db") 
collection = chroma_client.get_or_create_collection(name="products_collection")

# 2. تحميل الذكاء الاصطناعي 
model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

# 3. قراءة الصور وتحويلها لبيانات
image_folder = "images" 

print("يبدأ الآن فحص الصور وحفظها... انتظر قليلاً")

# الدوران على كل صورة داخل مجلد الصور
for filename in os.listdir(image_folder):
    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        img_path = os.path.join(image_folder, filename)
        
        try:
            # فتح الصورة
            image = Image.open(img_path).convert("RGB")
            
            # تحويل الصورة إلى بصمة رقمية (Embeddings)
            inputs = processor(images=image, return_tensors="pt")
            with torch.no_grad():
                image_features = model.get_image_features(**inputs)
            
            # تحويل البيانات لشكل يقبله التخزين
            embedding = image_features[0].tolist()
            
            # تخزين البصمة الرقمية واسم الصورة في قاعدة البيانات
            collection.add(
                embeddings=[embedding],
                metadatas=[{"filename": filename}],
                ids=[filename] # نجعل اسم الملف هو المعرف الفريد
            )
            print(f"✅ تم حفظ الصورة: {filename}")
            
        except Exception as e:
            print(f"❌ حدث خطأ في صورة {filename}: {e}")

print("🎉 اكتمل بناء قاعدة البيانات بنجاح!")