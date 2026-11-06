const API_BASE_URL = 'http://127.0.0.1:5000';

async function fetchStatus() {
    const statusBox = document.getElementById('status-box');
    const statusMessage = document.getElementById('status-message');
    const retryBtn = document.getElementById('retry-btn');
    const icon = statusBox.querySelector('.icon');

    // تنظیم حالت در حال بارگذاری
    statusBox.className = 'status-box loading';
    icon.textContent = '⏳';
    statusMessage.textContent = 'در حال ارتباط با بک‌اند...';
    retryBtn.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE_URL}/api/test`);
        
        if (!response.ok) {
            throw new Error(`خطای سرور: ${response.status}`);
        }

        const data = await response.json();
        
        // نمایش پیام دریافتی از سرور
        statusBox.className = 'status-box success';
        icon.textContent = '✅';
        statusMessage.textContent = data.message;
    } catch (error) {
        // مدیریت خطا در صورت در دسترس نبودن سرور
        statusBox.className = 'status-box error';
        icon.textContent = '❌';
        statusMessage.textContent = 'خطا در ارتباط با بک‌اند! آیا سرور روشن است؟';
        retryBtn.style.display = 'inline-block';
        console.error('Fetch error:', error);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    fetchStatus();

    const retryBtn = document.getElementById('retry-btn');
    if (retryBtn) {
        retryBtn.addEventListener('click', fetchStatus);
    }
});

