const API_URL = "http://127.0.0.1:5000";

function showAlert(msg, type) {
    const alert = document.getElementById("alertBox");
    alert.innerHTML = `<div class="alert ${type}">${msg}</div>`;
    setTimeout(() => alert.innerHTML = "", 3000);
}

async function addExpense() {
    let amount = document.getElementById("amount").value;
    let category = document.getElementById("category").value;
    let date = document.getElementById("date").value;
    let description = document.getElementById("description").value;

    if (!amount || !category || !date) {
        showAlert("Please fill all required fields!", "error");
        return;
    }

    let res = await fetch(`${API_URL}/expenses`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ amount, category, date, description })
    });

    if (res.ok) {
        showAlert("Expense added successfully!", "success");
        loadExpenses();
    }
}

async function loadExpenses() {
    let res = await fetch(`${API_URL}/expenses`);
    let data = await res.json();

    let list = document.getElementById("expenseList");
    list.innerHTML = "";

    data.forEach(exp => {
        list.innerHTML += `
            <div class="expense-item">
                <strong>${exp.category}</strong> - ${exp.amount} USD 
                <span class="edit-btn" onclick="editExpense(${exp.id})">✏ Edit</span>
                <span class="delete-btn" onclick="deleteExpense(${exp.id})">🗑 Delete</span>
                <br>
                <small>${exp.date}</small><br>
                ${exp.description || ""}
            </div>
        `;
    });
}

async function deleteExpense(id) {
    await fetch(`${API_URL}/expenses/${id}`, { method: "DELETE" });
    showAlert("Expense deleted", "success");
    loadExpenses();
}

async function editExpense(id) {
    let newAmount = prompt("New amount:");
    let newCategory = prompt("New category:");
    let newDate = prompt("New date (YYYY-MM-DD):");
    let newDesc = prompt("New description:");

    await fetch(`${API_URL}/expenses/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            amount: newAmount,
            category: newCategory,
            date: newDate,
            description: newDesc
        })
    });

    showAlert("Expense updated", "success");
    loadExpenses();
}

loadExpenses();
