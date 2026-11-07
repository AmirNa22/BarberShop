import os
import sys
import re
from datetime import datetime

# افزودن مسیر پوشه backend به sys.path جهت امکان اجرای منعطف
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from flask import Flask, jsonify, request
from flask_cors import CORS
from database import init_db, get_db_connection

app = Flask(__name__)
# فعال‌سازی CORS برای برقراری ارتباط با فرانت‌اند
CORS(app)

# اسلات‌های زمانی معتبر ۳۰ دقیقه‌ای بین ۱۰:۰۰ تا ۲۰:۰۰ (قانون R1)
VALID_SLOTS = [
    "10:00", "10:30", "11:00", "11:30",
    "12:00", "12:30", "13:00", "13:30",
    "14:00", "14:30", "15:00", "15:30",
    "16:00", "16:30", "17:00", "17:30",
    "18:00", "18:30", "19:00", "19:30"
]

def normalize_digits(text: str) -> str:
    """تبدیل ارقام فارسی و عربی به ارقام انگلیسی"""
    if not text:
        return ""
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    arabic_digits = '٠١٢٣٤٥٦٧٨٩'
    for i in range(10):
        text = text.replace(persian_digits[i], str(i)).replace(arabic_digits[i], str(i))
    return text

# مقداردهی اولیه پایگاه‌داده
init_db()

@app.route('/api/test', methods=['GET'])
def test_route():
    """مسیر تست برای بررسی وضعیت بک‌اند"""
    return jsonify({
        "status": "success",
        "message": "سلام، بک‌اند کار می‌کند"
    }), 200

@app.route('/api/services', methods=['GET'])
def get_services():
    """دریافت فهرست تمام خدمات آرایشگاه از دیتابیس"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, price, duration FROM services')
        rows = cursor.fetchall()
        conn.close()

        services = [
            {
                "id": row["id"],
                "name": row["name"],
                "price": row["price"],
                "duration": row["duration"]
            }
            for row in rows
        ]
        return jsonify(services), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/appointments', methods=['POST'])
def create_appointment():
    """ثبت نوبت جدید با اعتبارسنجی قطعی قوانین R1 تا R3"""
    try:
        data = request.get_json() or {}
        name = (data.get('name') or '').strip()
        phone = (data.get('phone') or '').strip()
        service_name = (data.get('service_name') or '').strip()
        date_str = (data.get('date') or '').strip()
        time_str = (data.get('time') or '').strip()

        # بررسی الزامی بودن تمام فیلدها
        if not all([name, phone, service_name, date_str, time_str]):
            return jsonify({
                "status": "error",
                "message": "لطفاً تمامی فیلدها (نام، شماره تماس، خدمت، تاریخ و ساعت) را تکمیل فرمایید."
            }), 400

        # اعتبارسنجی طول نام (حداکثر ۵۰ کاراکتر)
        if len(name) > 50:
            return jsonify({
                "status": "error",
                "message": "نام و نام خانوادگی نباید بیشتر از ۵۰ کاراکتر باشد."
            }), 400

        if len(name) < 2:
            return jsonify({
                "status": "error",
                "message": "نام و نام خانوادگی باید حداقل دارای ۲ کاراکتر باشد."
            }), 400

        # نرمال‌سازی ارقام و اعتبارسنجی قطعی شماره موبایل ایران (۱۱ رقم با پیش‌شماره 09)
        phone = normalize_digits(phone)
        if not re.match(r'^09\d{9}$', phone):
            return jsonify({
                "status": "error",
                "message": "شماره موبایل نامعتبر است. شماره باید ۱۱ رقم بوده و با ۰۹ شروع شود (مثال: 09123456789)."
            }), 400

        # بررسی قانون R1: ساعات مجاز و بازه‌های ۳۰ دقیقه‌ای
        if time_str not in VALID_SLOTS:
            return jsonify({
                "status": "error",
                "message": "ساعت انتخابی نامعتبر است. ساعات کاری بین ۱۰:۰۰ تا ۲۰:۰۰ و در بازه‌های ۳۰ دقیقه‌ای می‌باشد."
            }), 400

        # بررسی فرمت تاریخ و قانون R3: ممانعت از رزرو برای زمان گذشته
        try:
            appointment_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except ValueError:
            return jsonify({
                "status": "error",
                "message": "فرمت تاریخ یا ساعت صحیح نمی‌باشد (فرمت تاریخ: YYYY-MM-DD)."
            }), 400

        if appointment_datetime < datetime.now():
            return jsonify({
                "status": "error",
                "message": "امکان رزرو برای تاریخ یا ساعت گذشته وجود ندارد."
            }), 400

        # بررسی قانون R2: جلوگیری از رزرو تکراری در همان اسلات فعال
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM appointments WHERE date = ? AND time = ? AND status = 'active'",
            (date_str, time_str)
        )
        existing_appointment = cursor.fetchone()

        if existing_appointment:
            conn.close()
            return jsonify({
                "status": "error",
                "message": "این ساعت قبلاً رزرو شده است. لطفاً بازه زمانی دیگری را انتخاب نمایید."
            }), 409

        # ثبت نوبت در پایگاه‌داده
        cursor.execute(
            '''
            INSERT INTO appointments (name, phone, service_name, date, time, status)
            VALUES (?, ?, ?, ?, ?, 'active')
            ''',
            (name, phone, service_name, date_str, time_str)
        )
        conn.commit()
        appointment_id = cursor.lastrowid
        conn.close()

        return jsonify({
            "status": "success",
            "message": "نوبت شما با موفقیت ثبت شد.",
            "appointment": {
                "id": appointment_id,
                "name": name,
                "phone": phone,
                "service_name": service_name,
                "date": date_str,
                "time": time_str,
                "status": "active"
            }
        }), 201

    except Exception as e:
        return jsonify({"status": "error", "message": f"خطای سرور: {str(e)}"}), 500

@app.route('/api/available-slots', methods=['GET'])
def get_available_slots():
    """دریافت بازه‌های زمانی و وضعیت پر یا خالی بودن آن‌ها برای یک تاریخ مشخص"""
    date_str = request.args.get('date', '').strip()
    if not date_str:
        return jsonify({"status": "error", "message": "پارامتر date الزامی است."}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT time FROM appointments WHERE date = ? AND status = 'active'",
            (date_str,)
        )
        booked_times = {row['time'] for row in cursor.fetchall()}
        conn.close()

        slots = []
        for slot in VALID_SLOTS:
            slots.append({
                "time": slot,
                "available": slot not in booked_times
            })

        return jsonify({"date": date_str, "slots": slots}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/appointments', methods=['GET'])
def get_appointments():
    """دریافت نوبت‌های یک تاریخ مشخص به ترتیب ساعت (ویژه صاحب‌کار)"""
    date_str = request.args.get('date', '').strip()
    if not date_str:
        return jsonify({
            "status": "error",
            "message": "پارامتر date برای دریافت نوبت‌ها الزامی است (فرمت: YYYY-MM-DD)."
        }), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT id, name, phone, service_name, date, time, status, created_at
            FROM appointments
            WHERE date = ?
            ORDER BY time ASC
            ''',
            (date_str,)
        )
        rows = cursor.fetchall()
        conn.close()

        appointments = [
            {
                "id": row["id"],
                "name": row["name"],
                "phone": row["phone"],
                "service_name": row["service_name"],
                "date": row["date"],
                "time": row["time"],
                "status": row["status"],
                "created_at": row["created_at"]
            }
            for row in rows
        ]
        return jsonify(appointments), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"خطای سرور: {str(e)}"}), 500

@app.route('/api/appointments/<int:appointment_id>/cancel', methods=['POST', 'PUT'])
def cancel_appointment(appointment_id):
    """لغو نوبت بر اساس قانون R4: تغییر وضعیت به 'cancelled' بدون حذف فیزیکی رکورد"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # بررسی وجود نوبت
        cursor.execute("SELECT id, status, date, time FROM appointments WHERE id = ?", (appointment_id,))
        appointment = cursor.fetchone()

        if not appointment:
            conn.close()
            return jsonify({
                "status": "error",
                "message": "نوبت مورد نظر یافت نشد."
            }), 404

        if appointment["status"] == "cancelled":
            conn.close()
            return jsonify({
                "status": "error",
                "message": "این نوبت قبلاً لغو شده است."
            }), 400

        # تغییر وضعیت به لغو شده
        cursor.execute(
            "UPDATE appointments SET status = 'cancelled' WHERE id = ?",
            (appointment_id,)
        )
        conn.commit()
        conn.close()

        return jsonify({
            "status": "success",
            "message": "نوبت با موفقیت لغو شد و بازه زمانی مجدداً آزاد گردید.",
            "appointment_id": appointment_id,
            "status_code": "cancelled"
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"خطای سرور: {str(e)}"}), 500

@app.route('/api/appointments/<int:appointment_id>', methods=['DELETE'])
@app.route('/api/appointments/<int:appointment_id>/delete', methods=['POST', 'DELETE'])
def delete_appointment(appointment_id):
    """حذف دائمی یک نوبت مشخص از پایگاه‌داده (ویژه صاحب‌کار)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # بررسی وجود نوبت
        cursor.execute("SELECT id, status, name, date, time FROM appointments WHERE id = ?", (appointment_id,))
        appointment = cursor.fetchone()

        if not appointment:
            conn.close()
            return jsonify({
                "status": "error",
                "message": "نوبت مورد نظر یافت نشد."
            }), 404

        # حذف فیزیکی رکورد از دیتابیس
        cursor.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
        conn.commit()
        conn.close()

        return jsonify({
            "status": "success",
            "message": "نوبت با موفقیت از سیستم حذف گردید.",
            "appointment_id": appointment_id
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"خطای سرور: {str(e)}"}), 500

@app.route('/api/appointments/clear-cancelled', methods=['POST', 'DELETE'])
def clear_cancelled_appointments():
    """حذف گروهی تمام نوبت‌های لغو شده یک روز مشخص جهت پاکسازی جدول"""
    date_str = request.args.get('date', '').strip()
    if not date_str:
        return jsonify({"status": "error", "message": "پارامتر date الزامی است."}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM appointments WHERE date = ? AND status = 'cancelled'",
            (date_str,)
        )
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        return jsonify({
            "status": "success",
            "message": f"تعداد {deleted_count} نوبت لغو شده با موفقیت پاک شدند.",
            "deleted_count": deleted_count
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"خطای سرور: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
