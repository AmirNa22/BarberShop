import os
import sys
import re
from datetime import datetime
from typing import Optional, List

# افزودن مسیر پوشه backend به sys.path جهت امکان اجرای منعطف
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from fastapi import FastAPI, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from database import init_db, get_db_connection

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

# مقداردهی اولیه دیتابیس
init_db()

app = FastAPI(
    title="Amir Style Studio API",
    description="سامانه مدرن نوبت‌دهی آرایشگاه توسعه‌یافته با FastAPI بر اساس استانداردهای مهندسی نرم‌افزار",
    version="2.0.0"
)

# فعال‌سازی CORS برای برقراری ارتباط با فرانت‌اند
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- دیتامدل‌های اعتبارسنجی ورودی (Pydantic) -----------------

class AppointmentCreate(BaseModel):
    name: str = Field(..., description="نام و نام خانوادگی مشتری")
    phone: str = Field(..., description="شماره موبایل ۱۱ رقمی معتبر ایران")
    service_name: str = Field(..., description="نام خدمت انتخاب‌شده")
    date: str = Field(..., description="تاریخ نوبت به فرمت YYYY-MM-DD")
    time: str = Field(..., description="ساعت اسلات ۳۰ دقیقه‌ای")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = (v or '').strip()
        if len(v) < 2:
            raise ValueError("نام و نام خانوادگی باید حداقل دارای ۲ کاراکتر باشد.")
        if len(v) > 50:
            raise ValueError("نام و نام خانوادگی نباید بیشتر از ۵۰ کاراکتر باشد.")
        return v

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = normalize_digits((v or '').strip())
        if not re.match(r'^09\d{9}$', v):
            raise ValueError("شماره موبایل نامعتبر است. شماره باید ۱۱ رقم بوده و با ۰۹ شروع شود (مثال: 09123456789).")
        return v

    @field_validator('service_name')
    @classmethod
    def validate_service_name(cls, v: str) -> str:
        v = (v or '').strip()
        if not v:
            raise ValueError("انتخاب خدمت الزامی است.")
        return v

    @field_validator('time')
    @classmethod
    def validate_time(cls, v: str) -> str:
        v = (v or '').strip()
        if v not in VALID_SLOTS:
            raise ValueError("ساعت انتخابی نامعتبر است. ساعات کاری بین ۱۰:۰۰ تا ۲۰:۰۰ و در بازه‌های ۳۰ دقیقه‌ای می‌باشد.")
        return v

    @field_validator('date')
    @classmethod
    def validate_date(cls, v: str) -> str:
        v = (v or '').strip()
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("فرمت تاریخ صحیح نمی‌باشد (فرمت استاندارد: YYYY-MM-DD).")
        return v

from fastapi.exceptions import RequestValidationError

# ----------------- مدیریت یکپارچه خطاهای اعتبارسنجی -----------------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    errors = exc.errors()
    msg = errors[0].get("msg", "داده‌های ارسالی نامعتبر است.") if errors else "داده‌های ارسالی نامعتبر است."
    if msg.startswith("Value error, "):
        msg = msg.replace("Value error, ", "")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"status": "error", "message": msg}
    )

@app.exception_handler(ValueError)
async def value_error_handler(request, exc: ValueError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"status": "error", "message": str(exc)}
    )

# ----------------- مسیرهای API -----------------

@app.get('/api/test', summary="بررسی وضعیت سرور")
def test_route():
    """مسیر تست برای بررسی سلامت و ارتباط با بک‌اند"""
    return {
        "status": "success",
        "message": "سلام، بک‌اند با FastAPI کار می‌کند"
    }

@app.get('/api/services', summary="دریافت لیست خدمات")
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
        return services
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "error", "message": str(e)}
        )

@app.get('/api/available-slots', summary="دریافت وضعیت اسلات‌های زمانی")
def get_available_slots(date: str = Query(..., description="تاریخ مورد نظر به فرمت YYYY-MM-DD")):
    """دریافت بازه‌های زمانی ۳۰ دقیقه‌ای و بررسی آزاد/پر بودن آن‌ها (قوانین R1 و R2)"""
    date_str = date.strip()
    if not date_str:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": "error", "message": "پارامتر date الزامی است."}
        )

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT time FROM appointments WHERE date = ? AND status = 'active'",
            (date_str,)
        )
        booked_times = {row['time'] for row in cursor.fetchall()}
        conn.close()

        slots = [
            {
                "time": slot,
                "available": slot not in booked_times
            }
            for slot in VALID_SLOTS
        ]

        return {"date": date_str, "slots": slots}
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "error", "message": str(e)}
        )

@app.post('/api/appointments', status_code=status.HTTP_201_CREATED, summary="ثبت نوبت جدید")
def create_appointment(payload: AppointmentCreate):
    """ثبت نوبت جدید با اعتبارسنجی قطعی قوانین R1 تا R3"""
    try:
        # قانون R3: ممانعت از رزرو در گذشته
        try:
            appointment_datetime = datetime.strptime(f"{payload.date} {payload.time}", "%Y-%m-%d %H:%M")
        except ValueError:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"status": "error", "message": "فرمت تاریخ یا ساعت صحیح نمی‌باشد."}
            )

        if appointment_datetime < datetime.now():
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"status": "error", "message": "امکان رزرو برای تاریخ یا ساعت گذشته وجود ندارد."}
            )

        # قانون R2: بررسی عدم تداخل نوبت در همان اسلات فعال
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM appointments WHERE date = ? AND time = ? AND status = 'active'",
            (payload.date, payload.time)
        )
        existing_appointment = cursor.fetchone()

        if existing_appointment:
            conn.close()
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "status": "error",
                    "message": "این ساعت قبلاً رزرو شده است. لطفاً بازه زمانی دیگری را انتخاب نمایید."
                }
            )

        # ثبت رکورد جدید در دیتابیس
        cursor.execute(
            '''
            INSERT INTO appointments (name, phone, service_name, date, time, status)
            VALUES (?, ?, ?, ?, ?, 'active')
            ''',
            (payload.name, payload.phone, payload.service_name, payload.date, payload.time)
        )
        conn.commit()
        appointment_id = cursor.lastrowid
        conn.close()

        return {
            "status": "success",
            "message": "نوبت شما با موفقیت ثبت شد.",
            "appointment": {
                "id": appointment_id,
                "name": payload.name,
                "phone": payload.phone,
                "service_name": payload.service_name,
                "date": payload.date,
                "time": payload.time,
                "status": "active"
            }
        }

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "error", "message": f"خطای سرور: {str(e)}"}
        )

@app.get('/api/appointments', summary="دریافت لیست نوبت‌های روز")
def get_appointments(date: str = Query(..., description="تاریخ مورد نظر به فرمت YYYY-MM-DD")):
    """دریافت نوبت‌های یک تاریخ مشخص به ترتیب ساعت (ویژه پنل مدیریت صاحب‌کار)"""
    date_str = date.strip()
    if not date_str:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": "error", "message": "پارامتر date الزامی است."}
        )

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
        return appointments
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "error", "message": f"خطای سرور: {str(e)}"}
        )

@app.api_route('/api/appointments/{appointment_id}/cancel', methods=['POST', 'PUT'], summary="لغو نوبت")
def cancel_appointment(appointment_id: int):
    """لغو نوبت بر اساس قانون R4: تغییر وضعیت به 'cancelled' بدون حذف فیزیکی رکورد"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # بررسی وجود نوبت
        cursor.execute("SELECT id, status, date, time FROM appointments WHERE id = ?", (appointment_id,))
        appointment = cursor.fetchone()

        if not appointment:
            conn.close()
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": "error", "message": "نوبت مورد نظر یافت نشد."}
            )

        if appointment["status"] == "cancelled":
            conn.close()
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"status": "error", "message": "این نوبت قبلاً لغو شده است."}
            )

        # تغییر وضعیت نوبت به cancelled
        cursor.execute(
            "UPDATE appointments SET status = 'cancelled' WHERE id = ?",
            (appointment_id,)
        )
        conn.commit()
        conn.close()

        return {
            "status": "success",
            "message": "نوبت با موفقیت لغو شد و بازه زمانی مجدداً آزاد گردید.",
            "appointment_id": appointment_id,
            "status_code": "cancelled"
        }

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "error", "message": f"خطای سرور: {str(e)}"}
        )

if __name__ == '__main__':
    import uvicorn
    # اجرای مستقیم سرور روی پورت ۵۰۰۰ سازگار با فرانت‌اند
    uvicorn.run("app:app", host="127.0.0.1", port=5000, reload=True)
