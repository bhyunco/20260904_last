/**
 * TaskFlow Application JavaScript
 * Vanilla JS implementation for state management, REST API interaction, and UI rendering.
 */

document.addEventListener('DOMContentLoaded', () => {
    // Current App State
    const state = {
        todos: [],
        currentStatus: 'all',
        currentCategory: 'all',
        currentSort: 'newest',
        searchQuery: '',
        theme: localStorage.getItem('taskflow_theme') || 'dark'
    };

    // DOM Elements
    const elements = {
        // Theme & Header
        body: document.body,
        themeToggleBtn: document.getElementById('btn-theme-toggle'),
        themeIcon: document.querySelector('.theme-icon'),
        currentDateDisplay: document.getElementById('current-date-display'),

        // Stats elements
        statTotal: document.getElementById('stat-total-count'),
        statPending: document.getElementById('stat-pending-count'),
        statCompleted: document.getElementById('stat-completed-count'),
        statRate: document.getElementById('stat-rate-count'),
        statProgressBar: document.getElementById('stat-progress-bar'),

        // Badges on tabs
        badgeAll: document.getElementById('badge-all-count'),
        badgeActive: document.getElementById('badge-active-count'),
        badgeCompleted: document.getElementById('badge-completed-count'),

        // Create Task Form
        todoForm: document.getElementById('todo-form'),
        inputTitle: document.getElementById('input-task-title'),
        selectCategory: document.getElementById('select-category'),
        selectPriority: document.getElementById('select-priority'),
        inputDueDate: document.getElementById('input-due-date'),
        inputDesc: document.getElementById('input-task-desc'),

        // Controls
        statusTabs: document.querySelectorAll('.tab-button'),
        inputSearch: document.getElementById('input-search'),
        btnClearSearch: document.getElementById('btn-clear-search'),
        filterCategory: document.getElementById('filter-category'),
        filterSort: document.getElementById('filter-sort'),
        btnClearCompleted: document.getElementById('btn-clear-completed'),

        // List & State
        todoItemsList: document.getElementById('todo-items-list'),
        emptyState: document.getElementById('empty-state'),
        loadingSpinner: document.getElementById('loading-spinner'),

        // Edit Modal
        editModal: document.getElementById('edit-modal'),
        editForm: document.getElementById('edit-form'),
        editTaskId: document.getElementById('edit-task-id'),
        editTitle: document.getElementById('edit-title'),
        editCategory: document.getElementById('edit-category'),
        editPriority: document.getElementById('edit-priority'),
        editDueDate: document.getElementById('edit-due-date'),
        editDesc: document.getElementById('edit-description'),
        btnCloseModal: document.getElementById('btn-close-modal'),
        btnCancelEdit: document.getElementById('btn-cancel-edit'),

        // Toast Container
        toastContainer: document.getElementById('toast-container')
    };

    // ================= Initialization =================
    initTheme();
    initDateDisplay();
    bindEvents();
    loadTodos();
    loadStats();

    // ================= Theme & Date =================
    function initTheme() {
        if (state.theme === 'light') {
            elements.body.classList.remove('theme-dark');
            elements.body.classList.add('theme-light');
            elements.themeIcon.textContent = '☀️';
        } else {
            elements.body.classList.remove('theme-light');
            elements.body.classList.add('theme-dark');
            elements.themeIcon.textContent = '🌙';
        }
    }

    function toggleTheme() {
        const isLight = elements.body.classList.toggle('theme-light');
        elements.body.classList.toggle('theme-dark', !isLight);
        state.theme = isLight ? 'light' : 'dark';
        elements.themeIcon.textContent = isLight ? '☀️' : '🌙';
        localStorage.setItem('taskflow_theme', state.theme);
        showToast(`테마가 ${isLight ? '라이트' : '다크'} 모드로 변경되었습니다.`, 'info');
    }

    function initDateDisplay() {
        const now = new Date();
        const days = ['일요일', '월요일', '화요일', '수요일', '목요일', '금요일', '토요일'];
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const date = String(now.getDate()).padStart(2, '0');
        const dayName = days[now.getDay()];
        
        if (elements.currentDateDisplay) {
            elements.currentDateDisplay.textContent = `📅 ${year}.${month}.${date} (${dayName})`;
        }

        // Set default due date input to today
        if (elements.inputDueDate) {
            elements.inputDueDate.min = `${year}-${month}-${date}`;
        }
    }

    // ================= Toast Notifications =================
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        let icon = 'ℹ️';
        if (type === 'success') icon = '✅';
        if (type === 'error') icon = '⚠️';

        toast.innerHTML = `<span>${icon}</span><span>${escapeHtml(message)}</span>`;
        elements.toastContainer.appendChild(toast);

        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 3600);
    }

    // ================= API Operations =================
    async function loadTodos() {
        showLoading(true);
        try {
            const params = new URLSearchParams({
                status: state.currentStatus,
                category: state.currentCategory,
                sort: state.currentSort,
                search: state.searchQuery
            });

            const res = await fetch(`/api/todos?${params.toString()}`);
            const data = await res.json();
            
            if (data.success) {
                state.todos = data.todos;
                renderTodos();
            } else {
                showToast(data.error || '목록 로드 실패', 'error');
            }
        } catch (err) {
            console.error('Failed to fetch todos:', err);
            showToast('서버 연결 중 오류가 발생했습니다.', 'error');
        } finally {
            showLoading(false);
        }
    }

    async function loadStats() {
        try {
            const res = await fetch('/api/stats');
            const data = await res.json();
            if (data.success) {
                updateStatsUI(data.stats);
            }
        } catch (err) {
            console.error('Failed to fetch stats:', err);
        }
    }

    function updateStatsUI(stats) {
        if (!stats) return;
        elements.statTotal.textContent = stats.total;
        elements.statPending.textContent = stats.pending;
        elements.statCompleted.textContent = stats.completed;
        elements.statRate.textContent = `${stats.completion_rate}%`;
        elements.statProgressBar.style.width = `${stats.completion_rate}%`;

        // Update tab badges
        elements.badgeAll.textContent = stats.total;
        elements.badgeActive.textContent = stats.pending;
        elements.badgeCompleted.textContent = stats.completed;
    }

    async function handleAddTodo(e) {
        e.preventDefault();
        const title = elements.inputTitle.value.trim();
        if (!title) {
            showToast('할 일 제목을 입력해주세요.', 'error');
            return;
        }

        const payload = {
            title: title,
            category: elements.selectCategory.value,
            priority: elements.selectPriority.value,
            due_date: elements.inputDueDate.value,
            description: elements.inputDesc.value.trim()
        };

        try {
            const res = await fetch('/api/todos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            
            if (data.success) {
                showToast('새로운 할 일이 추가되었습니다!', 'success');
                elements.inputTitle.value = '';
                elements.inputDesc.value = '';
                elements.inputDueDate.value = '';
                elements.inputTitle.focus();
                
                updateStatsUI(data.stats);
                loadTodos();
            } else {
                showToast(data.error || '등록 실패', 'error');
            }
        } catch (err) {
            console.error('Add todo error:', err);
            showToast('할 일 등록 중 문제가 발생했습니다.', 'error');
        }
    }

    async function handleToggleTodo(id) {
        try {
            const res = await fetch(`/api/todos/${id}/toggle`, { method: 'PATCH' });
            const data = await res.json();
            
            if (data.success) {
                const todo = data.todo;
                showToast(todo.completed ? '🎉 할 일을 완료했습니다!' : '할 일을 다시 진행 중으로 변경했습니다.', 'success');
                updateStatsUI(data.stats);
                
                // If currently filtered on active or completed, reload, else update in-place
                if (state.currentStatus !== 'all') {
                    loadTodos();
                } else {
                    const itemIdx = state.todos.findIndex(t => t.id === id);
                    if (itemIdx !== -1) {
                        state.todos[itemIdx] = todo;
                        renderTodos();
                    }
                }
            } else {
                showToast(data.error || '상태 변경 실패', 'error');
            }
        } catch (err) {
            console.error('Toggle error:', err);
            showToast('상태 변경 실패', 'error');
        }
    }

    async function handleDeleteTodo(id) {
        if (!confirm('정말 이 할 일을 삭제하시겠습니까?')) return;

        try {
            const res = await fetch(`/api/todos/${id}`, { method: 'DELETE' });
            const data = await res.json();
            
            if (data.success) {
                showToast('할 일이 삭제되었습니다.', 'info');
                updateStatsUI(data.stats);
                loadTodos();
            } else {
                showToast(data.error || '삭제 실패', 'error');
            }
        } catch (err) {
            console.error('Delete error:', err);
            showToast('삭제 중 오류가 발생했습니다.', 'error');
        }
    }

    async function handleClearCompleted() {
        if (!confirm('완료된 모든 할 일을 정리하시겠습니까?')) return;

        try {
            const res = await fetch('/api/todos/completed', { method: 'DELETE' });
            const data = await res.json();
            
            if (data.success) {
                showToast(data.message, 'success');
                updateStatsUI(data.stats);
                loadTodos();
            } else {
                showToast(data.error || '삭제 실패', 'error');
            }
        } catch (err) {
            console.error('Clear completed error:', err);
            showToast('정리 중 오류 발생', 'error');
        }
    }

    // ================= Edit Modal =================
    function openEditModal(todo) {
        elements.editTaskId.value = todo.id;
        elements.editTitle.value = todo.title;
        elements.editCategory.value = todo.category || '업무';
        elements.editPriority.value = todo.priority || '보통';
        elements.editDueDate.value = todo.due_date || '';
        elements.editDesc.value = todo.description || '';

        elements.editModal.classList.add('active');
        elements.editModal.setAttribute('aria-hidden', 'false');
        elements.editTitle.focus();
    }

    function closeEditModal() {
        elements.editModal.classList.remove('active');
        elements.editModal.setAttribute('aria-hidden', 'true');
    }

    async function handleSaveEdit(e) {
        e.preventDefault();
        const id = elements.editTaskId.value;
        const title = elements.editTitle.value.trim();
        if (!title) {
            showToast('제목을 입력해주세요.', 'error');
            return;
        }

        const payload = {
            title: title,
            category: elements.editCategory.value,
            priority: elements.editPriority.value,
            due_date: elements.editDueDate.value,
            description: elements.editDesc.value.trim()
        };

        try {
            const res = await fetch(`/api/todos/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();

            if (data.success) {
                showToast('할 일이 성공적으로 수정되었습니다.', 'success');
                closeEditModal();
                updateStatsUI(data.stats);
                loadTodos();
            } else {
                showToast(data.error || '수정 실패', 'error');
            }
        } catch (err) {
            console.error('Save edit error:', err);
            showToast('수정 중 오류 발생', 'error');
        }
    }

    // ================= Rendering =================
    function renderTodos() {
        elements.todoItemsList.innerHTML = '';

        if (!state.todos || state.todos.length === 0) {
            elements.emptyState.style.display = 'flex';
            return;
        }

        elements.emptyState.style.display = 'none';

        const todayStr = new Date().toISOString().split('T')[0];

        state.todos.forEach(todo => {
            const card = document.createElement('div');
            
            // Priority class
            let priorityClass = 'priority-med';
            let priorityBadgeClass = 'badge-priority-med';
            if (todo.priority === '높음') {
                priorityClass = 'priority-high';
                priorityBadgeClass = 'badge-priority-high';
            } else if (todo.priority === '낮음') {
                priorityClass = 'priority-low';
                priorityBadgeClass = 'badge-priority-low';
            }

            card.className = `todo-card ${priorityClass} ${todo.completed ? 'completed' : ''}`;
            card.id = `todo-item-${todo.id}`;
            card.setAttribute('role', 'listitem');

            // Overdue check
            const isOverdue = !todo.completed && todo.due_date && todo.due_date < todayStr;
            const dueBadgeHtml = todo.due_date ? `
                <span class="badge badge-due-date ${isOverdue ? 'is-overdue' : ''}">
                    📅 ${escapeHtml(todo.due_date)} ${isOverdue ? '⚠️ 기한초과' : ''}
                </span>
            ` : '';

            // Category emoji map
            const categoryEmojiMap = {
                '업무': '🏢',
                '개인': '👤',
                '공부': '📚',
                '쇼핑': '🛒',
                '아이디어': '💡',
                '기타': '📌'
            };
            const catEmoji = categoryEmojiMap[todo.category] || '📌';

            card.innerHTML = `
                <div class="todo-checkbox-wrapper">
                    <input 
                        type="checkbox" 
                        id="checkbox-todo-${todo.id}" 
                        class="todo-checkbox" 
                        ${todo.completed ? 'checked' : ''} 
                        aria-label="${escapeHtml(todo.title)} 완료 토글"
                    >
                </div>
                <div class="todo-content-area">
                    <div class="todo-header-row">
                        <span class="todo-title">${escapeHtml(todo.title)}</span>
                    </div>
                    ${todo.description ? `<p class="todo-description">${escapeHtml(todo.description)}</p>` : ''}
                    <div class="todo-meta-row">
                        <span class="badge badge-category">${catEmoji} ${escapeHtml(todo.category)}</span>
                        <span class="badge ${priorityBadgeClass}">${escapeHtml(todo.priority)}</span>
                        ${dueBadgeHtml}
                    </div>
                </div>
                <div class="todo-actions">
                    <button type="button" class="btn-action btn-edit" title="수정" aria-label="할 일 수정">
                        ✏️
                    </button>
                    <button type="button" class="btn-action btn-delete" title="삭제" aria-label="할 일 삭제">
                        🗑️
                    </button>
                </div>
            `;

            // Event Listeners for this card
            const checkbox = card.querySelector('.todo-checkbox');
            checkbox.addEventListener('change', () => handleToggleTodo(todo.id));

            const btnEdit = card.querySelector('.btn-edit');
            btnEdit.addEventListener('click', () => openEditModal(todo));

            const btnDelete = card.querySelector('.btn-delete');
            btnDelete.addEventListener('click', () => handleDeleteTodo(todo.id));

            elements.todoItemsList.appendChild(card);
        });
    }

    function showLoading(show) {
        if (elements.loadingSpinner) {
            elements.loadingSpinner.style.display = show ? 'flex' : 'none';
        }
    }

    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // ================= Event Bindings =================
    function bindEvents() {
        // Theme Toggle
        elements.themeToggleBtn.addEventListener('click', toggleTheme);

        // Form Submit
        elements.todoForm.addEventListener('submit', handleAddTodo);

        // Status Tabs
        elements.statusTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                elements.statusTabs.forEach(t => {
                    t.classList.remove('active');
                    t.setAttribute('aria-selected', 'false');
                });
                tab.classList.add('active');
                tab.setAttribute('aria-selected', 'true');
                state.currentStatus = tab.dataset.status;
                loadTodos();
            });
        });

        // Search Input (with debounce)
        let searchTimeout;
        elements.inputSearch.addEventListener('input', (e) => {
            const val = e.target.value;
            state.searchQuery = val;
            elements.btnClearSearch.style.display = val ? 'block' : 'none';

            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                loadTodos();
            }, 250);
        });

        elements.btnClearSearch.addEventListener('click', () => {
            elements.inputSearch.value = '';
            state.searchQuery = '';
            elements.btnClearSearch.style.display = 'none';
            loadTodos();
            elements.inputSearch.focus();
        });

        // Category Filter
        elements.filterCategory.addEventListener('change', (e) => {
            state.currentCategory = e.target.value;
            loadTodos();
        });

        // Sort Selector
        elements.filterSort.addEventListener('change', (e) => {
            state.currentSort = e.target.value;
            loadTodos();
        });

        // Clear Completed Button
        elements.btnClearCompleted.addEventListener('click', handleClearCompleted);

        // Modal Events
        elements.btnCloseModal.addEventListener('click', closeEditModal);
        elements.btnCancelEdit.addEventListener('click', closeEditModal);
        elements.editForm.addEventListener('submit', handleSaveEdit);

        // Close modal on escape or background click
        window.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && elements.editModal.classList.contains('active')) {
                closeEditModal();
            }
        });
        elements.editModal.addEventListener('click', (e) => {
            if (e.target === elements.editModal) {
                closeEditModal();
            }
        });
    }
});
