import os
import pandas as pd
import openpyxl
from openpyxl_image_loader import SheetImageLoader

print("⏳ جاري قراءة ملف الإكسيل... (هذا قد يستغرق دقيقة أو دقيقتين بسبب حجم البيانات الكبير، يرجى الانتظار)")

# 1. تجهيز مجلد الصور
image_folder = "images"
if not os.path.exists(image_folder):
    os.makedirs(image_folder)

# 2. تحميل الإكسيل وأداة سحب الصور
try:
    pxl_doc = openpyxl.load_workbook('data.xlsx', data_only=True)
    sheet = pxl_doc.active
    image_loader = SheetImageLoader(sheet)
except Exception as e:
    print(f"❌ حدث خطأ في قراءة ملف الإكسيل: {e}")
    exit()

# 3. إعداد قائمة لحفظ البيانات لعمل ملف CSV
products_data = []

# ==========================================
# ⚠️ يرجى تعديل حروف الأعمدة هنا إذا كانت مختلفة في ملفك
IMAGE_COL = 'A'  # عمود الصورة
CODE_COL = 'B'   # عمود الكود
NAME_COL = 'C'   # عمود الاسم
# ==========================================

start_row = 2  # نبدأ من الصف الثاني لتخطي صف العناوين
max_row = sheet.max_row
success_count = 0

print(f"🚀 بدأ استخراج البيانات والصور لـ {max_row - 1} منتج...")

for row in range(start_row, max_row + 1):
    cell_image = f"{IMAGE_COL}{row}"
    cell_code = f"{CODE_COL}{row}"
    cell_name = f"{NAME_COL}{row}"
    
    # قراءة الكود والاسم
    code_val = sheet[cell_code].value
    name_val = sheet[cell_name].value
    
    if code_val:
        # تنظيف الكود ليكون اسماً صالحاً للملفات
        clean_code = str(code_val).strip().replace("/", "-").replace("\\", "-")
        filename = f"{clean_code}.jpg"
        
        try:
            # محاولة سحب الصورة من الخلية
            image = image_loader.get(cell_image)
            # تحويل الصورة إلى RGB لضمان حفظها بصيغة JPG بدون مشاكل
            if image.mode != 'RGB':
                image = image.convert('RGB')
                
            image.save(os.path.join(image_folder, filename))
            
            # حفظ البيانات في القائمة
            products_data.append({
                "filename": filename,
                "code": clean_code,
                "name": str(name_val).strip() if name_val else "بدون اسم"
            })
            
            success_count += 1
            if success_count % 100 == 0:
                print(f"✅ تم استخراج {success_count} صورة بنجاح...")
                
        except ValueError:
            pass # لا توجد صورة في هذه الخلية
        except Exception as e:
            print(f"⚠️ خطأ في سحب صورة الصف {row}: {e}")

# 4. إنشاء ملف products.csv تلقائياً
print("\n📝 جاري إنشاء ملف قاعدة البيانات (products.csv)...")
df = pd.DataFrame(products_data)
df.to_csv('products.csv', index=False, encoding='utf-8-sig')

print(f"🎉 اكتملت المهمة بنجاح! تم استخراج {success_count} صورة وإنشاء ملف products.csv الخاص بالبرنامج.")