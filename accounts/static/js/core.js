// core.js – shared site behavior
document.addEventListener('DOMContentLoaded', function() {
    /* ===== Search form ===== */
    const searchForm = document.getElementById('search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            const searchInput = document.getElementById('search-input');
            const query = searchInput ? searchInput.value.trim() : '';

            // Only block submit if empty
            if (!query) {
                e.preventDefault();
                alert('Please enter a search term');
            }
        });
    }

    /* ===== Book carousel controls (used on home & trend) ===== */
    const carouselControls = document.querySelectorAll('.prev-btn, .next-btn');
    carouselControls.forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            if (!targetId) return;

            const carousel = document.getElementById(targetId);
            if (!carousel) return;

            const scrollAmount = 300;
            const direction = this.classList.contains('next-btn') ? 1 : -1;

            carousel.scrollBy({
                left: scrollAmount * direction,
                behavior: 'smooth'
            });
        });
    });

    /* ===== Smooth scrolling for in-page anchors ===== */
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href === '#') return;
            const target = document.querySelector(href);
            if (!target) return;

            e.preventDefault();
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    });

    /* ===== Auto-hide alerts ===== */
    document.querySelectorAll('.alert').forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.5s';
            alert.style.opacity = '0';
            setTimeout(() => {
                if (alert.parentNode) {
                    alert.remove();
                }
            }, 500);
        }, 5000);
    });

    /* ===== Close buttons (no inline onclick) ===== */
    document.querySelectorAll('.close-alert').forEach(btn => {
        btn.addEventListener('click', () => {
            const parent = btn.parentElement;
            if (parent) parent.remove();
        });
    });

    /* ===== Simple required-field validation (opt-in) ===== */
    const forms = document.querySelectorAll('form[data-validate="true"]');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;

            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('error');
                } else {
                    field.classList.remove('error');
                }
            });

            if (!isValid) {
                e.preventDefault();
                alert('Please fill in all required fields');
            }
        });
    });

    /* ===== Password visibility toggle ===== */
    window.togglePasswordVisibility = function(fieldId, iconId) {
        const field = document.getElementById(fieldId);
        if (!field) return;
        const icon = iconId ? document.getElementById(iconId) : null;

        if (field.type === 'password') {
            field.type = 'text';
            if (icon) {
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            }
        } else {
            field.type = 'password';
            if (icon) {
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        }
    };
});
