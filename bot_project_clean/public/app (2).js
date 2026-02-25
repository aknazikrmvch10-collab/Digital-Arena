// ArenaSlot Landing Page - Animations & Interactivity

document.addEventListener('DOMContentLoaded', () => {
    // Animate stats numbers on scroll
    const statNumbers = document.querySelectorAll('.stat-number');

    const animateNumber = (el) => {
        const target = parseInt(el.dataset.target);
        const duration = 1500;
        const start = performance.now();

        const update = (now) => {
            const elapsed = now - start;
            const progress = Math.min(elapsed / duration, 1);
            // Ease out cubic
            const eased = 1 - Math.pow(1 - progress, 3);
            const current = Math.round(target * eased);
            el.textContent = current;

            if (progress < 1) {
                requestAnimationFrame(update);
            } else {
                // Add "+" suffix for some numbers
                if (target >= 5 && target < 100) {
                    el.textContent = target + '+';
                }
            }
        };

        requestAnimationFrame(update);
    };

    // Intersection Observer for scroll animations
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');

                // If it's a stat number, animate it
                if (entry.target.classList.contains('stat-number')) {
                    animateNumber(entry.target);
                }

                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.2 });

    // Observe elements
    statNumbers.forEach(el => observer.observe(el));

    document.querySelectorAll('.feature-card, .step-card, .benefit-item, .stat-card').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
        observer.observe(el);
    });

    // Add animate-in class styles
    const style = document.createElement('style');
    style.textContent = `.animate-in { opacity: 1 !important; transform: translateY(0) !important; }`;
    document.head.appendChild(style);

    // Stagger animation for grid items
    document.querySelectorAll('.features-grid, .steps-grid, .stats-grid, .benefits-grid').forEach(grid => {
        const gridObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const items = entry.target.children;
                    Array.from(items).forEach((item, i) => {
                        item.style.transitionDelay = `${i * 0.1}s`;
                        setTimeout(() => item.classList.add('animate-in'), 50);
                    });
                    gridObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1 });
        gridObserver.observe(grid);
    });

    // Smooth navbar background on scroll
    const navbar = document.querySelector('.navbar');
    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            navbar.style.background = 'rgba(5,5,16,0.95)';
        } else {
            navbar.style.background = 'rgba(5,5,16,0.8)';
        }
    });
});
