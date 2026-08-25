import os
import chromadb
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from tqdm import tqdm

print("جاري تحميل موديل CLIP الاحترافي (قد يستغرق بعض الوقت للتحميل لأول مرة)...")
# استخدام موديل CLIP الخاص بـ OpenAI
model_id = "openai/clip-vit-base-patch32"
processor = CLIPProcessor.from_pretrained(model_id)
model = CLIPModel.from_pretrained(model_id)

print("جاري تهيئة قاعدة البيانات الجديدة...")
client = chromadb.PersistentClient(path="./chroma_db")
# إنشاء الكوليكشن الجديد
collection = client.get_or_create_collection(name="products_collection")

# مسار فولدر الصور بتاعك
image_folder = "compressed_images"
image_files = [f for f in os.listdir(image_folder) if f.endswith(('.png', '.jpg', '.jpeg'))]

print(f"تم العثور على {len(image_files)} صورة. جاري بدء المعالجة...")

# حلقة التكرار مع عداد للوقت
for img_name in tqdm(image_files):
    img_path = os.path.join(image_folder, img_name)
    try:
        image = Image.open(img_path).convert('RGB')
        
        # استخراج الخصائص بذكاء CLIP
        inputs = processor(images=image, return_tensors="pt")
        with torch.no_grad():
            features = model.get_image_features(**inputs)
            
            # سطر الحماية عشان الإيرور ميظهرش على جهازك
            if not isinstance(features, torch.Tensor):
                if hasattr(features, 'pooler_output'):
                    features = features.pooler_output
                else:
                    features = features[0]
                    
        embedding = features.squeeze().numpy().tolist()
        
        # الحفظ في قاعدة البيانات
        collection.add(
            embeddings=[embedding],
            metadatas=[{"filename": img_name}],
            ids=[img_name] 
        )
    except Exception as e:
        # لو حصل إيرور في صورة معينة هيكتبها باللون الأحمر ويكمل عادي
        print(f"\n❌ خطأ في {img_name}: {e}")

print("\n✅ تمت العملية بنجاح! قاعدة البيانات الجديدة جاهزة في فولدر chroma_db")