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
    marker_file = "./chroma_db/dinov2_installed.txt"
    download_url = "https://github.com/abobakradel90-source/search-app/releases/download/v1.0/chroma_db.zip"
    
    if os.path.exists(extract_path) and not os.path.exists(marker_file):
        shutil.rmtree(extract_path)
        
    if not os.path.exists(extract_path):
        with st.spinner('جاري سحب قاعدة البيانات البصرية الدقيقة...'):
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

# 2. تحميل موديل DINOv2
@st.cache_resource
def load_vision_system():
    download_new_chroma_db()
    processor = AutoImageProcessor.from_pretrained('facebook/dinov2-base')
    model = AutoModel.from_pretrained('facebook/dinov2-base')
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

# 4. دوال تحليل الألوان (السحر الجديد للتفرقة بين الألوان)
def get_color_histogram(image, is_db_image=False):
    img = image.convert("RGB")
    # لو الصورة من الداتا بيز، بنقص الحواف البيضاء عشان اللون الأبيض مايغطيش على لون الكوتشي
    if is_db_image:
        w, h = img.size
        img = img.crop((w*0.15, h*0.15, w*0.85, h*0.85))
    
    img = img.resize((64, 64))
    hist = img.histogram()
    total = sum(hist)
    return [h / total for h in hist] if total > 0 else hist

def compare_colors(hist1, hist2):
    # حساب نسبة الاختلاف اللوني
    return sum(abs(a - b) for a, b in zip(hist1, hist2))

def get_image_embedding(image):
    image = ImageOps.autocontrast(image, cutoff=1)
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(1.5)
    
    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
        embedding = outputs.last_hidden_state[:, 0, :].squeeze().numpy().tolist()
    return embedding

# --- الواجهة ---
st.title("ED STORE ABOBAKR ADEl 👟🔥")
st.info(f"📦 المنتجات: {collection.count()} | 🦅 محرك DINOv2 + فلتر الألوان مفعل")

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
        with st.spinner('🦅 جاري فحص الهيكل والألوان بدقة...'):
            try:
                # 1. طلب أفضل 10 كوتشيات في الهيكل من الذكاء الاصطناعي
                results = collection.query(
                    query_embeddings=[get_image_embedding(cropped_img)],
                    n_results=10, 
                    include=['distances', 'metadatas']
                )
                
                if results['distances'][0]:
                    # 2. استخراج البصمة اللونية للصورة اللي إنت صورتها
                    user_color_hist = get_color_histogram(cropped_img, is_db_image=False)
                    
                    refined_results = []
                    
                    for i in range(len(results['distances'][0])):
                        meta = results['metadatas'][0][i]
                        dino_dist = results['distances'][0][i]
                        filename = meta.get('filename', '')
                        img_path = os.path.join("compressed_images", filename)
                        
                        color_dist = 0
                        if os.path.exists(img_path):
                            # 3. حساب البصمة اللونية لصور الداتا بيز ومقارنتها
                            db_img = Image.open(img_path)
                            db_color_hist = get_color_histogram(db_img, is_db_image=True)
                            color_dist = compare_colors(user_color_hist, db_color_hist)
                        
                        # 4. دمج دقة الهيكل مع دقة اللون (السر هنا)
                        final_score = dino_dist + (color_dist * 0.8)
                        
                        refined_results.append({
                            'filename': filename,
                            'dino_dist': dino_dist,
                            'color_dist': color_dist,
                            'final_score': final_score,
                            'metadata': meta
                        })
                    
                    # 5. ترتيب النتائج من الأفضل للأسوأ بناءً على الهيكل واللون معاً
                    refined_results.sort(key=lambda x: x['final_score'])
                    
                    st.success("✅ أفضل التطابقات (مدعومة بفلتر الألوان):")
                    # عرض أفضل 3 نتائج فقط
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
                            st.caption(f"مؤشر التطابق النهائي: {result['final_score']:.3f}")
                        st.markdown("---")
            except Exception as e:
                st.error(f"خطأ: {e}")