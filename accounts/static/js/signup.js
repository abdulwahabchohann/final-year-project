// Wait for DOM to load
document.addEventListener('DOMContentLoaded', function() {
    
    // Search Form Handler
    const searchForm = document.getElementById('search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const searchInput = document.getElementById('search-input');
            const query = searchInput.value.trim();
            
            if (query) {
                alert('Search functionality coming soon! You searched for: ' + query);
                // Later we'll implement actual search
            }
        });
    }

    // Book Carousel Functionality
    const carouselControls = document.querySelectorAll('.prev-btn, .next-btn');
    carouselControls.forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const carousel = document.getElementById(targetId);
            const scrollAmount = 300;
            
            if (this.classList.contains('next-btn')) {
                carousel.scrollBy({ left: scrollAmount, behavior: 'smooth' });
            } else {
                carousel.scrollBy({ left: -scrollAmount, behavior: 'smooth' });
            }
        });
    });

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href !== '#') {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            }
        });
    });

    // Auto-hide messages after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.5s';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });
});

// Password Toggle Function
function togglePassword(fieldId) {
    const field = document.getElementById(fieldId);
    const icon = field.nextElementSibling;
    
    if (field.type === "password") {
        field.type = "text";
        icon.classList.remove("fa-eye");
        icon.classList.add("fa-eye-slash");
    } else {
        field.type = "password";
        icon.classList.remove("fa-eye-slash");
        icon.classList.add("fa-eye");
    }
}