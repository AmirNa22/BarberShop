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
        selectElem.innerHTML = '<option value="">⚠️ خطا در بارگذاری خدمات (عدم اتصال به سرور)</option>';
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

// دریافت و نمایش اسلات‌های زمانی به صورت دکمه‌های مستقیم در دسترس (بدون منوی کشویی)
async function loadAvailableSlots(dateStr) {
    const slotsContainer = document.getElementById('slots-container');
    const timeInput = document.getElementById('time-input');
    const previewBox = document.getElementById('selected-slot-preview');
    const previewTime = document.getElementById('selected-slot-time');

    // ریست انتخاب قبلی
    timeInput.value = '';
    if (previewBox) previewBox.style.display = 'none';

    if (!dateStr) {
        slotsContainer.innerHTML = '<div class="slots-empty-notice">ابتدا تاریخ را انتخاب فرمایید.</div>';
        return;
    }

    slotsContainer.innerHTML = '<div class="slots-loading">در حال بررسی ساعت‌های آزاد...</div>';

    try {
        const response = await fetch(`${API_BASE_URL}/api/available-slots?date=${encodeURIComponent(dateStr)}`);
        if (!response.ok) throw new Error('خطا در دریافت وضعیت اسلات‌ها');
        const data = await response.json();

        slotsContainer.innerHTML = '';
        let availableCount = 0;

        data.slots.forEach(slot => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'slot-btn';
            btn.setAttribute('data-time', slot.time);

            if (slot.available) {
                availableCount++;
                btn.innerHTML = `<span class="slot-time">${toPersianDigits(slot.time)}</span><span class="slot-badge-free">آزاد</span>`;
                btn.addEventListener('click', () => {
                    document.querySelectorAll('.slot-btn').forEach(b => b.classList.remove('selected'));
                    btn.classList.add('selected');
                    timeInput.value = slot.time;
                    previewTime.textContent = toPersianDigits(slot.time);
                    if (previewBox) previewBox.style.display = 'flex';
                });
            } else {
                btn.classList.add('disabled');
                btn.disabled = true;
                btn.innerHTML = `<span class="slot-time">${toPersianDigits(slot.time)}</span><span class="slot-badge-taken">پر شده</span>`;
            }

            slotsContainer.appendChild(btn);
        });

        if (availableCount === 0) {
            slotsContainer.innerHTML = '<div class="slots-empty-notice">متأسفانه برای این تاریخ تمامی نوبت‌ها رزرو شده است. لطفاً تاریخ دیگری را انتخاب فرمایید.</div>';
        }

    } catch (err) {
        console.error('Error loading slots:', err);
        slotsContainer.innerHTML = '';
        DEFAULT_SLOTS.forEach(time => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'slot-btn';
            btn.setAttribute('data-time', time);
            btn.innerHTML = `<span class="slot-time">${toPersianDigits(time)}</span><span class="slot-badge-free">انتخاب</span>`;
            btn.addEventListener('click', () => {
                document.querySelectorAll('.slot-btn').forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
                timeInput.value = time;
                previewTime.textContent = toPersianDigits(time);
                if (previewBox) previewBox.style.display = 'flex';
            });
            slotsContainer.appendChild(btn);
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

        const nameInput = document.getElementById('customer-name');
        const phoneInput = document.getElementById('customer-phone');

        let rawPhone = phoneInput.value.trim();
        // نرمال‌سازی ارقام فارسی و عربی به ارقام انگلیسی
        let phone = rawPhone
            .replace(/[۰-۹]/g, d => '۰۱۲۳۴۵۶۷۸۹'.indexOf(d))
            .replace(/[٠-٩]/g, d => '٠١٢٣٤٥٦٧٨٩'.indexOf(d));
        let name = nameInput.value.trim();

        const payload = {
            name: name,
            phone: phone,
            service_name: document.getElementById('service-select').value,
            date: document.getElementById('date-input').value,
            time: (document.getElementById('time-input').value || '').trim()
        };

        if (!payload.name || !payload.phone || !payload.service_name || !payload.date) {
            errorBox.textContent = 'لطفاً تمامی فیلدهای نام، شماره تماس، نوع خدمت و تاریخ را تکمیل فرمایید.';
            errorBox.style.display = 'block';
            return;
        }

        if (!payload.time) {
            errorBox.textContent = '⚠️ لطفاً یکی از ساعت‌های آزاد را از بین گزینه‌ها انتخاب فرمایید.';
            errorBox.style.display = 'block';
            document.getElementById('slots-container').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            return;
        }

        // بررسی طول نام
        if (payload.name.length > 50) {
            errorBox.textContent = '⚠️ نام و نام خانوادگی نباید بیشتر از ۵۰ کاراکتر باشد.';
            errorBox.style.display = 'block';
            nameInput.focus();
            return;
        }

        if (payload.name.length < 2) {
            errorBox.textContent = '⚠️ نام و نام خانوادگی باید حداقل دارای ۲ کاراکتر باشد.';
            errorBox.style.display = 'block';
            nameInput.focus();
            return;
        }

        // بررسی فرمت شماره موبایل معتبر ایران (۱۱ رقم، شروع با 09)
        const irPhoneRegex = /^09\d{9}$/;
        if (!irPhoneRegex.test(payload.phone)) {
            errorBox.textContent = '⚠️ شماره موبایل نامعتبر است. شماره باید ۱۱ رقم بوده و با ۰۹ شروع شود (مثال: 09123456789).';
            errorBox.style.display = 'block';
            phoneInput.focus();
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
            let errorMsg = err.message || 'خطای ناشناخته رخ داده است.';
            if (err.name === 'TypeError' || errorMsg.includes('fetch') || errorMsg.includes('Failed') || errorMsg.includes('Network')) {
                errorMsg = 'خطا در اتصال به سرور بک‌اند. لطفاً اطمینان حاصل کنید که سرور (پورت ۵۰۰۰) در حال اجرا است.';
            }
            errorBox.textContent = `⚠️ ${errorMsg}`;
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
        const timeInput = document.getElementById('time-input');
        if (timeInput) timeInput.value = '';
        const previewBox = document.getElementById('selected-slot-preview');
        if (previewBox) previewBox.style.display = 'none';
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

