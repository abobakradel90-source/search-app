import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
import chromadb
import logging
import pandas as pd
import arabic_reshaper
from bidi.algorithm import get_display

# دالة ذكية لضبط تشبيك واتجاه الحروف العربية في الويندوز
def fix_ar(text):
    reshaped_text = arabic_reshaper.reshape(str(text))
    bidi_text = get_display(reshaped_text)
    return bidi_text

logging.getLogger("transformers").setLevel(logging.ERROR)
print(fix_ar("🌟 جاري تشغيل محرك البحث البصري المتقدم..."))

# محاولة قراءة ملف الأكواد
try:
    df = pd.read_csv("products.csv")
    has_data = True
except FileNotFoundError:
    print(fix_ar("⚠️ تنبيه: لم يتم العثور على ملف products.csv، سيتم عرض أسماء الصور فقط."))
    has_data = False

chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_collection(name="products_collection")

model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

query_image_path = "test.jpg" 

try:
    image = Image.open(query_image_path).convert("RGB")
    inputs = processor(images=image, return_tensors="pt")
    
    with torch.no_grad():
        features = model.get_image_features(pixel_values=inputs['pixel_values'])
    
    if isinstance(features, torch.Tensor):
        query_embedding = features.flatten().tolist()
    else:
        query_embedding = features.pooler_output.flatten().tolist() if hasattr(features, "pooler_output") else features[0].flatten().tolist()
    
    db_size = collection.count()
    if db_size == 0:
        print(fix_ar("❌ قاعدة البيانات فارغة!"))
    else:
        search_results_count = min(3, db_size)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=search_results_count
        )
        
        print("\n" + fix_ar("✅ النتيجة: هذه أقرب الموديلات المطابقة لصورة العميل:"))
        print("=" * 60)
        
        for i in range(len(results['ids'][0])):
            match_filename = results['ids'][0][i]
            
            # سحب البيانات من ملف الـ CSV
            product_name = "غير مسجل"
            product_code = "غير مسجل"
            
            if has_data:
                row = df[df['filename'] == match_filename]
                if not row.empty:
                    product_code = row['code'].values[0]
                    product_name = row['name'].values[0]
            
            print(fix_ar(f"🥇 التطابق رقم {i+1}:"))
            print(fix_ar(f"   🔹 صورة الموديل: {match_filename}"))
            print(fix_ar(f"   🔹 كود المنتج : {product_code}"))
            print(fix_ar(f"   🔹 اسم الموديل: {product_name}"))
            print("-" * 60)
            
except FileNotFoundError:
    print(fix_ar(f"❌ لم يتم العثور على صورة البحث: {query_image_path}"))
except Exception as e:
    print(fix_ar(f"❌ حدث خطأ: {e}"))