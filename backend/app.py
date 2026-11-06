import os
import sys
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

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
