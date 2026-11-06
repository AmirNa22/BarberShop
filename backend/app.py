from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
# فعال‌سازی CORS برای امکان اتصال درخواست‌های فرانت‌اند
CORS(app)

@app.route('/api/test', methods=['GET'])
def test_route():
    """مسیر تست برای بررسی صحت عملکرد سرور بک‌اند"""
    return jsonify({
        "status": "success",
        "message": "سلام، بک‌اند کار می‌کند"
    }), 200

if __name__ == '__main__':
    # اجرای سرور به صورت لوکال روی پورت 5000
    app.run(host='127.0.0.1', port=5000, debug=True)

