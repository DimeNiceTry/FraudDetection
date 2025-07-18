/**
 * Класс для управления аутентификацией в приложении
 */
class Auth {
    constructor() {
        this.token = localStorage.getItem('token');
        this.user = JSON.parse(localStorage.getItem('user')) || null;
        this.isAuthenticated = Boolean(this.token);
        
        // DOM элементы для обработки UI
        this.loginModal = document.getElementById('login-modal');
        this.registerModal = document.getElementById('register-modal');
        this.loginForm = document.getElementById('login-form');
        this.registerForm = document.getElementById('register-form');
        this.loginError = document.getElementById('login-error');
        this.registerError = document.getElementById('register-error');
        this.userInfo = document.getElementById('user-info');
        this.authButtons = document.getElementById('auth-buttons');
        this.usernameSpan = document.getElementById('username');
        this.logoutBtn = document.getElementById('logout-btn');
        this.loginNavBtn = document.getElementById('login-nav-btn');
        this.registerNavBtn = document.getElementById('register-nav-btn');
        
        // Привязываем обработчики событий
        this.bindEvents();
        
        // Обновляем UI в зависимости от состояния аутентификации
        this.updateUI();
    }
    
    /**
     * Привязывает обработчики событий
     */
    bindEvents() {
        // Обработчики форм
        this.loginForm.addEventListener('submit', this.handleLogin.bind(this));
        this.registerForm.addEventListener('submit', this.handleRegister.bind(this));
        
        // Обработчики кнопок
        this.logoutBtn.addEventListener('click', this.handleLogout.bind(this));
        this.loginNavBtn.addEventListener('click', this.showLoginModal.bind(this));
        this.registerNavBtn.addEventListener('click', this.showRegisterModal.bind(this));
        
        // Закрытие модальных окон
        const closeButtons = document.querySelectorAll('.close');
        closeButtons.forEach(button => {
            button.addEventListener('click', this.closeModals.bind(this));
        });
        
        // Закрытие модальных окон при клике за пределами модального окна
        window.addEventListener('click', event => {
            if (event.target === this.loginModal) {
                this.loginModal.style.display = 'none';
            }
            if (event.target === this.registerModal) {
                this.registerModal.style.display = 'none';
            }
        });
    }
    
    /**
     * Обработчик входа в систему
     * @param {Event} event - Событие отправки формы
     */
    async handleLogin(event) {
        event.preventDefault();
        
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;
        
        try {
            this.loginError.classList.add('hidden');
            
            const response = await AuthAPI.login(username, password);
            this.token = response.access_token;
            localStorage.setItem('token', this.token);
            
            // Получаем информацию о пользователе
            const user = await AuthAPI.getCurrentUser();
            this.user = user;
            localStorage.setItem('user', JSON.stringify(user));
            
            this.isAuthenticated = true;
            this.updateUI();
            this.closeModals();
            
            // Очищаем форму
            this.loginForm.reset();
        } catch (error) {
            this.loginError.textContent = error.message || 'Ошибка при входе в систему';
            this.loginError.classList.remove('hidden');
        }
    }
    
    /**
     * Обработчик регистрации пользователя
     * @param {Event} event - Событие отправки формы
     */
    async handleRegister(event) {
        event.preventDefault();
        
        const username = document.getElementById('register-username').value;
        const email = document.getElementById('register-email').value;
        const password = document.getElementById('register-password').value;
        
        try {
            this.registerError.classList.add('hidden');
            
            // Регистрируем пользователя
            await AuthAPI.register(username, password, email);
            
            // После успешной регистрации выполняем вход
            const response = await AuthAPI.login(username, password);
            this.token = response.access_token;
            localStorage.setItem('token', this.token);
            
            // Получаем информацию о пользователе
            const user = await AuthAPI.getCurrentUser();
            this.user = user;
            localStorage.setItem('user', JSON.stringify(user));
            
            this.isAuthenticated = true;
            this.updateUI();
            this.closeModals();
            
            // Очищаем форму
            this.registerForm.reset();
        } catch (error) {
            this.registerError.textContent = error.message || 'Ошибка при регистрации';
            this.registerError.classList.remove('hidden');
        }
    }
    
    /**
     * Обработчик выхода из системы
     * @param {Event} event - Событие клика
     */
    handleLogout(event) {
        event.preventDefault();
        
        // Удаляем токен и информацию о пользователе
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        
        this.token = null;
        this.user = null;
        this.isAuthenticated = false;
        
        // Обновляем UI
        this.updateUI();
    }
    
    /**
     * Показывает модальное окно для входа
     */
    showLoginModal() {
        this.loginModal.style.display = 'block';
    }
    
    /**
     * Показывает модальное окно для регистрации
     */
    showRegisterModal() {
        this.registerModal.style.display = 'block';
    }
    
    /**
     * Закрывает все модальные окна
     */
    closeModals() {
        this.loginModal.style.display = 'none';
        this.registerModal.style.display = 'none';
    }
    
    /**
     * Обновляет UI в зависимости от состояния аутентификации
     */
    updateUI() {
        if (this.isAuthenticated && this.user) {
            this.userInfo.classList.remove('hidden');
            this.authButtons.classList.add('hidden');
            this.usernameSpan.textContent = this.user.username;
            
            // Разблокируем доступ к защищенным разделам
            document.querySelectorAll('nav ul li a').forEach(link => {
                link.classList.remove('disabled');
            });
        } else {
            this.userInfo.classList.add('hidden');
            this.authButtons.classList.remove('hidden');
            this.usernameSpan.textContent = '';
            
            // Показываем только публичные разделы
            document.getElementById('nav-home').click();
        }
    }
    
    /**
     * Проверяет, авторизован ли пользователь
     * @returns {boolean} - Статус авторизации
     */
    isLoggedIn() {
        return this.isAuthenticated;
    }
    
    /**
     * Выполняет проверку статуса авторизации при инициализации приложения
     */
    async checkAuthStatus() {
        if (this.token) {
            try {
                const user = await AuthAPI.getCurrentUser();
                this.user = user;
                localStorage.setItem('user', JSON.stringify(user));
                this.isAuthenticated = true;
            } catch (error) {
                console.error('Ошибка при проверке статуса авторизации:', error);
                this.handleLogout({ preventDefault: () => {} });
            }
        }
        
        this.updateUI();
    }
    
    /**
     * Алиас для метода checkAuthStatus для обратной совместимости
     */
    async checkAuth() {
        return await this.checkAuthStatus();
    }
} 