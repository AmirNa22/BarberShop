import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'barbershop.db')

def get_db_connection():
    """ایجاد اتصال به دیتابیس SQLite با قابلیت دسترسی به نام ستون‌ها"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """ساخت جداول دیتابیس و مقداردهی اولیه خدمات"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # ایجاد جدول خدمات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            duration INTEGER NOT NULL
        )
    ''')

    # بررسی وجود خدمات اولیه
    cursor.execute('SELECT COUNT(*) FROM services')
    count = cursor.fetchone()[0]

    if count == 0:
        initial_services = [
            ('اصلاح مو', 300000, 30),
            ('اصلاح مو و ریش', 350000, 60),
            ('رنگ مو', 900000, 90),
            ('شست‌وشو و حالت‌دهی', 150000, 30)
        ]
        cursor.executemany(
            'INSERT INTO services (name, price, duration) VALUES (?, ?, ?)',
            initial_services
        )
        conn.commit()

    conn.close()

if __name__ == '__main__':
    init_db()
    print("دیتابیس با موفقیت راه‌اندازی و مقداردهی اولیه شد.")

