// ============================================================
// LAYOUT - Control del sidebar en móvil
// ============================================================
document.addEventListener('DOMContentLoaded', function () {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    const toggle = document.getElementById('sidebar-toggle');

    if (!sidebar || !toggle) return;

    function openSidebar() {
        sidebar.classList.add('open');
        if (overlay) overlay.classList.add('show');
    }

    function closeSidebar() {
        sidebar.classList.remove('open');
        if (overlay) overlay.classList.remove('show');
    }

    toggle.addEventListener('click', function () {
        if (sidebar.classList.contains('open')) {
            closeSidebar();
        } else {
            openSidebar();
        }
    });

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

    // Resaltar enlace activo según la URL actual
    const currentPath = window.location.pathname;
    sidebar.querySelectorAll('.nav-link').forEach(function (link) {
        const href = link.getAttribute('href');
        if (!href || href === '#') return;
        // Ignorar enlaces externos o anclas
        if (href.startsWith('http') || href.startsWith('#')) return;
        if (href === '/' ? currentPath === '/' : currentPath.startsWith(href)) {
            link.classList.add('active');
        }
    });
});