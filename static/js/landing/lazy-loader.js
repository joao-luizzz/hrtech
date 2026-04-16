// Lazy loading for below-fold sections
// Uses Intersection Observer to defer animations and graph initialization

export function initializeLazyLoading() {
  const observerOptions = {
    threshold: 0.1,
    rootMargin: '50px'
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const section = entry.target;

        // Start fade-in animation
        section.classList.add('visible');

        // Initialize section-specific graphs/animations
        if (section.id === 'how-it-works') {
          // Dynamically import and initialize how-it-works graph
          import('./graph-visualization.js').then(mod => {
            mod.initializeHowItWorksGraph();
          }).catch(err => {
            console.warn('How-it-works graph failed to load:', err);
          });
        }

        // Unobserve after animation completes (match transition duration ~600ms)
        setTimeout(() => {
          observer.unobserve(section);
        }, 600);
      }
    });
  }, observerOptions);

  // Observe all lazy sections
  document.querySelectorAll('.lazy-section').forEach(section => {
    observer.observe(section);
  });

  // Return observer for potential debugging/testing
  return observer;
}

// Auto-initialize on page load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeLazyLoading);
} else {
  initializeLazyLoading();
}
