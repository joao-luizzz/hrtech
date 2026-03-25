// ========== DARK MODE FUNCTIONALITY FOR ADMIN ==========
// Executado APENAS para adicionar o toggle button, o tema já foi carregado no extrastyle

(function() {
    // Aguardar o header estar pronto antes de adicionar o botão
    const addToggleButtonWhenReady = function() {
        const userTools = document.getElementById('user-tools');

        if (userTools) {
            addThemeToggle();
            window.removeEventListener('load', addToggleButtonWhenReady);
        }
    };

    // Tentar adicionar imediatamente se o DOM já estiver pronto
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', addToggleButtonWhenReady);
    } else {
        // DOM já está pronto
        addToggleButtonWhenReady();
    }

    // Fallback se o elemento não estiver disponível ainda
    if (!document.getElementById('user-tools')) {
        window.addEventListener('load', addToggleButtonWhenReady);
    }
})();

function addThemeToggle() {
    const userTools = document.getElementById('user-tools');
    if (!userTools || document.getElementById('admin-theme-toggle')) {
        // Já foi adicionado
        return;
    }

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
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 4px;
        padding: 0.5rem 0.75rem;
        cursor: pointer;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        color: white;
        font-size: 1rem;
        min-width: auto;
    `;

    // Criar ícone
    const themeIcon = document.createElement('i');
    themeIcon.id = 'admin-theme-icon';
    themeIcon.className = 'bi';
    themeIcon.style.cssText = `
        font-size: 1rem;
    `;

    const themeLabelSpan = document.createElement('span');
    themeLabelSpan.id = 'admin-theme-label';
    themeLabelSpan.style.cssText = `
        font-size: 0.85rem;
        font-weight: 500;
    `;

    themeToggleBtn.appendChild(themeIcon);
    themeToggleBtn.appendChild(themeLabelSpan);
    themeToggleContainer.appendChild(themeToggleBtn);

    // Inserir no início do user-tools
    userTools.insertBefore(themeToggleContainer, userTools.firstChild);

    // Atualizar ícone com o tema atual (sem flickering)
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
    updateThemeIcon(currentTheme);

    // Adicionar event listener
    themeToggleBtn.addEventListener('click', function(e) {
        e.preventDefault();
        toggleTheme();
    });

    // Hover effect
    themeToggleBtn.addEventListener('mouseenter', function() {
        this.style.background = 'rgba(255, 255, 255, 0.25)';
        this.style.borderColor = 'rgba(255, 255, 255, 0.4)';
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

    // Aplicar tema imediatamente
    htmlElement.setAttribute('data-theme', newTheme);
    htmlElement.style.colorScheme = newTheme;
    localStorage.setItem('theme', newTheme);

    // Atualizar UI
    updateThemeIcon(newTheme);
}

function updateThemeIcon(theme) {
    const themeIcon = document.getElementById('admin-theme-icon');
    const themeLabelSpan = document.getElementById('admin-theme-label');

    if (themeIcon) {
        if (theme === 'dark') {
            themeIcon.className = 'bi bi-sun-fill';
            if (themeLabelSpan) themeLabelSpan.textContent = 'Light';
        } else {
            themeIcon.className = 'bi bi-moon-stars-fill';
            if (themeLabelSpan) themeLabelSpan.textContent = 'Dark';
        }
    }
}
