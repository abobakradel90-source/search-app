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
import base64
from streamlit_cropper import st_cropper

# --- 1. إعدادات الصفحة (أول سطر لازم) ---
st.set_page_config(page_title="ED STORE | المتجر الذكي", page_icon="👟", layout="centered")

# --- 2. كود CSS الخارق (تصميم المواقع العالمية) ---
st.markdown("""
    <style>
        /* خط احترافي من جوجل */
        @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800;900&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Tajawal', sans-serif !important;
            direction: rtl;
        }
        
        /* خلفية الموقع بالكامل */
        .stApp {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }
        
        /* إخفاء قوائم Streamlit */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* يافطة الموقع (Hero Section) */
        .hero-section {
            background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
            padding: 40px 20px;
            border-radius: 20px;
            text-align: center;
            box-shadow: 0px 20px 40px rgba(0,0,0,0.2);
            color: white;
            margin-bottom: 30px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .hero-section h1 {
            font-size: 3rem;
            font-weight: 900;
            margin: 0;
            background: -webkit-linear-gradient(#fff, #f0f0f0);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .hero-section p {
            font-size: 1.2rem;
            color: #b0c4de;
            margin-top: 10px;
        }
        
        /* تصميم التابات (Tabs) */
        button[role="tab"] {
            font-size: 18px !important;
            font-weight: 700 !important;
            padding: 10px 20px !important;
            background-color: transparent;
        }
        button[role="tab"][aria-selected="true"] {
            background-color: #ffffff !important;
            color: #2563eb !important;
            border-radius: 15px 15px 0 0 !important;
            box-shadow: 0 -4px 10px rgba(0,0,0,0.05);
        }
        
        /* زرار البحث الخارق (Interactive CTA) */
        .stButton > button {
            background: linear-gradient(45deg, #FF512F 0%, #DD2476 100%);
            border: none;
            color: white !important;
            font-size: 22px;
            font-weight: 800;
            padding: 15px 30px;
            border-radius: 50px;
            box-shadow: 0 10px 25px rgba(221, 36, 118, 0.4);
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
            width: 100%;
            margin-top: 20px;
        }
        .stButton > button:hover {
            transform: scale(1.03) translateY(-3px);
            box-shadow: 0 15px 35px rgba(221, 36, 118, 0.6);
        }
        
        /* كروت المنتجات الاحترافية (Product Cards) */
        .product-card {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.08);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            display: flex;
            align-items: center;
            gap: 25px;
            margin-bottom: 20px;
            border: 1px solid rgba(255, 255, 255, 0.5);
            direction: rtl;
            text-align: right;
        }
        .product-card:hover {
            transform: translateY(-8px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.12);
        }
        .product-img {
            width: 140px;
            height: 140px;
            border-radius: 15px;
            object-fit: cover;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            background: #f8f9fa;
        }
        .product-details {
            flex-grow: 1;
        }
        .code-badge {
            display: inline-block;
            background: linear-gradient(135deg, #e0e7ff, #c7d2fe);
            color: #4f46e5;
            padding: 6px 15px;
            border-radius: 30px;
            font-size: 13px;
            font-weight: 800;
            margin-bottom: 12px;
        }
        .product-title {
            font-size: 24px;
            font-weight: 800;
            color: #1e293b;
            margin: 0 0 10px 0;
            line-height: 1.2;
        }
        .match-rate {
            font-size: 14px;
            color: #10b981;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 5px;
        }
    </style>
""", unsafe_allow_html=True)

# دالة لتحويل الصورة لكود HTML عشان تظهر في الكارت الشيك
def get_image_base64(img_path):
    with open(img_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

# --- 3. محرك الذكاء الاصطناعي (كما هو بقوته) ---
@st.cache_resource
def download_new_chroma_db():
    zip_path = "chroma_db.zip"
    extract_path = "./chroma_db"
    marker_file = "./chroma_db/fashion_clip_v3.txt"
    download_url = "https://github.com/abobakradel90-source/search-app/releases/download/v1.0/chroma_db.zip"
    
    if os.path.exists(extract_path) and not os.path.exists(marker_file):
        shutil.rmtree(extract_path)
    if not os.path.exists(extract_path):
        with st.spinner('جاري تهيئة قاعدة البيانات...'):
            try:
                urllib.request.urlretrieve(download_url, zip_path)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(".")
                if os.path.exists(zip_path):
                    os.remove(zip_path)
                with open(marker_file, 'w') as f:
                    f.write("done")
            except Exception as e: pass

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
        except Exception: return None, "Error"

df_products, error_msg = load_csv_data()

def get_image_embedding(image):
    image = ImageOps.autocontrast(image.convert("RGB"), cutoff=1)
    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        features = model.get_image_features(**inputs)
        if not isinstance(features, torch.Tensor):
            if hasattr(features, 'image_embeds'): features = features.image_embeds
            elif hasattr(features, 'pooler_output'): features = features.pooler_output
            else: features = features[0]
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

# --- 4. واجهة المستخدم HTML ---
st.markdown("""
<div class="hero-section">
    <h1>ED STORE 👟</h1>
    <p>أسرع وأدق محرك بحث بصري للملابس والأحذية</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📸 التقاط بكاميرا الموبايل", "📁 رفع من الاستوديو", "🔍 بحث بكود المنتج"])

with tab3:
    if df_products is not None:
        search_query = st.text_input("اكتب اسم أو كود المنتج هنا...")
        if search_query:
            mask = pd.Series([False]*len(df_products))
            for col in df_products.columns:
                mask = mask | df_products[col].astype(str).str.contains(search_query, case=False, na=False)
            matched = df_products[mask]
            if not matched.empty:
                for idx, row in matched.iterrows():
                    st.success(f"النتيجة: {row.to_dict()}")

raw_image = None
with tab1:
    cam_photo = st.camera_input("صور الكوتشي دلوقتي")
    if cam_photo: raw_image = Image.open(cam_photo).convert("RGB")

with tab2:
    up_file = st.file_uploader("ارفع صورة الكوتشي", type=["jpg", "jpeg", "png"])
    if up_file: raw_image = Image.open(up_file).convert("RGB")

if raw_image:
    st.markdown("### ✂️ قص الكوتشي بالمربع الأزرق:")
    cropped_img = st_cropper(raw_image, realtime_update=True, box_color='#FF512F', aspect_ratio=None)
    
    if st.button("🚀 ابحث بالذكاء الاصطناعي الآن"):
        st.markdown("---")
        with st.spinner('🎯 جاري المسح البصري وتحليل الألوان...'):
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
                    
                    st.success("✨ تم العثور على هذه التطابقات:")
                    
                    # طباعة النتائج في كروت HTML تفاعلية
                    for result in refined_results[:3]:
                        p_code = result['filename'].split('.')[0]
                        p_name = "الصنف غير مسجل بالإكسيل"
                        
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
                        
                        img_path = os.path.join("compressed_images", result['filename'])
                        if os.path.exists(img_path):
                            img_base64 = get_image_base64(img_path)
                            # الكارت السحري
                            st.markdown(f"""
                            <div class="product-card">
                                <img src="data:image/jpeg;base64,{img_base64}" class="product-img">
                                <div class="product-details">
                                    <div class="code-badge">كود: {p_code}</div>
                                    <h3 class="product-title">{p_name}</h3>
                                    <div class="match-rate">✔️ تطابق بصري ولوني عالي</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        
            except Exception as e:
                st.error(f"خطأ: {e}")