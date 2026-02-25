// ========== Digital Arena Web — Standalone App ==========
// Adapted from miniapp/app.js without Telegram dependency

const API_BASE_URL = "https://digital-arena-njok.onrender.com/api";

// ========== AUTH STATE ==========
let authToken = localStorage.getItem('da_token');
let currentUser = null;

// ========== APP STATE ==========
let computers = [];
let selectedComputer = null;
let currentZone = 'all';
let currentVenueType = 'computer_club';

let bookingState = {
    dayOffset: 0,
    selectedHour: null,
    durationMinutes: 60
};

let paginationState = {
    itemsPerPage: 20,
    currentPage: 1
};

// ========== INIT ==========
async function init() {
    updateLangUI();
    updateAuthUI();
    await loadClubData();
}

function updateAuthUI() {
    const authBtn = document.getElementById('auth-nav-btn');
    const bookingsBtn = document.getElementById('bookings-nav-btn');

    if (authToken && currentUser) {
        authBtn.textContent = currentUser.name || 'Профиль';
        authBtn.onclick = () => { doLogout(); };
        bookingsBtn.style.display = 'inline-flex';
    } else if (authToken) {
        validateToken();
    } else {
        authBtn.textContent = 'Войти';
        authBtn.onclick = () => { openLoginModal(); };
        bookingsBtn.style.display = 'none';
    }
}

async function validateToken() {
    try {
        const resp = await fetch(`${API_BASE_URL}/web/me`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (resp.ok) {
            currentUser = await resp.json();
            updateAuthUI();
        } else {
            localStorage.removeItem('da_token');
            authToken = null;
            updateAuthUI();
        }
    } catch (e) {
        console.warn('Token validation failed:', e);
    }
}

// ========== TOAST ==========
function showToast(message, type = 'normal') {
    let container = document.querySelector('.toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    let icon = 'ℹ️';
    if (type === 'success') icon = '✅';
    if (type === 'error') icon = '⚠️';

    toast.innerHTML = `
        <div class="toast-icon">${icon}</div>
        <div class="toast-message">${message.replace(/\n/g, '<br>')}</div>
    `;

    container.appendChild(toast);
    setTimeout(() => {
        toast.style.animation = 'toastOut 0.3s forwards';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ========== LOGIN ==========
function openLoginModal() {
    const modal = document.getElementById('login-modal');
    modal.style.display = 'flex';
    setTimeout(() => {
        modal.classList.add('active');
        document.getElementById('phone-input').focus();
    }, 10);
}

function closeLoginModal() {
    const modal = document.getElementById('login-modal');
    modal.classList.remove('active');
    setTimeout(() => { modal.style.display = 'none'; }, 300);
}

async function doLogin() {
    const phoneInput = document.getElementById('phone-input');
    const phone = phoneInput.value.replace(/\s/g, '').replace(/[^0-9]/g, '');

    if (phone.length < 9) {
        showToast('Введите корректный номер телефона', 'error');
        return;
    }

    const fullPhone = '998' + phone;
    const btn = document.getElementById('login-btn');
    btn.textContent = 'Проверяем...';
    btn.disabled = true;

    try {
        const resp = await fetch(`${API_BASE_URL}/web/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone: fullPhone })
        });

        const data = await resp.json();

        if (resp.ok && data.token) {
            authToken = data.token;
            currentUser = data.user;
            localStorage.setItem('da_token', authToken);
            closeLoginModal();
            updateAuthUI();
            showToast(`Добро пожаловать, ${currentUser.name}!`, 'success');
        } else {
            showToast(data.detail || 'Номер не найден. Зарегистрируйтесь через бота.', 'error');
        }
    } catch (e) {
        showToast('Ошибка сети. Попробуйте позже.', 'error');
    } finally {
        btn.textContent = 'ВОЙТИ';
        btn.disabled = false;
    }
}

function doLogout() {
    localStorage.removeItem('da_token');
    authToken = null;
    currentUser = null;
    updateAuthUI();
    showToast('Вы вышли из аккаунта', 'normal');
}

// ========== CLUB DATA ==========
const urlParams = new URLSearchParams(window.location.search);
let clubId = urlParams.get('club_id');

async function loadClubData() {
    try {
        if (clubId) {
            showComputerSkeletons();
            const clubHeader = document.getElementById('club-header');
            if (clubHeader) clubHeader.style.display = 'block';
        }

        const clubResponse = await fetch(`${API_BASE_URL}/clubs`);
        const clubs = await clubResponse.json();

        // Update stats
        updateStaticStats(clubs.length);

        if (!clubId) {
            renderClubSelection(clubs);
            return;
        }

        const club = clubs.find(c => c.id == clubId);
        if (club) {
            currentVenueType = club.venue_type || 'computer_club';
            const nameEl = document.getElementById('club-name');
            if (nameEl) nameEl.textContent = club.name;
            const addressEl = document.getElementById('club-address');
            if (addressEl) {
                addressEl.innerHTML = `
                    <div style="margin-bottom: 4px;">${club.city}, ${club.address}</div>
                    <div style="font-size: 12px; color: var(--text2); margin-bottom: 8px;">
                        📞 ${club.admin_phone || "Не указан"} | 🕒 ${club.working_hours || "24/7"}
                    </div>
                `;
                const changeBtn = document.getElementById('change-club-btn');
                if (changeBtn) {
                    changeBtn.style.display = 'inline';
                    addressEl.appendChild(changeBtn);
                }
            }
        }

        const computersResponse = await fetch(`${API_BASE_URL}/clubs/${clubId}/computers`);
        computers = await computersResponse.json();

        if (computers.length === 0) {
            showEmptyState();
            return;
        }

        buildZonesFilter();
        renderComputers();
    } catch (error) {
        console.error('Error loading data:', error);
        showToast(`Ошибка загрузки: ${error.message}`, 'error');
    }
}

function renderClubSelection(clubs) {
    const grid = document.getElementById('computer-grid');
    if (!grid) return;
    grid.innerHTML = '';
    grid.style.gridTemplateColumns = '1fr';
    const zones = document.getElementById('zones');
    if (zones) zones.style.display = 'none';
    const clubsHeading = document.getElementById('clubs-heading');
    if (clubsHeading) clubsHeading.style.display = 'block';

    if (clubs.length === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🏢</div>
                <h3>Нет доступных клубов</h3>
                <p>Клубы пока не добавлены</p>
            </div>`;
        return;
    }

    clubs.forEach(club => {
        const card = document.createElement('div');
        card.className = 'club-card-inline';
        card.style.cssText = 'background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:20px; margin-bottom:12px; cursor:pointer; display:flex; justify-content:space-between; align-items:center; transition:0.3s;';
        card.onmouseover = () => { card.style.borderColor = 'var(--primary)'; card.style.background = 'rgba(255,255,255,0.05)'; };
        card.onmouseout = () => { card.style.borderColor = 'var(--border)'; card.style.background = 'var(--surface)'; };

        card.onclick = () => {
            const newUrl = new URL(window.location.href);
            newUrl.searchParams.set('club_id', club.id);
            newUrl.hash = 'booking';
            window.location.href = newUrl.toString();
        };

        const typeIcon = club.venue_type === 'restaurant' ? '🍽️' : '🎮';
        card.innerHTML = `
            <div>
                <div style="font-weight:700; font-size:16px;">${typeIcon} ${club.name}</div>
                <div style="font-size:12px; color:var(--text2); margin-top:2px;">${club.city}, ${club.address}</div>
                <div style="font-size:11px; color:var(--primary); margin-top:4px;">
                    📞 ${club.admin_phone || "Не указан"} | 🕒 ${club.working_hours || "24/7"}
                </div>
            </div>
            <div style="color:var(--primary); font-weight:700;">ВЫБРАТЬ ➜</div>
        `;
        grid.appendChild(card);
    });
}

// ========== ZONES ==========
function buildZonesFilter() {
    const zonesSet = new Set(computers.map(c => c.zone));
    const zonesContainer = document.getElementById('zones');
    if (!zonesContainer) return;
    zonesContainer.style.display = 'flex';
    zonesContainer.innerHTML = `<button class="zone-btn active" onclick="filterZone('all', this)">Все</button>`;

    zonesSet.forEach(zone => {
        zonesContainer.innerHTML += `
            <button class="zone-btn" onclick="filterZone('${zone}', this)">${zone}</button>
        `;
    });
}

function filterZone(zone, btn) {
    currentZone = zone;
    document.querySelectorAll('.zone-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    paginationState.currentPage = 1;
    renderComputers();
}

// ========== RENDER COMPUTERS ==========
function renderComputers() {
    const grid = document.getElementById('computer-grid');
    if (!grid) return;
    grid.style.gridTemplateColumns = 'repeat(auto-fill, minmax(100px, 1fr))';

    const filtered = currentZone === 'all'
        ? computers
        : computers.filter(c => c.zone === currentZone);

    if (filtered.length === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🔍</div>
                <h3>Нет мест в зоне ${currentZone}</h3>
                <p>Попробуйте выбрать другую зону</p>
            </div>`;
        grid.style.gridTemplateColumns = '1fr';
        return;
    }

    const itemsToShow = paginationState.currentPage * paginationState.itemsPerPage;
    const paginatedItems = filtered.slice(0, itemsToShow);
    const hasMore = filtered.length > itemsToShow;

    grid.innerHTML = '';
    paginatedItems.forEach(computer => {
        const card = document.createElement('div');
        card.className = 'computer-card available';
        if (selectedComputer && selectedComputer.id === computer.id) card.classList.add('selected');

        card.style.cssText = 'background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:15px; text-align:center; cursor:pointer; transition:0.3s;';
        card.onmouseover = () => { if (!card.classList.contains('selected')) card.style.borderColor = 'rgba(0,212,255,0.3)'; };
        card.onmouseout = () => { if (!card.classList.contains('selected')) card.style.borderColor = 'var(--border)'; };

        card.onclick = () => selectComputer(computer, card);

        card.innerHTML = `
            <div style="font-weight:700; font-size:14px;">${computer.name}</div>
            <div style="font-size:10px; color:var(--success); margin-top:4px;">● Свободен</div>
        `;
        grid.appendChild(card);
    });

    if (hasMore) {
        const loadMoreBtn = document.createElement('button');
        loadMoreBtn.className = 'btn-outline';
        loadMoreBtn.style.gridColumn = '1 / -1';
        loadMoreBtn.style.marginTop = '20px';
        loadMoreBtn.textContent = `Загрузить еще (${filtered.length - itemsToShow})`;
        loadMoreBtn.onclick = () => {
            paginationState.currentPage++;
            renderComputers();
        };
        grid.appendChild(loadMoreBtn);
    }
}

function selectComputer(computer, card) {
    selectedComputer = computer;
    document.querySelectorAll('.computer-grid > div').forEach(c => {
        c.classList.remove('selected');
        c.style.borderColor = 'var(--border)';
        c.style.boxShadow = 'none';
    });
    card.classList.add('selected');
    card.style.borderColor = 'var(--primary)';
    card.style.boxShadow = '0 0 15px rgba(0, 212, 255, 0.2)';

    const infoPanel = document.getElementById('selected-info');
    infoPanel.style.display = 'block';
    document.getElementById('selected-name').textContent = computer.name;
    document.getElementById('selected-price').textContent = `${computer.price_per_hour.toLocaleString()} UZS/ч`;

    document.getElementById('book-btn-bottom').textContent = `ВЫБРАТЬ ${computer.name}`;
}

// ========== BOOKING MODAL ==========
function openBookingModal() {
    if (!authToken) { showToast('Войдите, чтобы продолжить', 'error'); openLoginModal(); return; }
    document.getElementById('booking-modal').style.display = 'flex';
    document.getElementById('modal-pc-name').textContent = selectedComputer.name;
    bookingState.selectedHour = null;
    renderTimeGrid();
    updatePrice();
}

function closeBookingModal() {
    const modal = document.getElementById('booking-modal');
    modal.classList.remove('active');
    setTimeout(() => { modal.style.display = 'none'; }, 300);
}

function selectDate(offset, btn) {
    bookingState.dayOffset = offset;
    document.querySelectorAll('.date-tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderTimeGrid();
}

async function renderTimeGrid() {
    const grid = document.getElementById('time-grid');
    grid.innerHTML = '<div class="skeleton" style="height:100px; grid-column:1/-1;"></div>';

    const now = new Date();
    const isToday = bookingState.dayOffset === 0;
    const currentHour = now.getHours();

    grid.innerHTML = '';
    for (let h = 10; h < 24; h++) {
        const slot = document.createElement('button');
        slot.className = 'time-slot';
        slot.style.cssText = 'background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:10px; color:var(--text); cursor:pointer;';
        slot.textContent = `${h}:00`;

        if (isToday && h <= currentHour) {
            slot.disabled = true;
            slot.style.opacity = '0.3';
            slot.style.cursor = 'not-allowed';
        } else {
            slot.onclick = () => {
                bookingState.selectedHour = h;
                document.querySelectorAll('.time-slot').forEach(s => { s.style.borderColor = 'var(--border)'; s.style.background = 'var(--surface)'; });
                slot.style.borderColor = 'var(--primary)';
                slot.style.background = 'rgba(0,212,255,0.1)';
                updatePrice();
            };
        }
        grid.appendChild(slot);
    }
}

function adjustDuration(delta) {
    bookingState.durationMinutes = Math.max(30, Math.min(600, bookingState.durationMinutes + delta));
    const h = Math.floor(bookingState.durationMinutes / 60);
    const m = bookingState.durationMinutes % 60;
    document.getElementById('duration-display').textContent = `${h} ч ${m} мин`;
    updatePrice();
}

function updatePrice() {
    const hours = bookingState.durationMinutes / 60;
    const price = selectedComputer.price_per_hour * hours;
    document.getElementById('total-price').textContent = `${Math.round(price).toLocaleString()} сум`;

    const btn = document.getElementById('confirm-booking-btn');
    btn.disabled = bookingState.selectedHour === null;
    btn.style.opacity = btn.disabled ? '0.5' : '1';
}

async function confirmBooking() {
    const btn = document.getElementById('confirm-booking-btn');
    btn.textContent = 'Бронируем...';
    btn.disabled = true;

    try {
        const date = new Date();
        date.setDate(date.getDate() + bookingState.dayOffset);
        date.setHours(bookingState.selectedHour, 0, 0, 0);

        const localizedIso = date.getFullYear() + '-' +
            String(date.getMonth() + 1).padStart(2, '0') + '-' +
            String(date.getDate()).padStart(2, '0') + 'T' +
            String(date.getHours()).padStart(2, '0') + ':00:00+05:00';

        const resp = await fetch(`${API_BASE_URL}/bookings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
            body: JSON.stringify({
                user_id: currentUser.tg_id,
                club_id: parseInt(clubId),
                computer_id: String(selectedComputer.id),
                start_time: localizedIso,
                duration_minutes: bookingState.durationMinutes
            })
        });

        const res = await resp.json();
        if (resp.ok && res.success) {
            showToast(`✅ Бронь #${res.booking_id} создана!`, 'success');
            closeBookingModal();
            location.reload();
        } else {
            showToast(res.detail || 'Ошибка', 'error');
        }
    } catch (e) { showToast('Ошибка сети', 'error'); }
    finally { btn.textContent = 'ЗАБРОНИРОВАТЬ'; btn.disabled = false; }
}

// ========== MY BOOKINGS ==========
async function openMyBookings() {
    document.getElementById('my-bookings-modal').style.display = 'flex';
    const list = document.getElementById('my-bookings-list');
    list.innerHTML = 'Загрузка...';
    try {
        const resp = await fetch(`${API_BASE_URL}/web/bookings`, { headers: { 'Authorization': `Bearer ${authToken}` } });
        const bookings = await resp.json();
        list.innerHTML = bookings.length ? '' : 'У вас нет активных броней.';
        bookings.forEach(b => {
            const item = document.createElement('div');
            item.style.padding = '15px'; item.style.borderBottom = '1px solid var(--border)';
            item.style.display = 'flex'; item.style.justifyContent = 'space-between'; item.style.alignItems = 'center';

            const infoDiv = document.createElement('div');
            infoDiv.innerHTML = `<strong>${b.club_name}</strong><br>${b.computer_name} | ${b.display_time}`;
            item.appendChild(infoDiv);

            if (b.status === 'CONFIRMED' || b.status === 'ACTIVE') {
                const cancelBtn = document.createElement('button');
                cancelBtn.textContent = 'Отменить';
                cancelBtn.style.padding = '4px 10px'; cancelBtn.style.background = 'var(--danger)'; cancelBtn.style.color = '#fff'; cancelBtn.style.border = 'none'; cancelBtn.style.borderRadius = '4px'; cancelBtn.style.cursor = 'pointer';
                cancelBtn.onclick = () => webCancelBooking(b.id, cancelBtn);
                item.appendChild(cancelBtn);
            }

            list.appendChild(item);
        });
    } catch (e) { list.innerHTML = 'Ошибка загрузки'; }
}

function closeMyBookings() {
    const modal = document.getElementById('my-bookings-modal');
    modal.classList.remove('active');
    setTimeout(() => { modal.style.display = 'none'; }, 300);
}

async function webCancelBooking(bookingId, btnElement) {
    if (!confirm('❗ Вы уверены, что хотите отменить эту бронь?')) return;

    const originalText = btnElement.textContent;
    btnElement.textContent = 'Отмена...';
    btnElement.disabled = true;

    try {
        const response = await fetch(`${API_BASE_URL}/web/bookings/${bookingId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (response.ok) {
            const result = await response.json();
            showToast(result.message || 'Бронь успешно отменена!', 'success');
            openMyBookings();
        } else {
            let errorMsg = 'Не удалось отменить бронь';
            try {
                const errorData = await response.json();
                errorMsg = errorData.detail || errorMsg;
            } catch { }
            showToast(errorMsg, 'error');
        }
    } catch (e) {
        showToast('❌ Ошибка сети.', 'error');
    } finally {
        btnElement.textContent = originalText;
        btnElement.disabled = false;
    }
}

// ========== UTILS & STATS ==========
function updateStaticStats(count) {
    const el = document.getElementById('hero-stat-clubs');
    if (el) el.textContent = count + '+';
}

function showComputerSkeletons() {
    const grid = document.getElementById('computer-grid');
    grid.innerHTML = '<div class="skeleton" style="height:200px; grid-column:1/-1;"></div>';
}

function showEmptyState() {
    document.getElementById('computer-grid').innerHTML = 'В этом клубе пока нет компьютеров.';
}

function goBackToClubs() {
    const url = new URL(window.location.href);
    url.searchParams.delete('club_id');
    window.location.href = url.toString();
}

// ========== LANGUAGE & LOCALIZATION ==========
const translations = {
    ru: {
        'nav-problem': 'Проблема',
        'nav-platform': 'Платформа',
        'nav-gov': 'Для государства',
        'nav-pilot': 'Пилот',
        'nav-about': 'О проекте',
        'nav-booking': 'Бронирование',
        'nav-dashboard': '📊 Дашборд →',
        'btn-login': 'Войти',
        'btn-my-bookings': '📅 Мои брони',
        'hero-badge': 'Цифровая трансформация киберспорта',
        'hero-title': 'Единая экосистема для <span class="gradient-text">развития индустрии</span> компьютерных клубов',
        'hero-sub': 'Мы создаем прозрачную инфраструктуру для легализации, фискального контроля и комфортного бронирования игровых мест по всему Узбекистану.',
        'hero-demo-tip': 'Нажмите на ПК для демонстрации',
        'section-booking-badge': 'Бронирование',
        'section-booking-title': 'Забронируй место <span class="gradient-text">в один клик</span>',
        'section-booking-desc': 'Выбирай клуб, зону и компьютер. Без звонков и подтверждений.',
        'clubs-heading': 'Выберите заведение',
        'toast-lang-changed': 'Язык изменен на русский',
        'login-title': 'Вход в систему',
        'login-hint': 'Введите номер телефона, указанный при регистрации у бота @ArenaSlot_bot',
        'login-btn': 'ВОЙТИ',
        'login-error-phone': 'Введите корректный номер телефона'
    },
    uz: {
        'nav-problem': 'Muammo',
        'nav-platform': 'Platforma',
        'nav-gov': 'Davlat uchun',
        'nav-pilot': 'Pilot',
        'nav-about': 'Loyiha haqida',
        'nav-booking': 'Bron qilish',
        'nav-dashboard': '📊 Dashboard →',
        'btn-login': 'Kirish',
        'btn-my-bookings': '📅 Mening bronlarim',
        'hero-badge': 'Kibersportning raqamli transformatsiyasi',
        'hero-title': 'Kompyuter klublari <span class="gradient-text">sanoatini rivojlantirish</span> uchun yagona ekotizim',
        'hero-sub': 'Biz Butun Oʻzbekiston boʻylab oʻyin joylarini legallashtirish, fiskal nazorat va qulay bron qilish uchun shaffof infratuzilmani yaratmoqdamiz.',
        'hero-demo-tip': 'Namoyish uchun kompyuterni bosing',
        'section-booking-badge': 'Bron qilish',
        'section-booking-title': 'Joyni <span class="gradient-text">bir marta bosish</span> orqali bron qiling',
        'section-booking-desc': 'Klub, zona va kompyuterni tanlang. Qo\'ng\'iroqlarsiz va tasdiqlasiz.',
        'clubs-heading': 'Muassasani tanlang',
        'toast-lang-changed': 'Til oʻzbekchaga oʻzgartirildi',
        'login-title': 'Tizimga kirish',
        'login-hint': '@ArenaSlot_bot botida roʻyxatdan oʻtishda koʻrsatilgan telefon raqamini kiriting',
        'login-btn': 'KIRISH',
        'login-error-phone': 'Toʻgʻri telefon raqamini kiriting'
    }
};

let currentLang = localStorage.getItem('da_lang') || 'ru';

function toggleLang() {
    currentLang = currentLang === 'ru' ? 'uz' : 'ru';
    localStorage.setItem('da_lang', currentLang);
    updateLangUI();
    showToast(translations[currentLang]['toast-lang-changed'], 'normal');
}

function updateLangUI() {
    const t = translations[currentLang];
    const btn = document.getElementById('lang-btn');
    if (btn) btn.textContent = currentLang === 'ru' ? '🌐 RU' : '🌐 UZ';

    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (t[key]) {
            if (el.tagName === 'INPUT' && el.placeholder) {
                el.placeholder = t[key];
            } else {
                el.innerHTML = t[key];
            }
        }
    });
}

// ========== INIT LOAD ==========
document.addEventListener('DOMContentLoaded', () => {
    init();

    // Ported Scroll Animations from original website/app.js
    const statNumbers = document.querySelectorAll('.stat-number');
    const animateNumber = (el) => {
        const target = parseInt(el.dataset.target);
        if (isNaN(target)) return;
        const duration = 1500;
        const start = performance.now();
        const update = (now) => {
            const elapsed = now - start;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            el.textContent = Math.round(target * eased);
            if (progress < 1) requestAnimationFrame(update);
            else if (target >= 5 && target < 100) el.textContent = target + '+';
        };
        requestAnimationFrame(update);
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                if (entry.target.classList.contains('stat-number')) animateNumber(entry.target);
            }
        });
    }, { threshold: 0.1 });

    statNumbers.forEach(el => observer.observe(el));
    document.querySelectorAll('.reveal, .feature-card, .step, .card, .benefit, .stat, .phase').forEach(el => observer.observe(el));
});
