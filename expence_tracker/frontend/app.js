const currency = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 2,
});

let expenses = [];
let editingId = null;
let pieChart = null;
const currentFilters = { startDate: '', endDate: '', category: '' };
let selectedMonth = '';

const loginOverlay = document.getElementById('login-overlay');
const loginForm = document.getElementById('login-form');
const loginToggleButtons = document.querySelectorAll('.login-toggle .pill');
const loginTitle = document.getElementById('login-title');
const loginSubtitle = document.getElementById('login-subtitle');
const loginSubmitBtn = loginForm ? loginForm.querySelector('button[type=\"submit\"]') : null;
const captchaRow = document.getElementById('captcha-row');
const captchaQuestion = document.getElementById('captcha-question');
const captchaAnswerInput = document.getElementById('captcha-answer');
const closeLoginBtn = document.getElementById('close-login');
const logoutBtn = document.getElementById('logout-btn');
const form = document.getElementById('expense-form');
const submitBtn = form.querySelector('button[type="submit"]');
const cancelEditBtn = document.getElementById('cancel-edit');
const recentList = document.getElementById('recent-list');
const entriesCount = document.getElementById('entries-count');
const recentMeta = document.getElementById('recent-meta');
const totalSpent = document.getElementById('total-spent');
const categoryTable = document.getElementById('category-table');
const heroMonthTotal = document.getElementById('hero-month-total');
const heroPrediction = document.getElementById('hero-prediction');
const currentMonthLabel = document.getElementById('current-month');
const monthTotal = document.getElementById('month-total');
const monthCount = document.getElementById('month-count');
const monthlyList = document.getElementById('monthly-list');
const filterForm = document.getElementById('filter-form');
const startInput = document.getElementById('filter-start');
const endInput = document.getElementById('filter-end');
const categoryInput = document.getElementById('filter-category');
const resetFiltersBtn = document.getElementById('reset-filters');
const exportBtn = document.getElementById('export-csv');
const monthFilter = document.getElementById('month-filter');
const refreshPredictorBtn = document.getElementById('refresh-predictor');
const predictedAmountEl = document.getElementById('predicted-amount');
const spendProfileEl = document.getElementById('spend-profile');
const savingTipEl = document.getElementById('saving-tip');
const recentAverageEl = document.getElementById('recent-average');

const API_BASE = '';
let authMode = 'login';
let captchaSolution = null;
let authToken = localStorage.getItem('expenseTrackerToken') || null;
let currentUser = null;
const CACHE_SUFFIXES = ['expenses', 'stats', 'monthly', 'predict'];

window.addEventListener('DOMContentLoaded', () => {
  if (loginForm) {
    loginForm.addEventListener('submit', handleLogin);
    loginToggleButtons.forEach((button) => {
      button.addEventListener('click', () => switchAuthMode(button.dataset.mode));
    });
    switchAuthMode('login');
  }
  if (monthFilter) {
    const today = new Date();
    const value = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`;
    monthFilter.value = value;
    selectedMonth = value;
    monthFilter.addEventListener('change', () => {
      selectedMonth = monthFilter.value;
      loadMonthly();
    });
  }
  form.addEventListener('submit', handleSubmit);
  cancelEditBtn.addEventListener('click', resetForm);
  if (filterForm) {
    filterForm.addEventListener('submit', applyFilters);
  }
  resetFiltersBtn.addEventListener('click', resetFilters);
  exportBtn.addEventListener('click', exportCsv);
  if (logoutBtn) {
    logoutBtn.addEventListener('click', handleLogout);
  }
  if (closeLoginBtn) {
    closeLoginBtn.addEventListener('click', () => {
      if (authToken) {
        hideLogin();
      } else {
        alert('Please log in or sign up to continue.');
      }
    });
  }
  if (refreshPredictorBtn) {
    refreshPredictorBtn.addEventListener('click', loadPrediction);
  }
  initializeApp();
});

async function initializeApp() {
  if (authToken) {
    try {
      await fetchCurrentUser();
      hideLogin();
      loadCachedDashboard();
      await refreshEverything();
      return;
    } catch (error) {
      console.error('Unable to fetch current user', error);
      handleUnauthorized();
    }
  }
  showLogin();
}

async function refreshEverything() {
  if (!authToken) return;
  await Promise.all([refreshExpenses(), loadStats(), loadMonthly(), loadPrediction()]);
}

async function refreshExpenses() {
  try {
    const data = await request('/expenses');
    expenses = data || [];
    entriesCount.textContent = expenses.length;
    renderRecent();
    cacheData('expenses', expenses);
  } catch (error) {
    console.error(error);
  }
}

function renderRecent() {
  const latest = expenses.slice(0, 10);
  recentMeta.textContent = `${latest.length} shown of ${expenses.length}`;
  recentList.innerHTML = '';
  if (!latest.length) {
    recentList.innerHTML = `<tr><td colspan="5" class="muted">No expenses logged yet.</td></tr>`;
    return;
  }
  latest.forEach((expense) => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${formatDate(expense.date)}</td>
      <td>${expense.category}</td>
      <td>${expense.description || '—'}</td>
      <td>${currency.format(expense.amount)}</td>
      <td>
        <div class="actions">
          <button type="button" data-action="edit">Edit</button>
          <button type="button" data-action="delete">Delete</button>
        </div>
      </td>
    `;
    row.querySelector('[data-action="edit"]').addEventListener('click', () => startEdit(expense));
    row.querySelector('[data-action="delete"]').addEventListener('click', () => deleteExpense(expense.id));
    recentList.appendChild(row);
  });
}

async function handleSubmit(event) {
  event.preventDefault();
  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());
  payload.amount = Number(payload.amount);
  const method = editingId ? 'PUT' : 'POST';
  const url = editingId ? `/expenses/${editingId}` : '/expenses';
  try {
    await request(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    resetForm();
    await refreshEverything();
  } catch (error) {
    alert(error.message || 'Unable to save expense');
  }
}

function startEdit(expense) {
  editingId = expense.id;
  form.amount.value = expense.amount;
  form.category.value = expense.category;
  form.date.value = expense.date;
  form.description.value = expense.description || '';
  submitBtn.textContent = 'Update expense';
  cancelEditBtn.hidden = false;
}

function resetForm() {
  editingId = null;
  form.reset();
  submitBtn.textContent = 'Save expense';
  cancelEditBtn.hidden = true;
}

async function deleteExpense(id) {
  if (!confirm('Delete this expense?')) return;
  try {
    await request(`/expenses/${id}`, { method: 'DELETE' });
    await refreshEverything();
  } catch (error) {
    alert(error.message || 'Unable to delete expense');
  }
}

function applyFilters(event) {
  event.preventDefault();
  currentFilters.startDate = startInput.value;
  currentFilters.endDate = endInput.value;
  currentFilters.category = categoryInput.value;
  loadStats();
}

function resetFilters() {
  startInput.value = '';
  endInput.value = '';
  categoryInput.value = '';
  currentFilters.startDate = '';
  currentFilters.endDate = '';
  currentFilters.category = '';
  loadStats();
}

async function exportCsv() {
  try {
    const response = await fetch(`${API_BASE}/expenses/export${buildFilterQuery()}`, {
      headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
    });
    if (response.status === 401) {
      handleUnauthorized();
      throw new Error('Unauthorized');
    }
    if (!response.ok) throw new Error('Unable to export');
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'expenses.csv';
    a.click();
    window.URL.revokeObjectURL(url);
  } catch (error) {
    alert(error.message || 'Export failed');
  }
}

async function loadStats() {
  try {
    const stats = await request(`/expenses/stats${buildFilterQuery()}`);
    if (!stats) return;
    const total = stats.totalSpent || 0;
    totalSpent.textContent = `${currency.format(total)} spent`;
    updateCategoryTable(stats.categoryTotals || [], total);
    updatePieChart(stats.categoryTotals || []);
    cacheData('stats', stats);
  } catch (error) {
    console.error(error);
  }
}

function buildFilterQuery() {
  const params = new URLSearchParams();
  if (currentFilters.startDate) params.set('start_date', currentFilters.startDate);
  if (currentFilters.endDate) params.set('end_date', currentFilters.endDate);
  if (currentFilters.category) params.set('category', currentFilters.category);
  const query = params.toString();
  return query ? `?${query}` : '';
}

function updateCategoryTable(rows, total) {
  categoryTable.innerHTML = '';
  if (!rows.length) {
    categoryTable.innerHTML = '<tr><td colspan="3" class="muted">No categories yet</td></tr>';
    return;
  }
  rows.forEach((row) => {
    const share = total ? ((row.total / total) * 100).toFixed(1) : '0.0';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${row.category}</td>
      <td>${currency.format(row.total)}</td>
      <td>${share}%</td>
    `;
    categoryTable.appendChild(tr);
  });
}

function updatePieChart(rows) {
  const ctx = document.getElementById('category-chart');
  const labels = rows.map((row) => row.category);
  const data = rows.map((row) => row.total);
  const colors = labels.map((_, index) => palette(index));
  if (pieChart) {
    pieChart.data.labels = labels;
    pieChart.data.datasets[0].data = data;
    pieChart.data.datasets[0].backgroundColor = colors;
    pieChart.update();
    return;
  }
  pieChart = new Chart(ctx, {
    type: 'pie',
    data: {
      labels,
      datasets: [
        {
          data,
          backgroundColor: colors,
        },
      ],
    },
    options: {
      plugins: {
        legend: { position: 'bottom' },
      },
    },
  });
}

async function loadMonthly() {
  try {
    const query = selectedMonth ? `?month=${selectedMonth}` : '';
    const monthly = await request(`/expenses/monthly${query}`);
    if (!monthly) return;
    heroMonthTotal.textContent = currency.format(monthly.total || 0);
    currentMonthLabel.textContent = monthly.month;
    monthTotal.textContent = currency.format(monthly.total || 0);
    monthCount.textContent = `${monthly.count} entries`;
    renderMonthlyList(monthly.expenses || []);
    cacheData('monthly', monthly);
  } catch (error) {
    console.error(error);
  }
}

function renderMonthlyList(list) {
  monthlyList.innerHTML = '';
  if (!list.length) {
    monthlyList.innerHTML = '<p class="muted">No expenses recorded in this month.</p>';
    return;
  }
  list.slice(0, 8).forEach((expense) => {
    const div = document.createElement('div');
    div.className = 'monthly-item';
    div.innerHTML = `
      <div>
        <strong>${expense.category}</strong>
        <p class="muted">${expense.description || '—'}</p>
      </div>
      <div>
        <p class="muted">${formatDate(expense.date)}</p>
        <p>${currency.format(expense.amount)}</p>
      </div>
    `;
    monthlyList.appendChild(div);
  });
}

async function fetchCurrentUser() {
  if (!authToken) return null;
  const profile = await request('/me');
  currentUser = profile.user;
  return currentUser;
}

async function handleLogin(event) {
  event.preventDefault();
  const formData = new FormData(loginForm);
  const email = formData.get('email')?.toString().trim();
  const username = formData.get('username')?.toString().trim();
  const password = formData.get('password')?.toString();
  if (!email || !username || !password) {
    alert('Please complete all fields.');
    return;
  }
  if (authMode === 'signup') {
    if (!captchaAnswerInput || captchaSolution === null) {
      alert('Captcha error. Please refresh and try again.');
      return;
    }
    const answer = Number(captchaAnswerInput.value);
    if (Number.isNaN(answer) || answer !== captchaSolution) {
      alert('Incorrect captcha answer. Please try again.');
      generateCaptcha();
      captchaAnswerInput.value = '';
      return;
    }
  }
  const endpoint = authMode === 'signup' ? '/auth/signup' : '/auth/login';
  const payload =
    authMode === 'signup'
      ? { email, username, password }
      : { email, password };
  try {
    const result = await request(endpoint, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    authToken = result.token;
    currentUser = result.user;
    localStorage.setItem('expenseTrackerToken', authToken);
    hideLogin();
    loadCachedDashboard();
    await refreshEverything();
  } catch (error) {
    alert(error.message || 'Authentication failed');
  }
}

function handleLogout() {
  handleUnauthorized();
}

const AUTH_COPY = {
  login: {
    title: 'Welcome back',
    subtitle: 'Sign in with your project credentials to open your dashboard.',
    button: 'Enter workspace',
  },
  signup: {
    title: 'Create an account',
    subtitle: 'Invite teammates or set up a new profile to begin tracking expenses.',
    button: 'Create account',
  },
};

function switchAuthMode(mode) {
  if (!mode || mode === authMode) return;
  authMode = mode;
  loginToggleButtons.forEach((btn) => {
    if (btn.dataset.mode === mode) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });
  const copy = AUTH_COPY[mode];
  if (loginTitle) loginTitle.textContent = copy.title;
  if (loginSubtitle) loginSubtitle.textContent = copy.subtitle;
  if (loginSubmitBtn) loginSubmitBtn.textContent = copy.button;
  if (captchaRow) {
    if (mode === 'signup') {
      captchaRow.classList.remove('hidden');
      generateCaptcha();
    } else {
      captchaRow.classList.add('hidden');
    }
  }
  if (captchaAnswerInput) {
    captchaAnswerInput.required = mode === 'signup';
  }
}

function hideLogin() {
  if (loginOverlay) {
    loginOverlay.classList.add('hidden');
  }
}

function showLogin() {
  if (loginOverlay) {
    loginOverlay.classList.remove('hidden');
  }
  if (loginForm) {
    loginForm.reset();
  }
  switchAuthMode('login');
}

function generateCaptcha() {
  if (!captchaQuestion) return;
  const a = Math.floor(Math.random() * 9) + 1;
  const b = Math.floor(Math.random() * 9) + 1;
  captchaSolution = a + b;
  captchaQuestion.textContent = `Prove you're human: ${a} + ${b} = ?`;
  if (captchaAnswerInput) {
    captchaAnswerInput.value = '';
  }
}

function handleUnauthorized() {
  authToken = null;
  currentUser = null;
  localStorage.removeItem('expenseTrackerToken');
  clearDashboard();
  showLogin();
}

function clearDashboard() {
  expenses = [];
  editingId = null;
  entriesCount.textContent = '0';
  recentMeta.textContent = '--';
  recentList.innerHTML = '';
  categoryTable.innerHTML = '';
  totalSpent.textContent = '₹0 spent';
  heroMonthTotal.textContent = '₹0';
  heroPrediction.textContent = '₹0';
  currentMonthLabel.textContent = '--';
  monthTotal.textContent = '₹0';
  monthCount.textContent = '0 entries';
  monthlyList.innerHTML = '<p class=\"muted\">Login to view your expenses.</p>';
  predictedAmountEl.textContent = '₹0';
  spendProfileEl.textContent = '--';
  savingTipEl.textContent = 'Add a few months of data to unlock the forecast.';
  recentAverageEl.textContent = '₹0';
}

function cacheKey(suffix) {
  if (!currentUser || !currentUser.id) return null;
  return `expenseTracker_${currentUser.id}_${suffix}`;
}

function cacheData(suffix, value) {
  const key = cacheKey(suffix);
  if (!key) return;
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (error) {
    console.warn('Unable to cache data', error);
  }
}

function getCachedData(suffix) {
  const key = cacheKey(suffix);
  if (!key) return null;
  const data = localStorage.getItem(key);
  if (!data) return null;
  try {
    return JSON.parse(data);
  } catch (error) {
    return null;
  }
}

function loadCachedDashboard() {
  if (!currentUser) return;
  const cachedExpenses = getCachedData('expenses');
  if (Array.isArray(cachedExpenses)) {
    expenses = cachedExpenses;
    entriesCount.textContent = expenses.length;
    renderRecent();
  }
  const cachedStats = getCachedData('stats');
  if (cachedStats) {
    const total = cachedStats.totalSpent || 0;
    totalSpent.textContent = `${currency.format(total)} spent`;
    updateCategoryTable(cachedStats.categoryTotals || [], total);
    updatePieChart(cachedStats.categoryTotals || []);
  }
  const cachedMonthly = getCachedData('monthly');
  if (cachedMonthly) {
    heroMonthTotal.textContent = currency.format(cachedMonthly.total || 0);
    currentMonthLabel.textContent = cachedMonthly.month || '--';
    monthTotal.textContent = currency.format(cachedMonthly.total || 0);
    monthCount.textContent = `${cachedMonthly.count || 0} entries`;
    renderMonthlyList(cachedMonthly.expenses || []);
  }
  const cachedPredict = getCachedData('predict');
  if (cachedPredict) {
    predictedAmountEl.textContent = currency.format(cachedPredict.predictedAmount || 0);
    heroPrediction.textContent = currency.format(cachedPredict.predictedAmount || 0);
    spendProfileEl.textContent = cachedPredict.spenderType || '--';
    savingTipEl.textContent = cachedPredict.suggestion || '';
    recentAverageEl.textContent = currency.format(cachedPredict.recentAverage || 0);
  }
}

async function loadPrediction() {
  try {
    const prediction = await request('/predict');
    if (!prediction) return;
    predictedAmountEl.textContent = currency.format(prediction.predictedAmount || 0);
    heroPrediction.textContent = currency.format(prediction.predictedAmount || 0);
    spendProfileEl.textContent = prediction.spenderType || '--';
    savingTipEl.textContent = prediction.suggestion || '';
    recentAverageEl.textContent = currency.format(prediction.recentAverage || 0);
    cacheData('predict', prediction);
  } catch (error) {
    console.error(error);
  }
}

async function request(path, options = {}) {
  const opts = { ...options };
  const headers = new Headers(options.headers || {});
  if (authToken) {
    headers.set('Authorization', `Bearer ${authToken}`);
  }
  if (opts.body && !(opts.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  opts.headers = headers;
  const response = await fetch(`${API_BASE}${path}`, opts);
  if (response.status === 401) {
    handleUnauthorized();
    throw new Error('Unauthorized');
  }
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.error || 'Request failed');
  }
  return response.status === 204 ? null : await response.json();
}

function formatDate(value) {
  if (!value) return '--';
  const date = new Date(value);
  return date.toLocaleDateString('en-IN', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
  });
}

function palette(index) {
  const colors = ['#2d6cdf', '#00b894', '#fdcb6e', '#a55eea', '#ff7675', '#00cec9', '#fab1a0'];
  return colors[index % colors.length];
}
