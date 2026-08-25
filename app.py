import streamlit as st
import chromadb
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import torch
import os
import zipfile
import urllib.request
import pandas as pd
from rembg import remove # مكتبة السحر لعزل الخلفيات

# 1. دالة التحميل
@st.cache_resource
def download_new_chroma_db():
    zip_path = "chroma_db.zip"
    extract_path = "./chroma_db"
    
    download_url = "https://github.com/abobakradel90-source/search-app/releases/download/v1.0/chroma_db.zip"
    
    if os.path.exists(zip_path):
        os.remove(zip_path)
        
    if not os.path.exists(extract_path):
        with st.spinner('جاري تهيئة النظام وقاعدة البيانات الجديدة (CLIP)...'):
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

# 3. قراءة الـ CSV (مع جهاز الكشف)
@st.cache_data
def load_csv_data():
    try:
        df = pd.read_csv('products.csv') 
        return df, None
    except Exception as e:
        return None, str(e)

df_products, error_msg = load_csv_data()

# --- القائمة الجانبية للكشف عن المشكلة ---
with st.sidebar:
    st.header("🛠️ فحص ملف البيانات")
    if df_products is not None:
        st.success("✅ تم قراءة ملف products.csv بنجاح!")
        st.write("📌 الأعمدة اللي الموقع شايفها بالظبط هي:")
        st.code(df_products.columns.tolist())
    else:
        st.error(f"❌ لم يتم العثور على الملف أو حدث خطأ:\n{error_msg}")

# 4. دالة استخراج الخصائص بذكاء CLIP
def get_image_embedding(image):
    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        features = model.get_image_features(**inputs)
        if not isinstance(features, torch.Tensor):
            if hasattr(features, 'pooler_output'):
                features = features.pooler_output
            else:
                features = features[0]
    return features.squeeze().numpy().tolist()

# 5. الواجهة الرئيسية
st.title("ED STORE ABOBAKR ADEl 👟🔥")
st.info(f"📦 عدد المنتجات الجاهزة للبحث: {collection.count()} منتج")

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
    if st.button("ابحث عن المنتجات الآن", use_container_width=True):
        for img_file in images_to_process:
            st.markdown("---")
            
            with st.spinner('✨ جاري عزل الخلفية بالذكاء الاصطناعي للتركيز على الكوتشي...'):
                try:
                    # فتح الصورة المرفوعة
                    original_image = Image.open(img_file)
                    
                    # خطوة العزل السحرية (بترجع صورة بخلفية شفافة)
                    isolated_image_rgba = remove(original_image)
                    
                    # تحويل الخلفية الشفافة للون أبيض نقي عشان الذكاء الاصطناعي ميتشتتت
                    isolated_image = Image.new("RGB", isolated_image_rgba.size, (255, 255, 255))
                    isolated_image.paste(isolated_image_rgba, mask=isolated_image_rgba.split()[3])
                    
                    # عرض الصورة قبل وبعد العزل للمقارنة
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.image(original_image, caption='الصورة الأصلية', use_container_width=True)
                    with col_b:
                        st.image(isolated_image, caption='بعد عزل الخلفية (جاهزة للبحث)', use_container_width=True)
                    
                    # البحث بالصورة المعزولة النظيفة
                    query_embedding = get_image_embedding(isolated_image)
                    
                    results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=5, 
                        include=['distances', 'metadatas']
                    )
                    
                    if not results['distances'][0]:
                        st.warning("لم يتم العثور على أي منتج مطابق في قاعدة البيانات.")
                    else:
                        st.success(f"✅ تم العثور على أفضل {len(results['distances'][0])} نتائج مشابهة:")
                        
                        for i in range(len(results['distances'][0])):
                            distance = results['distances'][0][i]
                            metadata = results['metadatas'][0][i]
                            
                            filename = metadata.get('filename', 'غير متوفر')
                            product_code = filename.split('.')[0] if filename != 'غير متوفر' else 'غير متوفر'
                            product_name = "غير متوفر"
                            
                            # البحث في الـ CSV
                            if df_products is not None:
                                try:
                                    if 'Code' in df_products.columns and 'Name' in df_products.columns:
                                        clean_excel_codes = df_products['Code'].astype(str).str.strip()
                                        clean_target_code = str(product_code).strip()
                                        
                                        row = df_products[clean_excel_codes == clean_target_code]
                                        if not row.empty:
                                            product_name = str(row.iloc[0]['Name']).strip()
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
                                st.write(f"**نسبة الاختلاف:** {distance:.2f}")
                            
                            st.markdown("---")
                            
                except Exception as e:
                    st.error(f"حدث خطأ أثناء فحص الصورة: {str(e)}")