// recommendation.js
document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form[method="post"]');
    const errorMessage = document.querySelector('.error-message');
    const resultsSection = document.querySelector('.results-section');
    const emptyState = document.querySelector('.empty-state');
    const moodInput = document.getElementById('mood-input');
    const loadingIndicator = document.getElementById('sentiment-loading');

    /* Mood chips ƒ?" keyboard accessible */
    document.querySelectorAll('.mood-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const moodText = chip.dataset.mood || chip.textContent.trim();
            if (moodInput && moodText) {
                moodInput.value = moodText;
                moodInput.dispatchEvent(new Event('input', { bubbles: true }));
                moodInput.focus();
            }
        });
    });

    // Scroll to results or error after render
    if (errorMessage || resultsSection) {
        setTimeout(function() {
            const target = errorMessage || resultsSection || emptyState;
            if (!target) return;

            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            target.style.transition = 'box-shadow 0.3s ease';
            target.style.boxShadow = '0 0 20px rgba(108, 99, 255, 0.3)';
            setTimeout(function() {
                target.style.boxShadow = '';
            }, 2000);
        }, 100);
    }

    // Disable submit button on submit
    if (form) {
        form.addEventListener('submit', function() {
            if (loadingIndicator) {
                loadingIndicator.style.display = 'block';
            }
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = 'ƒ?3 Processing...';
            }
        });
    }

    if (loadingIndicator) {
        loadingIndicator.style.display = 'none';
    }
});
