// Service Worker para notificaciones push en background - ExpressATM

self.addEventListener('install', (event) => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(self.clients.claim());
});

// Escuchar mensajes desde la página principal para mostrar notificaciones
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SHOW_NOTIFICATION') {
        const { title, body, tag, icon } = event.data;
        self.registration.showNotification(title, {
            body: body || '',
            icon: icon || '/logos/expressatm-icon.svg',
            badge: '/logos/expressatm-icon.svg',
            tag: tag || 'expressatm-notification',
            renotify: true,
            requireInteraction: false
        });
    }
});

// Al hacer clic en la notificación, enfocar la ventana
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    event.waitUntil(
        self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
            for (const client of clientList) {
                if (client.url.includes('/') && 'focus' in client) {
                    return client.focus();
                }
            }
            if (self.clients.openWindow) {
                return self.clients.openWindow('/');
            }
        })
    );
});
