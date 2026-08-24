import os
import time
import torch
import requests
from PIL import Image
from transformers import AutoImageProcessor, AutoModel
from upstash_vector import Index
import logging

logging.getLogger("transformers").setLevel(logging.ERROR)

# ==========================================
# 🔑 ضع مفاتيحك السرية هنا بين علامات التنصيص
# تأكد من عدم وجود "مسافات" فارغة داخل علامات التنصيص
# ==========================================
UPSTASH_URL = "https://new-herring-33493-us1-vector.upstash.io"
UPSTASH_TOKEN = "ABUFMG5ldy1oZXJyaW5nLTMzNDkzLXVzMWFkbWluTjJNek5EazROREV0TW1OaE1TMDBORGxqTFdJek0yTXRNakF5TWpObU9XUXhNalJp"
IMGBB_API_KEY = "a0dc3eac46136db285cb1891e7c4a60c"
# ==========================================

print("🌐 جاري الاتصال بالذاكرة السحابية...")
index = Index(url=UPSTASH_URL, token=UPSTASH_TOKEN)

print("🧠 جاري تحميل عقل DINOv2...")
processor = AutoImageProcessor.from_pretrained('facebook/dinov2-base')
model = AutoModel.from_pretrained('facebook/dinov2-base')

image_folder = "test_images"

if not os.path.exists(image_folder):
    print(f"❌ لم أجد مجلد '{image_folder}'، يرجى إنشاؤه ووضع بعض الصور فيه.")
else:
    for filename in os.listdir(image_folder):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            img_path = os.path.join(image_folder, filename)
            
            max_retries = 3
            upload_success = False
            img_url = ""
            
            print(f"⬆️ جاري رفع الصورة للسحابة: {filename}...")
            
            for attempt in range(max_retries):
                try:
                    with open(img_path, "rb") as file:
                        # 💡 التعديل الأول: وضعنا المفتاح داخل الرابط مباشرة
                        upload_url = f"https://api.imgbb.com/1/upload?key={IMGBB_API_KEY}"
                        response = requests.post(
                            upload_url,
                            files={"image": file},
                            timeout=30 
                        )
                    
                    if response.status_code == 200:
                        img_url = response.json()["data"]["url"]
                        upload_success = True
                        break
                    else:
                        # 💡 التعديل الثاني: طباعة سبب الرفض بالضبط من السيرفر
                        print(f"⚠️ السيرفر رفض. السبب الحقيقي من ImgBB: {response.text}")
                        time.sleep(2)
                        
                except requests.exceptions.RequestException as e:
                    print(f"⏳ ضعف في الإنترنت (محاولة {attempt + 1} من {max_retries})... جاري إعادة المحاولة")
                    time.sleep(3)
            
            if upload_success:
                try:
                    image = Image.open(img_path).convert("RGB")
                    inputs = processor(images=image, return_tensors="pt")
                    with torch.no_grad():
                        outputs = model(**inputs)
                        embedding = outputs.last_hidden_state[0, 0].tolist()
                    
                    index.upsert(
                        vectors=[
                            (filename, embedding, {"filename": filename, "url": img_url})
                        ]
                    )
                    print(f"✅ تم الحفظ بنجاح! الرابط: {img_url}")
                except Exception as e:
                    print(f"❌ خطأ في الذكاء الاصطناعي مع {filename}: {e}")
            else:
                print(f"❌ فشل رفع {filename} نهائياً.")

    print("\n🎉 اكتملت العملية!")