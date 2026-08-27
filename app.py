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
st.set_page_config(page_title="ED STORE | Amazon Style", page_icon="🛒", layout="wide")

# دالة لتحويل الصور (اللوجو) لـ Base64 عشان نعرضها في الـ HTML
def get_image_base64(img_path):
    try:
        with open(img_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    except Exception:
        return "" # لو اللوجو مش موجود ميعملش إيرور

logo_base64 = get_image_base64("edstore.jpg")

# --- 2. كود CSS لمحاكاة تصميم Amazon ---
st.markdown(f"""
    <style>
        /* خط احترافي */
        @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800;900&display=swap');
        
        html, body, [class*="css"] {{
            font-family: 'Tajawal', sans-serif !important;
            direction: rtl;
        }}
        
        /* لون خلفية الموقع زي أمازون (رمادي فاتح جداً) */
        .stApp {{
            background-color: #EAEDED;
        }}
        
        /* تقليل الفراغ العلوي ليصبح الشريط بالأعلى تماماً */
        .block-container {{
            padding-top: 0rem !important;
            padding-bottom: 5rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: 1400px;
        }}
        
        /* إخفاء قوائم Streamlit */
        #MainMenu {{visibility: hidden;}}
        header {{visibility: hidden;}}
        
        /* الشريط العلوي (Amazon Navbar) */
        .amazon-navbar {{
            background-color: #131921;
            padding: 10px 20px;
            display: flex;
            align-items: center;
            color: white;
            width: 100%;
            margin-bottom: 20px;
            border-bottom: 2px solid #232f3e;
        }}
        .amazon-navbar img {{
            height: 45px;
            margin-left: 20px;
            border-radius: 5px;
            object-fit: contain;
            background-color: white;
            padding: 2px;
        }}
        .amazon-navbar h2 {{
            color: white;
            margin: 0;
            font-weight: 800;
            font-size: 1.8rem;
        }}
        
        /* ستايل التابات (زي الأقسام في أمازون) */
        button[role="tab"] {{
            font-size: 16px !important;
            font-weight: 700 !important;
            color: #0F1111 !important;
            background-color: transparent;
        }}
        button[role="tab"][aria-selected="true"] {{
            background-color: transparent !important;
            color: #E47911 !important; /* لون أمازون البرتقالي */
            border-bottom: 3px solid #E47911 !important;
        }}
        
        /* كروت المنتجات (Product Cards) */
        .product-card {{
            background: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            transition: box-shadow 0.3s ease;
            display: flex;
            align-items: center;
            gap: 20px;
            margin-bottom: 15px;
            border: 1px solid #ddd;
        }}
        .product-card:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        .product-img {{
            width: 120px;
            height: 120px;
            object-fit: contain;
        }}
        .code-badge {{
            color: #565959;
            font-size: 14px;
            margin-bottom: 5px;
        }}
        .product-title {{
            font-size: 18px;
            color: #0F1111;
            font-weight: 700;
            margin: 0 0 10px 0;
        }}
        
        /* زرار البحث الأساسي */
        .stButton > button {{
            background-color: #FFD814;
            border: 1px solid #FCD200;
            color: #0F1111 !important;
            border-radius: 8px;
            padding: 10px 20px;
            font-weight: 700;
            font-size: 16px;
            transition: background-color 0.2s;
            width: 100%;
        }}
        .stButton > button:hover {{
            background-color: #F7CA00;
            border-color: #F2C200;
        }}
        
        /* شريط حقوق الملكية السفلي */
        .footer {{
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            background-color: #232F3E;
            color: white;
            text-align: center;
            padding: 12px;
            font-family: 'Tajawal', sans-serif;
            font-size: 14px;
            font-weight: 500;
            z-index: 999;
            border-top: 1px solid #131921;
        }}
        .footer span {{
            color: #FF9900;
            font-weight: 700;
        }}
    </style>
""", unsafe_allow_html=True)

# --- واجهة Amazon العلوية (Navbar) ---
if logo_base64:
    st.markdown(f"""
    <div class="amazon-navbar">
        <img src="data:image/jpeg;base64,{logo_base64}" alt="ED Store Logo">
        <h2>ED STORE</h2>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="amazon-navbar">
        <h2>ED STORE</h2>
    </div>
    """, unsafe_allow_html=True)

# --- 3. محرك الذكاء الاصطناعي ---
@st.cache_resource
def download_new_chroma_db():
    zip_path = "chroma_db.zip"
    extract_path = "./chroma_db"
    marker_file = "./chroma_db/fashion_clip_v3.txt"
    download_url = "https://github.com/abobakradel90-source/search-app/releases/download/v1.0/chroma_db.zip"
    
    if os.path.exists(extract_path) and not os.path.exists(marker_file):
        shutil.rmtree(extract_path)
    if not os.path.exists(extract_path):
        with st.spinner('جاري تهيئة النظام...'):
            try:
                urllib.request.urlretrieve(download_url, zip_path)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(".")
                if os.path.exists(zip_path):
                    os.remove(zip_path)
                with open(marker_file, 'w') as f:
                    f.write("done")
            except Exception: pass

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

# --- 4. تخطيط الموقع (Amazon Layout) ---

# شريط البحث النصي (الأساسي فوق زي أمازون)
col_search, col_empty = st.columns([2, 1])
with col_search:
    search_query = st.text_input("بحث في ED STORE", placeholder="اكتب اسم أو كود المنتج هنا...", label_visibility="collapsed")
    if search_query and df_products is not None:
        mask = pd.Series([False]*len(df_products))
        for col in df_products.columns:
            mask = mask | df_products[col].astype(str).str.contains(search_query, case=False, na=False)
        matched = df_products[mask]
        if not matched.empty:
            for idx, row in matched.iterrows():
                st.success(f"نتيجة البحث: {row.to_dict()}")

st.markdown("---")

# تقسيم البحث البصري
tab1, tab2 = st.tabs(["📸 بحث بكاميرا الموبايل", "📁 بحث بصورة من الجهاز"])

raw_image = None
with tab1:
    # تنسيق الكاميرا عشان متكونش مالية الشاشة
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        cam_photo = st.camera_input("وجّه الكاميرا نحو المنتج")
        if cam_photo: raw_image = Image.open(cam_photo).convert("RGB")

with tab2:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        up_file = st.file_uploader("اختر صورة المنتج", type=["jpg", "jpeg", "png"])
        if up_file: raw_image = Image.open(up_file).convert("RGB")

if raw_image:
    st.markdown("### ✂️ تحديد المنتج:")
    # تصغير حجم أداة القص لتناسب التصميم
    crop_col1, crop_col2, crop_col3 = st.columns([1, 2, 1])
    with crop_col2:
        cropped_img = st_cropper(raw_image, realtime_update=True, box_color='#E47911', aspect_ratio=None)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # زرار البحث زي أمازون
    btn_col1, btn_col2, btn_col3 = st.columns([1, 2, 1])
    with btn_col2:
        if st.button("🔍 بحث عن المنتج المطابق"):
            st.markdown("---")
            with st.spinner('جاري البحث في المستودع...'):
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
                        
                        st.subheader("المنتجات المطابقة:")
                        
                        # طباعة النتائج في كروت أمازون
                        for result in refined_results[:3]:
                            p_code = result['filename'].split('.')[0]
                            p_name = "غير مسجل بالإكسيل"
                            
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
                                st.markdown(f"""
                                <div class="product-card">
                                    <img src="data:image/jpeg;base64,{img_base64}" class="product-img">
                                    <div>
                                        <div class="code-badge">الكود: {p_code}</div>
                                        <h3 class="product-title">{p_name}</h3>
                                        <div style="color: #007185; font-size: 14px;">✓ متوفر في المستودع</div>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                            
                except Exception as e:
                    st.error(f"خطأ: {e}")

# --- 5. شريط حقوق الملكية السفلي (Footer) ---
st.markdown("""
<div class="footer">
    تصميم وبرمجة: <span>أبوبكر عادل</span> © 2026
</div>
""", unsafe_allow_html=True)