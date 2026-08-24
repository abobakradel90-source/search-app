import os
import time
import torch
import requests
from PIL import Image
from transformers import AutoImageProcessor, AutoModel
from upstash_vector import Index

# 🔑 ضع مفاتيحك هنا
UPSTASH_URL = "https://new-herring-33493-us1-vector.upstash.io"
UPSTASH_TOKEN = "ABUFMG5ldy1oZXJyaW5nLTMzNDkzLXVzMWFkbWluTjJNek5EazROREV0TW1OaE1TMDBORGxqTFdJek0yTXRNakF5TWpObU9XUXhNalJp"
IMGBB_API_KEY = "a0dc3eac46136db285cb1891e7c4a60c"

index = Index(url=UPSTASH_URL, token=UPSTASH_TOKEN)
processor = AutoImageProcessor.from_pretrained('facebook/dinov2-base')
model = AutoModel.from_pretrained('facebook/dinov2-base')

image_folder = "products_images" # تأكد أن هذا هو اسم المجلد
log_file = "uploaded_log.txt"

# تحميل الصور التي تم رفعها مسبقاً (عشان لو فصل يكمل)
if os.path.exists(log_file):
    with open(log_file, "r") as f:
        already_uploaded = set(line.strip() for line in f)
else:
    already_uploaded = set()

print(f"🚀 بدء رفع {len(os.listdir(image_folder))} صورة...")

for filename in os.listdir(image_folder):
    if filename.lower().endswith(('.png', '.jpg', '.jpeg')) and filename not in already_uploaded:
        img_path = os.path.join(image_folder, filename)
        
        # 1. الرفع لـ ImgBB
        try:
            with open(img_path, "rb") as file:
                response = requests.post(
                    f"https://api.imgbb.com/1/upload?key={IMGBB_API_KEY}",
                    files={"image": file}, timeout=30
                )
            
            if response.status_code == 200:
                img_url = response.json()["data"]["url"]
                
                # 2. استخراج البصمة
                image = Image.open(img_path).convert("RGB")
                inputs = processor(images=image, return_tensors="pt")
                with torch.no_grad():
                    embedding = model(**inputs).last_hidden_state[0, 0].tolist()
                
                # 3. الحفظ في Upstash
                index.upsert(vectors=[(filename, embedding, {"filename": filename, "url": img_url})])
                
                # 4. تسجيل في السجل
                with open(log_file, "a") as f:
                    f.write(filename + "\n")
                
                print(f"✅ تم رفع: {filename}")
            else:
                print(f"❌ خطأ في رفع {filename}: {response.text}")
                
        except Exception as e:
            print(f"⚠️ تعثر في {filename}: {e}")
            time.sleep(5) # استراحة قصيرة إذا حدث خطأ

print("\n🎉 انتهت عملية الرفع بالكامل!")