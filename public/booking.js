// ==================== MOCK TELEGRAM ENVIRONMENT ====================
if (!window.Telegram) {
    window.Telegram = {};
}

if (!window.Telegram.WebApp) {
    console.log("Mocking Telegram WebApp environment...");
    window.Telegram.WebApp = {
        initData: "user_id=123456789&first_name=Demo&last_name=User",
        initDataUnsafe: {
            user: { id: 123456789, first_name: "Demo", last_name: "User", username: "demo_user" }
        },
        colorScheme: 'dark',
        themeParams: {
            bg_color: "#050510",
            text_color: "#ffffff",
            hint_color: "#7a7a7a",
            link_color: "#00f2ff",
            button_color: "#00f2ff",
            button_text_color: "#000000"
        },
        isExpanded: true,
        viewportHeight: 800,
        expand: () => console.log("TG: expand()"),
        ready: () => console.log("TG: ready()"),
        close: () => { console.log("TG: close()"); window.location.href = 'index.html'; },
        MainButton: {
            text: "BUTTON",
            color: "#00f2ff",
            textColor: "#000000",
            isVisible: false,
            isActive: true,
            show: function () { this.isVisible = true; this.update(); },
            hide: function () { this.isVisible = false; this.update(); },
            enable: function () { this.isActive = true; this.update(); },
            disable: function () { this.isActive = false; this.update(); },
            onClick: function (cb) { this.callback = cb; },
            offClick: function (cb) { this.callback = null; },
            callback: null,
            update: function () {
                // Sync with DOM button if we were real
                const btn = document.getElementById('tg-main-button-mock');
                if (btn) {
                    btn.style.display = this.isVisible ? 'block' : 'none';
                    btn.textContent = this.text;
                    btn.style.background = this.color;
                    btn.style.color = this.textColor;
                    btn.disabled = !this.isActive;
                }
            }
        },
        BackButton: {
            isVisible: false,
            show: function () { this.isVisible = true; this.update(); },
            hide: function () { this.isVisible = false; this.update(); },
            onClick: function (cb) { this.callback = cb; },
            callback: null,
            update: function () {
                const btn = document.getElementById('tg-back-button-mock');
                if (btn) {
                    btn.style.display = this.isVisible ? 'flex' : 'none';
                }
            }
        },
        HapticFeedback: {
            impactOccurred: (style) => console.log(`Haptic: impact ${style}`),
            notificationOccurred: (type) => console.log(`Haptic: notification ${type}`),
            selectionChanged: () => console.log(`Haptic: selection changed`)
        }
    };
}

// Initialization
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();
document.documentElement.setAttribute('data-theme', 'dark');

// --- Create Mock Buttons UI ---
function createMockTgUi() {
    // Back Button
    const backBtn = document.createElement('div');
    backBtn.id = 'tg-back-button-mock';
    backBtn.innerHTML = '←';
    Object.assign(backBtn.style, {
        position: 'fixed',
        top: '10px',
        left: '10px',
        width: '40px',
        height: '40px',
        background: 'rgba(0,0,0,0.5)',
        color: 'white',
        borderRadius: '50%',
        display: 'none',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: 'pointer',
        fontSize: '20px',
        zIndex: 9999,
        backdropFilter: 'blur(5px)',
        border: '1px solid rgba(255,255,255,0.2)'
    });
    backBtn.onclick = () => {
        if (tg.BackButton.callback) tg.BackButton.callback();
    };
    document.body.appendChild(backBtn);

    // Main Button
    const mainBtn = document.createElement('button');
    mainBtn.id = 'tg-main-button-mock';
    Object.assign(mainBtn.style, {
        position: 'fixed',
        bottom: '20px',
        left: '50%',
        transform: 'translateX(-50%)',
        width: '90%',
        maxWidth: '400px',
        padding: '16px',
        borderRadius: '16px',
        border: 'none',
        fontWeight: 'bold',
        fontSize: '16px',
        textTransform: 'uppercase',
        zIndex: 9999,
        display: 'none',
        cursor: 'pointer',
        boxShadow: '0 4px 20px rgba(0,0,0,0.5)'
    });
    mainBtn.onclick = () => {
        if (tg.MainButton.callback) tg.MainButton.callback();
    };
    document.body.appendChild(mainBtn);
}
// Run mock UI creation if not in iframe (or always for this demo page)
// Run mock UI creation if not in iframe (or always for this demo page)
createMockTgUi();

// --- LEVEL 100 LOADER LOGIC ---
window.addEventListener('load', () => {
    const loader = document.getElementById('loader');
    const consoleDiv = document.querySelector('.loader-console');

    // Simulate console logs
    const logs = [
        "> Establishing Secure Connection...",
        "> Verifying User Integrity Chain... [OK]",
        "> Loading Neural Maps... [OK]",
        "> Syncing Real-time Availability...",
        "> WELCOME TO DIGITAL ARENA"
    ];

    let delay = 0;
    logs.forEach((log, index) => {
        delay += (Math.random() * 500) + 200;
        setTimeout(() => {
            consoleDiv.innerHTML += `<div>${log}</div>`;
            consoleDiv.scrollTop = consoleDiv.scrollHeight;
        }, delay);
    });

    // Hide loader
    setTimeout(() => {
        loader.style.opacity = '0';
        loader.style.pointerEvents = 'none';
        setTimeout(() => {
            loader.style.display = 'none';
            // Trigger entry animations
            document.querySelectorAll('.hero-title, .hero-badge').forEach(el => {
                el.style.animation = 'none';
                el.offsetHeight; /* trigger reflow */
                el.style.animation = null;
            });
        }, 500);
    }, 2500);
});


// ==================== MOCK DATA ====================
const MOCK_CLUBS = [
    { id: 1, name: "CyberArena Pro", address: "Улица Амира Темура, 15", city: "Ташкент", venue_type: "computer_club" },
    { id: 2, name: "GameZone Elite", address: "Проспект Мирзо Улугбека, 7", city: "Ташкент", venue_type: "computer_club" },
    { id: 3, name: "Navoi Gaming", address: "Улица Навои, 22", city: "Навои", venue_type: "computer_club" }
];

const MOCK_COMPUTERS = [];
// Generate some computers
for (let i = 1; i <= 15; i++) {
    const zones = ['Standard', 'VIP', 'Bootcamp'];
    const zone = zones[Math.floor(Math.random() * zones.length)];
    let price = 15000;
    let gpu = "RTX 3060";
    if (zone === 'VIP') { price = 25000; gpu = "RTX 4070"; }
    if (zone === 'Bootcamp') { price = 20000; gpu = "RTX 3070"; }

    MOCK_COMPUTERS.push({
        id: i,
        name: `PC-${i.toString().padStart(2, '0')}`,
        zone: zone,
        status: "available",
        price_per_hour: price,
        cpu: "i5-12400F",
        gpu: gpu,
        ram_gb: 16,
        monitor_hz: 165,
        club_id: 1 // All in club 1 for demo simplicity
    });
}
// Add some for club 2
for (let i = 16; i <= 25; i++) {
    MOCK_COMPUTERS.push({
        id: i,
        name: `GZ-${(i - 15).toString().padStart(2, '0')}`,
        zone: 'Standard',
        status: "available",
        price_per_hour: 12000,
        club_id: 2
    });
}


let bookings = []; // Local storage of bookings

// ==================== APP LOGIC (Modified to use MOCK) ====================

// Debounce — предотвращает спам запросами при поиске
function debounce(func, delay = 300) {
    let timeoutId;
    return function (...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
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
    if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred(type === 'error' ? 'error' : 'success');

    // Auto remove
    setTimeout(() => {
        toast.style.animation = 'toastOut 0.3s forwards';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}


// --- MOCKED API CALLS ---

async function fetchClubs() {
    return new Promise(resolve => setTimeout(() => resolve(MOCK_CLUBS), 500));
}

async function fetchComputers(cId) {
    return new Promise(resolve => {
        setTimeout(() => {
            const pcs = MOCK_COMPUTERS.filter(pc => pc.club_id == cId);
            resolve(pcs);
        }, 500);
    });
}

async function fetchAvailability(cId, pcId, date) {
    return new Promise(resolve => {
        setTimeout(() => {
            // Mock random occupation
            const occupied = [];
            if (date === new Date().toISOString().split('T')[0]) {
                // Only mock simple occupation logic for demo
            }
            // Let's say 12:00 and 18:00 are always taken
            resolve({ occupied_hours: [12, 18] });
        }, 300);
    });
}

async function createBooking(payload) {
    return new Promise((resolve, reject) => {
        setTimeout(() => {
            const id = Math.floor(Math.random() * 10000);
            const booking = {
                id: id,
                ...payload,
                status: 'CONFIRMED',
                club_name: MOCK_CLUBS.find(c => c.id == payload.club_id).name,
                computer_name: MOCK_COMPUTERS.find(c => c.id == payload.computer_id).name,
                display_time: new Date(payload.start_time).toLocaleString()
            };
            bookings.push(booking);
            resolve({ success: true, booking_id: id });
        }, 1000);
    });
}

async function fetchMyBookings() {
    return new Promise(resolve => setTimeout(() => resolve(bookings), 500));
}


// Load club data
async function loadClubData() {
    try {
        // Show Skeletons initially
        if (!clubId) {
            showClubSkeletons();
        } else {
            showComputerSkeletons();
        }

        const clubs = await fetchClubs();

        // Check if clubId is present
        if (!clubId) {
            tg.BackButton.hide(); // Hide back button on list view
            renderClubSelection(clubs);
            return;
        }

        const club = clubs.find(c => c.id == clubId);

        if (club) {
            currentVenueType = club.venue_type || 'computer_club'; // Set global type

            document.getElementById('club-name').textContent = club.name;
            const addressEl = document.getElementById('club-address');
            if (addressEl) {
                addressEl.innerHTML = `
                ${club.city}, ${club.address} 
                <span class="change-club-link" onclick="goBackToClubs()">(Сменить)</span>
            `;
            }

            // Setup Telegram Back Button
            setupBackButton();
        }

        computers = await fetchComputers(clubId);

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

// --- renderClubSelection ---
function renderClubSelection(clubs) {
    const grid = document.getElementById('computer-grid');
    grid.innerHTML = '';
    grid.style.gridTemplateColumns = '1fr'; // List view
    document.getElementById('zones').style.display = 'none'; // Hide filters
    document.getElementById('club-name').textContent = "Выберите клуб";
    document.getElementById('club-address').innerHTML = `<a href="/" style="color:var(--primary);text-decoration:none">⬅ Вернуться на сайт</a>`;

    clubs.forEach(club => {
        const card = document.createElement('div');
        card.className = 'club-card';
        card.onclick = () => {
            const newUrl = new URL(window.location.href);
            newUrl.searchParams.set('club_id', club.id);
            window.location.href = newUrl.toString();
        };

        const typeIcon = club.venue_type === 'restaurant' ? '🍽️' : '🎮';

        card.innerHTML = `
            <div>
                <div class="club-title">${typeIcon} ${club.name}</div>
                <div class="club-location">${club.city}, ${club.address}</div>
            </div>
            <div class="club-action">➜</div>
        `;
        grid.appendChild(card);
    });
}

// --- buildZonesFilter ---
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
    if (tg.HapticFeedback) tg.HapticFeedback.selectionChanged();
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

    grid.innerHTML = ''; // Full redraw for simplicity in demo

    paginatedItems.forEach((computer, index) => {
        const computerId = String(computer.id);
        const card = document.createElement('div');
        card.className = 'computer-card available';
        card.dataset.computerId = computerId;
        card.onclick = () => selectComputer(computer);

        const isSelected = selectedComputer && selectedComputer.id === computer.id;
        card.classList.toggle('selected', isSelected);

        let statusText = "Свободен";
        card.innerHTML = `
            <div class="computer-name">${computer.name}</div>
            <div class="computer-status">${statusText}</div>
        `;
        grid.appendChild(card);
    });

    // Load More Button
    if (hasMore) {
        const loadMoreBtn = document.createElement('button');
        loadMoreBtn.className = 'load-more-btn';
        loadMoreBtn.textContent = `Загрузить еще (${filtered.length - itemsToShow} осталось)`;
        loadMoreBtn.onclick = () => {
            paginationState.currentPage++;
            renderComputers();
        };
        grid.appendChild(loadMoreBtn);
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
        const bgImages = {
            'VIP': 'https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=800&q=80',
            'Standard': 'https://images.unsplash.com/photo-1587202372775-e229f172b9d7?auto=format&fit=crop&w=800&q=80',
            'Bootcamp': 'https://images.unsplash.com/photo-1598550476439-6847785fcea6?auto=format&fit=crop&w=800&q=80'
        };
        imgEl.src = bgImages[computer.zone] || bgImages['Standard'];
    }

    // Update specs
    const specsContainer = document.querySelector('.specs');
    if (specsContainer) {
        specsContainer.innerHTML = `
            <div class="spec-item"><div class="spec-label">CPU</div><div class="spec-value">${computer.cpu || 'i5-12400'}</div></div>
            <div class="spec-item"><div class="spec-label">GPU</div><div class="spec-value">${computer.gpu || 'RTX 3060'}</div></div>
            <div class="spec-item"><div class="spec-label">RAM</div><div class="spec-value">${computer.ram_gb ? computer.ram_gb + ' GB' : '16 GB'}</div></div>
            <div class="spec-item"><div class="spec-label">Display</div><div class="spec-value">${computer.monitor_hz ? computer.monitor_hz + ' Hz' : '144 Hz'}</div></div>
        `;
    }

    // Configure Main Button
    tg.MainButton.setText(`ВЫБРАТЬ ${computer.name.toUpperCase()}`);
    tg.MainButton.show();
    tg.MainButton.enable();

    // IMPORTANT: Set OnClick handler
    tg.MainButton.offClick(openBookingModal); // Remove previous
    tg.MainButton.onClick(openBookingModal);

    if (tg.HapticFeedback) tg.HapticFeedback.impactOccurred('heavy');
}


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
    if (tg.HapticFeedback) tg.HapticFeedback.selectionChanged();
}

async function renderTimeGrid() {
    const grid = document.getElementById('time-grid');
    grid.innerHTML = '';

    const now = new Date();
    const isToday = bookingState.dayOffset === 0;
    const currentHour = now.getHours();

    // Calculate target date strings
    const targetDate = new Date();
    targetDate.setDate(targetDate.getDate() + bookingState.dayOffset);
    const dateStr = targetDate.toISOString().split('T')[0];

    // Show loading skeleton
    for (let h = 10; h < 24; h++) {
        const slot = document.createElement('button');
        slot.className = 'time-slot skeleton';
        slot.textContent = `${h}:00`;
        grid.appendChild(slot);
    }

    // Fetch occupied hours from MOCK API
    let occupiedHours = [];
    if (selectedComputer) {
        try {
            const data = await fetchAvailability(clubId, selectedComputer.id, dateStr);
            occupiedHours = data.occupied_hours || [];
        } catch (e) {
            console.warn('Failed to fetch availability:', e);
        }
    }

    // Re-render
    grid.innerHTML = '';
    for (let h = 10; h < 24; h++) {
        const slot = document.createElement('button');
        slot.className = 'time-slot';
        slot.textContent = `${h}:00`;

        let disabled = false;

        // Disable past hours
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
                if (tg.HapticFeedback) tg.HapticFeedback.selectionChanged();
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
    if (newDuration > 600) newDuration = 600;

    bookingState.durationMinutes = newDuration;

    // Format display
    const h = Math.floor(newDuration / 60);
    const m = newDuration % 60;
    let text = "";
    if (h > 0) text += `${h} ч `;
    if (m > 0) text += `${m} мин`;

    document.getElementById('duration-display').textContent = text;
    updatePrice();
    if (tg.HapticFeedback) tg.HapticFeedback.impactOccurred('light');
}

function updatePrice() {
    const hours = bookingState.durationMinutes / 60;
    let price;

    if (currentVenueType === 'restaurant') {
        price = selectedComputer.price_per_hour || 0;
    } else {
        price = selectedComputer.price_per_hour * hours;
    }

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
        const date = new Date();
        date.setDate(date.getDate() + bookingState.dayOffset);
        date.setHours(bookingState.selectedHour, 0, 0, 0);

        const payload = {
            user_id: 123456789,
            club_id: parseInt(clubId),
            computer_id: String(selectedComputer.id),
            start_time: date.toISOString(),
            duration_minutes: bookingState.durationMinutes
        };

        const result = await createBooking(payload);

        if (result.success) {
            showToast(`✅ Бронь #${result.booking_id} создана!`, 'success');
            closeBookingModal();
            unselectComputer();

            // Allow time to see toast
            if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
        } else {
            showToast('Ошибка бронирования', 'error');
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

    if (tg.close) tg.close();
}

// --- NEW: Tab Switching & Profile Logic ---

function switchTab(tabId, btn) {
    // 1. Activate Button
    document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    // 2. Show Content
    document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
    document.getElementById(`tab-${tabId}`).style.display = 'block';

    // 3. Specific Actions
    if (tabId === 'home') {
        tg.BackButton.isVisible ? tg.BackButton.show() : tg.BackButton.hide();
        // Check if we are in club view or list view
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('club_id')) {
            tg.BackButton.show();
        } else {
            tg.BackButton.hide();
        }
    } else {
        tg.BackButton.hide();
    }

    if (tabId === 'profile') {
        renderMockProfile();
    }

    // Level 100 Map Animation
    if (tabId === 'map') {
        startMapAnimation();
    } else {
        stopMapAnimation();
    }

    if (tg.HapticFeedback) tg.HapticFeedback.selectionChanged();
}

let mapInterval;
function startMapAnimation() {
    const pins = document.querySelectorAll('.map-pin');
    // Clear existing
    if (mapInterval) clearInterval(mapInterval);

    // Animate every 2 seconds
    mapInterval = setInterval(() => {
        pins.forEach(pin => {
            // Random small movement
            const currentTop = parseFloat(pin.style.top) || 50;
            const currentLeft = parseFloat(pin.style.left) || 50;

            const newTop = currentTop + (Math.random() * 10 - 5);
            const newLeft = currentLeft + (Math.random() * 10 - 5);

            // Clamp
            const clampedTop = Math.max(10, Math.min(90, newTop));
            const clampedLeft = Math.max(10, Math.min(90, newLeft));

            pin.style.transition = 'all 2s ease-in-out';
            pin.style.top = `${clampedTop}%`;
            pin.style.left = `${clampedLeft}%`;
        });
    }, 2000);
}

function stopMapAnimation() {
    if (mapInterval) clearInterval(mapInterval);
}

async function renderMockProfile() {
    const list = document.getElementById('mock-bookings-list');
    list.innerHTML = `<div class="empty-state-small">Загрузка...</div>`;

    // Fetch mock bookings
    const myBookings = await fetchMyBookings();

    list.innerHTML = '';
    if (myBookings.length === 0) {
        list.innerHTML = `<div class="empty-state-small">Нет активных броней</div>`;
        return;
    }

    myBookings.forEach(b => {
        const div = document.createElement('div');
        div.className = 'booking-card';
        // Add basic styles
        div.style.background = 'rgba(255,255,255,0.05)';
        div.style.padding = '12px';
        div.style.marginBottom = '8px';
        div.style.borderRadius = '12px';

        div.innerHTML = `
            <div>
                <div style="font-weight:600; font-size:14px; color:#fff">${b.club_name}</div>
                <div style="font-size:12px; color:rgba(255,255,255,0.6)">${b.computer_name} | ${b.display_time}</div>
            </div>
            <div class="status-badge ${b.status.toLowerCase()}" style="font-size:10px; padding:4px 8px; border-radius:8px; background:rgba(0,255,157,0.1); color:#00ff9d">${b.status}</div>
        `;
        list.appendChild(div);
    });
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

// --- New Feature: My Bookings ---

async function openMyBookings() {
    const modal = document.getElementById('my-bookings-modal');
    const list = document.getElementById('my-bookings-list');
    modal.style.display = 'flex';

    list.innerHTML = `<div class="empty-state-small">Загрузка...</div>`;

    try {
        const bookings = await fetchMyBookings();
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
        // Add basic styles for this card inline or rely on existing CSS
        div.style.background = 'rgba(255,255,255,0.05)';
        div.style.padding = '12px';
        div.style.marginBottom = '8px';
        div.style.borderRadius = '12px';

        div.innerHTML = `
            <div class="booking-info">
                <h4 style="margin-bottom:4px">${b.club_name}</h4>
                <p style="font-size:12px;opacity:0.7">🖥️ ${b.computer_name}</p>
                <p style="font-size:12px;opacity:0.7">🕒 ${b.display_time}</p>
            </div>
            <div class="booking-actions" style="margin-top:8px;display:flex;justify-content:space-between;align-items:center">
                <span class="status-badge" style="color:var(--success);font-size:12px;border:1px solid var(--success);padding:2px 8px;border-radius:10px">${b.status}</span>
            </div>
        `;
        list.appendChild(div);
    });
}


// Start App
loadClubData();
