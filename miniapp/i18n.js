// ==================== i18n Internationalization ====================
// Supports: Russian (ru), Uzbek (uz), English (en)
// Usage: t('key')  → returns translated string
//        setLanguage('uz') → switch language + re-render UI

const TRANSLATIONS = {
    ru: {
        // General
        loading: 'Загрузка...',
        error_server: 'Ошибка сервера. Попробуйте ещё раз.',
        error_no_internet: 'Нет соединения с сервером. Проверьте интернет.',
        error_server_starting: 'Сервер просыпается. Подождите 30 секунд и попробуйте снова.',

        // Auth Screen
        auth_title: 'Войти в приложение',
        auth_subtitle: 'Введите номер телефона и код из бота',
        auth_phone_placeholder: '+998901234567',
        auth_code_placeholder: 'Код из бота (6 цифр)',
        auth_btn: '🔐 Войти',
        auth_no_code: 'Нет кода? Нажмите',
        auth_bot_btn: '«📱 Приложение»',
        auth_in_bot: 'в боте.',
        auth_ios_hint: 'Для iOS: нажмите «Поделиться» ➡️ «На экран Домой»',
        auth_install_btn: '📥 Установить Приложение',
        auth_error_fields: 'Введите номер телефона и код (6 цифр)',
        auth_checking: '⏳ Проверяем...',
        auth_wrong_code: 'Неверный код',

        // Nav
        nav_clubs: 'Клубы',
        nav_bookings: 'Брони',
        nav_profile: 'Профиль',
        nav_info: 'Инфо',

        // Clubs / Booking
        select_club: 'Выберите клуб',
        available_clubs: 'Список доступных мест',
        change_club: '(Сменить)',
        booking_title: 'Бронирование',
        today: 'Сегодня',
        tomorrow: 'Завтра',
        start_time: 'Время начала',
        duration: 'Длительность',
        total: 'Итого:',
        book_btn: 'ЗАБРОНИРОВАТЬ',
        select_time_btn: 'ВЫБЕРИТЕ ВРЕМЯ',
        no_computers: 'нет свободных мест',
        free: 'Свободен',
        occupied_label: 'Занято',
        load_more: 'Загрузить еще',

        // Bookings Tab
        my_bookings: '📅 Мои Брони',
        no_bookings: 'Нет активных броней',
        cancel_booking: 'Отменить',
        show_qr: 'Показать QR',

        // Profile
        profile_title: '👤 Профиль',
        your_name: 'Имя',
        your_phone: 'Телефон',
        your_id: 'Telegram ID',
        logout: '🚪 Выйти',
        language_label: 'Язык / Language / Til',

        // Info Tab
        info_title: 'ℹ️ О нас',
        info_who_title: 'Кто мы?',
        info_who_text: 'Digital Arena — современная платформа для онлайн-бронирования мест в компьютерных клубах Узбекистана. Мы соединяем геймеров с лучшими клубами, делая процесс удобным и мгновенным.',
        info_contact_title: '📞 Контакты',
        info_phone: '+998 50 747 49 34',
        info_telegram: 'Телеграм-бот: @ArenaSlot_bot',
        info_how_title: '🎬 Как бронировать?',
        info_how_text: 'Посмотрите короткое видео ниже, чтобы узнать, как выбрать клуб, компьютер и забронировать время за 1 минуту.',
        info_version: 'Версия приложения: 1.0',

        // QR Modal
        your_code: 'Ваш код',
        show_code: 'Покажите код администратору',

        // Payment
        pay_title: '💳 Оплата',
        pay_amount: 'Сумма к оплате',
        pay_btn: '💳 Оплатить',
        pay_test_label: '🧪 Тестовый режим — реальные деньги не списываются',
        pay_success: '✅ Оплата прошла успешно!',
        pay_pending: '⏳ Ожидает оплаты',
        pay_failed: '❌ Ошибка оплаты',
        pay_currency: 'сум',
    },

    uz: {
        loading: 'Yuklanmoqda...',
        error_server: 'Server xatosi. Qaytadan urinib ko\'ring.',
        error_no_internet: 'Serverga ulanib bo\'lmadi. Internetni tekshiring.',
        error_server_starting: 'Server yoqilmoqda. 30 soniya kuting va qaytadan urinib ko\'ring.',

        auth_title: 'Ilovaga kirish',
        auth_subtitle: 'Telefon raqamingiz va botdan olgan kodni kiriting',
        auth_phone_placeholder: '+998901234567',
        auth_code_placeholder: 'Botdan kelgan kod (6 raqam)',
        auth_btn: '🔐 Kirish',
        auth_no_code: 'Kod yo\'qmi? Botda',
        auth_bot_btn: '«📱 Ilova»',
        auth_in_bot: 'tugmasini bosing.',
        auth_ios_hint: 'iOS uchun: «Ulashish» ➡️ «Bosh ekranga qo\'shish» ni bosing',
        auth_install_btn: '📥 Ilovani o\'rnatish',
        auth_error_fields: 'Telefon raqam va 6 xonali kodni kiriting',
        auth_checking: '⏳ Tekshirilmoqda...',
        auth_wrong_code: 'Noto\'g\'ri kod',

        nav_clubs: 'Klublar',
        nav_bookings: 'Bronlar',
        nav_profile: 'Profil',
        nav_info: 'Ma\'lumot',

        select_club: 'Klub tanlang',
        available_clubs: 'Mavjud joylar ro\'yxati',
        change_club: '(O\'zgartirish)',
        booking_title: 'Bron qilish',
        today: 'Bugun',
        tomorrow: 'Ertaga',
        start_time: 'Boshlanish vaqti',
        duration: 'Davomiyligi',
        total: 'Jami:',
        book_btn: 'BRON QILISH',
        select_time_btn: 'VAQT TANLANG',
        no_computers: 'bo\'sh joy yo\'q',
        free: 'Bo\'sh',
        occupied_label: 'Band',
        load_more: 'Ko\'proq yuklash',

        my_bookings: '📅 Bronlarim',
        no_bookings: 'Faol bronlar yo\'q',
        cancel_booking: 'Bekor qilish',
        show_qr: 'QR ko\'rsatish',

        profile_title: '👤 Profil',
        your_name: 'Ism',
        your_phone: 'Telefon',
        your_id: 'Telegram ID',
        logout: '🚪 Chiqish',
        language_label: 'Язык / Language / Til',

        info_title: 'ℹ️ Biz haqimizda',
        info_who_title: 'Biz kimiz?',
        info_who_text: 'Digital Arena — O\'zbekistondagi kompyuter klublarda o\'rinlarni onlayn bron qilish uchun zamonaviy platforma. Biz geymerlarni eng yaxshi klublar bilan bog\'laymiz, bu jarayonni qulay va tezkor qilamiz.',
        info_contact_title: '📞 Aloqa',
        info_phone: '+998 50 747 49 34',
        info_telegram: 'Telegram-bot: @ArenaSlot_bot',
        info_how_title: '🎬 Qanday bron qilish mumkin?',
        info_how_text: 'Klub, kompyuter tanlash va 1 daqiqada bron qilishni qanday qilishni bilish uchun quyidagi qisqa videoni tomosha qiling.',
        info_version: 'Ilova versiyasi: 1.0',

        your_code: 'Sizning kodingiz',
        show_code: 'Kodni administratorga ko\'rsating',

        pay_title: '💳 To\'lov',
        pay_amount: 'To\'lov summasi',
        pay_btn: '💳 To\'lash',
        pay_test_label: '🧪 Test rejimi — haqiqiy pul yechilmaydi',
        pay_success: '✅ To\'lov muvaffaqiyatli o\'tdi!',
        pay_pending: '⏳ To\'lov kutilmoqda',
        pay_failed: '❌ To\'lov xatosi',
        pay_currency: 'so\'m',
    },

    en: {
        loading: 'Loading...',
        error_server: 'Server error. Please try again.',
        error_no_internet: 'No connection to server. Please check your internet.',
        error_server_starting: 'Server is starting up. Please wait 30 seconds and try again.',

        auth_title: 'Sign in to the app',
        auth_subtitle: 'Enter your phone number and code from the bot',
        auth_phone_placeholder: '+998901234567',
        auth_code_placeholder: 'Code from bot (6 digits)',
        auth_btn: '🔐 Sign In',
        auth_no_code: 'No code? Press',
        auth_bot_btn: '«📱 App»',
        auth_in_bot: 'in the bot.',
        auth_ios_hint: 'For iOS: tap «Share» ➡️ «Add to Home Screen»',
        auth_install_btn: '📥 Install App',
        auth_error_fields: 'Enter phone number and 6-digit code',
        auth_checking: '⏳ Verifying...',
        auth_wrong_code: 'Invalid code',

        nav_clubs: 'Clubs',
        nav_bookings: 'Bookings',
        nav_profile: 'Profile',
        nav_info: 'Info',

        select_club: 'Select a Club',
        available_clubs: 'List of available venues',
        change_club: '(Change)',
        booking_title: 'Book a Seat',
        today: 'Today',
        tomorrow: 'Tomorrow',
        start_time: 'Start time',
        duration: 'Duration',
        total: 'Total:',
        book_btn: 'BOOK NOW',
        select_time_btn: 'SELECT A TIME',
        no_computers: 'no available seats',
        free: 'Available',
        occupied_label: 'Occupied',
        load_more: 'Load more',

        my_bookings: '📅 My Bookings',
        no_bookings: 'No active bookings',
        cancel_booking: 'Cancel',
        show_qr: 'Show QR',

        profile_title: '👤 Profile',
        your_name: 'Name',
        your_phone: 'Phone',
        your_id: 'Telegram ID',
        logout: '🚪 Sign Out',
        language_label: 'Язык / Language / Til',

        info_title: 'ℹ️ About Us',
        info_who_title: 'Who are we?',
        info_who_text: 'Digital Arena is a modern platform for online booking of seats in computer clubs across Uzbekistan. We connect gamers with the best clubs, making the process convenient and instant.',
        info_contact_title: '📞 Contact',
        info_phone: '+998 50 747 49 34',
        info_telegram: 'Telegram bot: @ArenaSlot_bot',
        info_how_title: '🎬 How to book?',
        info_how_text: 'Watch the short video below to learn how to select a club, computer, and book a time slot in 1 minute.',
        info_version: 'App version: 1.0',

        your_code: 'Your code',
        show_code: 'Show this code to the administrator',

        pay_title: '💳 Payment',
        pay_amount: 'Amount to pay',
        pay_btn: '💳 Pay',
        pay_test_label: '🧪 Test mode — no real money charged',
        pay_success: '✅ Payment successful!',
        pay_pending: '⏳ Awaiting payment',
        pay_failed: '❌ Payment failed',
        pay_currency: 'UZS',
    }
};

// ---- Core i18n engine ----

let _currentLang = localStorage.getItem('da_lang') || 'ru';

/** Translate a key to the current language */
function t(key) {
    const dict = TRANSLATIONS[_currentLang] || TRANSLATIONS['ru'];
    return dict[key] || TRANSLATIONS['ru'][key] || key;
}

/** Switch language and persist choice */
function setLanguage(lang) {
    if (!TRANSLATIONS[lang]) return;
    _currentLang = lang;
    localStorage.setItem('da_lang', lang);
    applyTranslations();
    // Update active state on language buttons
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.lang === lang);
    });
}

/** Walk all [data-i18n] elements and update their text */
function applyTranslations() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        const val = t(key);
        if (el.tagName === 'INPUT') {
            el.placeholder = val;
        } else {
            el.textContent = val;
        }
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        el.placeholder = t(el.getAttribute('data-i18n-placeholder'));
    });
}

// Apply on load
applyTranslations();
