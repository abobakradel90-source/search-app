import streamlit as st
import chromadb
from transformers import CLIPProcessor, CLIPModel
from PIL import Image, ImageOps, ImageEnhance
import torch
import os
import zipfile
import urllib.request
import pandas as pd
import shutil

# 1. سحب قاعدة البيانات
@st.cache_resource
def download_new_chroma_db():
    zip_path = "chroma_db.zip"
    extract_path = "./chroma_db"
    marker_file = "./chroma_db/large_model_installed.txt"
    download_url = "https://github.com/abobakradel90-source/search-app/releases/download/v1.0/chroma_db.zip"
    
    if os.path.exists(extract_path) and not os.path.exists(marker_file):
        shutil.rmtree(extract_path)
        
    if not os.path.exists(extract_path):
        with st.spinner('جاري سحب قاعدة البيانات...'):
            try:
                urllib.request.urlretrieve(download_url, zip_path)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(".")
                if os.path.exists(zip_path):
                    os.remove(zip_path)
                with open(marker_file, 'w') as f:
                    f.write("done")
            except Exception as e:
                st.error(f"خطأ أثناء التحميل: {e}")

# 2. تحميل الموديل
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

# 3. القراءة المرنة جداً لملف CSV (السر هنا)
@st.cache_data
def load_csv_data():
    try:
        # engine='python' و sep=None بيخلوا بايثون يكتشف الفاصل أوتوماتيك
        df = pd.read_csv('products.csv', sep=None, engine='python', encoding='utf-8-sig')
        df.columns = df.columns.astype(str).str.strip()
        return df, None
    except Exception:
        try:
            df = pd.read_csv('products.csv', sep=None, engine='python', encoding='cp1256')
            df.columns = df.columns.astype(str).str.strip()
            return df, None
        except Exception as e2:
            return None, str(e2)

df_products, error_msg = load_csv_data()

# --- القائمة الجانبية للكشف على الملف ---
with st.sidebar:
    st.header("🛠️ فحص ملف البيانات")
    if df_products is not None:
        st.success("✅ تم قراءة ملف products.csv!")
        st.write("📌 نظرة على أول 3 صفوف (عشان نتأكد بايثون شايفهم إزاي):")
        st.dataframe(df_products.head(3))
    else:
        st.error(f"❌ خطأ:\n{error_msg}")

# 4. معالجة الصور
def process_mobile_photo(image):
    image = image.convert("RGB")
    image = ImageOps.autocontrast(image, cutoff=2)
    width, height = image.size
    left = width * 0.15
    top = height * 0.15
    right = width * 0.85
    bottom = height * 0.85
    cropped_image = image.crop((left, top, right, bottom))
    enhancer = ImageEnhance.Sharpness(cropped_image)
    return enhancer.enhance(1.5)

# 5. استخراج الخصائص
def get_image_embedding(image):
    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        features = model.get_image_features(**inputs)
        if not isinstance(features, torch.Tensor):
            if hasattr(features, 'image_embeds'):
                features = features.image_embeds
            elif hasattr(features, 'pooler_output'):
                features = features.pooler_output
            else:
                features = features[0]
    return features.squeeze().numpy().tolist()

# 6. الواجهة الرئيسية
st.title("ED STORE ABOBAKR ADEl 👟🔥 (High Precision)")
st.info(f"📦 المنتجات: {collection.count()} | 🦅 محرك البحث العملاق مفعل")

tab1, tab2, tab3 = st.tabs(["📷 التقاط بالموبايل", "📁 رفع صورة", "🔍 بحث نصي بالكود"])

with tab3:
    st.subheader("البحث الفوري بالكود والاسم")
    if df_products is not None:
        search_query = st.text_input("اكتب اسم أو كود المنتج:")
        if search_query:
            # بحث في كل الأعمدة بدون تحديد اسم عمود معين
            mask = pd.Series([False]*len(df_products))
            for col in df_products.columns:
                mask = mask | df_products[col].astype(str).str.contains(search_query, case=False, na=False)
            
            matched = df_products[mask]
            if not matched.empty:
                for idx, row in matched.iterrows():
                    st.success(f"👟 النتيجة: {row.to_dict()}")
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
                            target_code = str(p_code).strip().lower()
                            # بحث شامل في كل خلايا الملف
                            for col in df_products.columns:
                                cleaned_col = df_products[col].astype(str).str.strip().str.lower()
                                if (cleaned_col == target_code).any():
                                    row_idx = cleaned_col[cleaned_col == target_code].index[0]
                                    
                                    # تحديد عمود الاسم (لو الكود في العمود 0 يبقى الاسم في 1 والعكس)
                                    col_index = df_products.columns.get_loc(col)
                                    name_col_index = 1 if col_index == 0 else 0
                                    
                                    if len(df_products.columns) > 1:
                                        p_name = str(df_products.iloc[row_idx, name_col_index]).strip()
                                    else:
                                        p_name = "مشكلة في الإكسيل: الأعمدة ملزوقة في بعض"
                                    break
                        except Exception:
                            pass
                    
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