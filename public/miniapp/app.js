// Telegram Web App initialization
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

// Debug Auth - REMOVED
// setTimeout(() => { ... }, 1000);

if (!tg.initData) {
    showToast('⚠️ Внимание: Нет данных авторизации Telegram!\nПопробуйте перезапустить бота.', 'error');
    document.body.innerHTML = '<div style="color:white;text-align:center;margin-top:50px;">🚫 Доступ запрещен. Откройте приложение через Telegram бота.</div>';
    throw new Error('No Telegram Auth Data');
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

// API Configuration — dynamic URL based on host
const IS_LOCAL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
const API_BASE_URL = IS_LOCAL
    ? `http://${window.location.host}/api`
    : "https://digital-arena-njok.onrender.com/api";

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
function renderClubSelection(clubs) {
    const grid = document.getElementById('computer-grid');
    grid.innerHTML = '';
    grid.style.gridTemplateColumns = '1fr'; // List view
    document.getElementById('zones').style.display = 'none'; // Hide filters
    document.getElementById('club-name').textContent = "Выберите клуб";
    document.getElementById('club-address').textContent = "Список доступных мест";

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

        card.innerHTML = `
            <div>
                <div class="club-title">${typeIcon} ${club.name}</div>
                <div class="club-location">${safeCity}, ${safeAddress}</div>
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
        // Build start_time in Tashkent timezone (UTC+5)
        const tashkent = nowTashkent();
        tashkent.setDate(tashkent.getDate() + bookingState.dayOffset);
        tashkent.setHours(bookingState.selectedHour, 0, 0, 0);
        // Convert Tashkent time back to UTC for API (subtract 5 hours)
        const startTimeUTC = new Date(tashkent.getTime() - (5 * 3600000));

        let userId = 0;
        if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
            userId = tg.initDataUnsafe.user.id;
        } else {
            // For testing only
            userId = 123456789;
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
                'X-Telegram-Init-Data': tg.initData
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

            // Refresh logic? Maybe go to My Bookings
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
                'X-Telegram-Init-Data': tg.initData
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
                'X-Telegram-Init-Data': tg.initData
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
}

async function renderBookingsTab() {
    const container = document.getElementById('my-bookings-tab-list');
    if (!container) return;
    container.innerHTML = '<p style="text-align:center;color:rgba(255,255,255,0.4)">Загрузка...</p>';

    const userId = tg.initDataUnsafe?.user?.id;
    if (!userId) {
        container.innerHTML = '<p style="text-align:center;color:rgba(255,255,255,0.4)">Войдите через Telegram</p>';
        return;
    }
    try {
        const r = await fetch(`${API_BASE_URL}/web/bookings?tg_id=${userId}`, {
            headers: {
                'ngrok-skip-browser-warning': 'true',
                'X-Telegram-Init-Data': tg.initData
            }
        });
        const bookings = await r.json();
        if (!bookings.length) {
            container.innerHTML = '<p style="text-align:center;color:rgba(255,255,255,0.4);padding:32px 0">📋 Нет броней</p>';
            return;
        }
        container.innerHTML = bookings.map(b => `
            <div class="booking-card" style="margin-bottom:12px">
                <div class="booking-header">
                    <strong>${b.computer_name}</strong>
                    <span class="booking-status-badge status-${(b.status || '').toLowerCase()}">${{
                'CONFIRMED': '✅ Подтверждено', 'ACTIVE': '🟢 Активно',
                'COMPLETED': '✔ Завершено', 'CANCELLED': '❌ Отменено',
                'NO_SHOW': '👻 Не явился'
            }[b.status] || b.status}</span>
                </div>
                <div class="booking-info">${b.club_name} · ${b.display_time}</div>
                <div class="booking-action-buttons">
                    <button class="qr-btn-small" onclick="showQRCode('${b.id}')">🎟 Показать код</button>
                </div>
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = `<p style="text-align:center;color:var(--error)">Ошибка: ${e.message}</p>`;
    }
}

async function renderProfileTab() {
    const container = document.getElementById('profile-content');
    const user = tg.initDataUnsafe?.user;

    if (!user) {
        container.innerHTML = '<p style="text-align:center;color:rgba(255,255,255,0.4)">Войдите через Telegram</p>';
        return;
    }

    // Fetch referral code from API
    let referralCode = '—';
    try {
        const r = await fetch(`${API_BASE_URL}/web/profile?tg_id=${user.id}`, {
            headers: { 'X-Telegram-Init-Data': tg.initData }
        });
        if (r.ok) {
            const data = await r.json();
            referralCode = data.referral_code || '—';
        }
    } catch (e) { }

    const botUsername = 'ArenaSlot_bot'; // Update if bot username changes
    const inviteLink = `https://t.me/${botUsername}?start=ref_${referralCode}`;

    container.innerHTML = `
        <div class="profile-card">
            <h4>Аккаунт</h4>
            <div class="profile-row">
                <span>👤 Имя</span>
                <span class="profile-value">${user.first_name || ''} ${user.last_name || ''}</span>
            </div>
            ${user.username ? `<div class="profile-row">
                <span>@ Username</span>
                <span class="profile-value">@${user.username}</span>
            </div>` : ''}
            <div class="profile-row">
                <span>🆔 Telegram ID</span>
                <span class="profile-value">${user.id}</span>
            </div>
        </div>

        <div class="profile-card">
            <h4>🎁 Реферальная программа</h4>
            <div class="profile-row">
                <span>Ваш код</span>
                <span class="profile-value" onclick="navigator.clipboard.writeText('${referralCode}')" style="cursor:pointer" title="Нажмите для копирования">${referralCode} 📋</span>
            </div>
            <div style="margin-top:10px">
                <a href="https://t.me/share/url?url=${encodeURIComponent(inviteLink)}&text=${encodeURIComponent('Бронируй ПК через Digital Arena!')}"
                   style="display:block;text-align:center;background:linear-gradient(135deg,#00f2ff,#8b5cf6);color:#000;border-radius:10px;padding:10px;font-weight:700;text-decoration:none;font-size:14px">
                   📤 Поделиться ссылкой
                </a>
            </div>
        </div>

        <div class="profile-card">
            <h4>🌍 Язык</h4>
            <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:4px">
                <button onclick="setLanguageFromApp('ru')" style="flex:1;padding:10px;border-radius:10px;border:1px solid rgba(255,255,255,0.1);background:rgba(255,255,255,0.05);color:#fff;cursor:pointer;font-size:13px">🇷🇺 Русский</button>
                <button onclick="setLanguageFromApp('uz')" style="flex:1;padding:10px;border-radius:10px;border:1px solid rgba(255,255,255,0.1);background:rgba(255,255,255,0.05);color:#fff;cursor:pointer;font-size:13px">🇺🇿 O'zbek</button>
                <button onclick="setLanguageFromApp('kz')" style="flex:1;padding:10px;border-radius:10px;border:1px solid rgba(255,255,255,0.1);background:rgba(255,255,255,0.05);color:#fff;cursor:pointer;font-size:13px">🇰🇿 Қазақ</button>
            </div>
        </div>
    `;
}

async function setLanguageFromApp(lang) {
    const userId = tg.initDataUnsafe?.user?.id;
    if (!userId) return;
    try {
        await fetch(`${API_BASE_URL}/web/language`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Telegram-Init-Data': tg.initData },
            body: JSON.stringify({ tg_id: userId, language: lang })
        });
        const labels = { ru: 'Русский 🇷🇺', uz: "O'zbek 🇺🇿", kz: 'Қазақ 🇰🇿' };
        showToast(`✅ Язык изменён: ${labels[lang]}`, 'success');
    } catch (e) {
        showToast('Ошибка при смене языка', 'error');
    }
}

// Initialize
loadClubData();
enableGlobalScroll();
