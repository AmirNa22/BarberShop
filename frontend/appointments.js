// آدرس پایه سرور بک‌اند
const API_BASE_URL = 'http://127.0.0.1:5000';

// المان‌های DOM
const datePicker = document.getElementById('date-picker');
const todayBtn = document.getElementById('today-btn');
const loadingState = document.getElementById('loading-state');
const errorState = document.getElementById('error-state');
const errorMessage = document.getElementById('error-message');
const emptyState = document.getElementById('empty-state');
const tableContainer = document.getElementById('table-container');
const appointmentsTbody = document.getElementById('appointments-tbody');
const alertBox = document.getElementById('alert-box');
const retryBtn = document.getElementById('retry-btn');

const totalCountEl = document.getElementById('total-count');
const activeCountEl = document.getElementById('active-count');
const cancelledCountEl = document.getElementById('cancelled-count');

/**
 * دریافت تاریخ امروز به فرمت YYYY-MM-DD با در نظر گرفتن منطقه زمانی محلی
 */
function getTodayDateString() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

/**
 * تبدیل اعداد انگلیسی به فارسی برای نمایش زیبا
 */
function toPersianDigits(str) {
    if (str === null || str === undefined) return '';
    return str.toString().replace(/\d/g, d => '۰۱۲۳۴۵۶۷۸۹'[d]);
}

/**
 * جلوگیری از تزریق کدهای مخرب (XSS Safe Escape)
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

/**
 * نمایش پیام موقت اعلان (موفقیت یا خطا)
 */
function showAlert(message, type = 'success') {
    alertBox.textContent = message;
    alertBox.className = `alert-box alert-${type}`;
    alertBox.style.display = 'block';

    // مخفی‌سازی خودکار پس از ۵ ثانیه
    setTimeout(() => {
        alertBox.style.display = 'none';
    }, 5000);
}

/**
 * دریافت نوبت‌های یک تاریخ مشخص از سرور و نمایش در جدول
 */
async function fetchAppointments(date) {
    if (!date) return;

    // پنهان‌سازی بخش‌ها و نمایش لودینگ
    loadingState.style.display = 'block';
    errorState.style.display = 'none';
    emptyState.style.display = 'none';
    tableContainer.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE_URL}/api/appointments?date=${encodeURIComponent(date)}`);
        
        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.message || `خطای سرور (${response.status})`);
        }

        const appointments = await response.json();
        renderAppointments(appointments);

    } catch (err) {
        console.error('Error fetching appointments:', err);
        loadingState.style.display = 'none';
        errorState.style.display = 'block';
        errorMessage.textContent = `⚠️ ${err.message || 'خطا در ارتباط با سرور'}`;
    }
}

/**
 * رندر کردن ردیف‌های جدول و به‌روزرسانی آمار
 */
function renderAppointments(appointments) {
    loadingState.style.display = 'none';
    appointmentsTbody.innerHTML = '';

    // آمار نوبت‌ها
    let activeCount = 0;
    let cancelledCount = 0;

    appointments.forEach(app => {
        if (app.status === 'active') activeCount++;
        else if (app.status === 'cancelled') cancelledCount++;
    });

    totalCountEl.textContent = toPersianDigits(appointments.length);
    activeCountEl.textContent = toPersianDigits(activeCount);
    cancelledCountEl.textContent = toPersianDigits(cancelledCount);

    if (appointments.length === 0) {
        emptyState.style.display = 'block';
        tableContainer.style.display = 'none';
        return;
    }

    appointments.forEach(app => {
        const tr = document.createElement('tr');
        const isActive = app.status === 'active';

        const statusBadge = isActive
            ? '<span class="badge-status badge-active">فعال</span>'
            : '<span class="badge-status badge-cancelled">لغو شده</span>';

        // دکمه لغو نوبت فقط برای نوبت‌های فعال
        let actionCell = '<span style="color: var(--text-muted); font-size: 0.85rem;">-</span>';
        if (isActive) {
            actionCell = `
                <button class="btn-cancel" data-id="${app.id}" data-time="${escapeHtml(app.time)}" data-name="${escapeHtml(app.name)}">
                    ✕ لغو نوبت
                </button>
            `;
        }

        tr.innerHTML = `
            <td><span class="time-cell">${escapeHtml(app.time)}</span></td>
            <td class="customer-name-cell"><strong>${escapeHtml(app.name)}</strong></td>
            <td><span dir="ltr">${escapeHtml(app.phone)}</span></td>
            <td>${escapeHtml(app.service_name)}</td>
            <td>${statusBadge}</td>
            <td>${actionCell}</td>
        `;

        appointmentsTbody.appendChild(tr);
    });

    tableContainer.style.display = 'block';

    // اتصال رویداد به دکمه‌های لغو
    attachCancelListeners();
}

/**
 * اتصال رویداد به کلیه دکمه‌های لغو جدول
 */
function attachCancelListeners() {
    const cancelButtons = appointmentsTbody.querySelectorAll('.btn-cancel');
    cancelButtons.forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const btnEl = e.currentTarget;
            const id = btnEl.getAttribute('data-id');
            const time = btnEl.getAttribute('data-time');
            const name = btnEl.getAttribute('data-name');

            // دریافت تاییدیه (Confirm) از کاربر قبل از لغو نوبت
            const confirmMessage = `آیا از لغو نوبت ساعت ${time} برای مشتری «${name}» اطمینان دارید؟\nاین بازه زمانی مجدداً برای رزرو مشتریان آزاد خواهد شد.`;
            if (!window.confirm(confirmMessage)) {
                return;
            }

            await handleCancelAppointment(id, btnEl);
        });
    });
}

/**
 * ارسال درخواست لغو نوبت به سرور
 */
async function handleCancelAppointment(id, btnEl) {
    try {
        btnEl.disabled = true;
        btnEl.textContent = 'در حال لغو...';

        const response = await fetch(`${API_BASE_URL}/api/appointments/${id}/cancel`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message || 'خطا در لغو نوبت');
        }

        showAlert('✅ نوبت با موفقیت لغو شد و بازه زمانی آزاد گردید.', 'success');

        // به‌روزرسانی لیست نوبت‌های همین روز
        await fetchAppointments(datePicker.value);

    } catch (err) {
        console.error('Error cancelling appointment:', err);
        showAlert(`⚠️ ${err.message || 'خطا در انجام عملیات لغو'}`, 'error');
        btnEl.disabled = false;
        btnEl.textContent = '✕ لغو نوبت';
    }
}

// مقداردهی اولیه صفحه پس از بارگذاری کامل DOM
document.addEventListener('DOMContentLoaded', () => {
    // تنظیم پیش‌فرض تاریخ روی امروز
    const today = getTodayDateString();
    datePicker.value = today;

    // بارگذاری نوبت‌های امروز
    fetchAppointments(today);

    // تغییر تاریخ توسط کاربر
    datePicker.addEventListener('change', () => {
        if (datePicker.value) {
            fetchAppointments(datePicker.value);
        }
    });

    // دکمه بازگشت به تاریخ امروز
    todayBtn.addEventListener('click', () => {
        const todayStr = getTodayDateString();
        datePicker.value = todayStr;
        fetchAppointments(todayStr);
    });

    // دکمه تلاش مجدد در صورت خطای اتصال
    retryBtn.addEventListener('click', () => {
        fetchAppointments(datePicker.value || getTodayDateString());
    });
});

