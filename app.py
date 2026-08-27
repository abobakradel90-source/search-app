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

# --- 1. إعدادات الصفحة وتهيئة الذاكرة المؤقتة (Session State) ---
st.set_page_config(page_title="ED STORE | المتجر الرسمي", page_icon="👟", layout="wide")

# تهيئة ذاكرة الجرد
if 'inventory_session' not in st.session_state:
    st.session_state.inventory_session = {} 
if 'inv_active' not in st.session_state:
    st.session_state.inv_active = False
if 'inv_name' not in st.session_state:
    st.session_state.inv_name = ""
if 'inv_reason' not in st.session_state:
    st.session_state.inv_reason = ""
if 'inv_date' not in st.session_state:
    st.session_state.inv_date = ""
if 'inv_custom_df' not in st.session_state:
    st.session_state.inv_custom_df = None

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
        html, body, [class*="css"] {{ font-family: 'Tajawal', sans-serif !important; direction: rtl; }}
        .stApp {{ background-color: #F0F4F8; }}
        #MainMenu {{visibility: hidden;}} header {{visibility: hidden;}}
        .block-container {{ padding-top: 0rem !important; padding-bottom: 5rem !important; max-width: 1300px; }}
        
        .brand-navbar {{
            background: linear-gradient(90deg, #1C65A6 0%, #144A7A 100%);
            padding: 15px 20px; display: flex; align-items: center; justify-content: center;
            color: white; width: 100%; margin-bottom: 20px;
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
        with st.spinner('📦 جاري تهيئة مستودع البيانات الذكي...'):
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

try: 
    model, processor, collection = load_vision_system()
except Exception as e: 
    st.error(f"⚠️ حدث خطأ أثناء تحميل محرك الذكاء الاصطناعي: {e}")

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
        
        # الكود الأصلي المحكم اللي كان شغال وتم إرجاعه + إضافة flatten لضمان عدم حدوث الإيرور 3D
        if not isinstance(features, torch.Tensor):
            if hasattr(features, 'image_embeds'):
                features = features.image_embeds
            elif hasattr(features, 'pooler_output'):
                features = features.pooler_output
            else:
                features = features[0]
                
        # flatten بتجبر البيانات إنها تكون في بُعد واحد (1D Array) مهما كان شكلها
        embedding = features.flatten().numpy().tolist()
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

def render_product_card(p_code, p_name, p_stock, custom_message=""):
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

    st.markdown(f"""
    <div class="product-card">
        {img_html}
        <div class="product-details" style="flex-grow: 1;">
            <div class="code-badge">الكود: {p_code}</div>
            <h3 class="product-title">{p_name}</h3>
            <div class="{stock_class}">{stock_text}</div>
            {msg_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- 4. التخطيط الرئيسي ---
main_tab1, main_tab2 = st.tabs(["🔍 محرك البحث الذكي", "📦 نظام إدارة الجرد والمخازن"])

# ==========================================
# التبويب الأول: محرك البحث الأساسي
# ==========================================
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
            for idx, row in matched.iterrows():
                p_code, p_name, p_stock = parse_row_info(row, df_products.columns)
                render_product_card(p_code, p_name, p_stock)
        else: st.warning("⚠️ لم يتم العثور على المنتج.")
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
                except Exception as e: 
                    st.error(f"⚠️ حدث خطأ في البحث البصري: {e}")

# ==========================================
# التبويب الثاني: مديول الجرد المتكامل (نظام الجلسات)
# ==========================================
with main_tab2:
    if not st.session_state.inv_active:
        st.markdown("### 🆕 إعداد جلسة جرد جديدة")
        st.info("قم بإنشاء جلسة جرد ورفع ملف الأرصدة الخاص بها (لو لم ترفع ملف، سيتم الجرد على الأرصدة الحالية في الموقع).")
        
        with st.form("inv_setup_form"):
            col1, col2, col3 = st.columns(3)
            with col1: inv_name = st.text_input("اسم/رقم الجرد", placeholder="مثال: جرد شهر أغسطس")
            with col2: inv_reason = st.selectbox("سبب الجرد", ["جرد دوري", "جرد مفاجئ", "تسليم عهدة", "جرد نهاية العام", "أخرى"])
            with col3: inv_date = st.date_input("تاريخ الجرد", datetime.date.today())
            
            uploaded_inv_file = st.file_uploader("📎 رفع ملف الأرصدة الدفترية اللحظية (Excel أو CSV) - اختياري", type=['csv', 'xlsx'])
            
            submitted_setup = st.form_submit_button("🚀 فتح جلسة الجرد وبدء العمل")
            if submitted_setup:
                if not inv_name:
                    st.error("⚠️ برجاء كتابة اسم أو رقم الجرد أولاً!")
                else:
                    st.session_state.inv_name = inv_name
                    st.session_state.inv_reason = inv_reason
                    st.session_state.inv_date = str(inv_date)
                    st.session_state.inventory_session = {}
                    st.session_state.inv_active = True
                    
                    if uploaded_inv_file is not None:
                        try:
                            if uploaded_inv_file.name.endswith('.csv'):
                                st.session_state.inv_custom_df = pd.read_csv(uploaded_inv_file, encoding='utf-8-sig')
                            else:
                                st.session_state.inv_custom_df = pd.read_excel(uploaded_inv_file)
                        except:
                            st.error("حدث خطأ في قراءة الملف المرفق، سيتم الاعتماد على الأرصدة الأساسية.")
                            st.session_state.inv_custom_df = None
                    else:
                        st.session_state.inv_custom_df = None
                        
                    st.rerun()
    else:
        st.markdown(f"""
        <div class="inv-active-bar">
            <div>📌 <b>جرد نشط:</b> {st.session_state.inv_name} &nbsp;|&nbsp; <b>السبب:</b> {st.session_state.inv_reason} &nbsp;|&nbsp; <b>التاريخ:</b> {st.session_state.inv_date}</div>
        </div>
        """, unsafe_allow_html=True)
        
        active_df = st.session_state.inv_custom_df if st.session_state.inv_custom_df is not None else df_products
        
        if active_df is None:
            st.error("⚠️ لا توجد داتا أرصدة لإجراء الجرد!")
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

            with inv_tab1:
                st.markdown("### 📊 ملخص الأرصدة الدفترية لهذه الجلسة")
                col1, col2, col3 = st.columns(3)
                with col1: st.markdown(f'<div class="metric-card"><div class="metric-title">الأصناف الدفترية</div><div class="metric-value" style="color:#1C65A6;">{total_items}</div></div>', unsafe_allow_html=True)
                with col2: st.markdown(f'<div class="metric-card" style="border-color:#10B981;"><div class="metric-title">القطع الدفترية المتوفرة</div><div class="metric-value" style="color:#10B981;">{int(total_qty)}</div></div>', unsafe_allow_html=True)
                with col3: st.markdown(f'<div class="metric-card" style="border-color:#DC2626;"><div class="metric-title">أصناف صفرية دفترية</div><div class="metric-value" style="color:#DC2626;">{out_of_stock}</div></div>', unsafe_allow_html=True)
                st.markdown("<br>### 🛒 إجمالي ما تم مسحه فعلياً: **{}** قطعة".format(sum(st.session_state.inventory_session.values())), unsafe_allow_html=True)

            with inv_tab2:
                st.markdown("### 🔫 مسح الباركود للجرد")
                with st.form("barcode_scanner_form", clear_on_submit=True):
                    col_b, col_q = st.columns([3, 1])
                    with col_b: scan_code = st.text_input("كود الصنف (الباركود):")
                    with col_q: add_qty = st.number_input("الكمية المضافة:", min_value=1, value=1)
                    submitted = st.form_submit_button("إضافة للرصيد الفعلي 📥")
                    
                    if submitted and scan_code:
                        clean_code = str(scan_code).strip().upper()
                        found = False
                        for sys_c in system_inventory.keys():
                            if sys_c.upper() == clean_code:
                                clean_code = sys_c 
                                found = True
                                break
                                
                        if found:
                            st.session_state.inventory_session[clean_code] = st.session_state.inventory_session.get(clean_code, 0) + add_qty
                            st.success(f"✅ تمت إضافة ({add_qty}) للصنف: {clean_code} | المجرد الفعلي: {st.session_state.inventory_session[clean_code]}")
                            render_product_card(clean_code, system_inventory[clean_code]['name'], system_inventory[clean_code]['sys_stock'], f"إجمالي الجرد الفعلي: {st.session_state.inventory_session[clean_code]} قطعة")
                        else:
                            st.error(f"❌ الباركود ({scan_code}) غير مسجل في أرصدة هذه الجلسة!")

            with inv_tab3:
                st.markdown("### ⚖️ تقرير الفروقات (الرصيد الدفتري vs الفعلي)")
                
                report_data = []
                for code, info in system_inventory.items():
                    sys_qty = info['sys_stock']
                    actual_qty = st.session_state.inventory_session.get(code, 0)
                    variance = actual_qty - sys_qty
                    
                    status = "🟢 مطابق"
                    if variance > 0: status = "🔵 زيادة"
                    elif variance < 0: status = "🔴 عجز"
                    
                    report_data.append({
                        "كود الصنف": code,
                        "اسم الصنف": info['name'],
                        "الرصيد الدفتري (سيستم)": sys_qty,
                        "الرصيد الفعلي (مجرد)": actual_qty,
                        "الفروقات (عجز/زيادة)": variance,
                        "الحالة": status
                    })
                    
                df_report = pd.DataFrame(report_data)
                
                def color_variance(val):
                    if val < 0: return 'color: red; font-weight: bold;'
                    elif val > 0: return 'color: blue; font-weight: bold;'
                    return 'color: green;'
                    
                styled_report = df_report.style.map(color_variance, subset=['الفروقات (عجز/زيادة)'])
                st.dataframe(styled_report, use_container_width=True, hide_index=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                csv = df_report.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 تحميل التقرير النهائي (Excel/CSV)",
                    data=csv,
                    file_name=f"Inventory_Report_{st.session_state.inv_name}_{st.session_state.inv_date}.csv",
                    mime="text/csv",
                )
                
                st.markdown("---")
                if st.button("🛑 إغلاق وإنهاء جلسة الجرد (مسح الذاكرة)"):
                    st.session_state.inv_active = False
                    st.session_state.inv_custom_df = None
                    st.session_state.inventory_session = {}
                    st.rerun()

st.markdown('<div class="footer">تصميم وبرمجة: <span>أبوبكر عادل</span> © 2026</div>', unsafe_allow_html=True)