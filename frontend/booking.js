const API_BASE_URL = 'http://127.0.0.1:5000';

// اسلات‌های زمانی معتبر ۳۰ دقیقه‌ای بین ۱۰:۰۰ تا ۲۰:۰۰ (قانون R1)
const DEFAULT_SLOTS = [
    "10:00", "10:30", "11:00", "11:30",
    "12:00", "12:30", "13:00", "13:30",
    "14:00", "14:30", "15:00", "15:30",
    "16:00", "16:30", "17:00", "17:30",
    "18:00", "18:30", "19:00", "19:30"
];

// تبدیل اعداد به ارقام فارسی
function toPersianDigits(num) {
    return num.toString().replace(/\d/g, d => '۰۱۲۳۴۵۶۷۸۹'[d]);
}

// دریافت پارامترهای آدرس صفحه
function getQueryParam(param) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(param);
}

// بارگذاری لیست خدمات در منوی کشویی
async function loadServicesDropdown() {
    const selectElem = document.getElementById('service-select');
    try {
        const response = await fetch(`${API_BASE_URL}/api/services`);
        if (!response.ok) throw new Error('خطا در دریافت خدمات');
        const services = await response.json();

        selectElem.innerHTML = '<option value="">-- لطفاً یک خدمت را انتخاب کنید --</option>';
        
        const preselectedService = getQueryParam('service');

        services.forEach(service => {
            const option = document.createElement('option');
            option.value = service.name;
            const priceFormatted = Number(service.price).toLocaleString('fa-IR');
            option.textContent = `${service.name} (${toPersianDigits(service.duration)} دقیقه - ${priceFormatted} تومان)`;
            
            if (preselectedService && service.name.trim() === preselectedService.trim()) {
                option.selected = true;
            }

            selectElem.appendChild(option);
        });
    } catch (err) {
        console.error('Error loading services:', err);
        selectElem.innerHTML = '<option value="">⚠️ خطا در بارگذاری خدمات</option>';
    }
}

// تنظیم حداقل تاریخ انتخاب به تاریخ امروز
function setupDatePicker() {
    const dateInput = document.getElementById('date-input');
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    const minDateStr = `${yyyy}-${mm}-${dd}`;
    
    dateInput.min = minDateStr;
    dateInput.value = minDateStr;

    // بارگذاری اسلات‌های تاریخ امروز
    loadAvailableSlots(minDateStr);

    dateInput.addEventListener('change', (e) => {
        loadAvailableSlots(e.target.value);
    });
}

// دریافت اسلات‌های آزاد برای تاریخ انتخابی
async function loadAvailableSlots(dateStr) {
    const timeSelect = document.getElementById('time-select');
    if (!dateStr) {
        timeSelect.innerHTML = '<option value="">ابتدا تاریخ را انتخاب کنید</option>';
        return;
    }

    timeSelect.innerHTML = '<option value="">در حال بررسی بازه‌های آزاد...</option>';

    try {
        const response = await fetch(`${API_BASE_URL}/api/available-slots?date=${encodeURIComponent(dateStr)}`);
        if (!response.ok) throw new Error('خطا در دریافت اسلات‌ها');
        const data = await response.json();

        timeSelect.innerHTML = '<option value="">-- انتخاب ساعت --</option>';
        
        data.slots.forEach(slot => {
            const option = document.createElement('option');
            option.value = slot.time;
            if (slot.available) {
                option.textContent = `${toPersianDigits(slot.time)} (آزاد)`;
            } else {
                option.textContent = `${toPersianDigits(slot.time)} (پر شده)`;
                option.disabled = true;
            }
            timeSelect.appendChild(option);
        });
    } catch (err) {
        console.error('Error loading slots:', err);
        // اگر API اسلات در دسترس نبود، گزینه‌های پیش‌فرض را نشان بده
        timeSelect.innerHTML = '<option value="">-- انتخاب ساعت --</option>';
        DEFAULT_SLOTS.forEach(time => {
            const option = document.createElement('option');
            option.value = time;
            option.textContent = toPersianDigits(time);
            timeSelect.appendChild(option);
        });
    }
}

// مدیریت ارسال فرم رزرو
function setupFormSubmit() {
    const form = document.getElementById('booking-form');
    const errorBox = document.getElementById('form-error');
    const submitBtn = document.getElementById('submit-btn');
    const btnText = document.getElementById('btn-text');
    const btnSpinner = document.getElementById('btn-spinner');

    const bookingSection = document.getElementById('booking-section');
    const confirmationSection = document.getElementById('confirmation-section');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        errorBox.style.display = 'none';

        const payload = {
            name: document.getElementById('customer-name').value.trim(),
            phone: document.getElementById('customer-phone').value.trim(),
            service_name: document.getElementById('service-select').value,
            date: document.getElementById('date-input').value,
            time: document.getElementById('time-select').value
        };

        if (!payload.name || !payload.phone || !payload.service_name || !payload.date || !payload.time) {
            errorBox.textContent = 'لطفاً تمامی فیلدها را با دقت پر کنید.';
            errorBox.style.display = 'block';
            return;
        }

        // حالت لودینگ دکمه
        submitBtn.disabled = true;
        btnText.textContent = 'در حال ثبت نوبت...';
        btnSpinner.style.display = 'inline-block';

        try {
            const response = await fetch(`${API_BASE_URL}/api/appointments`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.message || 'خطا در ثبت نوبت');
            }

            // نمایش پیام و مشخصات خلاصه نوبت
            const apt = result.appointment;
            document.getElementById('summary-id').textContent = `#${toPersianDigits(apt.id)}`;
            document.getElementById('summary-name').textContent = apt.name;
            document.getElementById('summary-phone').textContent = apt.phone;
            document.getElementById('summary-service').textContent = apt.service_name;
            document.getElementById('summary-date').textContent = apt.date;
            document.getElementById('summary-time').textContent = `${toPersianDigits(apt.time)}`;

            bookingSection.style.display = 'none';
            confirmationSection.style.display = 'block';
            confirmationSection.scrollIntoView({ behavior: 'smooth' });

        } catch (err) {
            errorBox.textContent = `⚠️ ${err.message}`;
            errorBox.style.display = 'block';
            errorBox.scrollIntoView({ behavior: 'smooth' });
        } finally {
            submitBtn.disabled = false;
            btnText.textContent = 'ثبت نهایی نوبت';
            btnSpinner.style.display = 'none';
        }
    });

    // دکمه ثبت نوبت دیگر
    document.getElementById('book-another-btn').addEventListener('click', () => {
        form.reset();
        setupDatePicker();
        confirmationSection.style.display = 'none';
        bookingSection.style.display = 'block';
    });
}

document.addEventListener('DOMContentLoaded', () => {
    loadServicesDropdown();
    setupDatePicker();
    setupFormSubmit();
});

