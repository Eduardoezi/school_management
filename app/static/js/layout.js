// ============================================================
// LAYOUT - Sidebar responsive con mejoras móviles
// ============================================================
document.addEventListener('DOMContentLoaded', function () {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    const toggle = document.getElementById('sidebar-toggle');

    if (!sidebar) {
        console.warn('[layout.js] No se encontró el sidebar');
        return;
    }

    if (!toggle) {
        console.warn('[layout.js] No se encontró el botón de toggle');
        return;
    }

    console.log('[layout.js] Inicializado correctamente');

    function openSidebar() {
        sidebar.classList.add('open');
        if (overlay) overlay.classList.add('show');
        document.body.style.overflow = 'hidden';  // Bloquear scroll del fondo
    }

    function closeSidebar() {
        sidebar.classList.remove('open');
        if (overlay) overlay.classList.remove('show');
        document.body.style.overflow = '';         // Restaurar scroll
    }

    function toggleSidebar() {
        if (sidebar.classList.contains('open')) {
            closeSidebar();
        } else {
            openSidebar();
        }
    }

    // Click en el botón hamburguesa
    toggle.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        toggleSidebar();
    });

    // Click en el overlay
    if (overlay) {
        overlay.addEventListener('click', closeSidebar);
    }

    // Cerrar al hacer clic en un enlace (para móvil)
    sidebar.querySelectorAll('.nav-link').forEach(function (link) {
        link.addEventListener('click', function () {
            if (window.innerWidth <= 992) {
                closeSidebar();
            }
        });
    });

    // Cerrar con la tecla Escape
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && sidebar.classList.contains('open')) {
            closeSidebar();
        }
    });

    // Cerrar al cambiar de tamaño a escritorio
    window.addEventListener('resize', function () {
        if (window.innerWidth > 992 && sidebar.classList.contains('open')) {
            closeSidebar();
        }
    });

    // Resaltar enlace activo según la URL actual
    const currentPath = window.location.pathname;
    sidebar.querySelectorAll('.nav-link').forEach(function (link) {
        const href = link.getAttribute('href');
        if (!href || href === '#') return;
        if (href.startsWith('http') || href.startsWith('#')) return;
        if (href === '/' ? currentPath === '/' : currentPath.startsWith(href)) {
            link.classList.add('active');
        }
    });
});