import os
import sys

# افزودن مسیر پوشه backend به sys.path جهت امکان اجرای منعطف
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from flask import Flask, jsonify
from flask_cors import CORS
from database import init_db, get_db_connection

app = Flask(__name__)
# فعال‌سازی CORS برای برقراری ارتباط با فرانت‌اند
CORS(app)

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

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
