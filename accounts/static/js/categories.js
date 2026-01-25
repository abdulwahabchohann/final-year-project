// Minimal JS (sirf accessibility / future use)
(function () {
    const cards = document.querySelectorAll('.category-card');
    if (!cards.length) return;

    cards.forEach(card => {
        card.setAttribute('tabindex', '0');
        card.addEventListener('keydown', e => {
            if (e.key === 'Enter') {
                card.click();
            }
        });
    });
})();
