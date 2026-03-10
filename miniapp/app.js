// Telegram Web App initialization
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

// Debug Auth - REMOVED
// setTimeout(() => { ... }, 1000);

// ==================== AUTH LAYER ====================
let _sessionAuthData = null; // Holds { user_id, full_name, phone } from session token

// Helper to get auth headers for API calls
function getAuthHeaders() {
    if (tg.initData) {
        return { 'X-Telegram-Init-Data': tg.initData };
    }
    const token = localStorage.getItem('session_token');
    if (token) {
        return { 'X-Session-Token': token };
    }
    return {};
}

// Submit phone + code form from the auth screen
async function submitPhoneCode() {
    const phone = document.getElementById('auth-phone').value.trim();
    const code = document.getElementById('auth-code').value.trim();
    const errEl = document.getElementById('auth-error');
    const btn = document.getElementById('auth-submit-btn');

    errEl.style.display = 'none';

    if (!phone || !code || code.length < 6) {
        errEl.textContent = 'Введите номер телефона и код (6 цифр)';
        errEl.style.display = 'block';
        return;
    }

    btn.disabled = true;
    btn.textContent = '⏳ Проверяем...';

    try {
        let res;
        try {
            res = await fetch(`${API_BASE_URL}/auth/verify-code`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phone, code })
            });
        } catch (networkErr) {
            throw new Error('Нет соединения с сервером. Проверьте интернет и попробуйте снова.');
        }

        // Safely parse response — server might return HTML on error/sleep
        const rawText = await res.text();
        let data;
        try {
            data = JSON.parse(rawText);
        } catch {
            if (res.status === 503 || rawText.includes('<!doctype')) {
                throw new Error('Сервер просыпается (Render free tier). Подождите 30 секунд и попробуйте снова.');
            }
            throw new Error(`Ошибка сервера (${res.status}). Попробуйте ещё раз.`);
        }

        if (!res.ok) {
            throw new Error(data.detail || 'Неверный код');
        }

        // Save session
        localStorage.setItem('session_token', data.session_token);
        localStorage.setItem('session_user', JSON.stringify({
            id: data.user_id,
            first_name: data.full_name || 'User',
            phone: data.phone
        }));

        // Trigger success feedback if available
        if (typeof haptic === 'function') haptic('success');

        if (!data.has_password) {
            // New user or no password set up -> Complete profile
            switchAuthTab('complete');
            btn.disabled = false;
            btn.textContent = '🔐 Войти';
        } else {
            // Already has password, reload the page to transition out
            window.location.reload();
        }

    } catch (e) {
        errEl.textContent = e.message;
        errEl.style.display = 'block';
        btn.disabled = false;
        btn.textContent = '🔐 Войти';
    }
}

// Switch between OTP / Password / Complete / Register tabs on auth screen
function switchAuthTab(tab) {
    ['otp', 'login', 'register', 'complete'].forEach(t => {
        const panel = document.getElementById(`auth-panel-${t}`);
        const tabBtn = document.getElementById(`tab-${t}`);
        if (panel) panel.style.display = (t === tab) ? 'flex' : 'none';
        if (tabBtn) tabBtn.classList.toggle('active', t === tab);
    });
    const errEl = document.getElementById('auth-error');
    if (errEl) errEl.style.display = 'none';
}

// Login with phone + password
async function submitPasswordLogin() {
    const phone = document.getElementById('login-phone').value.trim();
    const password = document.getElementById('login-password').value.trim();
    const errEl = document.getElementById('auth-error');
    errEl.style.display = 'none';

    if (!phone || !password) {
        errEl.textContent = 'Введите номер телефона и пароль';
        errEl.style.display = 'block';
        return;
    }

    try {
        const res = await fetch(`${API_BASE_URL}/auth/login-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone, password })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Ошибка входа');

        localStorage.setItem('session_token', data.session_token);
        localStorage.setItem('session_user', JSON.stringify({
            id: data.user_id,
            first_name: data.full_name || 'User',
            phone: data.phone
        }));
        haptic('success');
        window.location.reload();
    } catch (e) {
        errEl.textContent = e.message;
        errEl.style.display = 'block';
    }
}

// Register a new account
async function submitRegister() {
    const name = document.getElementById('reg-name').value.trim();
    const phone = document.getElementById('reg-phone').value.trim();
    const password = document.getElementById('reg-password').value.trim();
    const password2 = document.getElementById('reg-password2').value.trim();
    const errEl = document.getElementById('auth-error');
    errEl.style.display = 'none';

    if (!name || !phone || !password) {
        errEl.textContent = 'Заполните все поля';
        errEl.style.display = 'block';
        return;
    }
    if (password.length < 6) {
        errEl.textContent = 'Пароль должен быть минимум 6 символов';
        errEl.style.display = 'block';
        return;
    }
    if (password !== password2) {
        errEl.textContent = 'Пароли не совпадают';
        errEl.style.display = 'block';
        return;
    }

    try {
        const res = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ full_name: name, phone, password })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Ошибка регистрации');

        localStorage.setItem('session_token', data.session_token);
        localStorage.setItem('session_user', JSON.stringify({
            id: data.user_id,
            first_name: data.full_name || name,
            phone: data.phone
        }));
        haptic('success');
        window.location.reload();
    } catch (e) {
        errEl.textContent = e.message;
        errEl.style.display = 'block';
    }
}

// Complete profile after OTP (name + password)
async function submitCompleteProfile() {
    const name = document.getElementById('complete-name').value.trim();
    const password = document.getElementById('complete-password').value.trim();
    const passwordConfirm = document.getElementById('complete-password-confirm').value.trim();
    const btn = document.getElementById('auth-complete-btn');
    const errEl = document.getElementById('auth-error');

    errEl.style.display = 'none';

    if (!name || !password) {
        errEl.textContent = 'Заполните все поля';
        errEl.style.display = 'block';
        return;
    }

    if (password.length < 6) {
        errEl.textContent = 'Пароль должен быть длиннее 6 символов';
        errEl.style.display = 'block';
        return;
    }

    if (password !== passwordConfirm) {
        errEl.textContent = 'Пароли не совпадают';
        errEl.style.display = 'block';
        return;
    }

    const token = localStorage.getItem('session_token');
    if (!token) {
        errEl.textContent = 'Нет сессии. Начните заново.';
        errEl.style.display = 'block';
        return;
    }

    btn.disabled = true;
    btn.textContent = '⏳ Секунду...';

    try {
        const res = await fetch(`${API_BASE_URL}/auth/complete_profile`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-session-token': token
            },
            body: JSON.stringify({ full_name: name, password: password })
        });
        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.detail || 'Не удалось завершить профиль');
        }

        // Update local storage user data info with the new name
        let userData = JSON.parse(localStorage.getItem('session_user') || '{}');
        userData.first_name = data.full_name || name;
        localStorage.setItem('session_user', JSON.stringify(userData));

        haptic('success');
        window.location.reload();
    } catch (e) {
        errEl.textContent = e.message;
        errEl.style.display = 'block';
        btn.disabled = false;
        btn.textContent = '🏁 Завершить';
    }
}

// ==================== PWA INSTALLATION ====================
let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
    // Prevent the mini-infobar from appearing on mobile
    e.preventDefault();
    // Stash the event so it can be triggered later.
    deferredPrompt = e;
    // Update UI notify the user they can install the PWA
    const installBtn = document.getElementById('pwa-install-banner');
    if (installBtn) {
        installBtn.style.display = 'block';
    }
});

async function installPWA() {
    if (deferredPrompt) {
        // Show the install prompt
        deferredPrompt.prompt();
        // Wait for the user to respond to the prompt
        const { outcome } = await deferredPrompt.userChoice;
        console.log(`User response to the install prompt: ${outcome}`);
        // We've used the prompt, and can't use it again, throw it away
        deferredPrompt = null;
        // Hide the install button
        const installBtn = document.getElementById('pwa-install-banner');
        if (installBtn) installBtn.style.display = 'none';
    } else {
        // Fallback for iOS Safari which doesn't support beforeinstallprompt
        alert("Для установки на iOS:\nНажмите кнопку 'Поделиться' внизу экрана (квадрат со стрелочкой) и выберите 'На экран «Домой»'.");
    }
}

window.addEventListener('appinstalled', () => {
    // Hide the app-provided install promotion
    console.log('PWA was installed');
    const installBtn = document.getElementById('pwa-install-banner');
    if (installBtn) installBtn.style.display = 'none';
});


// Check auth state and show form if not authenticated
async function checkAuthAndInit() {
    // 1. Inside Telegram Mini App
    if (tg.initData) {
        return true;
    }

    // 2. Standalone PWA with existing session
    const token = localStorage.getItem('session_token');
    const userData = localStorage.getItem('session_user');
    if (token && userData) {
        try {
            _sessionAuthData = JSON.parse(userData);
            return true;
        } catch (e) {
            localStorage.removeItem('session_token');
            localStorage.removeItem('session_user');
        }
    }

    // 3. Not authenticated — show form
    document.getElementById('auth-screen').style.display = 'flex';
    document.getElementById('loading-overlay').style.display = 'none';
    return false;
}


// ==================== DARK THEME ====================
// Авто-определение темы из Telegram
// FORCE DARK THEME for consistent branding
const theme = 'dark';
document.documentElement.setAttribute('data-theme', theme);

// Override Telegram colors with our Cyberpunk Palette
const root = document.documentElement;
root.style.setProperty('--tg-bg-color', '#1a1a2e');
root.style.setProperty('--tg-text-color', '#ffffff');
root.style.setProperty('--tg-hint-color', '#7a7a7a');
root.style.setProperty('--tg-link-color', '#00f2ff');
root.style.setProperty('--tg-button-color', '#00f2ff');
root.style.setProperty('--tg-button-text', '#000000');

// ==================== UTILITIES ====================

// Debounce — предотвращает спам запросами при поиске
function debounce(func, delay = 300) {
    let timeoutId;
    return function (...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
}

// Haptic Feedback — вибрация при действиях
function haptic(type = 'light') {
    try {
        if (tg.HapticFeedback) {
            if (type === 'success') {
                tg.HapticFeedback.notificationOccurred('success');
            } else if (type === 'error') {
                tg.HapticFeedback.notificationOccurred('error');
            } else if (type === 'warning') {
                tg.HapticFeedback.notificationOccurred('warning');
            } else {
                tg.HapticFeedback.impactOccurred(type); // 'light', 'medium', 'heavy'
            }
        }
    } catch (e) {
        // Haptic not supported
    }
}

// Get club_id from URL parameter
const urlParams = new URLSearchParams(window.location.search);
const clubId = urlParams.get('club_id');

let computers = [];
let selectedComputer = null;
let currentZone = 'all';

// Booking State
let bookingState = {
    dayOffset: 0, // 0 = Today, 1 = Tomorrow
    selectedHour: null,
    durationMinutes: 60
};

// Pagination state
let paginationState = {
    itemsPerPage: 20,
    currentPage: 1
};

// Track if scroll listeners are already attached
let scrollListenersAttached = false;

// Global Venue Type
let currentVenueType = 'computer_club';

// --- Toast Notifications ---
function showToast(message, type = 'normal') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

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

    // Safe haptic feedback
    try {
        if (tg && tg.HapticFeedback) {
            tg.HapticFeedback.notificationOccurred(type === 'error' ? 'error' : 'success');
        }
    } catch (e) {
        // Haptic not supported or disabled
    }

    // Auto remove
    setTimeout(() => {
        toast.style.animation = 'toastOut 0.3s forwards';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// API Configuration — use Render directly (CORS is configured for Firebase origins)
const IS_LOCAL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
const API_BASE_URL = IS_LOCAL
    ? `http://${window.location.host}/api`
    : 'https://digital-arena-njok.onrender.com/api';

// Load club data
async function loadClubData() {
    try {
        // Show Skeletons initially
        if (!clubId) {
            showClubSkeletons();
        } else {
            showComputerSkeletons();
        }

        // Load club info
        const clubResponse = await fetch(`${API_BASE_URL}/clubs?page=1&limit=100`, {
            headers: {
                'ngrok-skip-browser-warning': 'true',
                'X-Telegram-Init-Data': tg.initData
            }
        });
        const clubsData = await clubResponse.json();

        // Bulletproof array extraction (handles both new paginated {clubs: []} and old raw list [...])
        let clubs = [];
        if (Array.isArray(clubsData)) {
            clubs = clubsData;
        } else if (clubsData && Array.isArray(clubsData.clubs)) {
            clubs = clubsData.clubs;
        }

        // Check if clubId is present
        if (!clubId) {
            tg.BackButton.hide(); // Hide back button on list view
            renderClubSelection(clubs);
            return;
        }

        // Use filter instead of find to prevent "is not a function" on older Android WebViews
        const club = clubs.filter(c => c.id == clubId)[0];

        if (club) {
            currentVenueType = club.venue_type || 'computer_club'; // Set global type

            document.getElementById('club-name').textContent = club.name;
            // Add "Change" button next to address
            const addressEl = document.getElementById('club-address');
            if (addressEl) {
                addressEl.innerHTML = `
                ${club.city}, ${club.address} 
                <span class="change-club-link" onclick="goBackToClubs()">(Сменить)</span>
            `;
            }

            // Adjust title for Restaurants
            if (currentVenueType === 'restaurant') {
                document.title = "Restaurant Booking";
            }

            // Setup Telegram Back Button
            setupBackButton();
        }

        // Load items (computers or tables)
        const computersResponse = await fetch(`${API_BASE_URL}/clubs/${clubId}/computers?page=1&limit=100`, {
            headers: {
                'ngrok-skip-browser-warning': 'true',
                'X-Telegram-Init-Data': tg.initData
            }
        });
        const computerData = await computersResponse.json();
        computers = computerData.items || []; // Extract items from paginated response

        if (computers.length === 0) {
            showEmptyState();
            return;
        }

        // Build zones filter
        buildZonesFilter();

        // Render items
        renderComputers();
    } catch (error) {
        console.error('Error loading data:', error);
        showToast(`Ошибка: ${error.message}`, 'error');
    }
}

// --- restored: renderClubSelection ---
let _clubsMap = null; // Yandex Map instance

function renderClubSelection(clubs) {
    const grid = document.getElementById('computer-grid');
    grid.innerHTML = '';
    grid.style.gridTemplateColumns = '1fr'; // List view
    document.getElementById('zones').style.display = 'none'; // Hide filters
    document.getElementById('club-name').textContent = t('select_club');
    document.getElementById('club-address').textContent = t('available_clubs');

    // Show map if any club has coordinates
    const clubsWithCoords = clubs.filter(c => c.latitude && c.longitude);
    const mapContainer = document.getElementById('clubs-map-container');

    if (clubsWithCoords.length > 0 && typeof ymaps !== 'undefined') {
        mapContainer.style.display = 'block';
        ymaps.ready(() => {
            // Destroy previous map if exists
            if (_clubsMap) {
                _clubsMap.destroy();
                _clubsMap = null;
            }

            // Center on first club or Tashkent
            const centerLat = clubsWithCoords[0].latitude;
            const centerLng = clubsWithCoords[0].longitude;

            _clubsMap = new ymaps.Map('clubs-map', {
                center: [centerLat, centerLng],
                zoom: 12,
                controls: ['zoomControl']
            });

            // Add pin for each club
            clubsWithCoords.forEach(club => {
                const placemark = new ymaps.Placemark(
                    [club.latitude, club.longitude],
                    {
                        balloonContentHeader: `<strong>${club.name}</strong>`,
                        balloonContentBody: `${club.city}, ${club.address}<br>` +
                            (club.free_seats !== undefined ? `🟢 ${club.free_seats} ${t('free')}` : ''),
                        hintContent: club.name
                    },
                    {
                        preset: club.venue_type === 'restaurant'
                            ? 'islands#orangeFoodIcon'
                            : 'islands#blueGameIcon',
                        iconColor: '#7c3aed'
                    }
                );

                // Click pin → go to club
                placemark.events.add('click', () => {
                    const newUrl = new URL(window.location.href);
                    newUrl.searchParams.set('club_id', club.id);
                    window.location.href = newUrl.toString();
                });

                _clubsMap.geoObjects.add(placemark);
            });

            // Fit all markers if > 1
            if (clubsWithCoords.length > 1) {
                _clubsMap.setBounds(_clubsMap.geoObjects.getBounds(), {
                    checkZoomRange: true, zoomMargin: 40
                });
            }
        });
    } else {
        mapContainer.style.display = 'none';
    }

    clubs.forEach(club => {
        const card = document.createElement('div');
        card.className = 'club-card';
        card.onclick = () => {
            const newUrl = new URL(window.location.href);
            newUrl.searchParams.set('club_id', club.id);
            window.location.href = newUrl.toString();
        };

        const typeIcon = club.venue_type === 'restaurant' ? '🍽️' : '🎮';

        // Safe fallbacks for missing data
        const safeCity = club.city || 'Город не указан';
        const safeAddress = club.address || 'Адрес не указан';
        const safeTotalSeats = club.total_seats || 0;
        const safeFreeSeats = club.free_seats || 0;

        // Live seats badge
        const seatsBadge = safeTotalSeats > 0
            ? `<span class="seats-badge ${safeFreeSeats > 0 ? 'seats-free' : 'seats-full'}">
                 ${safeFreeSeats > 0 ? '🟢' : '🔴'} ${safeFreeSeats}/${safeTotalSeats} мест
               </span>`
            : '';

        // Rating badge
        const ratingBadge = club.avg_rating
            ? `<span class="rating-badge">⭐ ${club.avg_rating} (${club.review_count || 0})</span>`
            : '';

        // Map pin indicator
        const mapPin = (club.latitude && club.longitude) ? '📍 ' : '';

        card.innerHTML = `
            <div>
                <div class="club-title">${typeIcon} ${club.name}</div>
                <div class="club-location">${mapPin}${safeCity}, ${safeAddress}</div>
                <div class="club-meta">${seatsBadge} ${ratingBadge}</div>
            </div>
            <div class="club-action">➜</div>
        `;
        grid.appendChild(card);
    });
}

// --- restored: buildZonesFilter ---
function buildZonesFilter() {
    const zonesSet = new Set(computers.map(c => c.zone));
    const zonesContainer = document.getElementById('zones');
    zonesContainer.style.display = 'flex';
    zonesContainer.innerHTML = `<button class="zone-btn active" onclick="filterZone('all', this)">All</button>`;

    zonesSet.forEach(zone => {
        zonesContainer.innerHTML += `
            <button class="zone-btn" onclick="filterZone('${zone}', this)">${zone}</button>
        `;
    });
}

function filterZone(zone, btn) {
    currentZone = zone;

    // Update UI
    document.querySelectorAll('.zone-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    // Reset pagination
    paginationState.currentPage = 1;

    // Rerender
    renderComputers();
    tg.HapticFeedback.selectionChanged();
}

function showEmptyState() {
    const grid = document.getElementById('computer-grid');
    const itemLabel = currentVenueType === 'restaurant' ? 'столиков' : 'компьютеров';
    grid.innerHTML = `
        <div class="empty-state">
            <div class="empty-state-icon">${currentVenueType === 'restaurant' ? '🍽️' : '🖥️'}</div>
            <h3>Нет свободных ${itemLabel}</h3>
            <p>В этом заведении пока нет активных объектов.</p>
            <button onclick="window.location.search=''" class="zone-btn" style="margin-top:10px">Выбрать другое место</button>
        </div>
    `;
    grid.style.gridTemplateColumns = '1fr';
    document.getElementById('zones').style.display = 'none';
}

function showClubSkeletons() {
    const grid = document.getElementById('computer-grid');
    grid.innerHTML = '';
    grid.style.gridTemplateColumns = '1fr';
    for (let i = 0; i < 3; i++) {
        const skel = document.createElement('div');
        skel.className = 'club-card skeleton';
        skel.style.height = '80px';
        grid.appendChild(skel);
    }
}

function showComputerSkeletons() {
    const grid = document.getElementById('computer-grid');
    grid.innerHTML = '';
    // Determine grid columns based on screen width (CSS handles it, but we reset style here)
    grid.style.gridTemplateColumns = '';

    for (let i = 0; i < 12; i++) {
        const card = document.createElement('div');
        card.className = 'computer-card skeleton';
        grid.appendChild(card);
    }
}

// Optimized rendering with pagination
function renderComputers() {
    const grid = document.getElementById('computer-grid');
    grid.style.gridTemplateColumns = '';

    const filtered = currentZone === 'all'
        ? computers
        : computers.filter(c => c.zone === currentZone);

    if (filtered.length === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🔍</div>
                <h3>Нет мест в зоне ${currentZone}</h3>
                <p>Попробуйте выбрать другую зону</p>
            </div>
        `;
        grid.style.gridTemplateColumns = '1fr';
        return;
    }

    const itemsToShow = paginationState.currentPage * paginationState.itemsPerPage;
    const paginatedItems = filtered.slice(0, itemsToShow);
    const hasMore = filtered.length > itemsToShow;

    // Virtual DOM-like approach
    const existingCards = Array.from(grid.querySelectorAll('.computer-card'));

    // Remove old
    existingCards.forEach(card => {
        const cardId = card.dataset.computerId;
        if (!paginatedItems.find(c => String(c.id) === cardId)) {
            card.remove();
        }
    });

    // Add or update
    paginatedItems.forEach((computer, index) => {
        const computerId = String(computer.id);
        let card = grid.querySelector(`[data-computer-id="${computerId}"]`);

        if (!card) {
            card = document.createElement('div');
            card.className = 'computer-card available';
            card.dataset.computerId = computerId;
            card.onclick = () => selectComputer(computer);
            grid.insertBefore(card, grid.querySelector('.load-more-btn'));
        }

        const isSelected = selectedComputer && selectedComputer.id === computer.id;
        card.classList.toggle('selected', isSelected);

        let statusText = "Свободен";
        card.innerHTML = `
            <div class="computer-name">${computer.name}</div>
            <div class="computer-status">${statusText}</div>
        `;
    });

    // Load More Button
    let loadMoreBtn = grid.querySelector('.load-more-btn');
    if (hasMore) {
        if (!loadMoreBtn) {
            loadMoreBtn = document.createElement('button');
            loadMoreBtn.className = 'load-more-btn';
            loadMoreBtn.onclick = () => {
                paginationState.currentPage++;
                renderComputers();
            };
            grid.appendChild(loadMoreBtn);
        }
        loadMoreBtn.textContent = `Загрузить еще (${filtered.length - itemsToShow} осталось)`;
        loadMoreBtn.style.display = 'block';
    } else if (loadMoreBtn) {
        loadMoreBtn.style.display = 'none';
    }
}

function selectComputer(computer) {
    selectedComputer = computer;

    // Highlights
    document.querySelectorAll('.computer-card').forEach(card => {
        if (card.dataset.computerId === String(computer.id)) {
            card.classList.add('selected');
        } else {
            card.classList.remove('selected');
        }
    });

    // Show info panel
    const infoPanel = document.getElementById('selected-info');
    infoPanel.style.display = 'block';
    setTimeout(() => { infoPanel.style.transform = 'translateY(0)'; }, 10);

    document.getElementById('selected-name').textContent = computer.name;
    document.getElementById('selected-price').textContent = currentVenueType === 'restaurant'
        ? 'Бронь стола'
        : `${computer.price_per_hour.toLocaleString()} UZS/ч`;

    const imgEl = document.getElementById('selected-image');
    if (computer.image_url) {
        imgEl.src = computer.image_url;
    } else {
        // Fallbacks
        if (currentVenueType === 'restaurant') {
            imgEl.src = 'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=800&q=80';
        } else {
            const bgImages = {
                'VIP': 'https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=800&q=80',
                'Standard': 'https://images.unsplash.com/photo-1587202372775-e229f172b9d7?auto=format&fit=crop&w=800&q=80',
                'Bootcamp': 'https://images.unsplash.com/photo-1598550476439-6847785fcea6?auto=format&fit=crop&w=800&q=80'
            };
            imgEl.src = bgImages[computer.zone] || bgImages['Standard'];
        }
    }

    // Update specs
    const specsContainer = document.querySelector('.specs');
    if (specsContainer) {
        if (currentVenueType === 'restaurant') {
            specsContainer.innerHTML = `
                <div class="spec-item"><div class="spec-label">Вместимость</div><div class="spec-value">${computer.cpu || '4 чел.'}</div></div>
                <div class="spec-item"><div class="spec-label">Условия</div><div class="spec-value">${computer.gpu || 'Без депозита'}</div></div>
                <div class="spec-item"><div class="spec-label">Расположение</div><div class="spec-value">${computer.zone || 'Зал'}</div></div>
            `;
        } else {
            specsContainer.innerHTML = `
                <div class="spec-item"><div class="spec-label">CPU</div><div class="spec-value">${computer.cpu || 'i5-12400'}</div></div>
                <div class="spec-item"><div class="spec-label">GPU</div><div class="spec-value">${computer.gpu || 'RTX 3060'}</div></div>
                <div class="spec-item"><div class="spec-label">RAM</div><div class="spec-value">${computer.ram_gb ? computer.ram_gb + ' GB' : '16 GB'}</div></div>
                <div class="spec-item"><div class="spec-label">Display</div><div class="spec-value">${computer.monitor_hz ? computer.monitor_hz + ' Hz' : '144 Hz'}</div></div>
            `;
        }
    }

    // Configure Main Button
    tg.MainButton.setText(`ВЫБРАТЬ ${computer.name.toUpperCase()}`);
    tg.MainButton.color = '#00f2ff';
    tg.MainButton.textColor = '#000000';
    tg.MainButton.show();
    tg.MainButton.enable();

    // IMPORTANT: Set OnClick handler
    tg.MainButton.offClick(openBookingModal); // Remove previous
    tg.MainButton.onClick(openBookingModal);

    tg.HapticFeedback.impactOccurred('heavy');
}

// --- Restored & New: Booking Modal Logic ---

function openBookingModal() {
    const modal = document.getElementById('booking-modal');
    modal.style.display = 'flex';
    document.getElementById('modal-pc-name').textContent = selectedComputer.name;

    // Reset state
    bookingState.selectedHour = null;
    bookingState.durationMinutes = 60;

    // Select Today by default
    selectDate(0, document.querySelectorAll('.date-tab')[0]);
    updatePrice();
}

function closeBookingModal() {
    document.getElementById('booking-modal').style.display = 'none';
}

function selectDate(offset, btn) {
    bookingState.dayOffset = offset;

    document.querySelectorAll('.date-tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    renderTimeGrid();
    tg.HapticFeedback.selectionChanged();
}

// Helper: Get current time in Tashkent (UTC+5)
function nowTashkent() {
    const now = new Date();
    // Convert to UTC, then add 5 hours for Tashkent
    const utc = now.getTime() + (now.getTimezoneOffset() * 60000);
    return new Date(utc + (5 * 3600000));
}

// Helper: Format date as YYYY-MM-DD in Tashkent timezone
function tashkentDateStr(dayOffset = 0) {
    const d = nowTashkent();
    d.setDate(d.getDate() + dayOffset);
    return d.toISOString().split('T')[0];
}

async function renderTimeGrid() {
    const grid = document.getElementById('time-grid');
    grid.innerHTML = '';

    const tashkentNow = nowTashkent();
    const isToday = bookingState.dayOffset === 0;
    const currentHour = tashkentNow.getHours();

    // Calculate target date for API call using Tashkent time
    const dateStr = tashkentDateStr(bookingState.dayOffset);

    // Show loading skeleton while fetching (all 24 hours)
    for (let h = 0; h < 24; h++) {
        const slot = document.createElement('button');
        slot.className = 'time-slot skeleton';
        slot.textContent = `${String(h).padStart(2, '0')}:00`;
        grid.appendChild(slot);
    }

    // Fetch occupied hours from API
    let occupiedHours = [];
    if (selectedComputer) {
        try {
            const resp = await fetch(
                `${API_BASE_URL}/availability?club_id=${selectedComputer.club_id || clubId}&computer_id=${selectedComputer.id}&date=${dateStr}`
            );
            if (resp.ok) {
                const data = await resp.json();
                occupiedHours = data.occupied_hours || [];
            }
        } catch (e) {
            console.warn('Failed to fetch availability:', e);
        }
    }

    // Re-render with real data (all 24 hours, matching bot)
    grid.innerHTML = '';
    for (let h = 0; h < 24; h++) {
        const slot = document.createElement('button');
        slot.className = 'time-slot';
        slot.textContent = `${String(h).padStart(2, '0')}:00`;

        let disabled = false;

        // Disable past hours (using Tashkent time)
        if (isToday && h <= currentHour) {
            disabled = true;
            slot.classList.add('disabled');
            slot.title = 'Время прошло';
        }
        // Disable occupied hours
        else if (occupiedHours.includes(h)) {
            disabled = true;
            slot.classList.add('occupied');
            slot.title = 'Занято';
        }

        if (!disabled) {
            slot.onclick = () => {
                bookingState.selectedHour = h;

                document.querySelectorAll('.time-slot').forEach(s => s.classList.remove('selected'));
                slot.classList.add('selected');

                updatePrice();
                tg.HapticFeedback.selectionChanged();
            };
        }

        if (bookingState.selectedHour === h) {
            slot.classList.add('selected');
        }

        grid.appendChild(slot);
    }
}

function adjustDuration(delta) {
    let newDuration = bookingState.durationMinutes + delta;
    if (newDuration < 30) newDuration = 30;
    if (newDuration > 600) newDuration = 600; // 10 hours max

    bookingState.durationMinutes = newDuration;

    // Format display
    const h = Math.floor(newDuration / 60);
    const m = newDuration % 60;
    let text = "";
    if (h > 0) text += `${h} ч `;
    if (m > 0) text += `${m} мин`;

    document.getElementById('duration-display').textContent = text;
    updatePrice();
    tg.HapticFeedback.impactOccurred('light');
}

function updatePrice() {
    const hours = bookingState.durationMinutes / 60;
    let price;

    if (currentVenueType === 'restaurant') {
        // Restaurants: flat booking fee (deposit), NOT hourly
        price = selectedComputer.price_per_hour || 0; // booking_price mapped to price_per_hour
    } else {
        // Computer clubs: hourly rate
        price = selectedComputer.price_per_hour * hours;
    }

    const priceLabel = currentVenueType === 'restaurant' ? 'Депозит' : 'Итого';
    document.getElementById('total-price').textContent = price > 0 ? `${Math.round(price).toLocaleString()} сум` : "Бесплатно";

    const btn = document.getElementById('confirm-booking-btn');
    if (bookingState.selectedHour !== null) {
        btn.disabled = false;
        btn.style.opacity = '1';
        btn.textContent = price > 0
            ? `ЗАБРОНИРОВАТЬ (${Math.round(price).toLocaleString()} СУМ)`
            : `ПОДТВЕРДИТЬ БРОНЬ`;
    } else {
        btn.disabled = true;
        btn.style.opacity = '0.5';
        btn.textContent = 'ВЫБЕРИТЕ ВРЕМЯ';
    }
}

async function confirmBooking() {
    if (bookingState.selectedHour === null) return;

    const btn = document.getElementById('confirm-booking-btn');
    const originalText = btn.textContent;
    btn.textContent = 'Обработка...';
    btn.disabled = true;

    try {
        // Build start_time correctly: use UTC methods only to avoid device timezone interference.
        // Step 1: Get today's date in Tashkent (UTC+5) using UTC offset arithmetic
        const TASHKENT_OFFSET_MS = 5 * 60 * 60 * 1000;
        const nowMs = Date.now();
        // Date in Tashkent by shifting UTC timestamp
        const tashkentNow = new Date(nowMs + TASHKENT_OFFSET_MS);
        // Step 2: Apply day offset and set the selected hour (all in UTC methods on the shifted date)
        tashkentNow.setUTCDate(tashkentNow.getUTCDate() + bookingState.dayOffset);
        tashkentNow.setUTCHours(bookingState.selectedHour, 0, 0, 0);
        // Step 3: Shift back to real UTC
        const startTimeUTC = new Date(tashkentNow.getTime() - TASHKENT_OFFSET_MS);

        const user = getAuthUser();
        let userId = user ? user.id : 0;

        if (!userId) {
            throw new Error("⛔ Ошибка авторизации. Попробуйте перезайти.");
        }

        const payload = {
            user_id: userId,
            club_id: parseInt(clubId),
            computer_id: String(selectedComputer.id),
            start_time: startTimeUTC.toISOString(),
            duration_minutes: bookingState.durationMinutes
        };

        const response = await fetch(`${API_BASE_URL}/bookings`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'ngrok-skip-browser-warning': 'true',
                ...getAuthHeaders()
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            if (response.status === 401) {
                throw new Error("⛔ Ошибка авторизации.\nПожалуйста, откройте приложение внутри Telegram!");
            }
            const errText = await response.text();
            throw new Error(errText);
        }

        const result = await response.json();
        if (result.success) {
            showToast(`✅ Бронь #${result.booking_id} создана!`, 'success');
            closeBookingModal();
            unselectComputer();
            // Auto-navigate to My Bookings to show the new booking
            setTimeout(() => switchTab('bookings'), 800);
        } else {
            showToast(result.message + (result.conflict ? '\nВремя занято!' : ''), 'error');
        }

    } catch (error) {
        console.error("Booking Error:", error);
        showToast('Ошибка: ' + error.message, 'error');
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

// --- Navigation Helpers ---
function unselectComputer() {
    selectedComputer = null;
    document.getElementById('selected-info').style.transform = 'translateY(100%)';
    setTimeout(() => {
        document.getElementById('selected-info').style.display = 'none';
        tg.MainButton.hide();
    }, 300);
    document.querySelectorAll('.computer-card').forEach(card => card.classList.remove('selected'));
}

function handleBackButton() {
    const bookingModal = document.getElementById('booking-modal');
    if (bookingModal.style.display === 'flex') {
        closeBookingModal();
        return;
    }

    const myBookingsModal = document.getElementById('my-bookings-modal');
    if (myBookingsModal.style.display === 'flex') {
        closeMyBookings();
        return;
    }

    const infoPanel = document.getElementById('selected-info');
    if (infoPanel.style.display === 'block' && infoPanel.getBoundingClientRect().height > 0) {
        unselectComputer();
        return;
    }

    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('club_id')) {
        const newUrl = new URL(window.location.href);
        newUrl.searchParams.delete('club_id');
        window.location.href = newUrl.toString();
        return;
    }

    tg.close();
}

function goBackToClubs() {
    const newUrl = new URL(window.location.href);
    newUrl.searchParams.delete('club_id');
    window.location.href = newUrl.toString();
}

function setupBackButton() {
    tg.BackButton.show();
    tg.BackButton.onClick(handleBackButton);
}

function enableGlobalScroll() {
    if (scrollListenersAttached) return;
    scrollListenersAttached = true;
    // ... basic scroll lock/unlock interaction if needed ...
}

// --- New Feature: My Bookings ---

async function openMyBookings() {
    const modal = document.getElementById('my-bookings-modal');
    const list = document.getElementById('my-bookings-list');
    modal.style.display = 'flex';

    list.innerHTML = `<div class="empty-state-small">Загрузка...</div>`;

    try {
        const response = await fetch(`${API_BASE_URL}/user/bookings?page=1&limit=50`, {
            headers: {
                'ngrok-skip-browser-warning': 'true',
                ...getAuthHeaders()
            }
        });

        if (!response.ok) {
            if (response.status === 401) {
                throw new Error('⛔ Ошибка авторизации. Откройте приложение в Telegram');
            }
            throw new Error(`HTTP ${response.status}`);
        }

        const bookingsData = await response.json();
        const bookings = bookingsData.bookings || []; // Extract bookings from paginated response

        renderUserBookings(bookings);
    } catch (e) {
        list.innerHTML = `<div class="empty-state-small" style="color:var(--error)">Ошибка загрузки</div>`;
    }
}

function closeMyBookings() {
    document.getElementById('my-bookings-modal').style.display = 'none';
}

function renderUserBookings(bookings) {
    const list = document.getElementById('my-bookings-list');
    list.innerHTML = '';

    if (bookings.length === 0) {
        list.innerHTML = `<div class="empty-state-small">У вас нет активных бронирований.</div>`;
        return;
    }

    bookings.forEach(b => {
        const div = document.createElement('div');
        div.className = 'booking-card';

        // Check if QR code button should be shown
        let qrButtonHTML = '';
        if (b.confirmation_code && (b.status === 'CONFIRMED' || b.status === 'ACTIVE')) {
            // Need escaping for string arguments in inline onclick
            qrButtonHTML = `<button class="qr-btn-small" onclick="showQRCode('${b.confirmation_code}')">🎟 Показать код</button>`;
        }

        div.innerHTML = `
            <div class="booking-info">
                <h4>${b.club_name}</h4>
                <p>🖥️ ${b.computer_name}</p>
                <p>🕒 ${b.display_time}</p>
            </div>
            <div class="booking-actions">
                <span class="status-badge ${b.status.toLowerCase()}">${b.status}</span>
                <div class="booking-action-buttons">
                    ${qrButtonHTML}
                    ${b.status === 'CONFIRMED' ? `<button class="cancel-btn-small" onclick="cancelBooking(${b.id})">Отмена</button>` : ''}
                </div>
            </div>
        `;
        list.appendChild(div);
    });
}

async function cancelBooking(bookingId) {
    // 1️⃣ Confirmation (protect from accidental clicks)
    if (!confirm('❗ Вы уверены, что хотите отменить эту бронь?\n\nОтменить действие будет невозможно.')) {
        return;
    }

    // 2️⃣ Get button element
    const btnElement = event?.target; // Button that was clicked
    if (!btnElement) {
        showToast('❌ Ошибка: Не удалось найти кнопку', 'error');
        return;
    }

    const originalText = btnElement.textContent;
    btnElement.textContent = '⏳ Отмена...';
    btnElement.disabled = true;

    try {
        // 3️⃣ Send DELETE request with proper auth
        const response = await fetch(`${API_BASE_URL}/bookings/${bookingId}`, {
            method: 'DELETE',
            headers: {
                'ngrok-skip-browser-warning': 'true',
                ...getAuthHeaders()
            }
        });

        if (response.ok) {
            const result = await response.json();
            showToast(result.message || 'Бронь успешно отменена!', 'success');

            // Safe haptic
            try {
                if (tg && tg.HapticFeedback) {
                    tg.HapticFeedback.notificationOccurred('success');
                }
            } catch (e) { }

            // Refresh list
            setTimeout(() => openMyBookings(), 500);
        } else {
            // 4️⃣ Better error handling
            let errorMsg = 'Не удалось отменить бронь';

            try {
                const errorData = await response.json();
                errorMsg = errorData.detail || errorMsg;
            } catch {
                // Server didn't return JSON
                if (response.status === 404) {
                    errorMsg = 'Бронь не найдена или вам не принадлежит';
                } else if (response.status === 400) {
                    errorMsg = 'Невозможно отменить эту бронь';
                } else if (response.status === 401) {
                    errorMsg = '⛔ Вы не авторизованы';
                } else if (response.status >= 500) {
                    errorMsg = 'Ошибка сервера. Попробуйте позже';
                }
            }

            showToast(errorMsg, 'error');

            // Safe haptic
            try {
                if (tg && tg.HapticFeedback) {
                    tg.HapticFeedback.notificationOccurred('error');
                }
            } catch (e) { }
        }
    } catch (e) {
        // 5️⃣ Network errors
        console.error('Network error:', e);
        showToast('❌ Ошибка сети. Проверьте подключение к интернету.', 'error');

        // Safe haptic
        try {
            if (tg && tg.HapticFeedback) {
                tg.HapticFeedback.notificationOccurred('error');
            }
        } catch (e) { }
    } finally {
        // 6️⃣ Restore button in any case
        btnElement.textContent = originalText;
        btnElement.disabled = false;
    }
}

// --- QR Code Logic ---
let currentQRCode = null;

function showQRCode(code) {
    const modal = document.getElementById('qr-modal');
    const container = document.getElementById('qr-code-container');
    const textElement = document.getElementById('qr-code-text');

    // Clear previous QR
    container.innerHTML = '';
    textElement.textContent = code;

    // Generate new QR using QRCode.js
    currentQRCode = new QRCode(container, {
        text: code,
        width: 180,
        height: 180,
        colorDark: "#000000",
        colorLight: "#ffffff",
        correctLevel: QRCode.CorrectLevel.L
    });

    modal.style.display = 'flex';
}

function closeQRModal() {
    document.getElementById('qr-modal').style.display = 'none';
    if (currentQRCode) {
        currentQRCode.clear();
    }
}

// ======================================================
// Mini App 2.0: Tab Navigation
// ======================================================

let currentTab = 'clubs';

function switchTab(tab) {
    // When leaving clubs tab — deselect computer and hide info panel
    if (currentTab === 'clubs' && tab !== 'clubs') {
        unselectComputer();
    }

    // Hide all tab panels
    document.querySelectorAll('[id^="tab-"]').forEach(el => el.classList.add('hidden'));
    // Deactivate all nav buttons
    document.querySelectorAll('.bottom-nav-btn').forEach(btn => btn.classList.remove('active'));

    // Show selected tab
    const panel = document.getElementById(`tab-${tab}`);
    if (panel) panel.classList.remove('hidden');

    const btn = document.getElementById(`nav-${tab}`);
    if (btn) btn.classList.add('active');

    currentTab = tab;

    // Load content for the tab
    if (tab === 'bookings') renderBookingsTab();
    if (tab === 'profile') renderProfileTab();
    if (tab === 'bar') renderBarTab();
}

async function renderBookingsTab() {
    const container = document.getElementById('my-bookings-tab-list');
    if (!container) return;
    container.innerHTML = '<p style="text-align:center;padding:32px 0;color:rgba(255,255,255,0.4)">⏳ Загрузка...</p>';

    const user = getAuthUser();
    if (!user) {
        container.innerHTML = '<p style="text-align:center;padding:32px 0;color:rgba(255,255,255,0.4)">🔐 Войдите в аккаунт</p>';
        return;
    }

    try {
        const r = await fetch(`${API_BASE_URL}/web/bookings`, {
            headers: {
                'ngrok-skip-browser-warning': 'true',
                'X-Telegram-Init-Data': tg.initData || '',
                ...getAuthHeaders()
            }
        });

        if (!r.ok) {
            throw new Error(`Ошибка ${r.status}`);
        }

        const bookings = await r.json();
        if (!bookings.length) {
            container.innerHTML = '<p style="text-align:center;color:rgba(255,255,255,0.4);padding:32px 0">📋 Ещё нет броней</p>';
            return;
        }

        const statusMap = {
            'CONFIRMED': { label: '✅ Подтверждено', cls: 'confirmed' },
            'ACTIVE': { label: '🟢 Активно', cls: 'active' },
            'COMPLETED': { label: '✔ Завершено', cls: 'completed' },
            'CANCELLED': { label: '❌ Отменено', cls: 'cancelled' },
            'NO_SHOW': { label: '👻 Не явился', cls: 'cancelled' },
        };

        container.innerHTML = bookings.map(b => {
            const st = statusMap[b.status] || { label: b.status, cls: 'completed' };
            const canCancel = b.status === 'CONFIRMED' || b.status === 'ACTIVE';
            const hasQR = b.confirmation_code && canCancel;
            return `
                <div class="booking-card" style="margin-bottom:12px">
                    <div class="booking-header">
                        <strong>🖥 ${b.computer_name}</strong>
                        <span class="booking-status-badge status-${st.cls}">${st.label}</span>
                    </div>
                    <div class="booking-info" style="margin-top:4px;font-size:13px;opacity:0.7">
                        🏢 ${b.club_name} &nbsp;·&nbsp; 🕒 ${b.display_time}
                    </div>
                    <div class="booking-action-buttons" style="margin-top:8px;display:flex;gap:8px">
                        ${hasQR ? `<button class="qr-btn-small" onclick="showQRCode('${b.confirmation_code}')">🎟 QR-код</button>` : ''}
                        ${canCancel ? `<button class="cancel-btn-small" onclick="cancelBooking(${b.id})">✖ Отмена</button>` : ''}
                    </div>
                </div>
            `;
        }).join('');

    } catch (e) {
        container.innerHTML = `<p style="text-align:center;color:var(--error);padding:16px">❌ ${e.message}</p>`;
    }
}

async function renderProfileTab() {
    const container = document.getElementById('profile-content');
    const user = getAuthUser();

    if (!user) {
        container.innerHTML = '<p style="text-align:center;color:rgba(255,255,255,0.4);padding:32px">🔐 Войдите в аккаунт</p>';
        return;
    }

    // Show skeleton
    container.innerHTML = '<p style="text-align:center;padding:32px;opacity:0.5">⏳ Загрузка...</p>';

    let profile = null;
    try {
        const r = await fetch(`${API_BASE_URL}/web/profile`, {
            headers: { ...getAuthHeaders(), 'X-Telegram-Init-Data': tg.initData || '' }
        });
        if (r.ok) profile = await r.json();
    } catch (e) { }

    const name = profile?.full_name || user.first_name || 'Пользователь';
    const phone = profile?.phone || '—';
    const balance = profile?.balance ?? 0;
    const totalB = profile?.total_bookings ?? 0;
    const completedB = profile?.completed_bookings ?? 0;
    const loyalty = profile?.loyalty || { level: 'Bronze', icon: '🥉', next: 'Silver', needed: 5 };
    const referralCode = profile?.referral_code || '—';
    const loyaltyPct = loyalty.next
        ? Math.min(100, Math.round(((completedB % (loyalty.level === 'Bronze' ? 5 : loyalty.level === 'Silver' ? 15 : 30)) / (loyalty.level === 'Bronze' ? 5 : loyalty.level === 'Silver' ? 15 : 30)) * 100))
        : 100;

    container.innerHTML = `
        <!-- Loyalty Card -->
        <div class="profile-card" style="background:linear-gradient(135deg,rgba(124,58,237,0.3),rgba(0,242,255,0.15));border:1px solid rgba(124,58,237,0.3)">
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
                <div style="font-size:36px;line-height:1">${loyalty.icon}</div>
                <div>
                    <div style="font-size:20px;font-weight:700">${loyalty.level}</div>
                    <div style="font-size:12px;opacity:0.6">${loyalty.next ? `До ${loyalty.next}: ещё ${loyalty.needed} визитов` : 'Максимальный уровень!'}</div>
                </div>
            </div>
            <div style="background:rgba(255,255,255,0.1);border-radius:6px;height:6px;overflow:hidden">
                <div style="background:linear-gradient(90deg,var(--primary),var(--secondary));height:100%;width:${loyaltyPct}%;transition:width 0.5s"></div>
            </div>
        </div>

        <!-- Account Info -->
        <div class="profile-card">
            <h4 style="margin-bottom:12px">👤 Аккаунт</h4>
            <div class="profile-row"><span>Имя</span><span class="profile-value">${name}</span></div>
            <div class="profile-row"><span>📱 Телефон</span><span class="profile-value">${phone}</span></div>
            ${profile?.username ? `<div class="profile-row"><span>@ Username</span><span class="profile-value">@${profile.username}</span></div>` : ''}
        </div>

        <!-- Stats -->
        <div class="profile-card">
            <h4 style="margin-bottom:12px">📊 Статистика</h4>
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;text-align:center">
                <div style="background:rgba(255,255,255,0.05);border-radius:12px;padding:12px">
                    <div style="font-size:22px;font-weight:700;color:var(--primary)">${totalB}</div>
                    <div style="font-size:11px;opacity:0.6">Всего броней</div>
                </div>
                <div style="background:rgba(255,255,255,0.05);border-radius:12px;padding:12px">
                    <div style="font-size:22px;font-weight:700;color:#10b981">${completedB}</div>
                    <div style="font-size:11px;opacity:0.6">Завершено</div>
                </div>
                <div style="background:rgba(255,255,255,0.05);border-radius:12px;padding:12px">
                    <div style="font-size:22px;font-weight:700;color:var(--secondary)">${balance.toLocaleString()}</div>
                    <div style="font-size:11px;opacity:0.6">Баланс (UZS)</div>
                </div>
            </div>
        </div>

        <!-- Referral -->
        ${referralCode !== '—' ? `
        <div class="profile-card">
            <h4 style="margin-bottom:12px">🎁 Реферальный код</h4>
            <div class="profile-row">
                <span>Ваш код</span>
                <span class="profile-value" onclick="navigator.clipboard.writeText('${referralCode}');showToast('✅ Код скопирован!','success')" style="cursor:pointer">${referralCode} 📋</span>
            </div>
        </div>` : ''}

        <!-- Language -->
        <div class="profile-card">
            <h4 style="margin-bottom:12px">🌍 Язык</h4>
            <div style="display:flex;gap:8px">
                <button onclick="setLanguageFromApp('ru')" style="flex:1;padding:10px;border-radius:10px;border:1px solid rgba(255,255,255,0.1);background:rgba(255,255,255,0.05);color:#fff;cursor:pointer;font-size:13px">🇷🇺 Рус</button>
                <button onclick="setLanguageFromApp('uz')" style="flex:1;padding:10px;border-radius:10px;border:1px solid rgba(255,255,255,0.1);background:rgba(255,255,255,0.05);color:#fff;cursor:pointer;font-size:13px">🇺🇿 Uz</button>
                <button onclick="setLanguageFromApp('en')" style="flex:1;padding:10px;border-radius:10px;border:1px solid rgba(255,255,255,0.1);background:rgba(255,255,255,0.05);color:#fff;cursor:pointer;font-size:13px">🇬🇧 En</button>
            </div>
        </div>

        <!-- Logout -->
        <div style="padding:0 0 8px">
            <button onclick="logoutUser()" style="width:100%;padding:12px;border-radius:12px;border:1px solid rgba(255,100,100,0.3);background:rgba(255,0,0,0.08);color:rgba(255,100,100,0.9);cursor:pointer;font-size:14px;font-weight:600">🚪 Выйти из аккаунта</button>
        </div>
    `;
}

async function setLanguageFromApp(lang) {
    const user = getAuthUser();
    const userId = user?.id;
    if (!userId) return;
    try {
        await fetch(`${API_BASE_URL}/web/language`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...getAuthHeaders(), 'X-Telegram-Init-Data': tg.initData || '' },
            body: JSON.stringify({ tg_id: userId, language: lang })
        });
        const labels = { ru: 'Русский 🇷🇺', uz: "O'zbek 🇺🇿", en: 'English 🇬🇧' };
        showToast(`✅ Язык изменён: ${labels[lang]}`, 'success');
    } catch (e) {
        showToast('Ошибка при смене языка', 'error');
    }
}

function logoutUser() {
    if (!confirm('Выйти из аккаунта?')) return;
    // Call logout endpoint to invalidate session on server
    const token = localStorage.getItem('session_token');
    if (token) {
        fetch(`${API_BASE_URL}/auth/logout`, {
            method: 'POST',
            headers: { 'X-Session-Token': token }
        }).catch(() => { });
    }
    localStorage.removeItem('session_token');
    localStorage.removeItem('session_user');
    window.location.reload();
}


// ==================== AUTH USER HELPER ====================
function getAuthUser() {
    // 1. Inside Telegram Mini App
    if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
        return tg.initDataUnsafe.user;
    }
    // 2. Standalone PWA — session stored in localStorage
    if (_sessionAuthData) {
        return _sessionAuthData;
    }
    // 3. Fallback: read directly from localStorage
    const raw = localStorage.getItem('session_user');
    if (raw) {
        try { return JSON.parse(raw); } catch (e) { }
    }
    return null;
}

// ==================== INITIALIZATION ====================
function initApp() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.style.display = 'none';

    loadClubData();
    enableGlobalScroll();
}

// Start auth flow
checkAuthAndInit().then(isAuthenticated => {
    if (isAuthenticated) {
        initApp();
    }
});


// ======================================================
// Bar / Snacks Shop Logic
// ======================================================

let barItems = [];
let cart = {}; // itemId -> { item, qty }
let isCartOpen = false;

async function renderBarTab() {
    const list = document.getElementById('bar-items-list');
    list.innerHTML = '<p style="text-align:center;color:rgba(255,255,255,0.4)" data-i18n="loading">Загрузка...</p>';

    try {
        let url = `${API_BASE_URL}/bar/items`;
        if (currentClubId) url += `?club_id=${currentClubId}`;

        const res = await fetch(url, { headers: { 'ngrok-skip-browser-warning': 'true' } });
        if (!res.ok) throw new Error('Ошибка загрузки меню');

        barItems = await res.json();

        if (barItems.length === 0) {
            list.innerHTML = '<p style="text-align:center;color:rgba(255,255,255,0.4)">В этом клубе пока нет меню</p>';
            return;
        }

        list.innerHTML = barItems.map(item => `
            <div style="background:var(--card-bg); border-radius:16px; overflow:hidden; border:1px solid rgba(255,255,255,0.05); display:flex; flex-direction:column;">
                <div style="height:120px; background:rgba(0,0,0,0.5); display:flex; align-items:center; justify-content:center; overflow:hidden;">
                    ${item.image_url ? `<img src="${item.image_url}" style="width:100%; height:100%; object-fit:cover;">` : '<span style="font-size:40px;">🍔</span>'}
                </div>
                <div style="padding:12px; display:flex; flex-direction:column; flex:1;">
                    <div style="font-size:10px; color:var(--primary); font-weight:bold; margin-bottom:4px; text-transform:uppercase;">${item.category || 'Снеки'}</div>
                    <div style="font-weight:600; font-size:14px; margin-bottom:8px; line-height:1.2; flex:1;">${item.name}</div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:auto;">
                        <span style="font-weight:bold; color:var(--text); font-size:13px;">${item.price.toLocaleString()} сум</span>
                        <button onclick="addToCart(${item.id})" style="background:var(--primary); border:none; color:white; width:28px; height:28px; border-radius:8px; font-weight:bold; cursor:pointer;">+</button>
                    </div>
                </div>
            </div>
        `).join('');

    } catch (e) {
        list.innerHTML = `<p style="text-align:center;color:var(--danger)">${e.message}</p>`;
    }
}

function addToCart(itemId, delta = 1) {
    const item = barItems.find(i => i.id === itemId);
    if (!item) return;

    if (!cart[itemId]) cart[itemId] = { item, qty: 0 };
    cart[itemId].qty += delta;

    if (cart[itemId].qty <= 0) {
        delete cart[itemId];
    }

    updateCartUI();
    if (typeof haptic === 'function') haptic('light');
}

function updateCartUI() {
    const counts = Object.values(cart).reduce((sum, c) => sum + c.qty, 0);
    const badge = document.getElementById('cart-count');

    if (counts > 0) {
        badge.style.display = 'block';
        badge.textContent = counts;
    } else {
        badge.style.display = 'none';
        if (isCartOpen) toggleCart(); // Auto close if empty
    }

    if (isCartOpen) renderCartItems();
}

function renderCartItems() {
    const container = document.getElementById('cart-items');
    const totalEl = document.getElementById('cart-total');

    if (Object.keys(cart).length === 0) {
        container.innerHTML = '<p style="text-align:center;color:rgba(255,255,255,0.4)">Корзина пуста</p>';
        totalEl.textContent = '0 сум';
        return;
    }

    let total = 0;
    container.innerHTML = Object.values(cart).map(c => {
        total += c.item.price * c.qty;
        return `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; padding-bottom:10px; border-bottom:1px solid rgba(255,255,255,0.05);">
                <div style="flex:1;">
                    <div style="font-size:14px; font-weight:600;">${c.item.name}</div>
                    <div style="font-size:12px; color:rgba(255,255,255,0.6);">${c.item.price.toLocaleString()} сум</div>
                </div>
                <div style="display:flex; align-items:center; gap:10px;">
                    <button onclick="addToCart(${c.item.id}, -1)" style="width:28px; height:28px; border-radius:8px; background:rgba(255,255,255,0.1); border:none; color:white;">-</button>
                    <span style="font-weight:bold; min-width:20px; text-align:center;">${c.qty}</span>
                    <button onclick="addToCart(${c.item.id}, 1)" style="width:28px; height:28px; border-radius:8px; background:var(--primary); border:none; color:white;">+</button>
                </div>
            </div>
        `;
    }).join('');

    totalEl.textContent = `${total.toLocaleString()} сум`;
}

function toggleCart() {
    const panel = document.getElementById('cart-panel');
    const counts = Object.values(cart).reduce((sum, c) => sum + c.qty, 0);

    if (!isCartOpen) {
        if (counts === 0) return; // Don't open empty cart
        panel.style.display = 'block';
        isCartOpen = true;
        renderCartItems();
    } else {
        panel.style.display = 'none';
        isCartOpen = false;
    }
}

async function submitBarOrder() {
    if (Object.keys(cart).length === 0) return;

    const pcName = document.getElementById('bar-pc-name').value.trim();
    if (!pcName) {
        alert('Пожалуйста, укажите номер вашего компьютера или столика!');
        return;
    }

    if (!currentClubId) {
        alert('Клуб не выбран. Перейдите в раздел "Клубы" и выберите клуб, в котором вы сейчас находитесь.');
        return;
    }

    const items = Object.values(cart).map(c => ({
        id: c.item.id,
        name: c.item.name,
        qty: c.qty,
        price: c.item.price
    }));

    const total_price = items.reduce((sum, i) => sum + (i.qty * i.price), 0);
    const btn = event.target;
    const oldText = btn.innerHTML;
    btn.innerHTML = '⏳...';
    btn.disabled = true;

    try {
        const body = {
            club_id: currentClubId,
            pc_name: pcName,
            items: items,
            total_price: total_price
        };

        const res = await fetch(`${API_BASE_URL}/bar/order`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
            },
            body: JSON.stringify(body)
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Ошибка при оформлении заказа');

        alert(data.message || 'Заказ успешно оформлен! Ожидайте доставку.');

        // Clear cart
        cart = {};
        document.getElementById('bar-pc-name').value = '';
        toggleCart();
        updateCartUI();

    } catch (e) {
        alert(e.message);
    } finally {
        btn.innerHTML = oldText;
        btn.disabled = false;
    }
}
