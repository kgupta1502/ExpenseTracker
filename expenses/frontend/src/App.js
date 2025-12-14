import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [formData, setFormData] = useState({
    amount: '',
    category: '',
    date: '',
    description: ''
  });
  const [expenses, setExpenses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Fetch expenses on component mount
  useEffect(() => {
    fetchExpenses();
  }, []);

  const fetchExpenses = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/expenses');
      setExpenses(response.data);
      setError('');
    } catch (err) {
      setError('Failed to fetch expenses. Make sure backend is running.');
      console.error('Fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Basic validation
    if (!formData.amount || !formData.category || !formData.date) {
      setError('Please fill in all required fields');
      return;
    }

    try {
      setLoading(true);
      await axios.post('/api/expenses', formData);

      // Reset form and refresh list
      setFormData({ amount: '', category: '', date: '', description: '' });
      fetchExpenses();
      setError('');
    } catch (err) {
      setError('Failed to add expense: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this expense?')) return;

    try {
      setLoading(true);
      await axios.delete(`/api/expenses/${id}`);
      fetchExpenses();
    } catch (err) {
      setError('Failed to delete expense');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      <header>
        <h1>💰 Expense Tracker - Module 1</h1>
        <p>Add, view, and manage your expenses</p>
      </header>

      <main>
        {error && <div className="error-message">{error}</div>}

        {/* Add Expense Form */}
        <section className="form-section">
          <h2>➕ Add New Expense</h2>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Amount ($)</label>
              <input
                type="number"
                name="amount"
                value={formData.amount}
                onChange={handleChange}
                placeholder="Enter amount"
                step="0.01"
                min="0"
                required
              />
            </div>

            <div className="form-group">
              <label>Category</label>
              <select
                name="category"
                value={formData.category}
                onChange={handleChange}
                required
              >
                <option value="">Select category</option>
                <option value="Food">Food</option>
                <option value="Transport">Transport</option>
                <option value="Shopping">Shopping</option>
                <option value="Bills">Bills</option>
                <option value="Entertainment">Entertainment</option>
                <option value="Other">Other</option>
              </select>
            </div>

            <div className="form-group">
              <label>Date</label>
              <input
                type="date"
                name="date"
                value={formData.date}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group">
              <label>Description (Optional)</label>
              <textarea
                name="description"
                value={formData.description}
                onChange={handleChange}
                placeholder="Add a description..."
                rows="2"
              />
            </div>

            <button type="submit" disabled={loading}>
              {loading ? 'Adding...' : 'Add Expense'}
            </button>
          </form>
        </section>

        {/* Expenses List */}
        <section className="list-section">
          <h2>📋 Recent Expenses (Last 10)</h2>

          {loading && expenses.length === 0 ? (
            <p>Loading expenses...</p>
          ) : expenses.length === 0 ? (
            <p>No expenses yet. Add your first expense!</p>
          ) : (
            <div className="expenses-table">
              <div className="table-header">
                <span>Date</span>
                <span>Category</span>
                <span>Amount</span>
                <span>Description</span>
                <span>Action</span>
              </div>

              {expenses.map((expense) => (
                <div key={expense.id} className="expense-row">
                  <span>{expense.date}</span>
                  <span className="category-badge">{expense.category}</span>
                  <span className="amount">${parseFloat(expense.amount).toFixed(2)}</span>
                  <span className="description">{expense.description || '-'}</span>
                  <span>
                    <button
                      onClick={() => handleDelete(expense.id)}
                      className="delete-btn"
                      disabled={loading}
                    >
                      Delete
                    </button>
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>

      <footer>
        <p>Module 1: Expense Logger | IIT Madras DT2 Project</p>
      </footer>
    </div>
  );
}

export default App;