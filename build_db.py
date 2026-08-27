import os
import chromadb
from transformers import AutoImageProcessor, AutoModel
from PIL import Image
import torch
import shutil

print("🚀 جاري تحميل موديل DINOv2 (الأقوى في العالم للمطابقة البصرية الدقيقة)...")
# استخدام موديل DINOv2 المخصص للبحث البصري الدقيق
processor = AutoImageProcessor.from_pretrained('facebook/dinov2-base')
model = AutoModel.from_pretrained('facebook/dinov2-base')

# مسح القاعدة القديمة
if os.path.exists("./chroma_db"):
    shutil.rmtree("./chroma_db")
    
client = chromadb.PersistentClient(path="./chroma_db")
# استخدام Cosine Similarity عشان بيجيب أدق نتيجة في الشبه البصري
collection = client.create_collection(
    name="products_collection",
    metadata={"hnsw:space": "cosine"}
)

image_folder = "compressed_images" # تأكد من مسار مجلد الصور
count = 0

print("🔍 جاري فحص الصور بدقة بصرية عميقة...")
for filename in os.listdir(image_folder):
    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        img_path = os.path.join(image_folder, filename)
        try:
            image = Image.open(img_path).convert('RGB')
            inputs = processor(images=image, return_tensors="pt")
            
            with torch.no_grad():
                outputs = model(**inputs)
                # استخراج البصمة البصرية الدقيقة جداً من الموديل
                embedding = outputs.last_hidden_state[:, 0, :].squeeze().numpy().tolist()
            
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
print("📦 اضغط مجلد chroma_db لـ zip وارفعه في قسم Releases على جيت هاب.")