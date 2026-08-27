import streamlit as st
import chromadb
from transformers import CLIPProcessor, CLIPModel
from PIL import Image, ImageOps
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
    marker_file = "./chroma_db/fashion_clip_v3.txt"
    download_url = "https://github.com/abobakradel90-source/search-app/releases/download/v1.0/chroma_db.zip"
    
    if os.path.exists(extract_path) and not os.path.exists(marker_file):
        shutil.rmtree(extract_path)
        
    if not os.path.exists(extract_path):
        with st.spinner('جاري التأكد من قاعدة البيانات...'):
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

# 2. تحميل موديل Fashion-CLIP
@st.cache_resource
def load_vision_system():
    download_new_chroma_db()
    model_id = "patrickjohncyh/fashion-clip"
    processor = CLIPProcessor.from_pretrained(model_id)
    model = CLIPModel.from_pretrained(model_id)
    client = chromadb.PersistentClient(path="./chroma_db")
    
    # 🔴 السطر ده اللي اتعدل: رجعناه لاسم قاعدتك الأصلية
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

# 4. دوال الذكاء الاصطناعي (الهيكل + فلتر الألوان الدقيق)
def get_image_embedding(image):
    image = ImageOps.autocontrast(image.convert("RGB"), cutoff=1)
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
        embedding = features.squeeze().numpy().tolist()
    return embedding

def get_color_histogram(image):
    # تحليل دقيق للألوان بنسبة 100%
    img = image.convert("RGB")
    w, h = img.size
    img = img.crop((w*0.15, h*0.15, w*0.85, h*0.85))
    hist = img.histogram() 
    total = sum(hist) / 3
    if total == 0: total = 1
    return [x / total for x in hist]

def compare_histograms(h1, h2):
    return sum(abs(a - b) for a, b in zip(h1, h2))

# --- الواجهة ---
st.title("ED STORE ABOBAKR ADEl 👟🔥")
st.info(f"📦 المنتجات: {collection.count()} | 👔 محرك Fashion-CLIP الهجين (هيكل + ألوان)")

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
        with st.spinner('👔 جاري تحليل التصميم وتطابق الألوان بدقة...'):
            try:
                # 1. بنطلب من Fashion-CLIP يجيب أفضل 8 كوتشيات
                results = collection.query(
                    query_embeddings=[get_image_embedding(cropped_img)],
                    n_results=8,
                    include=['distances', 'metadatas']
                )
                
                if results['distances'][0]:
                    # 2. تحليل ألوان الصورة بتاعتك
                    user_color_hist = get_color_histogram(cropped_img)
                    refined_results = []
                    
                    for i in range(len(results['distances'][0])):
                        meta = results['metadatas'][0][i]
                        fashion_dist = results['distances'][0][i]
                        filename = meta.get('filename', '')
                        img_path = os.path.join("compressed_images", filename)
                        
                        color_dist = 0
                        if os.path.exists(img_path):
                            # 3. تحليل ألوان الداتا بيز والمقارنة
                            db_img = Image.open(img_path)
                            db_color_hist = get_color_histogram(db_img)
                            color_dist = compare_histograms(user_color_hist, db_color_hist)
                        
                        # 4. دمج دقة الماركة مع دقة اللون
                        final_score = fashion_dist + (color_dist * 0.5)
                        
                        refined_results.append({
                            'filename': filename,
                            'final_score': final_score,
                            'metadata': meta
                        })
                    
                    # 5. الترتيب النهائي
                    refined_results.sort(key=lambda x: x['final_score'])
                    
                    st.success("✅ أفضل التطابقات (مدعومة بنظارة الألوان):")
                    for result in refined_results[:3]:
                        p_code = result['filename'].split('.')[0]
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
                            img_path = os.path.join("compressed_images", result['filename'])
                            if os.path.exists(img_path):
                                st.image(img_path, use_container_width=True)
                        with col2:
                            st.write(f"**الكود:** {p_code}")
                            st.write(f"**الاسم:** {p_name}")
                        st.markdown("---")
            except Exception as e:
                st.error(f"خطأ: {e}")