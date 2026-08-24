import streamlit as st
import torch
from transformers import AutoImageProcessor, AutoModel
from PIL import Image, ImageGrab  # أضفنا أداة قراءة ذاكرة الويندوز
import chromadb
import pandas as pd
import os
import logging
from streamlit_cropper import st_cropper

logging.getLogger("transformers").setLevel(logging.ERROR)

st.set_page_config(page_title="محرك البحث البصري الدقيق", layout="wide")
st.markdown("<h1 style='text-align: center; color: #2e6c80;'>البحث الصارم عن المنتجات 🔍</h1>", unsafe_allow_html=True)
st.markdown("---")

@st.cache_resource
def load_system():
    processor = AutoImageProcessor.from_pretrained('facebook/dinov2-base')
    model = AutoModel.from_pretrained('facebook/dinov2-base')
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    collection = chroma_client.get_collection(name="products_collection")
    return model, processor, collection

model, processor, collection = load_system()

try:
    df = pd.read_csv("products.csv")
    has_data = True
except FileNotFoundError:
    has_data = False

# حفظ الصورة الحالية في الذاكرة المؤقتة للبرنامج
if 'target_image' not in st.session_state:
    st.session_state.target_image = None

# واجهة سريعة مقسمة لنصفين
col_a, col_b = st.columns(2)

with col_a:
    uploaded_file = st.file_uploader("📂 رفع ملف صورة", type=['png', 'jpg', 'jpeg'])
    if uploaded_file is not None:
        st.session_state.target_image = Image.open(uploaded_file).convert("RGB")

with col_b:
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("📋 سحب الصورة المنسوخة (سريع) ⚡", use_container_width=True):
        try:
            # أمر بايثون السري لقراءة الحافظة مباشرة من الويندوز
            clipboard_content = ImageGrab.grabclipboard()
            if isinstance(clipboard_content, Image.Image):
                st.session_state.target_image = clipboard_content.convert("RGB")
            elif isinstance(clipboard_content, list) and len(clipboard_content) > 0:
                img_path = clipboard_content[0]
                if img_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                    st.session_state.target_image = Image.open(img_path).convert("RGB")
                else:
                    st.warning("⚠️ الملف المنسوخ ليس صورة.")
            else:
                st.warning("⚠️ الحافظة فارغة. قم بنسخ صورة (Copy) أولاً.")
        except Exception as e:
            st.error(f"حدث خطأ في قراءة الحافظة: {e}")

# عرض أداة القص والبحث إذا كانت هناك صورة
if st.session_state.target_image is not None:
    st.info("✂️ **القص الذكي:** اسحب المربع الأزرق لتحديد المنتج فقط قبل البحث.")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        cropped_image = st_cropper(st.session_state.target_image, realtime_update=True, box_color='#0000FF')
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("ابحث عن المطابق تماماً 🚀", use_container_width=True):
        with st.spinner("جاري المطابقة بالبصمة الدقيقة..."):
            inputs = processor(images=cropped_image, return_tensors="pt")
            with torch.no_grad():
                outputs = model(**inputs)
                query_embedding = outputs.last_hidden_state[0, 0].tolist()
            
            db_size = collection.count()
            if db_size == 0:
                st.error("قاعدة البيانات فارغة!")
            else:
                search_results_count = min(3, db_size)
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=search_results_count
                )
                
                st.success("✅ النتائج الأقرب هندسياً:")
                st.markdown("---")
                
                result_cols = st.columns(search_results_count)
                
                for i, col in enumerate(result_cols):
                    match_filename = results['ids'][0][i]
                    
                    product_code, product_name = "غير مسجل", "غير مسجل"
                    if has_data:
                        row = df[df['filename'] == match_filename]
                        if not row.empty:
                            product_code = row['code'].values[0]
                            product_name = row['name'].values[0]
                    
                    with col:
                        img_path = os.path.join("images", match_filename)
                        if os.path.exists(img_path):
                            st.image(Image.open(img_path), use_container_width=True)
                        
                        st.info(f"**الكود:** {product_code}\n\n**الاسم:** {product_name}")