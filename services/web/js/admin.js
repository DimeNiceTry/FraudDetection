/**
 * API для административных функций
 */
const AdminAPI = {
    /**
     * Получение списка всех пользователей
     * @returns {Promise<Array>} - Список пользователей
     */
    async getAllUsers() {
        return await fetchAPI('/admin/users', 'GET');
    },

    /**
     * Получение информации о пользователе
     * @param {string} userId - Идентификатор пользователя
     * @returns {Promise<Object>} - Информация о пользователе
     */
    async getUserDetails(userId) {
        return await fetchAPI(`/admin/users/${userId}`, 'GET');
    },

    /**
     * Пополнение баланса пользователя
     * @param {string} userId - Идентификатор пользователя
     * @param {number} amount - Сумма пополнения
     * @param {string} comment - Комментарий
     * @returns {Promise<Object>} - Результат операции
     */
    async topUpUserBalance(userId, amount, comment = '') {
        const data = {
            amount: parseFloat(amount),
            comment: comment
        };
        return await fetchAPI(`/admin/users/${userId}/balance/topup`, 'POST', data);
    },

    /**
     * Получение всех транзакций
     * @returns {Promise<Array>} - Список транзакций
     */
    async getAllTransactions() {
        return await fetchAPI('/admin/transactions', 'GET');
    },

    /**
     * Получение всех предсказаний
     * @returns {Promise<Array>} - Список предсказаний
     */
    async getAllPredictions() {
        return await fetchAPI('/admin/predictions', 'GET');
    }
};

/**
 * Класс для управления административной панелью
 */
class AdminPanel {
    constructor() {
        // Проверяем, является ли пользователь администратором
        this.isAdmin = false;
        this.adminSection = document.getElementById('admin-section');
        this.adminNav = document.querySelector('.admin-only');
        
        // Табы административной панели
        this.tabButtons = document.querySelectorAll('.tab-btn');
        this.tabPanes = document.querySelectorAll('.tab-pane');
        
        // Модальные окна
        this.userDetailsModal = document.getElementById('user-details-modal');
        this.userDetailsContent = document.getElementById('user-details-content');
        this.adminTopupModal = document.getElementById('admin-topup-modal');
        this.adminTopupForm = document.getElementById('admin-topup-form');
        this.adminTopupUserId = document.getElementById('admin-topup-user-id');
        this.adminTopupUsername = document.getElementById('admin-topup-username');
        this.adminTopupAmount = document.getElementById('admin-topup-amount');
        this.adminTopupComment = document.getElementById('admin-topup-comment');
        this.adminTopupError = document.getElementById('admin-topup-error');
        this.adminTopupUserBtn = document.getElementById('admin-topup-user-btn');
        
        // Элементы списков
        this.usersList = document.getElementById('users-list');
        this.adminTransactionList = document.getElementById('admin-transaction-list');
        this.adminPredictionList = document.getElementById('admin-prediction-list');
        
        // Фильтры
        this.userSearch = document.getElementById('user-search');
        this.transactionFilter = document.getElementById('transaction-filter');
        this.transactionSearch = document.getElementById('transaction-search');
        this.adminPredictionFilter = document.getElementById('admin-prediction-filter');
        this.predictionSearch = document.getElementById('prediction-search');
        
        // Привязываем события
        this.bindEvents();
        
        // Проверяем роль пользователя
        this.checkAdminRole();
    }
    
    /**
     * Привязывает обработчики событий
     */
    bindEvents() {
        // Обработка табов
        this.tabButtons.forEach(button => {
            button.addEventListener('click', this.handleTabClick.bind(this));
        });
        
        // Обработка модальных окон
        const closeButtons = document.querySelectorAll('.close');
        closeButtons.forEach(button => {
            button.addEventListener('click', () => {
                this.userDetailsModal.style.display = 'none';
                this.adminTopupModal.style.display = 'none';
            });
        });
        
        // Обработка кликов вне модальных окон
        window.addEventListener('click', event => {
            if (event.target === this.userDetailsModal) {
                this.userDetailsModal.style.display = 'none';
            }
            if (event.target === this.adminTopupModal) {
                this.adminTopupModal.style.display = 'none';
            }
        });
        
        // Обработка пополнения баланса
        this.adminTopupForm.addEventListener('submit', this.handleAdminTopUp.bind(this));
        this.adminTopupUserBtn.addEventListener('click', this.showAdminTopUpModal.bind(this));
        
        // Обработка фильтров
        this.userSearch.addEventListener('input', this.handleUserSearch.bind(this));
        this.transactionFilter.addEventListener('change', this.handleTransactionFilter.bind(this));
        this.transactionSearch.addEventListener('input', this.handleTransactionSearch.bind(this));
        this.adminPredictionFilter.addEventListener('change', this.handlePredictionFilter.bind(this));
        this.predictionSearch.addEventListener('input', this.handlePredictionSearch.bind(this));
        
        // Обработка перехода на вкладку администратора
        document.getElementById('nav-admin').addEventListener('click', () => {
            if (this.isAdmin) {
                this.loadAllData();
            }
        });
    }
    
    /**
     * Проверяет, является ли текущий пользователь администратором
     */
    async checkAdminRole() {
        try {
            const user = JSON.parse(localStorage.getItem('user'));
            if (user && user.is_admin) {
                this.isAdmin = true;
                this.showAdminInterface();
            }
        } catch (error) {
            console.error('Ошибка при проверке роли администратора:', error);
        }
    }
    
    /**
     * Показывает административный интерфейс
     */
    showAdminInterface() {
        this.adminNav.classList.remove('hidden');
        this.adminNav.classList.add('visible');
    }
    
    /**
     * Загружает все данные для административной панели
     */
    loadAllData() {
        this.loadUsers();
        this.loadTransactions();
        this.loadPredictions();
    }
    
    /**
     * Обработчик клика по вкладке
     * @param {Event} event - Событие клика
     */
    handleTabClick(event) {
        const tabName = event.target.dataset.tab;
        
        // Активируем вкладку
        this.tabButtons.forEach(button => {
            button.classList.remove('active');
        });
        event.target.classList.add('active');
        
        // Показываем соответствующую панель
        this.tabPanes.forEach(pane => {
            pane.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');
    }
    
    /**
     * Загружает список пользователей
     */
    async loadUsers() {
        if (!this.isAdmin) return;
        
        this.usersList.innerHTML = '<div class="loading">Загрузка пользователей...</div>';
        
        try {
            const users = await AdminAPI.getAllUsers();
            this.renderUsers(users);
        } catch (error) {
            console.error('Ошибка при загрузке пользователей:', error);
            this.usersList.innerHTML = `<div class="error">Ошибка: ${error.message}</div>`;
        }
    }
    
    /**
     * Отображает список пользователей
     * @param {Array} users - Список пользователей
     */
    renderUsers(users) {
        if (!users || users.length === 0) {
            this.usersList.innerHTML = '<div class="empty">Пользователи не найдены</div>';
            return;
        }
        
        let html = '';
        users.forEach(user => {
            html += `
                <div class="admin-list-item" data-user-id="${user.id}">
                    <h4>
                        ${user.username}
                        ${user.is_admin ? '<span class="badge">Администратор</span>' : ''}
                    </h4>
                    <p>Email: ${user.email || 'Не указан'}</p>
                    <p>Баланс: ${user.balance.toFixed(2)} кредитов</p>
                    <div class="admin-actions">
                        <button class="btn btn-sm view-user" data-user-id="${user.id}">Подробнее</button>
                        <button class="btn btn-sm btn-primary topup-user" data-user-id="${user.id}" data-username="${user.username}">Пополнить баланс</button>
                    </div>
                </div>
            `;
        });
        
        this.usersList.innerHTML = html;
        
        // Привязываем обработчики событий к кнопкам
        const viewButtons = this.usersList.querySelectorAll('.view-user');
        viewButtons.forEach(button => {
            button.addEventListener('click', event => {
                const userId = event.target.dataset.userId;
                this.showUserDetails(userId);
            });
        });
        
        const topupButtons = this.usersList.querySelectorAll('.topup-user');
        topupButtons.forEach(button => {
            button.addEventListener('click', event => {
                const userId = event.target.dataset.userId;
                const username = event.target.dataset.username;
                this.showTopUpModal(userId, username);
            });
        });
    }
    
    /**
     * Показывает детали пользователя
     * @param {string} userId - Идентификатор пользователя
     */
    async showUserDetails(userId) {
        this.userDetailsContent.innerHTML = '<div class="loading">Загрузка информации о пользователе...</div>';
        this.userDetailsModal.style.display = 'block';
        
        try {
            const user = await AdminAPI.getUserDetails(userId);
            
            let html = `
                <div class="user-details-card">
                    <div class="user-details-section">
                        <h3>Основная информация</h3>
                        <p><strong>Имя пользователя:</strong> ${user.username}</p>
                        <p><strong>Email:</strong> ${user.email || 'Не указан'}</p>
                        <p><strong>Баланс:</strong> ${user.balance.toFixed(2)} кредитов</p>
                        <p><strong>Роль:</strong> ${user.is_admin ? 'Администратор' : 'Пользователь'}</p>
                        <p><strong>Дата регистрации:</strong> ${new Date(user.created_at).toLocaleString('ru-RU', {
                            timeZone: 'Europe/Moscow'
                        })}</p>
                    </div>
                `;
                
            if (user.transactions && user.transactions.length > 0) {
                html += `
                    <div class="user-details-section">
                        <h3>Транзакции</h3>
                        <ul>
                `;
                
                user.transactions.forEach(transaction => {
                    html += `
                        <li>
                            ${transaction.type === 'deposit' ? 'Пополнение' : 'Списание'}: 
                            ${transaction.amount.toFixed(2)} кредитов - 
                            ${new Date(transaction.created_at).toLocaleString('ru-RU', {
                                timeZone: 'Europe/Moscow'
                            })}
                            ${transaction.comment ? ` - ${transaction.comment}` : ''}
                        </li>
                    `;
                });
                
                html += `
                        </ul>
                    </div>
                `;
            }
            
            if (user.predictions && user.predictions.length > 0) {
                html += `
                    <div class="user-details-section">
                        <h3>Предсказания</h3>
                        <ul>
                `;
                
                user.predictions.forEach(prediction => {
                    html += `
                        <li>
                            ${new Date(prediction.created_at).toLocaleString('ru-RU', {
                                timeZone: 'Europe/Moscow'
                            })} - 
                            ${prediction.status === 'success' ? 'Успешно' : prediction.status === 'pending' ? 'В обработке' : 'Ошибка'}
                            ${prediction.cost ? ` - Стоимость: ${prediction.cost.toFixed(2)} кредитов` : ''}
                        </li>
                    `;
                });
                
                html += `
                        </ul>
                    </div>
                `;
            }
            
            html += `</div>`;
            
            this.userDetailsContent.innerHTML = html;
            this.adminTopupUserId.value = userId;
            this.adminTopupUsername.value = user.username;
        } catch (error) {
            console.error('Ошибка при загрузке информации о пользователе:', error);
            this.userDetailsContent.innerHTML = `<div class="error">Ошибка: ${error.message}</div>`;
        }
    }
    
    /**
     * Показывает модальное окно для пополнения баланса
     * @param {string} userId - Идентификатор пользователя
     * @param {string} username - Имя пользователя
     */
    showTopUpModal(userId, username) {
        this.adminTopupUserId.value = userId;
        this.adminTopupUsername.value = username;
        this.adminTopupModal.style.display = 'block';
    }
    
    /**
     * Показывает модальное окно для пополнения баланса из деталей пользователя
     */
    showAdminTopUpModal() {
        this.adminTopupModal.style.display = 'block';
    }
    
    /**
     * Обработчик пополнения баланса
     * @param {Event} event - Событие отправки формы
     */
    async handleAdminTopUp(event) {
        event.preventDefault();
        
        const userId = this.adminTopupUserId.value;
        const amount = this.adminTopupAmount.value;
        const comment = this.adminTopupComment.value;
        
        if (!userId || !amount) {
            this.adminTopupError.textContent = 'Пожалуйста, заполните все обязательные поля';
            this.adminTopupError.classList.remove('hidden');
            return;
        }
        
        try {
            this.adminTopupError.classList.add('hidden');
            
            await AdminAPI.topUpUserBalance(userId, amount, comment);
            
            // Закрываем модальное окно
            this.adminTopupModal.style.display = 'none';
            
            // Обновляем список пользователей
            this.loadUsers();
            
            // Очищаем форму
            this.adminTopupForm.reset();
            
            // Если открыто модальное окно с информацией о пользователе, обновляем его
            if (this.userDetailsModal.style.display === 'block') {
                this.showUserDetails(userId);
            }
        } catch (error) {
            console.error('Ошибка при пополнении баланса:', error);
            this.adminTopupError.textContent = error.message;
            this.adminTopupError.classList.remove('hidden');
        }
    }
    
    /**
     * Загружает список транзакций
     */
    async loadTransactions() {
        if (!this.isAdmin) return;
        
        this.adminTransactionList.innerHTML = '<div class="loading">Загрузка транзакций...</div>';
        
        try {
            const transactions = await AdminAPI.getAllTransactions();
            this.allTransactions = transactions;
            this.renderTransactions(transactions);
        } catch (error) {
            console.error('Ошибка при загрузке транзакций:', error);
            this.adminTransactionList.innerHTML = `<div class="error">Ошибка: ${error.message}</div>`;
        }
    }
    
    /**
     * Отображает список транзакций
     * @param {Array} transactions - Список транзакций
     */
    renderTransactions(transactions) {
        if (!transactions || transactions.length === 0) {
            this.adminTransactionList.innerHTML = '<div class="empty">Транзакции не найдены</div>';
            return;
        }
        
        let html = '';
        transactions.forEach(transaction => {
            html += `
                <div class="admin-list-item">
                    <h4>
                        ${transaction.type === 'deposit' ? 'Пополнение' : 'Списание'}: ${transaction.amount.toFixed(2)} кредитов
                        <span>${new Date(transaction.created_at).toLocaleString('ru-RU', {
                            timeZone: 'Europe/Moscow'
                        })}</span>
                    </h4>
                    <p>Пользователь: ${transaction.username || transaction.user_id}</p>
                    ${transaction.comment ? `<p>Комментарий: ${transaction.comment}</p>` : ''}
                </div>
            `;
        });
        
        this.adminTransactionList.innerHTML = html;
    }
    
    /**
     * Загружает список предсказаний
     */
    async loadPredictions() {
        if (!this.isAdmin) return;
        
        this.adminPredictionList.innerHTML = '<div class="loading">Загрузка предсказаний...</div>';
        
        try {
            const predictions = await AdminAPI.getAllPredictions();
            this.allPredictions = predictions;
            this.renderPredictions(predictions);
        } catch (error) {
            console.error('Ошибка при загрузке предсказаний:', error);
            this.adminPredictionList.innerHTML = `<div class="error">Ошибка: ${error.message}</div>`;
        }
    }
    
    /**
     * Отображает список предсказаний
     * @param {Array} predictions - Список предсказаний
     */
    renderPredictions(predictions) {
        if (!predictions || predictions.length === 0) {
            this.adminPredictionList.innerHTML = '<div class="empty">Предсказания не найдены</div>';
            return;
        }
        
        let html = '';
        predictions.forEach(prediction => {
            const statusClass = prediction.status === 'success' ? 'status-success' : 
                               prediction.status === 'pending' ? 'status-pending' : 'status-error';
            const statusText = prediction.status === 'success' ? 'Успешно' : 
                              prediction.status === 'pending' ? 'В обработке' : 'Ошибка';
            
            html += `
                <div class="admin-list-item">
                    <h4>
                        Предсказание #${prediction.prediction_id}
                        <span class="status ${statusClass}">${statusText}</span>
                    </h4>
                    <p>Пользователь: ${prediction.username || prediction.user_id}</p>
                    <p>Дата: ${new Date(prediction.created_at).toLocaleString('ru-RU', {
                        timeZone: 'Europe/Moscow'
                    })}</p>
                    ${prediction.cost ? `<p>Стоимость: ${prediction.cost.toFixed(2)} кредитов</p>` : ''}
                    ${prediction.input_data ? `<p>Входные данные: ${JSON.stringify(prediction.input_data)}</p>` : ''}
                    ${prediction.result ? `<p>Результат: ${JSON.stringify(prediction.result)}</p>` : ''}
                    ${prediction.error ? `<p>Ошибка: ${prediction.error}</p>` : ''}
                </div>
            `;
        });
        
        this.adminPredictionList.innerHTML = html;
    }
    
    /**
     * Обработчик поиска пользователей
     * @param {Event} event - Событие ввода
     */
    handleUserSearch(event) {
        const searchTerm = event.target.value.toLowerCase();
        const userItems = this.usersList.querySelectorAll('.admin-list-item');
        
        userItems.forEach(item => {
            const username = item.querySelector('h4').textContent.toLowerCase();
            const email = item.querySelector('p').textContent.toLowerCase();
            
            if (username.includes(searchTerm) || email.includes(searchTerm)) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });
    }
    
    /**
     * Обработчик фильтрации транзакций
     */
    handleTransactionFilter() {
        this.filterTransactions();
    }
    
    /**
     * Обработчик поиска транзакций
     */
    handleTransactionSearch() {
        this.filterTransactions();
    }
    
    /**
     * Фильтрует транзакции
     */
    filterTransactions() {
        if (!this.allTransactions) return;
        
        const filterValue = this.transactionFilter.value;
        const searchTerm = this.transactionSearch.value.toLowerCase();
        
        const filteredTransactions = this.allTransactions.filter(transaction => {
            const matchesType = filterValue === 'all' || transaction.type === filterValue;
            const matchesSearch = !searchTerm || 
                                (transaction.username && transaction.username.toLowerCase().includes(searchTerm)) ||
                                (transaction.user_id && transaction.user_id.toString().includes(searchTerm));
            
            return matchesType && matchesSearch;
        });
        
        this.renderTransactions(filteredTransactions);
    }
    
    /**
     * Обработчик фильтрации предсказаний
     */
    handlePredictionFilter() {
        this.filterPredictions();
    }
    
    /**
     * Обработчик поиска предсказаний
     */
    handlePredictionSearch() {
        this.filterPredictions();
    }
    
    /**
     * Фильтрует предсказания
     */
    filterPredictions() {
        if (!this.allPredictions) return;
        
        const filterValue = this.adminPredictionFilter.value;
        const searchTerm = this.predictionSearch.value.toLowerCase();
        
        const filteredPredictions = this.allPredictions.filter(prediction => {
            const matchesStatus = filterValue === 'all' || prediction.status === filterValue;
            const matchesSearch = !searchTerm || 
                                (prediction.username && prediction.username.toLowerCase().includes(searchTerm)) ||
                                (prediction.user_id && prediction.user_id.toString().includes(searchTerm));
            
            return matchesStatus && matchesSearch;
        });
        
        this.renderPredictions(filteredPredictions);
    }
}

// Инициализация административной панели при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.adminPanel = new AdminPanel();
}); 