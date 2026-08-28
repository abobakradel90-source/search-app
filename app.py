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
import io
import datetime
import json
import streamlit.components.v1 as components

# --- 1. إعدادات الصفحة وبوابة الدخول ---
st.set_page_config(page_title="ED STORE | بوابة النظام", page_icon="🔒", layout="wide")

USERS = {
    "abobakr": "admin2026",    
    "mohamed": "123456",       
    "ahmed": "edstore"         
}

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = ""

# ==========================================
# 🌐 دوال الجرد التشاركي والأرشيف (الشبكة المركزية)
# ==========================================
SHARED_INV_FILE = "shared_inventory.json"
SHARED_DF_FILE = "shared_custom_df.csv"
HISTORY_FILE = "inventory_history.json"

def load_shared_inventory():
    if os.path.exists(SHARED_INV_FILE):
        try:
            with open(SHARED_INV_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {"is_active": False, "name": "", "reason": "", "date": "", "scanned_items": {}}

def save_shared_inventory(data):
    with open(SHARED_INV_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return []

def save_to_history(record):
    history = load_history()
    history.append(record)
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

def get_image_base64(img_path):
    try:
        with open(img_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    except Exception: return ""

logo_base64 = get_image_base64("edstore.jpg")

# --- 2. الهوية البصرية ---
st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800;900&display=swap');
        html, body, [class*="css"] {{ font-family: 'Tajawal', sans-serif !important; direction: rtl; }}
        .stApp {{ background-color: #F0F4F8; }}
        #MainMenu {{visibility: hidden;}} header {{visibility: hidden;}}
        .block-container {{ padding-top: 2rem !important; padding-bottom: 5rem !important; max-width: 1300px; }}
        
        .login-box {{
            background: white; padding: 40px; border-radius: 20px;
            box-shadow: 0 10px 30px rgba(28, 101, 166, 0.15);
            max-width: 450px; margin: 100px auto; text-align: center;
            border-top: 8px solid #1C65A6;
        }}
        .login-title {{ color: #1C65A6; font-weight: 900; font-size: 28px; margin-bottom: 5px; }}
        .login-subtitle {{ color: #64748B; font-size: 16px; margin-bottom: 30px; }}
        
        .brand-navbar {{
            background: linear-gradient(90deg, #1C65A6 0%, #144A7A 100%);
            padding: 15px 20px; display: flex; align-items: center; justify-content: center;
            color: white; width: 100%; margin-top: -30px; margin-bottom: 20px;
            border-bottom-left-radius: 20px; border-bottom-right-radius: 20px;
            box-shadow: 0 4px 15px rgba(28, 101, 166, 0.3);
        }}
        .brand-navbar img {{ height: 55px; margin-left: 15px; border-radius: 8px; background-color: white; padding: 2px; }}
        .brand-navbar h1 {{ color: white; margin: 0; font-weight: 900; font-size: 2.2rem; }}
        
        .stButton > button {{
            background-color: #1C65A6 !important; color: white !important;
            border-radius: 12px; border: none; padding: 12px 24px; font-weight: 800; font-size: 18px; width: 100%;
            box-shadow: 0 6px 15px rgba(28, 101, 166, 0.3); transition: all 0.3s ease;
        }}
        .stButton > button:hover {{ background-color: #144A7A !important; transform: translateY(-3px); }}
        
        .logout-btn > button {{
            background-color: #EF4444 !important; font-size: 14px !important; padding: 5px 15px !important;
            width: auto !important; margin-bottom: 20px;
        }}
        .logout-btn > button:hover {{ background-color: #DC2626 !important; }}
        
        .stTabs [data-baseweb="tab-list"] {{ gap: 20px; justify-content: center; background: white; padding: 10px; border-radius: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 20px; }}
        .stTabs [data-baseweb="tab"] {{ font-size: 20px !important; font-weight: 900 !important; color: #5C7C99 !important; padding: 10px 20px; border-radius: 10px; }}
        .stTabs [aria-selected="true"] {{ background-color: #1C65A6 !important; color: white !important; }}
        
        .product-card {{ background: white; border-radius: 15px; padding: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); display: flex; align-items: center; gap: 25px; margin-bottom: 20px; border: 1px solid #E1E8F0; border-right: 6px solid #1C65A6; transition: transform 0.3s ease; }}
        .product-img {{ width: 130px; height: 130px; object-fit: contain; border-radius: 10px; background-color: #F8FAFC; padding: 5px; border: 1px solid #E1E8F0; }}
        .code-badge {{ background-color: #E8F0F8; color: #1C65A6; padding: 6px 15px; border-radius: 20px; font-size: 14px; font-weight: 800; display: inline-block; margin-bottom: 10px; }}
        .product-title {{ font-size: 20px; color: #0F172A; font-weight: 800; margin: 0 0 8px 0; line-height: 1.3; }}
        
        .stock-badge {{ display: inline-block; margin-top: 5px; padding: 5px 12px; border-radius: 8px; font-weight: 700; font-size: 15px; }}
        .in-stock {{ background-color: #ECFDF5; color: #059669; border: 1px solid #A7F3D0; }}
        .out-of-stock {{ background-color: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; }}
        
        .metric-card {{ background: white; padding: 20px; border-radius: 15px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.05); border-bottom: 4px solid #1C65A6; }}
        .metric-title {{ color: #64748B; font-size: 18px; font-weight: 700; margin-bottom: 10px; }}
        .metric-value {{ color: #0F172A; font-size: 36px; font-weight: 900; }}
        
        .inv-active-bar {{ background: linear-gradient(90deg, #10B981, #059669); color: white; padding: 15px; border-radius: 10px; margin-bottom: 20px; font-weight: bold; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 10px rgba(16, 185, 129, 0.3); }}
        
        .footer {{ position: fixed; bottom: 0; left: 0; width: 100%; background-color: #144A7A; color: white; text-align: center; padding: 12px; font-weight: 500; z-index: 999; }}
        .footer span {{ color: #93C5FD; font-weight: 800; }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🛑 بوابة تسجيل الدخول
# ==========================================
if not st.session_state.logged_in:
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    if logo_base64:
        st.markdown(f'<img src="data:image/jpeg;base64,{logo_base64}" style="height: 80px; border-radius:10px; margin-bottom:15px;">', unsafe_allow_html=True)
    st.markdown('<div class="login-title">نظام إدارة ED STORE</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-subtitle">برجاء تسجيل الدخول للمتابعة</div>', unsafe_allow_html=True)
    
    username = st.text_input("👤 اسم المستخدم", placeholder="ادخل اليوزر نيم")
    password = st.text_input("🔑 كلمة المرور", placeholder="ادخل الباسورد", type="password")
    
    if st.button("تسجيل الدخول 🚀"):
        clean_user = str(username).strip().lower()
        clean_pass = str(password).strip()
        
        if clean_user in USERS and USERS[clean_user] == clean_pass:
            st.session_state.logged_in = True
            st.session_state.current_user = clean_user
            st.rerun()
        else:
            st.error("❌ البيانات غير صحيحة، تأكد من اسم المستخدم أو كلمة المرور.")
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==========================================
# ✅ محتوى الموقع بعد تسجيل الدخول
# ==========================================
if logo_base64:
    st.markdown(f'<div class="brand-navbar"><img src="data:image/jpeg;base64,{logo_base64}" alt="ED Store Logo"><h1>ED STORE</h1></div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="brand-navbar"><h1>ED STORE</h1></div>', unsafe_allow_html=True)

col_welc, col_out = st.columns([4, 1])
with col_welc:
    st.markdown(f"<h4 style='color:#1C65A6;'>👤 مرحباً بك: <b>{st.session_state.current_user}</b></h4>", unsafe_allow_html=True)
with col_out:
    st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
    if st.button("تسجيل خروج 🚪"):
        st.session_state.logged_in = False
        st.session_state.current_user = ""
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- 3. محرك الذكاء الاصطناعي والدوال ---
@st.cache_resource
def download_new_chroma_db():
    zip_path = "chroma_db.zip"
    extract_path = "./chroma_db"
    marker_file = "./chroma_db/fashion_clip_v3.txt"
    download_url = "https://github.com/abobakradel90-source/search-app/releases/download/v1.0/chroma_db.zip"
    if os.path.exists(extract_path) and not os.path.exists(marker_file): shutil.rmtree(extract_path)
    if not os.path.exists(extract_path):
        with st.spinner('📦 جاري تهيئة مستودع البيانات الذكي...'):
            try:
                urllib.request.urlretrieve(download_url, zip_path)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref: zip_ref.extractall(".")
                if os.path.exists(zip_path): os.remove(zip_path)
                with open(marker_file, 'w') as f: f.write("done")
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

try: model, processor, collection = load_vision_system()
except Exception as e: st.error(f"⚠️ حدث خطأ في محرك الذكاء الاصطناعي: {e}")

@st.cache_data
def load_csv_data():
    try:
        df = pd.read_csv('products.csv', encoding='utf-8-sig', on_bad_lines='skip', engine='python')
        df.columns = df.columns.astype(str).str.strip()
        return df
    except: return None

df_products = load_csv_data()

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
    img = image.convert("RGB").crop((image.size[0]*0.15, image.size[1]*0.15, image.size[0]*0.85, image.size[1]*0.85))
    hist = img.histogram() 
    total = sum(hist) / 3
    return [x / (total if total > 0 else 1) for x in hist]

def compare_histograms(h1, h2): return sum(abs(a - b) for a, b in zip(h1, h2))

def parse_row_info(row, df_cols):
    raw_code = str(row.iloc[0]).strip()
    p_code = raw_code.split('.')[0] 
    p_name, p_stock = "الاسم غير مسجل", "0"
    
    name_cols = [c for c in df_cols if any(k in c.lower() for k in ['اسم', 'صنف', 'name', 'title'])]
    if name_cols: p_name = str(row[name_cols[0]]).strip()
    elif len(df_cols) > 1: p_name = str(row.iloc[1]).strip()
        
    stock_cols = [c for c in df_cols if any(k in c.lower() for k in ['رصيد', 'كمية', 'عدد', 'stock', 'qty'])]
    if stock_cols: p_stock = str(row[stock_cols[0]]).strip()
    elif len(df_cols) > 2: p_stock = str(row.iloc[2]).strip()
        
    return p_code, p_name, p_stock

def render_product_card(p_code, p_name, p_stock, custom_message="", details_html=""):
    img_html = '<div class="product-img" style="display:flex; align-items:center; justify-content:center; color:#999; font-size:12px;">بدون صورة</div>'
    for ext in ['.jpg', '.jpeg', '.png', '.JPG']:
        img_path = os.path.join("compressed_images", f"{p_code}{ext}")
        if os.path.exists(img_path):
            img_base64 = get_image_base64(img_path)
            img_html = f'<img src="data:image/jpeg;base64,{img_base64}" class="product-img">'
            break
            
    try: is_out = float(p_stock) <= 0
    except: is_out = (str(p_stock).strip() in ['0', 'صفر'])
        
    stock_class = "stock-badge out-of-stock" if is_out else "stock-badge in-stock"
    stock_text = f"📦 الرصيد الدفتري: {p_stock}"
    msg_html = f'<div style="margin-top:10px; color:#1C65A6; font-weight:bold;">{custom_message}</div>' if custom_message else ""

    html_str = f"""<div class="product-card">
{img_html}
<div class="product-details" style="flex-grow: 1;">
<div class="code-badge">الكود: {p_code}</div>
<h3 class="product-title">{p_name}</h3>
<div class="{stock_class}">{stock_text}</div>
{details_html}
{msg_html}
</div>
</div>"""
    st.markdown(html_str, unsafe_allow_html=True)

# --- 4. التخطيط الرئيسي ---
main_tab1, main_tab2 = st.tabs(["🔍 محرك البحث الذكي", "📦 نظام إدارة الجرد والمخازن"])

with main_tab1:
    st.markdown("### 🔍 بحث سريع بكود المنتج أو الاسم")
    search_query = st.text_input("", placeholder="اكتب الكود أو اسم الصنف هنا...", key="search_bar", label_visibility="collapsed")

    if df_products is not None and search_query:
        query = str(search_query).strip().lower().split('.')[0]
        mask = pd.Series([False]*len(df_products))
        for col in df_products.columns:
            mask = mask | df_products[col].astype(str).str.lower().str.contains(query, case=False, na=False, regex=False)
        matched = df_products[mask]
        if not matched.empty:
            st.markdown("### ✨ نتائج البحث النصي:")
            for idx, row in matched.iterrows():
                p_code, p_name, p_stock = parse_row_info(row, df_products.columns)
                details = " | ".join([f"<b>{col}:</b> {row[col]}" for col in df_products.columns])
                details_html = f'<div style="color: #64748B; font-size: 14px; margin-top: 8px;">{details}</div>'
                render_product_card(p_code, p_name, p_stock, details_html=details_html)
        else: st.warning("⚠️ لم يتم العثور على أي منتج يطابق بحثك.")
    
    st.markdown("<br><hr><br>", unsafe_allow_html=True)

    cam_tab, upload_tab = st.tabs(["📸 التقاط بكاميرا الموبايل", "📁 رفع صورة من الجهاز"])
    raw_image = None
    with cam_tab:
        cam_photo = st.camera_input("وجّه الكاميرا نحو المنتج")
        if cam_photo: raw_image = Image.open(cam_photo).convert("RGB")
    with upload_tab:
        up_file = st.file_uploader("ارفع صورة المنتج", type=["jpg", "jpeg", "png"])
        if up_file: raw_image = Image.open(up_file).convert("RGB")

    if raw_image:
        st.markdown("### ✂️ قص المنتج (تحديد بؤرة البحث):")
        cropped_img = st_cropper(raw_image, realtime_update=True, box_color='#1C65A6', aspect_ratio=None)
        if st.button("🚀 ابحث عن المنتج في المستودع الآن"):
            with st.spinner('جاري المسح البصري...'):
                try:
                    results = collection.query(query_embeddings=[get_image_embedding(cropped_img)], n_results=8, include=['distances', 'metadatas'])
                    if results['distances'][0]:
                        user_color = get_color_histogram(cropped_img)
                        refined = []
                        for i in range(len(results['distances'][0])):
                            meta = results['metadatas'][0][i]
                            fn = meta.get('filename', '')
                            dist = results['distances'][0][i]
                            c_dist = 0
                            img_p = os.path.join("compressed_images", fn)
                            if os.path.exists(img_p):
                                c_dist = compare_histograms(user_color, get_color_histogram(Image.open(img_p)))
                            refined.append({'fn': fn, 'score': dist + (c_dist * 0.5)})
                        refined.sort(key=lambda x: x['score'])
                        st.markdown("### ✨ المنتجات المطابقة:")
                        for res in refined[:3]:
                            p_code = res['fn'].split('.')[0]
                            p_name, p_stock = "غير مسجل", "0"
                            if df_products is not None:
                                tc = str(p_code).strip().lower()
                                for col in df_products.columns:
                                    cleaned = df_products[col].astype(str).str.strip().str.lower().str.replace('.jpg','',regex=False).str.replace('.png','',regex=False)
                                    if (cleaned == tc).any():
                                        row_idx = cleaned[cleaned == tc].index[0]
                                        row_data = df_products.loc[row_idx]
                                        _, p_name, p_stock = parse_row_info(row_data, df_products.columns)
                                        break
                            render_product_card(p_code, p_name, p_stock)
                except Exception as e: st.error(f"⚠️ حدث خطأ في البحث البصري: {e}")

# ==========================================
# 🌐 التبويب الثاني: مديول الجرد الشبكي المتكامل
# ==========================================
with main_tab2:
    shared_inv = load_shared_inventory()
    
    if not shared_inv.get("is_active", False):
        st.markdown("### 🆕 إعداد جلسة جرد تشاركية جديدة")
        with st.form("inv_setup_form"):
            col1, col2, col3 = st.columns(3)
            with col1: inv_name = st.text_input("اسم/رقم الجرد", placeholder="مثال: جرد شهر أغسطس")
            with col2: inv_reason = st.selectbox("سبب الجرد", ["جرد دوري", "جرد مفاجئ", "تسليم عهدة", "جرد نهاية العام", "أخرى"])
            with col3: inv_date = st.date_input("تاريخ الجرد", datetime.date.today())
            
            uploaded_inv_file = st.file_uploader("📎 رفع ملف الأرصدة الدفترية اللحظية (Excel/CSV) - اختياري", type=['csv', 'xlsx'])
            
            submitted_setup = st.form_submit_button("🚀 فتح جلسة الجرد للجميع")
            if submitted_setup:
                if not inv_name: st.error("⚠️ برجاء كتابة اسم أو رقم الجرد أولاً!")
                else:
                    if uploaded_inv_file is not None:
                        try:
                            if uploaded_inv_file.name.endswith('.csv'): 
                                df_custom = pd.read_csv(uploaded_inv_file, encoding='utf-8-sig')
                            else: 
                                df_custom = pd.read_excel(uploaded_inv_file)
                            df_custom.to_csv(SHARED_DF_FILE, index=False, encoding='utf-8-sig')
                        except:
                            st.error("خطأ في الملف المرفق، سيتم استخدام الأرصدة الأساسية.")
                            if os.path.exists(SHARED_DF_FILE): os.remove(SHARED_DF_FILE)
                    else:
                        if os.path.exists(SHARED_DF_FILE): os.remove(SHARED_DF_FILE)
                    
                    data = {
                        "is_active": True,
                        "name": inv_name,
                        "reason": inv_reason,
                        "date": str(inv_date),
                        "scanned_items": {}
                    }
                    save_shared_inventory(data)
                    st.rerun()
    else:
        st.markdown(f"""
        <div class="inv-active-bar">
            <div>📌 <b>جرد شبكي نشط:</b> {shared_inv.get('name')} &nbsp;|&nbsp; <b>السبب:</b> {shared_inv.get('reason')} &nbsp;|&nbsp; <b>التاريخ:</b> {shared_inv.get('date')}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if os.path.exists(SHARED_DF_FILE):
            try: active_df = pd.read_csv(SHARED_DF_FILE, encoding='utf-8-sig')
            except: active_df = df_products
        else:
            active_df = df_products
            
        if active_df is None: st.error("⚠️ لا توجد داتا أرصدة لإجراء الجرد!")
        else:
            inv_tab1, inv_tab2, inv_tab3 = st.tabs(["📊 ملخص الأرصدة", "🔫 مسح الباركود الفعلي", "⚖️ تقرير الفروقات (تصدير)"])
            
            total_items = len(active_df)
            out_of_stock, total_qty = 0, 0
            system_inventory = {} 
            
            for idx, row in active_df.iterrows():
                code, name, stock = parse_row_info(row, active_df.columns)
                try: s_val = float(stock)
                except: s_val = 0
                total_qty += s_val
                if s_val <= 0: out_of_stock += 1
                system_inventory[code] = {'name': name, 'sys_stock': s_val}
                
            scanned_items = shared_inv.get("scanned_items", {})
            total_scanned = sum(scanned_items.values())

            with inv_tab1:
                st.markdown("### 📊 ملخص الأرصدة الدفترية لهذه الجلسة")
                col1, col2, col3 = st.columns(3)
                with col1: st.markdown(f'<div class="metric-card"><div class="metric-title">الأصناف الدفترية</div><div class="metric-value" style="color:#1C65A6;">{total_items}</div></div>', unsafe_allow_html=True)
                with col2: st.markdown(f'<div class="metric-card" style="border-color:#10B981;"><div class="metric-title">القطع المتوفرة</div><div class="metric-value" style="color:#10B981;">{int(total_qty)}</div></div>', unsafe_allow_html=True)
                with col3: st.markdown(f'<div class="metric-card" style="border-color:#DC2626;"><div class="metric-title">أصناف صفرية</div><div class="metric-value" style="color:#DC2626;">{out_of_stock}</div></div>', unsafe_allow_html=True)
                st.markdown(f"<br>### 🛒 إجمالي ما تم مسحه فعلياً من جميع الموظفين: **{total_scanned}** قطعة", unsafe_allow_html=True)
                if st.button("🔄 تحديث الأرقام (ريفرش)"): st.rerun()

            with inv_tab2:
                st.markdown("### 🔫 مسح الباركود للجرد (التحقق قبل الإضافة أو الخصم)")
                
                if "scan_input" not in st.session_state: st.session_state.scan_input = ""
                if "last_success_msg" not in st.session_state: st.session_state.last_success_msg = ""
                if "clear_scan" not in st.session_state: st.session_state.clear_scan = False
                
                if st.session_state.clear_scan:
                    st.session_state.scan_input = ""
                    st.session_state.clear_scan = False
                
                if st.session_state.last_success_msg:
                    st.success(st.session_state.last_success_msg)
                    st.session_state.last_success_msg = ""

                scan_code = st.text_input("كود الصنف (الباركود):", key="scan_input")
                
                if scan_code:
                    clean_code = str(scan_code).strip().upper()
                    found = False
                    for sys_c in system_inventory.keys():
                        if sys_c.upper() == clean_code:
                            clean_code = sys_c 
                            found = True
                            break
                            
                    if found:
                        st.info("✅ تم العثور على الصنف. تأكد من البيانات ثم أضف/اخصم الكمية:")
                        render_product_card(clean_code, system_inventory[clean_code]['name'], system_inventory[clean_code]['sys_stock'])
                        
                        with st.form("confirm_add_form"):
                            add_qty = st.number_input("الكمية المضافة أو المخصومة (اكتب - قبل الرقم للخصم):", value=1)
                            confirmed = st.form_submit_button("تأكيد العملية 📥")
                            
                            if confirmed:
                                latest_inv = load_shared_inventory()
                                if "scanned_items" not in latest_inv: latest_inv["scanned_items"] = {}
                                
                                current_qty = latest_inv["scanned_items"].get(clean_code, 0)
                                new_qty = current_qty + add_qty
                                if new_qty < 0: new_qty = 0
                                    
                                latest_inv["scanned_items"][clean_code] = new_qty
                                save_shared_inventory(latest_inv)
                                
                                action_word = "إضافة" if add_qty >= 0 else "خصم"
                                abs_qty = abs(add_qty)
                                
                                st.session_state.last_success_msg = f"✅ تمت {action_word} ({abs_qty}) للصنف: {clean_code} | إجمالي الصنف الفعلي الآن: {latest_inv['scanned_items'][clean_code]}"
                                st.session_state.clear_scan = True
                                st.rerun()
                    else:
                        st.error(f"❌ الباركود ({scan_code}) غير مسجل في أرصدة هذه الجلسة!")
                        if st.button("مسح الكود والمحاولة مرة أخرى"):
                            st.session_state.clear_scan = True
                            st.rerun()

                js_code = """
                <script>
                const focusInput = () => {
                    const doc = window.parent.document;
                    const isScanEmpty = "%s" === "";
                    if (isScanEmpty) {
                        const inputs = doc.querySelectorAll('input[type="text"]');
                        for (let input of inputs) {
                            if (input.getAttribute('aria-label') === 'كود الصنف (الباركود):') {
                                input.focus();
                                break;
                            }
                        }
                    } else {
                        const numInputs = doc.querySelectorAll('input[type="number"]');
                        if(numInputs.length > 0) {
                            numInputs[0].focus();
                        }
                    }
                };
                focusInput();
                setTimeout(focusInput, 100);
                setTimeout(focusInput, 500);
                </script>
                """ % (st.session_state.scan_input)
                components.html(js_code, height=0)

            with inv_tab3:
                st.markdown("### ⚖️ تقرير الفروقات النهائي (الرصيد الدفتري vs الفعلي)")
                report_data = []
                for code, info in system_inventory.items():
                    sys_qty = info['sys_stock']
                    actual_qty = scanned_items.get(code, 0)
                    variance = actual_qty - sys_qty
                    status = "🟢 مطابق"
                    if variance > 0: status = "🔵 زيادة"
                    elif variance < 0: status = "🔴 عجز"
                    report_data.append({"كود الصنف": code, "اسم الصنف": info['name'], "الرصيد الدفتري": sys_qty, "الرصيد الفعلي": actual_qty, "الفروقات (عجز/زيادة)": variance, "الحالة": status})
                    
                df_report = pd.DataFrame(report_data)
                def color_variance(val):
                    if val < 0: return 'color: red; font-weight: bold;'
                    elif val > 0: return 'color: blue; font-weight: bold;'
                    return 'color: green;'
                st.dataframe(df_report.style.map(color_variance, subset=['الفروقات (عجز/زيادة)']), use_container_width=True, hide_index=True)
                st.markdown("<br>", unsafe_allow_html=True)
                
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_report.to_excel(writer, index=False, sheet_name='تقرير الجرد')
                
                st.download_button(
                    label="📥 تحميل التقرير النهائي للتسليم (Excel)",
                    data=buffer.getvalue(),
                    file_name=f"Inventory_Report_{shared_inv.get('name')}_{shared_inv.get('date')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                st.markdown("---")
                
                # إخفاء زرار الإغلاق عن الموظفين، وإظهاره للأدمن فقط مع ميزة الأرشفة
                if st.session_state.current_user == "abobakr":
                    if st.button("🛑 إغلاق وإنهاء جلسة الجرد للجميع وحفظها بالأرشيف"):
                        record = {
                            "timestamp": str(datetime.datetime.now()),
                            "name": shared_inv.get('name', 'بدون اسم'),
                            "date": shared_inv.get('date', ''),
                            "reason": shared_inv.get('reason', ''),
                            "report": report_data
                        }
                        save_to_history(record)
                        
                        latest_inv = load_shared_inventory()
                        latest_inv["is_active"] = False
                        latest_inv["scanned_items"] = {}
                        save_shared_inventory(latest_inv)
                        if os.path.exists(SHARED_DF_FILE): os.remove(SHARED_DF_FILE)
                        st.rerun()
                else:
                    st.info("🔒 صلاحية إنهاء وإغلاق الجرد متاحة للإدارة (abobakr) فقط.")

    # ==========================================
    # 📁 أرشيف الإدارة (يظهر فقط للأدمن abobakr)
    # ==========================================
    if st.session_state.current_user == "abobakr":
        st.markdown("<br><hr>", unsafe_allow_html=True)
        st.markdown("### 📁 أرشيف جلسات الجرد السابقة (للإدارة فقط)")
        
        history = load_history()
        if not history:
            st.info("لا توجد جلسات جرد سابقة محفوظة في الأرشيف.")
        else:
            for idx, record in enumerate(reversed(history)):
                with st.expander(f"📌 جرد: {record['name']} | التاريخ: {record['date']} | السبب: {record['reason']}"):
                    df_hist = pd.DataFrame(record['report'])
                    
                    def color_variance_hist(val):
                        if val < 0: return 'color: red; font-weight: bold;'
                        elif val > 0: return 'color: blue; font-weight: bold;'
                        return 'color: green;'
                        
                    st.dataframe(df_hist.style.map(color_variance_hist, subset=['الفروقات (عجز/زيادة)']), use_container_width=True, hide_index=True)
                    
                    buffer_hist = io.BytesIO()
                    with pd.ExcelWriter(buffer_hist, engine='openpyxl') as writer:
                        df_hist.to_excel(writer, index=False, sheet_name='تقرير الجرد')
                    
                    st.download_button(
                        label=f"📥 تحميل تقرير {record['name']} (Excel)",
                        data=buffer_hist.getvalue(),
                        file_name=f"Archive_{record['name']}_{record['date']}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"dl_hist_{idx}"
                    )

st.markdown('<div class="footer">تصميم وبرمجة: <span>أبوبكر عادل</span> © 2026</div>', unsafe_allow_html=True)