// ========== DARK MODE FUNCTIONALITY FOR ADMIN ==========

document.addEventListener('DOMContentLoaded', function() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);

    // Adicionar botão de toggle no header
    addThemeToggle();
});

function addThemeToggle() {
    const userTools = document.getElementById('user-tools');
    if (!userTools) return;

    // Criar container do botão
    const themeToggleContainer = document.createElement('div');
    themeToggleContainer.style.cssText = `
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        margin-right: 1rem;
    `;

    // Criar botão
    const themeToggleBtn = document.createElement('button');
    themeToggleBtn.type = 'button';
    themeToggleBtn.id = 'admin-theme-toggle';
    themeToggleBtn.setAttribute('aria-label', 'Toggle dark mode');
    themeToggleBtn.style.cssText = `
        background: rgba(255, 255, 255, 0.15);
        border: 2px solid rgba(255, 255, 255, 0.2);
        border-radius: 50px;
        padding: 0.4rem 0.8rem;
        cursor: pointer;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        color: white;
        font-size: 1rem;
    `;

    // Criar ícone
    const themeIcon = document.createElement('i');
    themeIcon.id = 'admin-theme-icon';
    themeIcon.className = 'bi bi-moon-stars-fill';
    themeIcon.style.cssText = `
        font-size: 1.1rem;
    `;

    themeToggleBtn.appendChild(themeIcon);
    themeToggleContainer.appendChild(themeToggleBtn);

    // Inserir antes do texto "Welcome"
    userTools.insertBefore(themeToggleContainer, userTools.firstChild);

    // Atualizar ícone inicial
    const currentTheme = document.documentElement.getAttribute('data-theme');
    updateThemeIcon(currentTheme);

    // Adicionar event listener
    themeToggleBtn.addEventListener('click', toggleTheme);

    // Hover effect
    themeToggleBtn.addEventListener('mouseenter', function() {
        this.style.background = 'rgba(255, 255, 255, 0.2)';
        this.style.borderColor = 'rgba(255, 255, 255, 0.3)';
    });

    themeToggleBtn.addEventListener('mouseleave', function() {
        this.style.background = 'rgba(255, 255, 255, 0.15)';
        this.style.borderColor = 'rgba(255, 255, 255, 0.2)';
    });
}

function toggleTheme() {
    const htmlElement = document.documentElement;
    const currentTheme = htmlElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';

    htmlElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
}

function updateThemeIcon(theme) {
    const themeIcon = document.getElementById('admin-theme-icon');
    if (themeIcon) {
        if (theme === 'dark') {
            themeIcon.className = 'bi bi-sun-fill';
        } else {
            themeIcon.className = 'bi bi-moon-stars-fill';
        }
    }
}
