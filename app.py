import streamlit as st
import chromadb
from transformers import CLIPProcessor, CLIPModel
from PIL import Image, ImageEnhance
import torch
import os
import zipfile
import urllib.request
import pandas as pd

# 1. دالة التحميل
@st.cache_resource
def download_new_chroma_db():
    zip_path = "chroma_db.zip"
    extract_path = "./chroma_db"
    
    download_url = "https://github.com/abobakradel90-source/search-app/releases/download/v1.0/chroma_db.zip"
    
    if os.path.exists(zip_path):
        os.remove(zip_path)
        
    if not os.path.exists(extract_path):
        with st.spinner('جاري تهيئة النظام وقاعدة البيانات (CLIP)...'):
            try:
                urllib.request.urlretrieve(download_url, zip_path)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(".")
                if os.path.exists(zip_path):
                    os.remove(zip_path)
            except Exception as e:
                st.error(f"حدث خطأ أثناء تحميل قاعدة البيانات: {e}")

# 2. تحميل موديل CLIP
@st.cache_resource
def load_clip_system():
    download_new_chroma_db()
    
    model_id = "openai/clip-vit-base-patch32"
    processor = CLIPProcessor.from_pretrained(model_id)
    model = CLIPModel.from_pretrained(model_id)
    
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_collection(name="products_collection")
    return model, processor, collection

model, processor, collection = load_clip_system()

# 3. قراءة الـ CSV وتنظيف الأعمدة
@st.cache_data
def load_csv_data():
    try:
        df = pd.read_csv('products.csv')
        df.columns = df.columns.astype(str).str.strip()
        return df, None
    except Exception as e:
        return None, str(e)

df_products, error_msg = load_csv_data()

# --- القائمة الجانبية الفاحصة ---
with st.sidebar:
    st.header("🛠️ فحص ملف البيانات")
    if df_products is not None:
        st.success("✅ تم قراءة ملف products.csv بنجاح!")
        st.write("📌 الأعمدة المتاحة:")
        st.code(df_products.columns.tolist())
    else:
        st.error(f"❌ خطأ في الملف:\n{error_msg}")

# 4. دالة متقدمة لتحسين صورة الكاميرا (تعديل التباين والسطوع لزيادة الدقة)
def enhance_camera_image(image):
    image = image.convert("RGB")
    
    # تحسين التباين والسطوع عشان يتغلب على إضاءة الموبايل الضعيفة أو الظلال
    enhancer_contrast = ImageEnhance.Contrast(image)
    image = enhancer_contrast.enhance(1.2)  # زيادة طفيفة في التباين لإبراز تفاصيل الكوتشي
    
    enhancer_sharpness = ImageEnhance.Sharpness(image)
    image = enhancer_sharpness.enhance(1.5) # زيادة الحِدة لتوضيح خيوط ونقشة الكوتشي
    
    # وضع الصورة داخل إطار مربع أبيض نقي لمنع التشوه
    max_size = max(image.size)
    new_img = Image.new("RGB", (max_size, max_size), (255, 255, 255))
    new_img.paste(image, ((max_size - image.size[0]) // 2, (max_size - image.size[1]) // 2))
    
    return new_img

# 5. دالة استخراج الخصائص
def get_image_embedding(image):
    processed_img = enhance_camera_image(image)
    inputs = processor(images=processed_img, return_tensors="pt")
    with torch.no_grad():
        features = model.get_image_features(**inputs)
        if not isinstance(features, torch.Tensor):
            if hasattr(features, 'pooler_output'):
                features = features.pooler_output
            else:
                features = features[0]
    return features.squeeze().numpy().tolist()

# 6. الواجهة الرئيسية
st.title("ED STORE ABOBAKR ADEl 👟🔥")
st.info(f"📦 عدد المنتجات الجاهزة للبحث: {collection.count()} منتج | 📸 وضع تحسين صور الكاميرا مفعل")

tab1, tab2 = st.tabs(["📁 رفع صور من الجهاز", "📷 التقاط بالكاميرا"])
images_to_process = []

with tab1:
    uploaded_files = st.file_uploader("اختر صورة أو أكثر...", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    if uploaded_files:
        images_to_process.extend(uploaded_files)
        
with tab2:
    camera_photo = st.camera_input("التقط صورة للمنتج")
    if camera_photo:
        images_to_process.append(camera_photo)

if images_to_process:
    if st.button("ابحث بدقة عالية الآن", use_container_width=True):
        for img_file in images_to_process:
            st.markdown("---")
            st.image(img_file, caption=f'الصورة المرفوعة: {img_file.name}', use_container_width=True)
            
            with st.spinner('📸 جاري معالجة إضاءة وتفاصيل صورة الكاميرا للبحث بدقة...'):
                try:
                    image = Image.open(img_file)
                    query_embedding = get_image_embedding(image)
                    
                    # طلب أفضل 3 نتائج فقط عشان نركز على الأعلى مطابقة
                    results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=3, 
                        include=['distances', 'metadatas']
                    )
                    
                    if not results['distances'][0]:
                        st.warning("لم يتم العثور على أي منتج مطابق في قاعدة البيانات.")
                    else:
                        st.success(f"✅ أفضل النتائج المطابقة:")
                        
                        for i in range(len(results['distances'][0])):
                            distance = results['distances'][0][i]
                            metadata = results['metadatas'][0][i]
                            
                            filename = metadata.get('filename', 'غير متوفر')
                            product_code = filename.split('.')[0] if filename != 'غير متوفر' else 'غير متوفر'
                            product_name = "غير متوفر"
                            
                            if df_products is not None:
                                try:
                                    cols = df_products.columns
                                    code_col = 'Code' if 'Code' in cols else (cols[0] if len(cols) > 0 else None)
                                    name_col = 'Name' if 'Name' in cols else (cols[1] if len(cols) > 1 else None)
                                    
                                    if code_col and name_col:
                                        df_products['cleaned_code'] = df_products[code_col].astype(str).str.strip().str.lower()
                                        target_cleaned = str(product_code).strip().lower()
                                        
                                        row = df_products[df_products['cleaned_code'] == target_cleaned]
                                        if not row.empty:
                                            product_name = str(row.iloc[0][name_col]).strip()
                                except Exception:
                                    pass

                            st.markdown(f"### النتيجة رقم {i+1}")
                            col1, col2 = st.columns([1, 2])
                            
                            with col1:
                                img_path = os.path.join("compressed_images", filename)
                                if os.path.exists(img_path):
                                    st.image(img_path, use_container_width=True)
                                else:
                                    st.warning("صورة النتيجة غير موجودة بالمسار")
                                    
                            with col2:
                                st.write(f"**كود المنتج:** {product_code}")
                                st.write(f"**اسم المنتج:** {product_name}")
                                st.write(f"**مؤشر المطابقة (Distance):** {distance:.4f}")
                                
                                # تنبيه ذكي لو النتيجة بعيدة
                                if distance > 0.35:
                                    st.caption("⚠️ تنبيه: نسبة الشبه منخفضة، يفضل التقاط الصورة بإضاءة أوضح.")
                                else:
                                    st.caption("✨ تطابق ممتاز عالي الثقة!")
                            
                            st.markdown("---")
                            
                except Exception as e:
                    st.error(f"حدث خطأ أثناء فحص الصورة: {str(e)}")