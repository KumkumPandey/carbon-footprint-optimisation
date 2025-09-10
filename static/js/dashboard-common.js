// Common Dashboard JavaScript Functions

// Dark mode toggle
function toggleDarkMode() {
    document.body.classList.toggle('dark-mode');
    const isDark = document.body.classList.contains('dark-mode');
    const toggle = document.querySelector('.dark-mode-toggle');
    if (toggle) {
        toggle.innerHTML = isDark ? '<span>☀️</span> Light' : '<span>🌙</span> Dark';
    }
    localStorage.setItem('darkMode', isDark);
}

// Load dark mode preference
if (localStorage.getItem('darkMode') === 'true') {
    document.body.classList.add('dark-mode');
    const toggle = document.querySelector('.dark-mode-toggle');
    if (toggle) {
        toggle.innerHTML = '<span>☀️</span> Light';
    }
}

// Toggle mobile sidebar
function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    sidebar.classList.toggle('mobile-open');
}

// Close sidebar when clicking outside on mobile
document.addEventListener('click', function(event) {
    const sidebar = document.querySelector('.sidebar');
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    
    if (window.innerWidth <= 768 && 
        !sidebar.contains(event.target) && 
        !mobileMenuBtn.contains(event.target) &&
        sidebar.classList.contains('mobile-open')) {
        sidebar.classList.remove('mobile-open');
    }
});

// Handle window resize
window.addEventListener('resize', function() {
    const sidebar = document.querySelector('.sidebar');
    if (window.innerWidth > 768) {
        sidebar.classList.remove('mobile-open');
    }
});

// Dropdown functionality
document.addEventListener('DOMContentLoaded', function() {
    const dropdownBtn = document.querySelector('.dropbtn');
    if (dropdownBtn) {
        dropdownBtn.addEventListener('click', function(e) {
            e.preventDefault();
            const dropdown = this.parentElement;
            dropdown.classList.toggle('active');
        });
    }
});