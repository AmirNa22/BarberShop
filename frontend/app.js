const API_BASE_URL = 'http://127.0.0.1:5000';

// تبدیل اعداد به فرمت سه‌رقم‌سه‌رقم فارسی
function formatPrice(price) {
    return Number(price).toLocaleString('fa-IR') + ' تومان';
}

// تبدیل اعداد به ارقام فارسی
function toPersianDigits(num) {
    return num.toString().replace(/\d/g, d => '۰۱۲۳۴۵۶۷۸۹'[d]);
}

// بررسی وضعیت ارتباط با سرور
async function checkServerStatus() {
    const statusBar = document.getElementById('status-bar');
    const statusText = document.getElementById('status-text');

    try {
        const response = await fetch(`${API_BASE_URL}/api/test`);
        if (!response.ok) throw new Error('خطا در پاسخ سرور');
        const data = await response.json();

        statusBar.className = 'status-bar success';
        statusText.textContent = data.message || 'ارتباط با سرور برقرار است';
        return true;
    } catch (err) {
        statusBar.className = 'status-bar error';
        statusText.textContent = 'خطا در اتصال به سرور بک‌اند (پورت ۵۰۰۰)';
        return false;
    }
}

// دریافت و نمایش خدمات
async function loadServices() {
    const loadingElem = document.getElementById('services-loading');
    const errorElem = document.getElementById('services-error');
    const gridElem = document.getElementById('services-grid');

    loadingElem.style.display = 'block';
    errorElem.style.display = 'none';
    gridElem.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE_URL}/api/services`);
        if (!response.ok) {
            throw new Error(`خطای دریافت خدمات: ${response.status}`);
        }

        const services = await response.json();

        // پاکسازی کارت‌های قبلی
        gridElem.innerHTML = '';

        services.forEach(service => {
            const card = document.createElement('div');
            card.className = 'service-card';
            card.innerHTML = `
                <div class="service-card-top">
                    <h3 class="service-name">${service.name}</h3>
                    <span class="service-duration">⏱ ${toPersianDigits(service.duration)} دقیقه</span>
                </div>
                <div class="service-card-bottom">
                    <div>
                        <span class="service-price-label">هزینه خدمت:</span>
                        <div class="service-price">${formatPrice(service.price)}</div>
                    </div>
                    <a href="booking.html?service=${encodeURIComponent(service.name)}" class="btn btn-sm btn-service-book">رزرو نوبت ←</a>
                </div>
            `;
            gridElem.appendChild(card);
        });

        loadingElem.style.display = 'none';
        gridElem.style.display = 'grid';
    } catch (err) {
        console.error('Error fetching services:', err);
        loadingElem.style.display = 'none';
        errorElem.style.display = 'block';
    }
}

// راه‌اندازی اولیه صفحه
document.addEventListener('DOMContentLoaded', () => {
    checkServerStatus();
    loadServices();

    const retryBtn = document.getElementById('retry-services-btn');
    if (retryBtn) {
        retryBtn.addEventListener('click', () => {
            checkServerStatus();
            loadServices();
        });
    }
});
