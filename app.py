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

# --- 🎨 إعدادات الصفحة والتصميم العالمي (يجب أن تكون أول سطر) ---
st.set_page_config(page_title="ED STORE | البحث الذكي", page_icon="👟", layout="centered")

# --- 🎨 كود CSS لتحويل شكل الموقع بالكامل ---
st.markdown("""
    <style>
        /* استيراد خط Cairo من جوجل */
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;800&display=swap');
        
        /* تطبيق الخط على كل الموقع وضبط الاتجاه */
        html, body, [class*="css"] {
            font-family: 'Cairo', sans-serif !important;
        }
        
        /* إخفاء علامات Streamlit المزعجة */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* تصميم عنوان الموقع */
        .main-header {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: white;
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.2);
            margin-bottom: 25px;
        }
        .main-header h1 {
            margin: 0;
            font-weight: 800;
            font-size: 2.2rem;
            color: white;
        }
        .main-header p {
            margin: 5px 0 0 0;
            color: #94a3b8;
            font-size: 1.1rem;
        }
        
        /* تصميم الأزرار (Gradients and Shadows) */
        .stButton > button {
            background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%);
            color: white !important;
            border-radius: 12px;
            border: none;
            padding: 10px 20px;
            font-weight: 700;
            font-size: 18px;
            box-shadow: 0 4px 15px -3px rgba(37, 99, 235, 0.4);
            transition: all 0.3s ease;
            width: 100%;
        }
        .stButton > button:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 20px -3px rgba(37, 99, 235, 0.5);
            border: none;
        }
        
        /* تصميم كروت النتائج */
        .result-card {
            background-color: #ffffff;
            padding: 15px;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            border: 1px solid #f1f5f9;
            margin-bottom: 10px;
        }
        .code-badge {
            background-color: #f1f5f9;
            color: #334155;
            padding: 4px 10px;
            border-radius: 8px;
            font-size: 0.9rem;
            font-weight: bold;
            display: inline-block;
            margin-bottom: 8px;
        }
        .product-name {
            color: #0f172a;
            font-size: 1.2rem;
            font-weight: 700;
            margin-bottom: 15px;
        }
    </style>
""", unsafe_allow_html=True)

# 1. سحب قاعدة البيانات
@st.cache_resource
def download_new_chroma_db():
    zip_path = "chroma_db.zip"
    extract_path = "./chroma_db"
    marker_file = "./chroma_db/fashion_clip_v2.txt"
    download_url = "https://github.com/abobakradel90-source/search-app/releases/download/v1.0/chroma_db.zip"
    
    if os.path.exists(extract_path) and not os.path.exists(marker_file):
        shutil.rmtree(extract_path)
    if not os.path.exists(extract_path):
        with st.spinner('جاري التأكد من قاعدة بيانات Fashion-CLIP...'):
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

# 4. دوال الذكاء الاصطناعي
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
    img = image.convert("RGB")
    w, h = img.size
    img = img.crop((w*0.15, h*0.15, w*0.85, h*0.85))
    hist = img.histogram() 
    total = sum(hist) / 3
    if total == 0: total = 1
    return [x / total for x in hist]

def compare_histograms(h1, h2):
    return sum(abs(a - b) for a, b in zip(h1, h2))

# --- بناء الواجهة الجديدة ---
st.markdown("""
<div class="main-header">
    <h1>ED STORE 👟🔥</h1>
    <p>محرك البحث البصري الذكي | مدعوم بـ Fashion-CLIP</p>
</div>
""", unsafe_allow_html=True)

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
    cropped_img = st_cropper(raw_image, realtime_update=True, box_color='#2563eb', aspect_ratio=None)
    
    st.markdown("<br>", unsafe_allow_html=True) # مسافة جمالية
    if st.button("🔍 ابحث عن الكوتشي المحدد الآن"):
        st.markdown("---")
        with st.spinner('👔 جاري تحليل التصميم وتطابق الألوان بدقة...'):
            try:
                results = collection.query(
                    query_embeddings=[get_image_embedding(cropped_img)],
                    n_results=8,
                    include=['distances', 'metadatas']
                )
                
                if results['distances'][0]:
                    user_color_hist = get_color_histogram(cropped_img)
                    refined_results = []
                    
                    for i in range(len(results['distances'][0])):
                        meta = results['metadatas'][0][i]
                        fashion_dist = results['distances'][0][i]
                        filename = meta.get('filename', '')
                        img_path = os.path.join("compressed_images", filename)
                        
                        color_dist = 0
                        if os.path.exists(img_path):
                            db_img = Image.open(img_path)
                            db_color_hist = get_color_histogram(db_img)
                            color_dist = compare_histograms(user_color_hist, db_color_hist)
                        
                        final_score = fashion_dist + (color_dist * 0.5)
                        refined_results.append({
                            'filename': filename,
                            'final_score': final_score,
                            'metadata': meta
                        })
                    
                    refined_results.sort(key=lambda x: x['final_score'])
                    
                    st.success("✅ أفضل التطابقات:")
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
                        
                        # تصميم كارت النتيجة الاحترافي
                        st.markdown('<div class="result-card">', unsafe_allow_html=True)
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            img_path = os.path.join("compressed_images", result['filename'])
                            if os.path.exists(img_path):
                                st.image(img_path, use_container_width=True)
                        with col2:
                            st.markdown(f'<div class="code-badge">الكود: {p_code}</div>', unsafe_allow_html=True)
                            st.markdown(f'<div class="product-name">{p_name}</div>', unsafe_allow_html=True)
                            # إخفاء رقم المطابقة لأنه تفصيلة برمجية ملهاش لازمة للعميل
                        st.markdown('</div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"خطأ: {e}")