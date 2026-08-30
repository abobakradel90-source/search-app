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
import re
import time

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
# 🌐 دوال إدارة قواعد البيانات
# ==========================================
SHARED_INV_FILE = "shared_inventory.json"
MASTER_DB_FILE = "master_database.csv"
HISTORY_INV_FILE = "inventory_history.json"
SHARED_SALES_FILE = "shared_sales.json"
HISTORY_SALES_FILE = "sales_history.json"

def load_json(file_path, default_data):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return default_data

def save_json(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)

def load_shared_inventory(): return load_json(SHARED_INV_FILE, {"is_active": False, "name": "", "reason": "", "date": "", "scanned_items": {}})
def save_shared_inventory(data): save_json(SHARED_INV_FILE, data)
def load_inv_history(): return load_json(HISTORY_INV_FILE, [])
def save_to_inv_history(record):
    history = load_inv_history()
    history.append(record)
    save_json(HISTORY_INV_FILE, history)

def load_shared_sales(): return load_json(SHARED_SALES_FILE, {"is_active": False, "name": "", "date": "", "invoices": [], "deductions": {}})
def save_shared_sales(data): save_json(SHARED_SALES_FILE, data)
def load_sales_history(): return load_json(HISTORY_SALES_FILE, [])
def save_to_sales_history(record):
    history = load_sales_history()
    history.append(record)
    save_json(HISTORY_SALES_FILE, history)

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
# ✅ محتوى الموقع والقائمة الجانبية
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

if st.session_state.current_user == "abobakr":
    with st.sidebar:
        st.markdown("### ⚙️ إدارة النظام والأسعار")
        with st.form("master_db_upload_form"):
            st.markdown("ارفع شيت الإكسيل لتحديث **الأسعار والأرصدة** بشكل دائم:")
            new_db = st.file_uploader("تحديث قاعدة البيانات", type=['csv', 'xlsx'])
            if st.form_submit_button("تحديث الداتا الآن 💾"):
                if new_db is not None:
                    try:
                        if new_db.name.endswith('.csv'): d = pd.read_csv(new_db, encoding='utf-8-sig', sep=None, engine='python')
                        else: d = pd.read_excel(new_db)
                        d.to_csv(MASTER_DB_FILE, index=False, encoding='utf-8-sig')
                        st.success("✅ تم تحديث جميع الأسعار والأرصدة بنجاح!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e: st.error(f"حدث خطأ: {e}")
                else: st.warning("⚠️ برجاء اختيار ملف أولاً.")
        st.markdown("---")

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

def get_image_embedding(image):
    image = ImageOps.autocontrast(image.convert("RGB"), cutoff=1)
    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        features = model.get_image_features(**inputs)
        if not isinstance(features, torch.Tensor): features = features.image_embeds if hasattr(features, 'image_embeds') else features[0]
        return features.squeeze().numpy().tolist()

def get_color_histogram(image):
    img = image.convert("RGB").crop((image.size[0]*0.15, image.size[1]*0.15, image.size[0]*0.85, image.size[1]*0.85))
    hist = img.histogram(); total = sum(hist) / 3
    return [x / (total if total > 0 else 1) for x in hist]

def compare_histograms(h1, h2): return sum(abs(a - b) for a, b in zip(h1, h2))

# ==========================================
# 🚀 محرك استخراج البيانات الموحد
# ==========================================
system_inventory = {}

def parse_val(val):
    try:
        m = re.search(r'-?\d+(\.\d+)?', str(val).replace(',', '').strip())
        return float(m.group()) if m else 0.0
    except: return 0.0

def process_df_into_inventory(df):
    if df is None or df.empty: return
    cols = [str(c).lower().strip() for c in df.columns]
    code_col = name_col = stock_col = price_col = None
    
    for orig, low in zip(df.columns, cols):
        if not code_col and any(k in low for k in ['code', 'كود', 'باركود', 'file']): code_col = orig
        elif not name_col and any(k in low for k in ['name', 'اسم', 'صنف', 'title']): name_col = orig
        elif not stock_col and any(k in low for k in ['stock', 'qty', 'رصيد', 'كمية', 'عدد']): stock_col = orig
        elif not price_col and any(k in low for k in ['price', 'سعر', 'ثمن', 'جملة', 'بيع', 'قيمة']): price_col = orig
    
    if not code_col and len(df.columns) > 0: code_col = df.columns[0]
    if not name_col and len(df.columns) > 1: name_col = df.columns[1]
    if not stock_col and len(df.columns) > 2: stock_col = df.columns[2]
    if not price_col and len(df.columns) > 4: price_col = df.columns[4]

    for _, row in df.iterrows():
        raw_code = str(row.get(code_col, "")).strip()
        if raw_code.lower() in ['nan', 'none', '']: continue
        p_code = raw_code.split('.')[0].upper()
        
        p_name = str(row.get(name_col, "بدون اسم")).strip()
        if p_name.lower() in ['nan', 'none']: p_name = "بدون اسم"
        
        p_stock = parse_val(row.get(stock_col, 0))
        p_price = parse_val(row.get(price_col, 0))
            
        if p_price == 0.0:
            for c in df.columns:
                if any(k in str(c).lower().strip() for k in ['price', 'سعر', 'ثمن', 'جملة']):
                    t_price = parse_val(row[c])
                    if t_price > 0: p_price = t_price; break
                        
        system_inventory[p_code] = {'name': p_name, 'sys_stock': p_stock, 'price': p_price}

try: df_products = pd.read_csv('products.csv', encoding='utf-8-sig', sep=None, engine='python')
except: df_products = None
process_df_into_inventory(df_products)

if os.path.exists(MASTER_DB_FILE):
    try: df_master = pd.read_csv(MASTER_DB_FILE, encoding='utf-8-sig', sep=None, engine='python')
    except: df_master = None
    process_df_into_inventory(df_master)

def render_product_card(p_code, p_name, p_stock, p_price=None, custom_message="", details_html="", is_sales=False):
    img_html = '<div class="product-img" style="display:flex; align-items:center; justify-content:center; color:#999; font-size:12px;">بدون صورة</div>'
    for ext in ['.jpg', '.jpeg', '.png', '.JPG']:
        img_path = os.path.join("compressed_images", f"{p_code}{ext}")
        if os.path.exists(img_path):
            img_html = f'<img src="data:image/jpeg;base64,{get_image_base64(img_path)}" class="product-img">'
            break
            
    is_out = float(p_stock) <= 0
    stock_class = "stock-badge out-of-stock" if is_out else "stock-badge in-stock"
    
    if is_sales:
        price_str = f" &nbsp;|&nbsp; 💰 السعر: {p_price} ج.م" if p_price and float(p_price) > 0 else " &nbsp;|&nbsp; ⚠️ السعر غير مسجل"
        stock_text = f"🛒 الرصيد المتاح: {p_stock}{price_str}"
    else: stock_text = f"📦 الرصيد الدفتري: {p_stock}"
        
    msg_html = f'<div style="margin-top:10px; color:#1C65A6; font-weight:bold;">{custom_message}</div>' if custom_message else ""

    st.markdown(f"""<div class="product-card">
{img_html}
<div class="product-details" style="flex-grow: 1;">
<div class="code-badge">الكود: {p_code}</div>
<h3 class="product-title">{p_name}</h3>
<div class="{stock_class}">{stock_text}</div>
{details_html}
{msg_html}
</div></div>""", unsafe_allow_html=True)

# 🛑 تجهيز التبويبات
if st.session_state.current_user == "abobakr":
    tabs = st.tabs(["🔍 البحث", "📦 الجرد", "🛒 الفواتير", "📖 الكاتالوج", "📈 الإدارة"])
    main_tab1, main_tab2, main_tab3, main_tab_cat, main_tab4 = tabs
else:
    tabs = st.tabs(["🔍 البحث", "📦 الجرد", "🛒 الفواتير", "📖 الكاتالوج"])
    main_tab1, main_tab2, main_tab3, main_tab_cat = tabs

# ==========================================
# التبويب 1: البحث
# ==========================================
with main_tab1:
    search_query = st.text_input("", placeholder="اكتب الكود أو اسم الصنف هنا...", key="search_bar", label_visibility="collapsed")
    if search_query:
        query = str(search_query).strip().lower()
        matched_codes = [c for c, v in system_inventory.items() if query in c.lower() or query in v.get('name','').lower()]
        
        if matched_codes:
            st.markdown("### ✨ نتائج البحث:")
            for p_code in matched_codes[:10]:
                item = system_inventory[p_code]
                render_product_card(p_code, item.get('name',''), item.get('sys_stock',0), p_price=item.get('price',0), is_sales=True)
        else: st.warning("⚠️ لم يتم العثور على أي منتج يطابق بحثك.")
    
    st.markdown("<br><hr><br>", unsafe_allow_html=True)
    cam_tab, upload_tab = st.tabs(["📸 الكاميرا", "📁 رفع صورة"])
    raw_image = None
    with cam_tab:
        cam_photo = st.camera_input("وجّه الكاميرا نحو المنتج")
        if cam_photo: raw_image = Image.open(cam_photo).convert("RGB")
    with upload_tab:
        up_file = st.file_uploader("ارفع صورة المنتج", type=["jpg", "jpeg", "png"])
        if up_file: raw_image = Image.open(up_file).convert("RGB")

    if raw_image:
        st.markdown("### ✂️ قص المنتج:")
        cropped_img = st_cropper(raw_image, realtime_update=True, box_color='#1C65A6', aspect_ratio=None)
        if st.button("🚀 ابحث عن المنتج"):
            with st.spinner('جاري البحث...'):
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
                        for res in refined[:3]:
                            p_code = res['fn'].split('.')[0].upper()
                            if p_code in system_inventory:
                                item = system_inventory[p_code]
                                render_product_card(p_code, item.get('name',''), item.get('sys_stock',0), p_price=item.get('price',0), is_sales=True)
                except Exception as e: st.error(f"حدث خطأ: {e}")

# ==========================================
# التبويب 2: الجرد
# ==========================================
with main_tab2:
    shared_inv_state = load_shared_inventory()
    if not shared_inv_state.get("is_active", False):
        st.markdown("### 🆕 جلسة جرد جديدة")
        with st.form("inv_setup_form"):
            inv_name = st.text_input("اسم الجرد")
            inv_reason = st.selectbox("السبب", ["دوري", "مفاجئ", "نهاية العام"])
            inv_date = st.date_input("التاريخ")
            if st.form_submit_button("🚀 فتح الجرد"):
                if not inv_name: st.error("اكتب اسم الجرد أولاً!")
                else:
                    save_shared_inventory({"is_active": True, "name": inv_name, "reason": inv_reason, "date": str(inv_date), "scanned_items": {}})
                    st.rerun()
    else:
        st.markdown(f'<div class="inv-active-bar"><div>📌 <b>جرد نشط:</b> {shared_inv_state.get("name","")}</div></div>', unsafe_allow_html=True)
        inv_tab1, inv_tab2, inv_tab3 = st.tabs(["📊 ملخص", "🔫 مسح الباركود", "⚖️ التقرير"])
        
        scanned_items = shared_inv_state.get("scanned_items", {})
        
        with inv_tab1:
            st.markdown(f"### 🛒 إجمالي المجرد فعلياً: **{sum(scanned_items.values())}** قطعة")
            if st.button("🔄 ريفرش"): st.rerun()

        with inv_tab2:
            if "inv_clear" not in st.session_state: st.session_state.inv_clear = False
            if st.session_state.inv_clear: st.session_state.inv_scan = ""; st.session_state.inv_clear = False

            scan_code = st.text_input("كود الصنف للجرد:", key="inv_scan")
            if scan_code:
                clean_code = str(scan_code).strip().upper()
                if clean_code in system_inventory:
                    render_product_card(clean_code, system_inventory[clean_code].get('name',''), system_inventory[clean_code].get('sys_stock',0))
                    with st.form("confirm_add_form"):
                        add_qty = st.number_input("الكمية (+ للإضافة, - للخصم):", value=1)
                        if st.form_submit_button("تأكيد 📥"):
                            l_inv = load_shared_inventory()
                            if "scanned_items" not in l_inv: l_inv["scanned_items"] = {}
                            l_inv["scanned_items"][clean_code] = max(0, l_inv.get("scanned_items", {}).get(clean_code, 0) + add_qty)
                            save_shared_inventory(l_inv)
                            st.session_state.inv_clear = True
                            st.rerun()
                else:
                    st.error("❌ غير مسجل!")
                    if st.button("حاول مرة أخرى"): st.session_state.inv_clear = True; st.rerun()

        with inv_tab3:
            report = [{"كود الصنف": c, "اسم الصنف": i.get('name',''), "الرصيد الدفتري": i.get('sys_stock',0), "الرصيد الفعلي": scanned_items.get(c, 0), "الفروقات": scanned_items.get(c, 0) - i.get('sys_stock',0)} for c, i in system_inventory.items()]
            if report:
                df_report = pd.DataFrame(report)
                st.dataframe(df_report, use_container_width=True, hide_index=True)
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='openpyxl') as w: df_report.to_excel(w, index=False)
                st.download_button("📥 تحميل التقرير", buf.getvalue(), f"Inventory_{shared_inv_state.get('name','')}.xlsx")
            
            if st.session_state.current_user == "abobakr":
                if st.button("🛑 إغلاق وإنهاء الجرد"):
                    save_to_inv_history({"timestamp": str(datetime.datetime.now()), "name": shared_inv_state.get('name',''), "report": report})
                    save_shared_inventory({"is_active": False, "scanned_items": {}})
                    st.rerun()

# ==========================================
# التبويب 3: 🛒 الفواتير
# ==========================================
with main_tab3:
    shared_sales = load_shared_sales()
    
    if not shared_sales.get("is_active", False):
        st.markdown("### 🏬 فتح وردية مبيعات جديدة")
        with st.form("sales_setup_form"):
            s_name = st.text_input("اسم/رقم الوردية")
            s_date = st.date_input("تاريخ الوردية", datetime.date.today())
            if st.form_submit_button("🚀 فتح الوردية"):
                if not s_name: st.error("اكتب اسم الوردية!")
                else:
                    save_shared_sales({"is_active": True, "name": s_name, "date": str(s_date), "invoices": [], "deductions": {}})
                    st.rerun()
    else:
        st.markdown(f'<div class="sales-active-bar"><div>💳 <b>وردية نشطة:</b> {shared_sales.get("name","")}</div></div>', unsafe_allow_html=True)
        
        if st.session_state.get("last_invoice_b64"):
            st.success(f"🎉 تم حفظ الفاتورة بنجاح: {st.session_state.get('last_invoice_name')}")
            st.download_button(
                label="📥 اضغط هنا لتحميل الفاتورة (Excel)",
                data=base64.b64decode(st.session_state.last_invoice_b64),
                file_name=st.session_state.last_invoice_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
            if st.button("إخفاء رسالة التحميل والبدء من جديد"):
                st.session_state.last_invoice_b64 = None
                st.rerun()
            st.markdown("---")

        if "active_customer" not in st.session_state: st.session_state.active_customer = ""
        if "invoice_cart" not in st.session_state: st.session_state.invoice_cart = []
        if "pos_clear" not in st.session_state: st.session_state.pos_clear = False
        
        if st.session_state.pos_clear:
            st.session_state.pos_scan = ""
            st.session_state.pos_clear = False

        if not st.session_state.active_customer:
            st.markdown("### 📝 فاتورة لعميل جديد")
            with st.form("new_customer_form"):
                cust_name = st.text_input("اسم العميل:")
                if st.form_submit_button("بدء الفاتورة 🛒"):
                    if cust_name.strip():
                        st.session_state.active_customer = cust_name.strip()
                        st.session_state.invoice_cart = []
                        st.rerun()
                    else: st.error("يرجى إدخال الاسم.")
        else:
            st.markdown(f"### 🧾 العميل: <span style='color:#1C65A6;'>{st.session_state.active_customer}</span>", unsafe_allow_html=True)
            
            scan_code = st.text_input("كود الصنف للفاتورة:", key="pos_scan")
            if scan_code:
                clean_code = str(scan_code).strip().upper()
                if clean_code in system_inventory:
                    p_info = system_inventory[clean_code]
                    sys_qty = float(p_info.get('sys_stock', 0.0))
                    auto_price = float(p_info.get('price', 0.0))
                    global_sold = float(shared_sales.get("deductions", {}).get(clean_code, 0.0))
                    local_cart_qty = sum(float(item.get("qty", 0)) for item in st.session_state.invoice_cart if item.get("code", "") == clean_code)
                    live_qty = sys_qty - global_sold - local_cart_qty
                    
                    render_product_card(clean_code, p_info.get('name',''), live_qty, p_price=auto_price, is_sales=True)
                    
                    if live_qty <= 0:
                        st.error("❌ تحذير: رصيد هذا الصنف نفذ!")
                        if st.button("تخطي"): st.session_state.pos_clear = True; st.rerun()
                    else:
                        with st.form("add_to_cart_form"):
                            c1, c2 = st.columns(2)
                            with c1: sell_qty = st.number_input("الكمية:", min_value=1, max_value=int(live_qty) if live_qty>0 else 1, value=1)
                            with c2: 
                                st.number_input("السعر (للقراءة):", value=float(auto_price), disabled=True)
                                sell_price = float(auto_price)
                            
                            if st.form_submit_button("إضافة 📥"):
                                if sell_price <= 0: st.error("⚠️ السعر غير مسجل.")
                                else:
                                    st.session_state.invoice_cart.append({
                                        "code": clean_code, "name": p_info.get('name',''), "qty": sell_qty, "price": sell_price, "total": sell_qty * sell_price
                                    })
                                    st.session_state.pos_clear = True
                                    st.rerun()
                else:
                    st.error("❌ الباركود غير مسجل!")
                    if st.button("تخطي"): st.session_state.pos_clear = True; st.rerun()

            if st.session_state.invoice_cart:
                st.markdown("#### 🛒 الأصناف بالفاتورة:")
                df_cart = pd.DataFrame(st.session_state.invoice_cart)
                st.dataframe(df_cart[['code', 'name', 'qty', 'price', 'total']], use_container_width=True)
                
                cart_total = sum(float(item.get("total", 0.0)) for item in st.session_state.invoice_cart)
                st.markdown(f"<h3 style='color: #DC2626;'>الإجمالي المطلوب: {cart_total} ج.م</h3>", unsafe_allow_html=True)
                
                c_save, c_cancel = st.columns(2)
                with c_save:
                    if st.button("✅ حفظ وإصدار الفاتورة", type="primary"):
                        l_sales = load_shared_sales()
                        inv_id = max([i.get("invoice_id", 0) for i in l_sales.get("invoices", [])] + [0]) + 1
                        
                        l_sales["invoices"].append({
                            "invoice_id": inv_id, "time": str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M")),
                            "salesperson": st.session_state.current_user, "customer": st.session_state.active_customer,
                            "total": cart_total, "items": st.session_state.invoice_cart
                        })
                        for item in st.session_state.invoice_cart:
                            c_code = item.get("code", "")
                            l_sales["deductions"][c_code] = l_sales.get("deductions", {}).get(c_code, 0) + item.get("qty", 0)
                        save_shared_sales(l_sales)
                        
                        df_ex = pd.DataFrame(st.session_state.invoice_cart).rename(columns={'code':'الكود', 'name':'الاسم', 'qty':'الكمية', 'price':'السعر', 'total':'الإجمالي'})
                        buf = io.BytesIO()
                        with pd.ExcelWriter(buf, engine='openpyxl') as w: df_ex.to_excel(w, index=False)
                        
                        st.session_state.last_invoice_b64 = base64.b64encode(buf.getvalue()).decode()
                        st.session_state.last_invoice_name = f"Invoice_{inv_id}_{st.session_state.active_customer}.xlsx"
                        
                        st.session_state.active_customer = ""
                        st.session_state.invoice_cart = []
                        st.rerun()
                with c_cancel:
                    if st.button("🗑️ إلغاء الفاتورة"):
                        st.session_state.active_customer = ""
                        st.session_state.invoice_cart = []
                        st.rerun()

        if st.session_state.current_user == "abobakr":
            st.markdown("---")
            if st.button("🛑 إغلاق وردية الجملة (أرشيف)"):
                save_to_sales_history({"name": shared_sales.get("name", ""), "date": shared_sales.get("date", ""), "invoices": shared_sales.get("invoices", [])})
                save_shared_sales({"is_active": False, "invoices": [], "deductions": {}})
                st.rerun()

# ==========================================
# 🌟 التبويب 4: 📖 الكاتالوج الشامل بالصور
# ==========================================
with main_tab_cat:
    st.markdown("### 📖 الكاتالوج الشامل للأصناف (Live Catalog)")
    st.markdown("يعرض هذا الكاتالوج الأصناف المتوفرة فقط بالمخزن مع تفاصيل حركة الرصيد والأسعار.")

    shared_sales_cat = load_shared_sales()
    deductions_cat = shared_sales_cat.get("deductions", {})

    catalog_data = []
    for p_code, p_info in system_inventory.items():
        stock_before = float(p_info.get('sys_stock', 0.0))
        sales_qty = float(deductions_cat.get(p_code, 0.0))
        stock_after = stock_before - sales_qty
        item_price = float(p_info.get('price', 0.0))

        if stock_after > 0:
            img_uri = ""
            for ext in ['.jpg', '.jpeg', '.png', '.JPG']:
                img_path = os.path.join("compressed_images", f"{p_code}{ext}")
                if os.path.exists(img_path):
                    b64 = get_image_base64(img_path)
                    if b64: img_uri = f"data:image/jpeg;base64,{b64}"
                    break

            catalog_data.append({
                "صورة المنتج": img_uri,
                "كود الصنف": p_code,
                "اسم الصنف": p_info.get('name', ''),
                "الرصيد قبل المبيعات": stock_before,
                "كمية المبيعات": sales_qty,
                "الرصيد المتاح": stock_after,
                "سعر القطعة": item_price
            })

    if catalog_data:
        df_catalog = pd.DataFrame(catalog_data)

        st.dataframe(
            df_catalog,
            column_config={
                "صورة المنتج": st.column_config.ImageColumn("صورة المنتج", help="صورة الكوتشي"),
                "كود الصنف": st.column_config.TextColumn("كود الصنف"),
                "اسم الصنف": st.column_config.TextColumn("اسم الصنف"),
                "الرصيد قبل المبيعات": st.column_config.NumberColumn("الرصيد الدفتري"),
                "كمية المبيعات": st.column_config.NumberColumn("المبيعات بالوردية"),
                "الرصيد المتاح": st.column_config.NumberColumn("الرصيد اللحظي المتاح"),
                "سعر القطعة": st.column_config.NumberColumn("سعر القطعة (ج.م)", format="%.2f")
            },
            use_container_width=True,
            hide_index=True,
            height=600
        )

        df_excel_cat = df_catalog.drop(columns=["صورة المنتج"])
        buf_cat = io.BytesIO()
        with pd.ExcelWriter(buf_cat, engine='openpyxl') as w:
            df_excel_cat.to_excel(w, index=False, sheet_name='الكاتالوج')

        st.download_button(
            label="📥 تحميل الكاتالوج (Excel)",
            data=buf_cat.getvalue(),
            file_name=f"Catalog_{datetime.date.today()}.xlsx",
            type="primary"
        )
    else:
        st.info("📦 لا توجد أصناف متاحة بالمخزن (جميع الأرصدة صفر).")

# ==========================================
# التبويب 5: 📈 لوحة الإدارة
# ==========================================
if st.session_state.current_user == "abobakr":
    with main_tab4:
        st.markdown("## 📈 لوحة تحكم الإدارة (Live Dashboard)")
        flat_records = []
        for rec in load_sales_history():
            for inv in rec.get('invoices', []):
                for item in inv.get('items', []):
                    flat_records.append({"اسم العميل": inv.get('customer', ''), "الكمية": float(item.get('qty', 0)), "الإجمالي": float(item.get('total', 0.0))})
        for inv in load_shared_sales().get('invoices', []):
            for item in inv.get('items', []):
                flat_records.append({"اسم العميل": inv.get('customer', ''), "الكمية": float(item.get('qty', 0)), "الإجمالي": float(item.get('total', 0.0))})
        
        if flat_records:
            df_all = pd.DataFrame(flat_records)
            st.markdown(f"### 💰 الإيرادات: {df_all['الإجمالي'].sum()} ج.م")
            st.markdown("#### 👥 مشتريات العملاء")
            st.dataframe(df_all.groupby('اسم العميل').sum().sort_values(by='الإجمالي', ascending=False).reset_index(), use_container_width=True)
        else: st.info("لا توجد مبيعات.")

st.markdown('<div class="footer">تصميم وبرمجة: <span>أبوبكر عادل</span> © 2026</div>', unsafe_allow_html=True)