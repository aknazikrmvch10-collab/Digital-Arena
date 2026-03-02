// Digital Arena PWA — Service Worker
// Версия: v1. Увеличьте номер версии при каждом обновлении контента.
const CACHE_NAME = 'digital-arena-v1';

// Файлы, которые кешируем для работы офлайн
const STATIC_ASSETS = [
    '/miniapp/index.html',
    '/miniapp/app.js',
    '/miniapp/icon-192.png',
    '/miniapp/icon-512.png',
    '/miniapp/manifest.json'
];

// ===================== УСТАНОВКА =====================
// При установке кешируем все статические файлы
self.addEventListener('install', event => {
    console.log('[SW] Installing v1...');
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(STATIC_ASSETS))
            .then(() => {
                console.log('[SW] Installed! Skipping wait...');
                return self.skipWaiting(); // Активируем новый SW сразу
            })
    );
});

// ===================== АКТИВАЦИЯ =====================
// При активации удаляем устаревшие кеши
self.addEventListener('activate', event => {
    console.log('[SW] Activating...');
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys
                    .filter(key => key !== CACHE_NAME)
                    .map(key => {
                        console.log('[SW] Deleting old cache:', key);
                        return caches.delete(key);
                    })
            )
        ).then(() => self.clients.claim()) // Берём контроль над всеми вкладками
    );
});

// ===================== ЗАПРОСЫ =====================
// Стратегия: Network First для API, Cache First для статики
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // API запросы — всегда через сеть (real-time данные)
    if (url.pathname.startsWith('/api/') || url.hostname.includes('onrender.com')) {
        event.respondWith(
            fetch(event.request)
                .catch(() => new Response(
                    JSON.stringify({ error: 'No internet connection' }),
                    { headers: { 'Content-Type': 'application/json' } }
                ))
        );
        return;
    }

    // Статические файлы — Cache First, потом сеть
    event.respondWith(
        caches.match(event.request)
            .then(cached => {
                if (cached) {
                    // Фоновое обновление кеша
                    fetch(event.request).then(response => {
                        if (response && response.status === 200) {
                            caches.open(CACHE_NAME).then(cache => cache.put(event.request, response.clone()));
                        }
                    }).catch(() => { });
                    return cached;
                }
                return fetch(event.request);
            })
    );
});

// ===================== PUSH УВЕДОМЛЕНИЯ =====================
self.addEventListener('push', event => {
    if (!event.data) return;

    const data = event.data.json();
    const options = {
        body: data.body || 'У вас новое сообщение',
        icon: '/miniapp/icon-192.png',
        badge: '/miniapp/icon-192.png',
        vibrate: [100, 50, 100],
        data: { url: data.url || '/miniapp/index.html' },
        actions: [
            { action: 'open', title: '📋 Открыть' },
            { action: 'close', title: '✕ Закрыть' }
        ]
    };

    event.waitUntil(
        self.registration.showNotification(data.title || 'Digital Arena', options)
    );
});

// Клик по уведомлению — открываем нужную страницу
self.addEventListener('notificationclick', event => {
    event.notification.close();
    const targetUrl = event.notification.data?.url || '/miniapp/index.html';

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then(clientList => {
                // Если уже открыт — фокус на него
                for (const client of clientList) {
                    if (client.url.includes('miniapp') && 'focus' in client) {
                        return client.focus();
                    }
                }
                // Иначе открываем новую вкладку
                if (clients.openWindow) {
                    return clients.openWindow(targetUrl);
                }
            })
    );
});
