import streamlit as st
import chromadb
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import torch
import os
import zipfile
import urllib.request
import pandas as pd
from rembg import remove, new_session

# 1. تهيئة موديل عزل الخلفية الخفيف جداً (عشان السيرفر ميقعش)
@st.cache_resource
def get_rembg_session():
    # استخدام نسخة u2netp الخفيفة جداً (4 ميجابايت) بدلاً من النسخة الثقيلة
    return new_session("u2netp")

rembg_session = get_rembg_session()

# 2. دالة تحميل قاعدة البيانات
@st.cache_resource
def download_new_chroma_db():
    zip_path = "chroma_db.zip"
    extract_path = "./chroma_db"
    
    download_url = "https://github.com/abobakradel90-source/search-app/releases/download/v1.0/chroma_db.zip"
    
    if os.path.exists(zip_path):
        os.remove(zip_path)
        
    if not os.path.exists(extract_path):
        with st.spinner('جاري تهيئة النظام وقاعدة البيانات الأساسية...'):
            try:
                urllib.request.urlretrieve(download_url, zip_path)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(".")
                if os.path.exists(zip_path):
                    os.remove(zip_path)
            except Exception as e:
                st.error(f"حدث خطأ أثناء تحميل قاعدة البيانات: {e}")

# 3. تحميل موديل CLIP (النسخة الأصلية المتوافقة 100% مع قاعدة بياناتك)
@st.cache_resource
def load_clip_system():
    download_new_chroma_db()
    
    model_id = "openai/clip-vit-base-patch32"
    processor = CLIPProcessor.from_pretrained(model_id)
    model = CLIPModel.from_pretrained(model_id)
    
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_collection(name="products_collection")
    return model, processor, collection

model, processor, collection = load_clip_system()

# 4. قراءة الـ CSV
@st.cache_data
def load_csv_data():
    try:
        df = pd.read_csv('products.csv')
        df.columns = df.columns.astype(str).str.strip()
        return df, None
    except Exception as e:
        return None, str(e)

df_products, error_msg = load_csv_data()

# 5. دالة معالجة الصورة (السحر الحقيقي لدقة 100%)
def process_and_isolate_shoe(image):
    image = image.convert("RGB")
    
    # 1. عزل الخلفية بالموديل الخفيف لتركيز الذكاء الاصطناعي على الكوتشي فقط
    isolated_rgba = remove(image, session=rembg_session)
    
    # 2. وضع الكوتشي على خلفية بيضاء نقية (زي صور الاستوديو)
    final_image = Image.new("RGB", isolated_rgba.size, (255, 255, 255))
    final_image.paste(isolated_rgba, mask=isolated_rgba.split()[3])
    
    return final_image

def get_image_embedding(image):
    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        features = model.get_image_features(**inputs)
        if not isinstance(features, torch.Tensor):
            if hasattr(features, 'pooler_output'):
                features = features.pooler_output
            else:
                features = features[0]
    return features.squeeze().numpy().tolist()

# 6. الواجهة الرئيسية
st.title("ED STORE ABOBAKR ADEl 👟🔥 (Ultimate Precision)")
st.info(f"📦 المنتجات: {collection.count()} | 🎯 وضع الاستوديو وعزل الخلفية مفعل")

tab1, tab2, tab3 = st.tabs(["📷 تصوير بالكاميرا (مُحسن)", "📁 رفع صورة", "🔍 بحث بالكود (مضمون 100%)"])

# المتغير اللي هيشيل الصورة أياً كان مصدرها
image_to_search = None

with tab1:
    camera_photo = st.camera_input("التقط صورة واضحة للكوتشي")
    if camera_photo:
        image_to_search = camera_photo

with tab2:
    uploaded_file = st.file_uploader("اختر صورة من جهازك", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        image_to_search = uploaded_file

with tab3:
    st.subheader("البحث الفوري بالكود أو الاسم (لا يحتمل الخطأ)")
    if df_products is not None:
        search_query = st.text_input("اكتب الكود أو الاسم هنا:")
        if search_query:
            cols = df_products.columns
            code_col = 'Code' if 'Code' in cols else cols[0]
            name_col = 'Name' if 'Name' in cols else cols[1]
            
            mask = df_products[code_col].astype(str).str.contains(search_query, case=False, na=False) | \
                   df_products[name_col].astype(str).str.contains(search_query, case=False, na=False)
            
            matched_df = df_products[mask]
            if matched_df.empty:
                st.warning("لم يتم العثور على منتج.")
            else:
                for idx, row in matched_df.iterrows():
                    st.success(f"👟 {row[name_col]} | الكود: {row[code_col]}")

# معالجة البحث بالصورة
if image_to_search:
    if st.button("🔍 ابحث بالذكاء الاصطناعي الآن", use_container_width=True):
        st.markdown("---")
        
        with st.spinner('✨ جاري عزل الخلفية وتحويل الصورة لوضع الاستوديو للبحث بدقة...'):
            try:
                original_img = Image.open(image_to_search)
                
                # تطبيق العزل الذكي
                clean_studio_img = process_and_isolate_shoe(original_img)
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.image(original_img, caption="الصورة الأصلية", use_container_width=True)
                with col_b:
                    st.image(clean_studio_img, caption="الكوتشي بعد العزل (جاهز للبحث)", use_container_width=True)
                
                # استخراج الخصائص من الصورة النظيفة
                query_embedding = get_image_embedding(clean_studio_img)
                
                # البحث في قاعدة البيانات الأصلية
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=3, 
                    include=['distances', 'metadatas']
                )
                
                if not results['distances'][0]:
                    st.warning("لم يتم العثور على أي منتج مطابق.")
                else:
                    st.success(f"✅ أفضل النتائج المطابقة:")
                    for i in range(len(results['distances'][0])):
                        distance = results['distances'][0][i]
                        metadata = results['metadatas'][0][i]
                        filename = metadata.get('filename', 'غير متوفر')
                        product_code = filename.split('.')[0] if filename != 'غير متوفر' else 'غير متوفر'
                        product_name = "غير متوفر"
                        
                        if df_products is not None:
                            try:
                                cols = df_products.columns
                                code_col = 'Code' if 'Code' in cols else cols[0]
                                name_col = 'Name' if 'Name' in cols else cols[1]
                                df_products['cleaned_code'] = df_products[code_col].astype(str).str.strip().str.lower()
                                target_cleaned = str(product_code).strip().lower()
                                row = df_products[df_products['cleaned_code'] == target_cleaned]
                                if not row.empty:
                                    product_name = str(row.iloc[0][name_col]).strip()
                            except:
                                pass

                        st.markdown(f"### النتيجة #{i+1}")
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            img_path = os.path.join("compressed_images", filename)
                            if os.path.exists(img_path):
                                st.image(img_path, use_container_width=True)
                        with col2:
                            st.write(f"**الكود:** {product_code}")
                            st.write(f"**الاسم:** {product_name}")
                        st.markdown("---")
            except Exception as e:
                st.error(f"حدث خطأ أثناء فحص الصورة: {str(e)}")