import os
import chromadb
import logging
import arabic_reshaper
from bidi.algorithm import get_display

# الدالة السحرية لضبط العربي في الشاشة السوداء
def fix_ar(text):
    reshaped_text = arabic_reshaper.reshape(str(text))
    bidi_text = get_display(reshaped_text)
    return bidi_text

logging.getLogger("chromadb").setLevel(logging.ERROR)

print(fix_ar("🔍 جاري فحص الذاكرة ومطابقتها بالصور... لحظات من فضلك."))

# 1. عد الصور في المجلد
image_folder = "images"
try:
    folder_count = len([f for f in os.listdir(image_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
except FileNotFoundError:
    folder_count = 0

# 2. عد الصور في قاعدة البيانات
try:
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    collection = chroma_client.get_collection(name="products_collection")
    db_count = collection.count()
except Exception as e:
    db_count = 0

print("\n" + "=" * 50)
print(fix_ar(f"📁 إجمالي الصور في مجلد (images) على جهازك: {folder_count} صورة"))
print(fix_ar(f"🗄️ إجمالي الصور المحفوظة داخل (قاعدة البيانات): {db_count} صورة"))
print("=" * 50 + "\n")

# 3. النتيجة
if folder_count == 0:
    print(fix_ar("❌ مجلد الصور فارغ!"))
elif folder_count == db_count:
    print(fix_ar("✅ ممتاز! قاعدة البيانات سليمة 100% وكل الصور تم حفظها بداخلها."))
elif db_count < folder_count:
    missing = folder_count - db_count
    print(fix_ar(f"⚠️ انتبه: هناك نقص! يوجد {missing} صورة لم يتم حفظها في الذاكرة بعد."))
    print(fix_ar("💡 الحل: قم بتشغيل أيقونة (Update Database) من سطح المكتب واتركه حتى يكمل الصور الناقصة."))
else:
    print(fix_ar("⚠️ هناك خطأ ما، قاعدة البيانات بها صور أكثر من المجلد!"))