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

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="ED STORE | المتجر الرسمي", page_icon="👟", layout="wide")

# استخراج اللوجو 
def get_image_base64(img_path):
    try:
        with open(img_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    except Exception:
        return ""

logo_base64 = get_image_base64("edstore.jpg")

# --- 2. الهوية البصرية ---
st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800;900&display=swap');
        
        html, body, [class*="css"] {{
            font-family: 'Tajawal', sans-serif !important;
            direction: rtl;
        }}
        
        .stApp {{ background-color: #F0F4F8; }}
        #MainMenu {{visibility: hidden;}}
        header {{visibility: hidden;}}
        
        .block-container {{
            padding-top: 0rem !important;
            padding-bottom: 5rem !important;
            max-width: 1200px;
        }}
        
        .brand-navbar {{
            background: linear-gradient(90deg, #1C65A6 0%, #144A7A 100%);
            padding: 15px 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            width: 100%;
            margin-bottom: 30px;
            border-bottom-left-radius: 20px;
            border-bottom-right-radius: 20px;
            box-shadow: 0 4px 15px rgba(28, 101, 166, 0.3);
        }}
        .brand-navbar img {{
            height: 55px;
            margin-left: 15px;
            border-radius: 8px;
            background-color: white;
            padding: 2px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .brand-navbar h1 {{
            color: white; margin: 0; font-weight: 900; font-size: 2.2rem;
        }}
        
        .stButton > button {{
            background-color: #1C65A6 !important; color: white !important;
            border-radius: 12px; border: none; padding: 12px 24px;
            font-weight: 800; font-size: 18px; width: 100%;
            box-shadow: 0 6px 15px rgba(28, 101, 166, 0.3); transition: all 0.3s ease;
        }}
        .stButton > button:hover {{
            background-color: #144A7A !important; transform: translateY(-3px);
        }}
        
        button[role="tab"] {{ font-size: 18px !important; font-weight: 800 !important; color: #5C7C99 !important; }}
        button[role="tab"][aria-selected="true"] {{ color: #1C65A6 !important; border-bottom: 4px solid #1C65A6 !important; background-color: transparent !important; }}
        
        .product-card {{
            background: white; border-radius: 15px; padding: 20px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.05); display: flex; align-items: center;
            gap: 25px; margin-bottom: 20px; border: 1px solid #E1E8F0;
            border-right: 6px solid #1C65A6; transition: transform 0.3s ease;
        }}
        .product-card:hover {{ transform: scale(1.01); box-shadow: 0 8px 20px rgba(28, 101, 166, 0.15); }}
        .product-img {{
            width: 130px; height: 130px; object-fit: contain;
            border-radius: 10px; background-color: #F8FAFC; padding: 5px; border: 1px solid #E1E8F0;
        }}
        .code-badge {{
            background-color: #E8F0F8; color: #1C65A6; padding: 6px 15px;
            border-radius: 20px; font-size: 14px; font-weight: 800; display: inline-block; margin-bottom: 10px;
        }}
        .product-title {{ font-size: 20px; color: #0F172A; font-weight: 800; margin: 0 0 8px 0; line-height: 1.3; }}
        
        /* تصميم الرصيد (مهم) */
        .stock-badge {{
            display: inline-block; margin-top: 5px; padding: 5px 12px;
            border-radius: 8px; font-weight: 700; font-size: 15px;
        }}
        .in-stock {{ background-color: #ECFDF5; color: #059669; border: 1px solid #A7F3D0; }}
        .out-of-stock {{ background-color: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; }}
        
        .footer {{
            position: fixed; bottom: 0; left: 0; width: 100%;
            background-color: #144A7A; color: white; text-align: center;
            padding: 12px; font-weight: 500; z-index: 999;
        }}
        .footer span {{ color: #93C5FD; font-weight: 800; }}
        [data-testid="stCameraInput"] {{ border-radius: 15px; overflow: hidden; border: 2px solid #1C65A6; }}
    </style>
""", unsafe_allow_html=True)

if logo_base64:
    st.markdown(f'<div class="brand-navbar"><img src="data:image/jpeg;base64,{logo_base64}" alt="ED Store Logo"><h1>ED STORE</h1></div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="brand-navbar"><h1>ED STORE</h1></div>', unsafe_allow_html=True)

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

# --- 4. القارئ الذكي للإكسيل (استخراج الاسم والرصيد) ---
def parse_row_info(row, df_cols):
    p_code = str(row.iloc[0]).strip()
    p_name = "الاسم غير مسجل"
    p_stock = "غير محدد"
    
    # البحث عن عمود الاسم بذكاء
    name_cols = [c for c in df_cols if any(k in c.lower() for k in ['اسم', 'صنف', 'name', 'title'])]
    if name_cols: p_name = str(row[name_cols[0]]).strip()
    elif len(df_cols) > 1: p_name = str(row.iloc[1]).strip()
        
    # البحث عن عمود الرصيد بذكاء
    stock_cols = [c for c in df_cols if any(k in c.lower() for k in ['رصيد', 'كمية', 'عدد', 'stock', 'qty'])]
    if stock_cols: p_stock = str(row[stock_cols[0]]).strip()
    elif len(df_cols) > 2: p_stock = str(row.iloc[2]).strip()
        
    return p_code, p_name, p_stock

def render_product_card(p_code, p_name, p_stock):
    img_html = '<div class="product-img" style="display:flex; align-items:center; justify-content:center; color:#999; font-size:12px;">بدون صورة</div>'
    for ext in ['.jpg', '.jpeg', '.png']:
        img_path = os.path.join("compressed_images", f"{p_code}{ext}")
        if os.path.exists(img_path):
            img_base64 = get_image_base64(img_path)
            img_html = f'<img src="data:image/jpeg;base64,{img_base64}" class="product-img">'
            break
            
    # تحديد حالة الرصيد (أخضر أم أحمر)
    try:
        stock_val = float(p_stock)
        is_out = stock_val <= 0
    except:
        is_out = (p_stock == '0' or p_stock == 'صفر')
        
    stock_class = "stock-badge out-of-stock" if is_out else "stock-badge in-stock"
    stock_text = f"📦 الرصيد: {p_stock}" if p_stock != "غير محدد" else "📦 الرصيد غير محدد"
    if is_out: stock_text = "❌ نفذ من المخزون (الرصيد: 0)"

    st.markdown(f"""
    <div class="product-card">
        {img_html}
        <div class="product-details" style="flex-grow: 1;">
            <div class="code-badge">الكود: {p_code}</div>
            <h3 class="product-title">{p_name}</h3>
            <div class="{stock_class}">{stock_text}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- 5. تخطيط الموقع ---
st.markdown("### 🔍 بحث سريع بكود المنتج أو الاسم")
search_query = st.text_input("", placeholder="اكتب الكود أو اسم الصنف هنا...", label_visibility="collapsed")

if df_products is None:
    st.error("⚠️ ملف الإكسيل (products.csv) غير موجود أو به مشكلة.")
elif search_query:
    query = str(search_query).strip().lower()
    mask = pd.Series([False]*len(df_products))
    for col in df_products.columns:
        mask = mask | df_products[col].astype(str).str.lower().str.contains(query, case=False, na=False, regex=False)
    
    matched = df_products[mask]
    if not matched.empty:
        st.markdown("### ✨ نتائج البحث النصي:")
        for idx, row in matched.iterrows():
            p_code, p_name, p_stock = parse_row_info(row, df_products.columns)
            render_product_card(p_code, p_name, p_stock)
    else:
        st.warning(f"⚠️ لم يتم العثور على أي منتج يطابق: {search_query}")

st.markdown("<br><hr><br>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📸 التقاط بكاميرا الموبايل", "📁 رفع صورة من الجهاز"])
raw_image = None
with tab1:
    cam_photo = st.camera_input("وجّه الكاميرا نحو المنتج")
    if cam_photo: raw_image = Image.open(cam_photo).convert("RGB")
with tab2:
    up_file = st.file_uploader("ارفع صورة المنتج", type=["jpg", "jpeg", "png"])
    if up_file: raw_image = Image.open(up_file).convert("RGB")

if raw_image:
    st.markdown("### ✂️ قص المنتج (تحديد بؤرة البحث):")
    cropped_img = st_cropper(raw_image, realtime_update=True, box_color='#1C65A6', aspect_ratio=None)
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("🚀 ابحث عن المنتج في المستودع الآن"):
        st.markdown("---")
        with st.spinner('جاري المسح البصري وتحليل الألوان...'):
            try:
                results = collection.query(query_embeddings=[get_image_embedding(cropped_img)], n_results=8, include=['distances', 'metadatas'])
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
                            color_dist = compare_histograms(user_color_hist, get_color_histogram(db_img))
                        
                        refined_results.append({'filename': filename, 'final_score': fashion_dist + (color_dist * 0.5)})
                    
                    refined_results.sort(key=lambda x: x['final_score'])
                    st.markdown("### ✨ المنتجات المطابقة:")
                    
                    for result in refined_results[:3]:
                        p_code = result['filename'].split('.')[0]
                        p_name, p_stock = "الصنف غير مسجل بالإكسيل", "غير محدد"
                        
                        if df_products is not None:
                            target_code = str(p_code).strip().lower()
                            for col in df_products.columns:
                                cleaned_col = df_products[col].astype(str).str.strip().str.lower()
                                if (cleaned_col == target_code).any():
                                    row_idx = cleaned_col[cleaned_col == target_code].index[0]
                                    row_data = df_products.iloc[row_idx]
                                    _, p_name, p_stock = parse_row_info(row_data, df_products.columns)
                                    break
                        
                        render_product_card(p_code, p_name, p_stock)
            except Exception as e:
                st.error(f"خطأ: {e}")

st.markdown('<div class="footer">تصميم وبرمجة: <span>أبوبكر عادل</span> © 2026</div>', unsafe_allow_html=True)