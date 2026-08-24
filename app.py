import streamlit as st
import chromadb
from transformers import AutoImageProcessor, AutoModel
from PIL import Image
import torch
import os
import zipfile
import urllib.request
import pandas as pd

# دالة لتحميل وفك ضغط قاعدة البيانات من جوجل درايف
@st.cache_resource
def download_and_extract_chroma():
    zip_path = "chroma_db.zip"
    extract_path = "./chroma_db"
    
    # رابط التحميل المباشر من جوجل درايف
    file_id = "12tEZL-ErKOakDhXeQAAv8X2tO-h56LTd"
    download_url = f"https://drive.google.com/uc?id={file_id}"
    
    # لو الفولدر مش موجود، نزله وفكه
    if not os.path.exists(extract_path):
        with st.spinner('جاري تهيئة قاعدة البيانات لأول مرة (قد يستغرق دقيقة)...'):
            try:
                # تحميل الملف المضغوط
                urllib.request.urlretrieve(download_url, zip_path)
                
                # فك الضغط
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(".")
                
                # مسح الملف المضغوط بعد الفك لتوفير المساحة
                os.remove(zip_path)
            except Exception as e:
                st.error(f"حدث خطأ أثناء تحميل قاعدة البيانات: {e}")

@st.cache_resource
def load_system():
    # استدعاء دالة التحميل أولاً
    download_and_extract_chroma()
    
    # تحميل الموديل
    processor = AutoImageProcessor.from_pretrained('facebook/dinov2-base')
    model = AutoModel.from_pretrained('facebook/dinov2-base')
    
    # تشغيل قاعدة البيانات المجهزة
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_collection(name="products_collection")
    
    return model, processor, collection

# تحميل النظام
model, processor, collection = load_system()

# استخراج الخصائص من الصورة
def get_image_embedding(image):
    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
    return outputs.last_hidden_state.mean(dim=1).squeeze().numpy().tolist()

# إعداد واجهة المستخدم
st.title("البحث الصارم عن المنتجات 🔍")
st.write("قم برفع صورة للبحث عن المنتجات المطابقة أو المشابهة جداً")

uploaded_file = st.file_uploader("اختر صورة...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # عرض الصورة المرفوعة
    image = Image.open(uploaded_file).convert('RGB')
    st.image(image, caption='الصورة المرفوعة', use_column_width=True)
    
    if st.button("ابحث عن المنتج"):
        with st.spinner('جاري البحث...'):
            try:
                # استخراج خصائص الصورة المرفوعة
                query_embedding = get_image_embedding(image)
                
                # البحث في قاعدة البيانات (البحث عن أقرب نتيجة واحدة)
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=5, # جلب أفضل 5 نتائج لفلترتها
                    include=['distances', 'metadatas']
                )
                
                # التحقق من وجود نتائج
                if not results['distances'][0]:
                    st.warning("لم يتم العثور على أي منتج مطابق في قاعدة البيانات.")
                else:
                    # فلترة النتائج بناءً على نسبة التطابق (المسافة)
                    # كلما قلت المسافة (distance)، زاد التطابق
                    strict_threshold = 50.0  # يمكنك تعديل هذا الرقم لزيادة أو تقليل الصرامة
                    
                    found_match = False
                    
                    for i in range(len(results['distances'][0])):
                        distance = results['distances'][0][i]
                        metadata = results['metadatas'][0][i]
                        
                        if distance < strict_threshold:
                            found_match = True
                            st.success("تم العثور على منتج مطابق!")
                            
                            # عرض بيانات المنتج
                            st.subheader("تفاصيل المنتج:")
                            st.write(f"**رقم المنتج (ID):** {metadata.get('id', 'غير متوفر')}")
                            st.write(f"**اسم المنتج:** {metadata.get('product_name', 'غير متوفر')}")
                            st.write(f"**السعر:** {metadata.get('price', 'غير متوفر')}")
                            st.write(f"**نسبة الاختلاف (Distance):** {distance:.2f} (كلما قل الرقم كان التطابق أفضل)")
                            
                            # التوقف عند أول منتج مطابق تماماً
                            break 
                    
                    if not found_match:
                         st.warning("لم يتم العثور على منتج مطابق تماماً. المنتجات الموجودة مختلفة عن الصورة المرفوعة.")
                         
            except Exception as e:
                st.error(f"حدث خطأ أثناء البحث: {str(e)}")