import streamlit as st
import chromadb
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import torch
import os
import zipfile
import urllib.request
import pandas as pd

@st.cache_resource
def download_new_chroma_db():
    zip_path = "chroma_db.zip"
    extract_path = "./chroma_db"
    download_url = "https://github.com/abobakradel90-source/search-app/releases/download/v1.0/chroma_db.zip"
    if os.path.exists(zip_path): os.remove(zip_path)
    if not os.path.exists(extract_path):
        with st.spinner('جاري تهيئة قاعدة البيانات...'):
            try:
                urllib.request.urlretrieve(download_url, zip_path)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref: zip_ref.extractall(".")
                if os.path.exists(zip_path): os.remove(zip_path)
            except Exception as e: st.error(f"خطأ: {e}")

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

@st.cache_data
def load_csv_data():
    try:
        df = pd.read_csv('products.csv')
        df.columns = df.columns.astype(str).str.strip()
        return df, None
    except Exception as e: return None, str(e)

df_products, error_msg = load_csv_data()

with st.sidebar:
    st.header("🛠️ فحص البيانات")
    if df_products is not None:
        st.success("✅ ملف products.csv جاهز!")
    else: st.error(f"❌ خطأ:\n{error_msg}")

def get_image_embedding(image):
    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        features = model.get_image_features(**inputs)
        features = features.pooler_output if hasattr(features, 'pooler_output') else features[0]
    return features.squeeze().numpy().tolist()

st.title("ED STORE ABOBAKR ADEl 👟🔥")
st.info(f"📦 المنتجات المتاحة: {collection.count()}")

tab_image, tab_text = st.tabs(["📷 البحث بالصورة (مساعد ذكي)", "🔍 البحث بالكود والاسم (دقة 100%)"])

with tab_text:
    st.subheader("البحث الفوري المضمون")
    if df_products is not None:
        search_query = st.text_input("اكتب اسم المنتج أو الكود هنا:")
        if search_query:
            cols = df_products.columns
            code_col = 'Code' if 'Code' in cols else cols[0]
            name_col = 'Name' if 'Name' in cols else cols[1]
            mask = df_products[code_col].astype(str).str.contains(search_query, case=False, na=False) | \
                   df_products[name_col].astype(str).str.contains(search_query, case=False, na=False)
            matched = df_products[mask]
            if matched.empty: st.warning("لا يوجد منتج بهذا الاسم.")
            else:
                for _, row in matched.iterrows():
                    st.success(f"👟 {row[name_col]} | الكود: {row[code_col]}")
                    img_path = os.path.join("compressed_images", f"{str(row[code_col]).strip()}.jpg")
                    if os.path.exists(img_path): st.image(img_path, width=200)

with tab_image:
    up_file = st.file_uploader("ارفع صورة", type=["jpg", "png", "jpeg"])
    cam_photo = st.camera_input("أو صور المنتج")
    img_target = cam_photo if cam_photo else up_file
    
    if img_target and st.button("ابحث بالصورة", use_container_width=True):
        st.image(img_target, width=250)
        with st.spinner('جاري البحث...'):
            image = Image.open(img_target).convert('RGB')
            results = collection.query(query_embeddings=[get_image_embedding(image)], n_results=3, include=['distances', 'metadatas'])
            if results['distances'][0]:
                for i in range(len(results['distances'][0])):
                    meta = results['metadatas'][0][i]
                    p_code = meta.get('filename', '').split('.')[0]
                    p_name = "غير متوفر"
                    if df_products is not None:
                        try:
                            cols = df_products.columns
                            df_products['clean_c'] = df_products[cols[0] if 'Code' not in cols else 'Code'].astype(str).str.strip().str.lower()
                            row = df_products[df_products['clean_c'] == str(p_code).strip().lower()]
                            if not row.empty: p_name = str(row.iloc[0][cols[1] if 'Name' not in cols else 'Name'])
                        except: pass
                    st.markdown(f"**النتيجة #{i+1}** | الكود: {p_code} | الاسم: {p_name}")
                    img_p = os.path.join("compressed_images", meta.get('filename', ''))
                    if os.path.exists(img_p): st.image(img_p, width=150)
                    st.markdown("---")