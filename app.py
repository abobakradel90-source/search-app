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
# 🌐 دوال إدارة قواعد البيانات (JSON)
# ==========================================
SHARED_INV_FILE = "shared_inventory.json"
SHARED_DF_FILE = "shared_custom_df.csv"
HISTORY_INV_FILE = "inventory_history.json"

SHARED_SALES_FILE = "shared_sales.json"
HISTORY_SALES_FILE = "sales_history.json"

# -- دوال الجرد --
def load_shared_inventory():
    if os.path.exists(SHARED_INV_FILE):
        try:
            with open(SHARED_INV_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return {"is_active": False, "name": "", "reason": "", "date": "", "scanned_items": {}}

def save_shared_inventory(data):
    with open(SHARED_INV_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)

def load_inv_history():
    if os.path.exists(HISTORY_INV_FILE):
        try:
            with open(HISTORY_INV_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return []

def save_to_inv_history(record):
    history = load_inv_history()
    history.append(record)
    with open(HISTORY_INV_FILE, 'w', encoding='utf-8') as f: json.dump(history, f, ensure_ascii=False, indent=4)

# -- دوال المبيعات (POS) --
def load_shared_sales():
    if os.path.exists(SHARED_SALES_FILE):
        try:
            with open(SHARED_SALES_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return {"is_active": False, "name": "", "date": "", "transactions": [], "deductions": {}}

def save_shared_sales(data):
    with open(SHARED_SALES_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)

def load_sales_history():
    if os.path.exists(HISTORY_SALES_FILE):
        try:
            with open(HISTORY_SALES_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return []

def save_to_sales_history(record):
    history = load_sales_history()
    history.append(record)
    with open(HISTORY_SALES_FILE, 'w', encoding='utf-8') as f: json.dump(history, f, ensure_ascii=False, indent=4)

def get_image_base64(img_path):
    try:
        with open(img_path, "rb") as img_file: return base64.b64encode(img_file.read()).decode('utf-8')
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
        .login-box {{ background: white; padding: 40px; border-radius: 20px; box-shadow: 0 10px 30px rgba(28, 101, 166, 0.15); max-width: 450px; margin: 100px auto; text-align: center; border-top: 8px solid #1C65A6; }}
        .login-title {{ color: #1C65A6; font-weight: 900; font-size: 28px; margin-bottom: 5px; }}
        .login-subtitle {{ color: #64748B; font-size: 16px; margin-bottom: 30px; }}
        .brand-navbar {{ background: linear-gradient(90deg, #1C65A6 0%, #144A7A 100%); padding: 15px 20px; display: flex; align-items: center; justify-content: center; color: white; width: 100%; margin-top: -30px; margin-bottom: 20px; border-bottom-left-radius: 20px; border-bottom-right-radius: 20px; box-shadow: 0 4px 15px rgba(28, 101, 166, 0.3); }}
        .brand-navbar img {{ height: 55px; margin-left: 15px; border-radius: 8px; background-color: white; padding: 2px; }}
        .brand-navbar h1 {{ color: white; margin: 0; font-weight: 900; font-size: 2.2rem; }}
        .stButton > button {{ background-color: #1C65A6 !important; color: white !important; border-radius: 12px; border: none; padding: 12px 24px; font-weight: 800; font-size: 18px; width: 100%; box-shadow: 0 6px 15px rgba(28, 101, 166, 0.3); transition: all 0.3s ease; }}
        .stButton > button:hover {{ background-color: #144A7A !important; transform: translateY(-3px); }}
        .logout-btn > button {{ background-color: #EF4444 !important; font-size: 14px !important; padding: 5px 15px !important; width: auto !important; margin-bottom: 20px; }}
        .logout-btn > button:hover {{ background-color: #DC2626 !important; }}
        .stTabs [data-baseweb="tab-list"] {{ gap: 20px; justify-content: center; background: white; padding: 10px; border-radius: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 20px; flex-wrap: wrap; }}
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
        .sales-active-bar {{ background: linear-gradient(90deg, #F59E0B, #D97706); color: white; padding: 15px; border-radius: 10px; margin-bottom: 20px; font-weight: bold; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 10px rgba(245, 158, 11, 0.3); }}
        .footer {{ position: fixed; bottom: 0; left: 0; width: 100%; background-color: #144A7A; color: white; text-align: center; padding: 12px; font-weight: 500; z-index: 999; }}
        .footer span {{ color: #93C5FD; font-weight: 800; }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🛑 بوابة تسجيل الدخول
# ==========================================
if not st.session_state.logged_in:
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    if logo_base64: st.markdown(f'<img src="data:image/jpeg;base64,{logo_base64}" style="height: 80px; border-radius:10px; margin-bottom:15px;">', unsafe_allow_html=True)
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
        else: st.error("❌ البيانات غير صحيحة.")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==========================================
# ✅ محتوى الموقع
# ==========================================
if logo_base64: st.markdown(f'<div class="brand-navbar"><img src="data:image/jpeg;base64,{logo_base64}" alt="ED Store Logo"><h1>ED STORE</h1></div>', unsafe_allow_html=True)
else: st.markdown('<div class="brand-navbar"><h1>ED STORE</h1></div>', unsafe_allow_html=True)

col_welc, col_out = st.columns([4, 1])
with col_welc: st.markdown(f"<h4 style='color:#1C65A6;'>👤 مرحباً بك: <b>{st.session_state.current_user}</b></h4>", unsafe_allow_html=True)
with col_out:
    st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
    if st.button("تسجيل خروج 🚪"):
        st.session_state.logged_in = False
        st.session_state.current_user = ""
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- محرك الذكاء والدوال ---
@st.cache_resource
def download_new_chroma_db():
    zip_path, extract_path, marker_file = "chroma_db.zip", "./chroma_db", "./chroma_db/fashion_clip_v3.txt"
    download_url = "https://github.com/abobakradel90-source/search-app/releases/download/v1.0/chroma_db.zip"
    if os.path.exists(extract_path) and not os.path.exists(marker_file): shutil.rmtree(extract_path)
    if not os.path.exists(extract_path):
        with st.spinner('📦 جاري تهيئة مستودع البيانات الذكي...'):
            try:
                urllib.request.urlretrieve(download_url, zip_path)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref: zip_ref.extractall(".")
                if os.path.exists(zip_path): os.remove(zip_path)
                with open(marker_file, 'w') as f: f.write("done")
            except: pass

@st.cache_resource
def load_vision_system():
    download_new_chroma_db()
    model_id = "patrickjohncyh/fashion-clip"
    return CLIPModel.from_pretrained(model_id), CLIPProcessor.from_pretrained(model_id), chromadb.PersistentClient(path="./chroma_db").get_collection(name="products_collection")

try: model, processor, collection = load_vision_system()
except Exception as e: st.error(f"⚠️ خطأ محرك الذكاء الاصطناعي: {e}")

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
            if hasattr(features, 'image_embeds'): features = features.image_embeds
            elif hasattr(features, 'pooler_output'): features = features.pooler_output
            else: features = features[0]
        return features.squeeze().numpy().tolist()

def get_color_histogram(image):
    img = image.convert("RGB").crop((image.size[0]*0.15, image.size[1]*0.15, image.size[0]*0.85, image.size[1]*0.85))
    hist = img.histogram(); total = sum(hist) / 3
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

def render_product_card(p_code, p_name, p_stock, custom_message="", details_html="", is_sales=False):
    img_html = '<div class="product-img" style="display:flex; align-items:center; justify-content:center; color:#999; font-size:12px;">بدون صورة</div>'
    for ext in ['.jpg', '.jpeg', '.png', '.JPG']:
        img_path = os.path.join("compressed_images", f"{p_code}{ext}")
        if os.path.exists(img_path):
            img_html = f'<img src="data:image/jpeg;base64,{get_image_base64(img_path)}" class="product-img">'
            break
            
    try: s_val = float(p_stock)
    except: s_val = 0
    is_out = s_val <= 0
        
    stock_class = "stock-badge out-of-stock" if is_out else "stock-badge in-stock"
    stock_text = f"🛒 الرصيد المتاح للبيع: {p_stock}" if is_sales else f"📦 الرصيد الدفتري: {p_stock}"
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

# بناء قاموس بيانات الأصناف للبحث السريع
system_inventory = {}
if df_products is not None:
    for idx, row in df_products.iterrows():
        code, name, stock = parse_row_info(row, df_products.columns)
        try: s_val = float(stock)
        except: s_val = 0
        system_inventory[code] = {'name': name, 'sys_stock': s_val}

# --- التخطيط الرئيسي ---
main_tab1, main_tab2, main_tab3 = st.tabs(["🔍 محرك البحث الذكي", "📦 الجرد التشاركي", "🛒 نقطة البيع (POS)"])

# ==========================================
# التبويب 1: البحث
# ==========================================
with main_tab1:
    search_query = st.text_input("", placeholder="اكتب الكود أو اسم الصنف هنا...", key="search_bar", label_visibility="collapsed")
    if df_products is not None and search_query:
        query = str(search_query).strip().lower().split('.')[0]
        mask = pd.Series([False]*len(df_products))
        for col in df_products.columns: mask = mask | df_products[col].astype(str).str.lower().str.contains(query, case=False, na=False, regex=False)
        matched = df_products[mask]
        if not matched.empty:
            st.markdown("### ✨ نتائج البحث النصي:")
            for idx, row in matched.iterrows():
                p_code, p_name, p_stock = parse_row_info(row, df_products.columns)
                details = " | ".join([f"<b>{col}:</b> {row[col]}" for col in df_products.columns])
                render_product_card(p_code, p_name, p_stock, details_html=f'<div style="color: #64748B; font-size: 14px; margin-top: 8px;">{details}</div>')
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
                            img_p = os.path.join("compressed_images", fn)
                            c_dist = compare_histograms(user_color, get_color_histogram(Image.open(img_p))) if os.path.exists(img_p) else 0
                            refined.append({'fn': fn, 'score': results['distances'][0][i] + (c_dist * 0.5)})
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
                                        row_data = df_products.loc[cleaned[cleaned == tc].index[0]]
                                        _, p_name, p_stock = parse_row_info(row_data, df_products.columns)
                                        break
                            render_product_card(p_code, p_name, p_stock)
                except Exception as e: st.error(f"⚠️ خطأ في البحث البصري: {e}")

# ==========================================
# التبويب 2: الجرد التشاركي
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
            uploaded_inv_file = st.file_uploader("📎 رفع ملف الأرصدة (Excel/CSV) - اختياري", type=['csv', 'xlsx'])
            if st.form_submit_button("🚀 فتح جلسة الجرد للجميع"):
                if not inv_name: st.error("⚠️ برجاء كتابة اسم أو رقم الجرد أولاً!")
                else:
                    if uploaded_inv_file is not None:
                        try:
                            if uploaded_inv_file.name.endswith('.csv'): df_custom = pd.read_csv(uploaded_inv_file, encoding='utf-8-sig')
                            else: df_custom = pd.read_excel(uploaded_inv_file)
                            df_custom.to_csv(SHARED_DF_FILE, index=False, encoding='utf-8-sig')
                        except:
                            st.error("خطأ في الملف، سيتم استخدام الأرصدة الأساسية.")
                            if os.path.exists(SHARED_DF_FILE): os.remove(SHARED_DF_FILE)
                    else:
                        if os.path.exists(SHARED_DF_FILE): os.remove(SHARED_DF_FILE)
                    save_shared_inventory({"is_active": True, "name": inv_name, "reason": inv_reason, "date": str(inv_date), "scanned_items": {}})
                    st.rerun()
    else:
        st.markdown(f'<div class="inv-active-bar"><div>📌 <b>جرد شبكي نشط:</b> {shared_inv.get("name")} &nbsp;|&nbsp; <b>السبب:</b> {shared_inv.get("reason")}</div></div>', unsafe_allow_html=True)
        active_df = pd.read_csv(SHARED_DF_FILE, encoding='utf-8-sig') if os.path.exists(SHARED_DF_FILE) else df_products
        if active_df is None: st.error("⚠️ لا توجد داتا أرصدة!")
        else:
            inv_tab1, inv_tab2, inv_tab3 = st.tabs(["📊 ملخص الأرصدة", "🔫 مسح الباركود الفعلي", "⚖️ تقرير الفروقات (تصدير)"])
            sys_inv = {}
            total_qty = 0; out_of_stock = 0
            for idx, row in active_df.iterrows():
                code, name, stock = parse_row_info(row, active_df.columns)
                try: s_val = float(stock)
                except: s_val = 0
                total_qty += s_val
                if s_val <= 0: out_of_stock += 1
                sys_inv[code] = {'name': name, 'sys_stock': s_val}
            
            scanned_items = shared_inv.get("scanned_items", {})
            
            with inv_tab1:
                col1, col2, col3 = st.columns(3)
                with col1: st.markdown(f'<div class="metric-card"><div class="metric-title">الأصناف الدفترية</div><div class="metric-value" style="color:#1C65A6;">{len(active_df)}</div></div>', unsafe_allow_html=True)
                with col2: st.markdown(f'<div class="metric-card" style="border-color:#10B981;"><div class="metric-title">القطع المتوفرة</div><div class="metric-value" style="color:#10B981;">{int(total_qty)}</div></div>', unsafe_allow_html=True)
                with col3: st.markdown(f'<div class="metric-card" style="border-color:#DC2626;"><div class="metric-title">أصناف صفرية</div><div class="metric-value" style="color:#DC2626;">{out_of_stock}</div></div>', unsafe_allow_html=True)
                st.markdown(f"<br>### 🛒 إجمالي المجرد فعلياً: **{sum(scanned_items.values())}** قطعة", unsafe_allow_html=True)
                if st.button("🔄 تحديث الأرقام (ريفرش)"): st.rerun()

            with inv_tab2:
                st.markdown("### 🔫 مسح الباركود للجرد")
                if "inv_scan" not in st.session_state: st.session_state.inv_scan = ""
                if "inv_msg" not in st.session_state: st.session_state.inv_msg = ""
                if "inv_clear" not in st.session_state: st.session_state.inv_clear = False
                
                if st.session_state.inv_clear: st.session_state.inv_scan = ""; st.session_state.inv_clear = False
                if st.session_state.inv_msg: st.success(st.session_state.inv_msg); st.session_state.inv_msg = ""

                scan_code = st.text_input("كود الصنف للجرد:", key="inv_scan")
                if scan_code:
                    clean_code = str(scan_code).strip().upper()
                    found_code = next((c for c in sys_inv.keys() if c.upper() == clean_code), None)
                    if found_code:
                        st.info("✅ تم العثور على الصنف. أضف/اخصم الكمية:")
                        render_product_card(found_code, sys_inv[found_code]['name'], sys_inv[found_code]['sys_stock'])
                        with st.form("confirm_add_form"):
                            add_qty = st.number_input("الكمية (+ للإضافة, - للخصم):", value=1)
                            if st.form_submit_button("تأكيد العملية 📥"):
                                l_inv = load_shared_inventory()
                                l_inv["scanned_items"][found_code] = max(0, l_inv.get("scanned_items", {}).get(found_code, 0) + add_qty)
                                save_shared_inventory(l_inv)
                                st.session_state.inv_msg = f"✅ نجاح ({add_qty}) للصنف: {found_code} | الرصيد: {l_inv['scanned_items'][found_code]}"
                                st.session_state.inv_clear = True; st.rerun()
                    else:
                        st.error("❌ الباركود غير مسجل!"); 
                        if st.button("حاول مرة أخرى"): st.session_state.inv_clear = True; st.rerun()

                components.html("""<script>
                const f = () => { const i = window.parent.document.querySelector('input[aria-label="كود الصنف للجرد:"]'); if(i && "%s"==="") i.focus(); else {const n = window.parent.document.querySelector('input[type="number"]'); if(n) n.focus();}};
                f(); setTimeout(f, 100); setTimeout(f, 500);</script>""" % st.session_state.inv_scan, height=0)

            with inv_tab3:
                report = [{"كود الصنف": c, "اسم الصنف": i['name'], "الرصيد الدفتري": i['sys_stock'], "الرصيد الفعلي": scanned_items.get(c, 0), "الفروقات": scanned_items.get(c, 0) - i['sys_stock']} for c, i in sys_inv.items()]
                df_report = pd.DataFrame(report)
                st.dataframe(df_report.style.map(lambda v: 'color:red;font-weight:bold;' if v<0 else ('color:blue;font-weight:bold;' if v>0 else 'color:green;'), subset=['الفروقات']), use_container_width=True, hide_index=True)
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer: df_report.to_excel(writer, index=False, sheet_name='تقرير الجرد')
                st.download_button("📥 تحميل التقرير (Excel)", data=buffer.getvalue(), file_name=f"Inventory_{shared_inv.get('name')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                
                if st.session_state.current_user == "abobakr":
                    if st.button("🛑 إغلاق وإنهاء جلسة الجرد وحفظها بالأرشيف"):
                        save_to_inv_history({"timestamp": str(datetime.datetime.now()), "name": shared_inv.get('name'), "date": shared_inv.get('date'), "report": report})
                        save_shared_inventory({"is_active": False, "scanned_items": {}})
                        if os.path.exists(SHARED_DF_FILE): os.remove(SHARED_DF_FILE)
                        st.rerun()
                else: st.info("🔒 الإغلاق متاح للإدارة (abobakr) فقط.")

# ==========================================
# التبويب 3: 🛒 نقطة البيع (POS) الجديدة كلياً
# ==========================================
with main_tab3:
    shared_sales = load_shared_sales()
    
    if not shared_sales.get("is_active", False):
        st.markdown("### 🏬 فتح وردية مبيعات جديدة")
        with st.form("sales_setup_form"):
            col1, col2 = st.columns(2)
            with col1: s_name = st.text_input("اسم/رقم الوردية", placeholder="مثال: وردية صباحي 29-8")
            with col2: s_date = st.date_input("تاريخ الوردية", datetime.date.today())
            
            if st.form_submit_button("🚀 فتح وردية البيع للكاشير"):
                if not s_name: st.error("⚠️ اكتب اسم الوردية أولاً!")
                else:
                    save_shared_sales({"is_active": True, "name": s_name, "date": str(s_date), "transactions": [], "deductions": {}})
                    st.rerun()
    else:
        st.markdown(f'<div class="sales-active-bar"><div>💳 <b>وردية المبيعات:</b> {shared_sales.get("name")} &nbsp;|&nbsp; <b>التاريخ:</b> {shared_sales.get("date")}</div></div>', unsafe_allow_html=True)
        
        # حساب المؤشرات اللحظية للمبيعات
        transactions = shared_sales.get("transactions", [])
        total_revenue = sum(t["total"] for t in transactions)
        total_items_sold = sum(t["qty"] for t in transactions)
        my_sales = sum(t["total"] for t in transactions if t["salesperson"] == st.session_state.current_user)
        
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f'<div class="metric-card"><div class="metric-title">إجمالي إيرادات الوردية</div><div class="metric-value" style="color:#1C65A6;">{total_revenue} ج.م</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="metric-card" style="border-color:#F59E0B;"><div class="metric-title">مبيعاتي أنا (اليوم)</div><div class="metric-value" style="color:#F59E0B;">{my_sales} ج.م</div></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="metric-card" style="border-color:#10B981;"><div class="metric-title">القطع المباعة للكل</div><div class="metric-value" style="color:#10B981;">{total_items_sold} قطعة</div></div>', unsafe_allow_html=True)
        
        st.markdown("### 🛒 مسح وبيع المنتجات (Live POS)")
        
        if "pos_scan" not in st.session_state: st.session_state.pos_scan = ""
        if "pos_msg" not in st.session_state: st.session_state.pos_msg = ""
        if "pos_clear" not in st.session_state: st.session_state.pos_clear = False
        
        if st.session_state.pos_clear: st.session_state.pos_scan = ""; st.session_state.pos_clear = False
        if st.session_state.pos_msg: st.success(st.session_state.pos_msg); st.session_state.pos_msg = ""

        pos_code = st.text_input("كود الصنف للبيع:", key="pos_scan")
        
        if pos_code:
            clean_code = str(pos_code).strip().upper()
            if clean_code in system_inventory:
                sys_qty = system_inventory[clean_code]['sys_stock']
                already_sold = shared_sales.get("deductions", {}).get(clean_code, 0)
                live_qty = sys_qty - already_sold # الرصيد الحي بعد خصم اللي اتباع
                
                render_product_card(clean_code, system_inventory[clean_code]['name'], live_qty, is_sales=True)
                
                if live_qty <= 0:
                    st.error("❌ تحذير: هذا الصنف نفذ من المخزن، لا يمكنك بيعه الآن!")
                    if st.button("مسح الكود والمحاولة مرة أخرى"): st.session_state.pos_clear = True; st.rerun()
                else:
                    with st.form("sell_form"):
                        cc1, cc2 = st.columns(2)
                        with cc1: sell_qty = st.number_input("الكمية المباعة:", min_value=1, max_value=int(live_qty), value=1)
                        with cc2: sell_price = st.number_input("سعر القطعة النهائي للعميل (ج.م):", min_value=0.0, value=0.0, step=10.0)
                        
                        if st.form_submit_button("💰 إتمام البيع والخصم من الرصيد"):
                            if sell_price <= 0: st.error("⚠️ يرجى إدخال سعر البيع!")
                            else:
                                l_sales = load_shared_sales()
                                trx = {
                                    "id": len(l_sales["transactions"]) + 1,
                                    "time": str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                                    "salesperson": st.session_state.current_user,
                                    "code": clean_code,
                                    "name": system_inventory[clean_code]['name'],
                                    "qty": sell_qty,
                                    "price": sell_price,
                                    "total": sell_qty * sell_price
                                }
                                l_sales["transactions"].append(trx)
                                l_sales["deductions"][clean_code] = l_sales.get("deductions", {}).get(clean_code, 0) + sell_qty
                                save_shared_sales(l_sales)
                                
                                st.session_state.pos_msg = f"💳 تم بيع ({sell_qty}) قطعة بنجاح! الإجمالي: {trx['total']} ج.م"
                                st.session_state.pos_clear = True
                                st.rerun()
            else:
                st.error("❌ الباركود غير مسجل في السيستم!")
                if st.button("حاول مرة أخرى"): st.session_state.pos_clear = True; st.rerun()
        
        components.html("""<script>
        const f = () => { const i = window.parent.document.querySelector('input[aria-label="كود الصنف للبيع:"]'); if(i && "%s"==="") i.focus(); else {const n = window.parent.document.querySelectorAll('input[type="number"]'); if(n.length>0) n[0].focus();}};
        f(); setTimeout(f, 100); setTimeout(f, 500);</script>""" % st.session_state.pos_scan, height=0)

        # جدول أحدث المبيعات للوردية الحالية
        if transactions:
            st.markdown("---")
            st.markdown("### 📋 فواتير الوردية الحالية")
            df_trx = pd.DataFrame(transactions)
            st.dataframe(df_trx[['time', 'salesperson', 'code', 'name', 'qty', 'price', 'total']], use_container_width=True, hide_index=True)

        if st.session_state.current_user == "abobakr":
            st.markdown("---")
            if st.button("🛑 إغلاق وردية البيع وحفظ لوحة التحكم بالأرشيف"):
                if transactions:
                    save_to_sales_history({
                        "name": shared_sales.get("name"), "date": shared_sales.get("date"),
                        "total_revenue": total_revenue, "transactions": transactions
                    })
                save_shared_sales({"is_active": False, "transactions": [], "deductions": {}})
                st.rerun()
        else:
            st.markdown("---")
            st.info("🔒 إغلاق الوردية متاح للإدارة فقط.")

# ==========================================
# 📁 أرشيف الإدارة (يظهر فقط للأدمن)
# ==========================================
if st.session_state.current_user == "abobakr":
    st.markdown("<br><hr>", unsafe_allow_html=True)
    st.markdown("### 📁 الأرشيف الإداري السري (جرد & مبيعات)")
    
    arch_tab1, arch_tab2 = st.tabs(["📦 أرشيف الجرد", "💰 أرشيف المبيعات"])
    
    with arch_tab1:
        inv_hist = load_inv_history()
        if not inv_hist: st.info("لا يوجد أرشيف جرد.")
        for idx, rec in enumerate(reversed(inv_hist)):
            with st.expander(f"📌 جرد: {rec['name']} | التاريخ: {rec['date']}"):
                df_h = pd.DataFrame(rec['report'])
                st.dataframe(df_h.style.map(lambda v: 'color:red;font-weight:bold;' if v<0 else ('color:blue;font-weight:bold;' if v>0 else 'color:green;'), subset=['الفروقات']), use_container_width=True, hide_index=True)
                b = io.BytesIO()
                with pd.ExcelWriter(b, engine='openpyxl') as w: df_h.to_excel(w, index=False)
                st.download_button("📥 تحميل الإكسيل", data=b.getvalue(), file_name=f"Arch_Inv_{rec['name']}.xlsx", key=f"inv_dl_{idx}")

    with arch_tab2:
        sales_hist = load_sales_history()
        if not sales_hist: st.info("لا يوجد أرشيف مبيعات.")
        for idx, rec in enumerate(reversed(sales_hist)):
            with st.expander(f"💳 وردية: {rec['name']} | الإيرادات: {rec['total_revenue']} ج.م"):
                df_s = pd.DataFrame(rec['transactions'])
                st.dataframe(df_s, use_container_width=True, hide_index=True)
                b_s = io.BytesIO()
                with pd.ExcelWriter(b_s, engine='openpyxl') as w: df_s.to_excel(w, index=False)
                st.download_button("📥 تحميل تفاصيل الفواتير (Excel)", data=b_s.getvalue(), file_name=f"Arch_Sales_{rec['name']}.xlsx", key=f"sal_dl_{idx}")

st.markdown('<div class="footer">تصميم وبرمجة: <span>أبوبكر عادل</span> © 2026</div>', unsafe_allow_html=True)