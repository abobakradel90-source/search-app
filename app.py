import streamlit as st
import chromadb
from transformers import AutoImageProcessor, AutoModel
from PIL import Image, ImageOps, ImageEnhance
import torch
import os
import zipfile
import urllib.request
import pandas as pd
import shutil
from streamlit_cropper import st_cropper

# 1. سحب قاعدة البيانات
@st.cache_resource
def download_new_chroma_db():
    zip_path = "chroma_db.zip"
    extract_path = "./chroma_db"
    marker_file = "./chroma_db/resnet50_installed.txt"
    download_url = "https://github.com/abobakradel90-source/search-app/releases/download/v1.0/chroma_db.zip"
    
    if os.path.exists(extract_path) and not os.path.exists(marker_file):
        shutil.rmtree(extract_path)
        
    if not os.path.exists(extract_path):
        with st.spinner('جاري سحب قاعدة البيانات (الحل الجذري ResNet-50)...'):
            try:
                urllib.request.urlretrieve(download_url, zip_path)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(".")
                if os.path.exists(zip_path):
                    os.remove(zip_path)
                with open(marker_file, 'w') as f:
                    f.write("done")
            except Exception as e:
                pass

# 2. تحميل موديل ResNet-50 (للمطابقة الحرفية للصور)
@st.cache_resource
def load_vision_system():
    download_new_chroma_db()
    processor = AutoImageProcessor.from_pretrained('microsoft/resnet-50')
    model = AutoModel.from_pretrained('microsoft/resnet-50')
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_collection(name="products_collection")
    return model, processor, collection

model, processor, collection = load_vision_system()

# 3. قراءة الإكسيل
@st.cache_data
def load_csv_data():
    try:
        df = pd.read_csv('products.csv', encoding='utf-8-sig', on_bad_lines='skip', engine='python')
        df.columns = df.columns.astype(str).str.strip()
        return df, None
    except Exception:
        try:
            df = pd.read_csv('products.csv', encoding='cp1256', on_bad_lines='skip', engine='python')
            df.columns = df.columns.astype(str).str.strip()
            return df, None
        except Exception as e:
            return None, str(e)

df_products, error_msg = load_csv_data()

# 4. استخراج البصمة البصرية الدقيقة جداً
def get_image_embedding(image):
    # توضيح بسيط جداً دون تغيير الألوان
    image = ImageOps.autocontrast(image.convert("RGB"), cutoff=1)
    
    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
        # تجميع الـ 2048 ميزة بصرية لاستخراج بصمة دقيقة للألوان والتفاصيل
        embedding = outputs.last_hidden_state.mean(dim=[2, 3]).squeeze().numpy().tolist()
    return embedding

# --- الواجهة ---
st.title("ED STORE ABOBAKR ADEl 👟🔥")
st.info(f"📦 المنتجات: {collection.count()} | 🦅 محرك المطابقة الحرفية (ResNet-50) مفعل")

tab1, tab2, tab3 = st.tabs(["📷 التقاط بالموبايل", "📁 رفع صورة", "🔍 بحث نصي"])

with tab3:
    if df_products is not None:
        search_query = st.text_input("اكتب اسم أو كود المنتج:")
        if search_query:
            mask = pd.Series([False]*len(df_products))
            for col in df_products.columns:
                mask = mask | df_products[col].astype(str).str.contains(search_query, case=False, na=False)
            matched = df_products[mask]
            if not matched.empty:
                for idx, row in matched.iterrows():
                    st.success(f"👟 النتيجة: {row.to_dict()}")
            else:
                st.warning("لا يوجد تطابق.")

raw_image = None
with tab1:
    cam_photo = st.camera_input("التقط صورة للكوتشي")
    if cam_photo:
        raw_image = Image.open(cam_photo).convert("RGB")

with tab2:
    up_file = st.file_uploader("اختر صورة", type=["jpg", "jpeg", "png"])
    if up_file:
        raw_image = Image.open(up_file).convert("RGB")

if raw_image:
    st.markdown("### ✂️ حدد الكوتشي فقط:")
    cropped_img = st_cropper(raw_image, realtime_update=True, box_color='#0000FF', aspect_ratio=None)
    
    if st.button("🔍 ابحث عن الكوتشي المحدد الآن", use_container_width=True):
        st.markdown("---")
        with st.spinner('🦅 جاري فحص البيكسلات والألوان والتطابق الحرفي...'):
            try:
                results = collection.query(
                    query_embeddings=[get_image_embedding(cropped_img)],
                    n_results=4,
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
                                target_code = str(p_code).strip().lower()
                                for col in df_products.columns:
                                    cleaned_col = df_products[col].astype(str).str.strip().str.lower()
                                    if (cleaned_col == target_code).any():
                                        row_idx = cleaned_col[cleaned_col == target_code].index[0]
                                        col_index = df_products.columns.get_loc(col)
                                        name_col_index = 1 if col_index == 0 else 0
                                        if len(df_products.columns) > 1:
                                            p_name = str(df_products.iloc[row_idx, name_col_index]).strip()
                                        break
                            except: pass
                        
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            img_path = os.path.join("compressed_images", meta.get('filename', ''))
                            if os.path.exists(img_path):
                                st.image(img_path, use_container_width=True)
                        with col2:
                            st.write(f"**الكود:** {p_code}")
                            st.write(f"**الاسم:** {p_name}")
                            st.caption(f"مؤشر المطابقة الحرفية: {distance:.3f}")
                        st.markdown("---")
            except Exception as e:
                st.error(f"خطأ: {e}")