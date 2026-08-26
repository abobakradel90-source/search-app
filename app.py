import streamlit as st
import chromadb
from transformers import CLIPProcessor, CLIPModel
from PIL import Image, ImageOps, ImageEnhance
import torch
import os
import zipfile
import urllib.request
import pandas as pd

# 1. تحميل قاعدة البيانات الجديدة (العملاقة)
@st.cache_resource
def download_new_chroma_db():
    zip_path = "chroma_db.zip"
    extract_path = "./chroma_db"
    # رابط الـ Release بتاعك (تأكد إنك رفعت الملف الجديد عليه)
    download_url = "https://github.com/abobakradel90-source/search-app/releases/download/v1.0/chroma_db.zip"
    
    if os.path.exists(zip_path):
        os.remove(zip_path)
    if not os.path.exists(extract_path):
        with st.spinner('جاري تهيئة قاعدة البيانات عالية الدقة...'):
            try:
                urllib.request.urlretrieve(download_url, zip_path)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(".")
                if os.path.exists(zip_path):
                    os.remove(zip_path)
            except Exception as e:
                st.error(f"حدث خطأ أثناء التحميل: {e}")

# 2. تحميل الموديل العملاق (Large)
@st.cache_resource
def load_clip_system():
    download_new_chroma_db()
    
    model_id = "openai/clip-vit-large-patch14"
    processor = CLIPProcessor.from_pretrained(model_id)
    model = CLIPModel.from_pretrained(model_id)
    
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_collection(name="products_collection")
    return model, processor, collection

model, processor, collection = load_clip_system()

# 3. قراءة ملف CSV
@st.cache_data
def load_csv_data():
    try:
        df = pd.read_csv('products.csv')
        df.columns = df.columns.astype(str).str.strip()
        return df, None
    except Exception as e:
        return None, str(e)

df_products, error_msg = load_csv_data()

# 4. القص الذكي لصور الموبايل (عشان نلغي الخلفية المشتتة)
def process_mobile_photo(image):
    image = image.convert("RGB")
    
    # تحسين التباين التلقائي عشان نعالج إضاءة الموبايل الضعيفة
    image = ImageOps.autocontrast(image, cutoff=2)
    
    # قص أطراف الصورة بنسبة 15% من كل الجوانب (التركيز على الكوتشي في النص)
    width, height = image.size
    left = width * 0.15
    top = height * 0.15
    right = width * 0.85
    bottom = height * 0.85
    cropped_image = image.crop((left, top, right, bottom))
    
    # زيادة حدة التفاصيل
    enhancer = ImageEnhance.Sharpness(cropped_image)
    final_image = enhancer.enhance(1.5)
    
    return final_image

def get_image_embedding(image):
    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        features = model.get_image_features(**inputs)
        features = features.pooler_output if hasattr(features, 'pooler_output') else features[0]
    return features.squeeze().numpy().tolist()

# 5. الواجهة
st.title("ED STORE ABOBAKR ADEl 👟🔥 (High Precision)")
st.info(f"📦 المنتجات: {collection.count()} | 🦅 محرك البحث العملاق مفعل")

tab1, tab2, tab3 = st.tabs(["📷 التقاط بالموبايل", "📁 رفع صورة", "🔍 بحث نصي بالكود"])

with tab3:
    st.subheader("البحث الفوري بالكود والاسم")
    if df_products is not None:
        search_query = st.text_input("اكتب اسم أو كود المنتج:")
        if search_query:
            cols = df_products.columns
            code_col = 'Code' if 'Code' in cols else cols[0]
            name_col = 'Name' if 'Name' in cols else cols[1]
            mask = df_products[code_col].astype(str).str.contains(search_query, case=False, na=False) | \
                   df_products[name_col].astype(str).str.contains(search_query, case=False, na=False)
            matched = df_products[mask]
            if not matched.empty:
                for _, row in matched.iterrows():
                    st.success(f"👟 {row[name_col]} | الكود: {row[code_col]}")
            else:
                st.warning("لا يوجد منتج مطابق.")

image_to_search = None
with tab1:
    cam_photo = st.camera_input("التقط صورة للكوتشي بحيث يكون في منتصف الشاشة")
    if cam_photo:
        image_to_search = process_mobile_photo(Image.open(cam_photo))
        st.image(image_to_search, caption="بعد المعالجة والتركيز الذكي", width=300)

with tab2:
    up_file = st.file_uploader("اختر صورة", type=["jpg", "jpeg", "png"])
    if up_file:
        image_to_search = process_mobile_photo(Image.open(up_file))
        st.image(image_to_search, caption="بعد المعالجة والتركيز الذكي", width=300)

if image_to_search and st.button("🔍 ابحث بالذكاء الاصطناعي", use_container_width=True):
    st.markdown("---")
    with st.spinner('🦅 جاري المطابقة بأعلى دقة...'):
        try:
            results = collection.query(
                query_embeddings=[get_image_embedding(image_to_search)],
                n_results=3, 
                include=['distances', 'metadatas']
            )
            
            if results['distances'][0]:
                st.success("✅ أفضل التطابقات:")
                for i in range(len(results['distances'][0])):
                    meta = results['metadatas'][0][i]
                    distance = results['distances'][0][i]
                    p_code = meta.get('filename', '').split('.')[0]
                    p_name = "غير متوفر"
                    
                    if df_products is not None:
                        try:
                            cols = df_products.columns
                            df_products['clean_c'] = df_products[cols[0] if 'Code' not in cols else 'Code'].astype(str).str.strip().str.lower()
                            row = df_products[df_products['clean_c'] == str(p_code).strip().lower()]
                            if not row.empty:
                                p_name = str(row.iloc[0][cols[1] if 'Name' not in cols else 'Name'])
                        except: pass
                    
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        img_path = os.path.join("compressed_images", meta.get('filename', ''))
                        if os.path.exists(img_path):
                            st.image(img_path, use_container_width=True)
                    with col2:
                        st.write(f"**الكود:** {p_code}")
                        st.write(f"**الاسم:** {p_name}")
                        st.caption(f"دقة المطابقة: {distance:.3f}")
                    st.markdown("---")
        except Exception as e:
            st.error(f"خطأ في البحث: {e}")