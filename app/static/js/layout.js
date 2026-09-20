// ============================================================
// LAYOUT - Sidebar responsive con mejoras móviles
// ============================================================

(function () {
    'use strict';

    const DEBUG = false;                      // true solo en desarrollo
    const MOBILE_BREAKPOINT = 992;            // debe coincidir con CSS
    const mobileQuery = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT}px)`);

    const log = (...args) => DEBUG && console.log('[layout.js]', ...args);
    const warn = (...args) => DEBUG && console.warn('[layout.js]', ...args);

    document.addEventListener('DOMContentLoaded', function () {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebar-overlay');
        const toggle  = document.getElementById('sidebar-toggle');

        if (!sidebar) {
            warn('No se encontró el sidebar');
            return;
        }
        if (!toggle) {
            warn('No se encontró el botón de toggle');
            return;
        }

        log('Inicializado');

        function openSidebar() {
            sidebar.classList.add('open');
            if (overlay) overlay.classList.add('show');
            document.body.classList.add('sidebar-open');
            toggle.setAttribute('aria-expanded', 'true');
            toggle.setAttribute('aria-label', 'Cerrar menú');
        }

        function closeSidebar() {
            sidebar.classList.remove('open');
            if (overlay) overlay.classList.remove('show');
            document.body.classList.remove('sidebar-open');
            toggle.setAttribute('aria-expanded', 'false');
            toggle.setAttribute('aria-label', 'Abrir menú');
        }

        function toggleSidebar() {
            sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
        }

        // Botón hamburguesa
        toggle.addEventListener('click', function (e) {
            e.preventDefault();
            toggleSidebar();
        });

        // Overlay
        if (overlay) {
            overlay.addEventListener('click', closeSidebar);
        }

        // Cerrar al hacer clic en un enlace (solo móvil)
        sidebar.querySelectorAll('.nav-link').forEach(function (link) {
            link.addEventListener('click', function () {
                if (mobileQuery.matches) closeSidebar();
            });
        });

        // Tecla Escape
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && sidebar.classList.contains('open')) {
                closeSidebar();
            }
        });

        // Cerrar al entrar en vista de escritorio
        mobileQuery.addEventListener('change', function (e) {
            if (!e.matches && sidebar.classList.contains('open')) {
                closeSidebar();
            }
        });

        // Resaltar el enlace activo
        const currentPath = window.location.pathname;
        sidebar.querySelectorAll('.nav-link').forEach(function (link) {
            const href = link.getAttribute('href');
            if (isActiveLink(href, currentPath)) {
                link.classList.add('active');
            }
        });
    });

    // ---------------------------------------------------------
    // Detecta si `href` corresponde a la ruta actual.
    // Evita falsos positivos como /schedule vs /schedule-archive.
    // ---------------------------------------------------------
    function isActiveLink(href, currentPath) {
        if (!href || href === '#') return false;
        if (href.startsWith('http') || href.startsWith('mailto:')) return false;

        if (href === '/') return currentPath === '/';

        const cleanHref = href.replace(/\/$/, '');
        const cleanPath = currentPath.replace(/\/$/, '');

        return cleanPath === cleanHref
            || cleanPath.startsWith(cleanHref + '/')
            || cleanPath.startsWith(cleanHref + '?');
    }
})();