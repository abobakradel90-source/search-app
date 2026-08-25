import streamlit as st
import chromadb
from transformers import AutoImageProcessor, AutoModel
from PIL import Image
import torch
import os
import zipfile
import urllib.request

# 1. دالة التحميل
@st.cache_resource
def download_and_extract_chroma():
    zip_path = "chroma_db.zip"
    extract_path = "./chroma_db"
    
    download_url = "https://github.com/abobakradel90-source/search-app/releases/download/v1.0/chroma_db.zip"
    
    if os.path.exists(zip_path):
        os.remove(zip_path)
        
    if not os.path.exists(extract_path):
        with st.spinner('جاري تهيئة النظام وقاعدة البيانات...'):
            try:
                urllib.request.urlretrieve(download_url, zip_path)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(".")
                if os.path.exists(zip_path):
                    os.remove(zip_path)
            except Exception as e:
                st.error(f"حدث خطأ أثناء تحميل قاعدة البيانات: {e}")

# 2. تحميل الموديل وقاعدة البيانات
@st.cache_resource
def load_system():
    download_and_extract_chroma()
    processor = AutoImageProcessor.from_pretrained('facebook/dinov2-base')
    model = AutoModel.from_pretrained('facebook/dinov2-base')
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_collection(name="products_collection")
    return model, processor, collection

model, processor, collection = load_system()

def get_image_embedding(image):
    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
    return outputs.last_hidden_state.mean(dim=1).squeeze().numpy().tolist()

# 3. واجهة المستخدم الاحترافية
st.title("البحث الصارم عن المنتجات 🔍")

tab1, tab2 = st.tabs(["📁 رفع صور من الجهاز", "📷 التقاط بالكاميرا"])

images_to_process = []

with tab1:
    uploaded_files = st.file_uploader("اختر صورة أو أكثر...", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    if uploaded_files:
        images_to_process.extend(uploaded_files)
        
with tab2:
    camera_photo = st.camera_input("التقط صورة للمنتج")
    if camera_photo:
        images_to_process.append(camera_photo)

if images_to_process:
    if st.button("ابحث عن المنتجات الآن", use_container_width=True):
        for img_file in images_to_process:
            st.markdown("---")
            
            st.image(img_file, caption=f'الصورة: {img_file.name}', use_container_width=True)
            
            with st.spinner('جاري البحث في قاعدة البيانات...'):
                try:
                    image = Image.open(img_file).convert('RGB')
                    query_embedding = get_image_embedding(image)
                    
                    results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=5,
                        include=['distances', 'metadatas']
                    )
                    
                    if not results['distances'][0]:
                        st.warning("لم يتم العثور على أي منتج مطابق في قاعدة البيانات.")
                    else:
                        strict_threshold = 50.0  
                        found_match = False
                        
                        for i in range(len(results['distances'][0])):
                            distance = results['distances'][0][i]
                            metadata = results['metadatas'][0][i]
                            
                            if distance < strict_threshold:
                                found_match = True
                                st.success("✅ تم العثور على منتج مطابق!")
                                
                                # استخراج البيانات المتاحة
                                filename = metadata.get('filename', 'غير متوفر')
                                
                                # استخراج كود المنتج بذكاء (إزالة .jpg أو .png)
                                product_code = filename.split('.')[0] if filename != 'غير متوفر' else 'غير متوفر'
                                
                                st.write(f"**كود المنتج:** {product_code}")
                                st.write(f"**اسم ملف الصورة الأصلية:** {filename}")
                                st.write(f"**نسبة الاختلاف:** {distance:.2f} (كلما قل الرقم كان التطابق أفضل)")
                                
                                break 
                        
                        if not found_match:
                             st.warning("⚠️ لم يتم العثور على منتج مطابق تماماً. المنتجات الموجودة مختلفة عن الصورة المرفوعة.")
                             
                except Exception as e:
                    st.error(f"حدث خطأ أثناء فحص الصورة: {str(e)}")