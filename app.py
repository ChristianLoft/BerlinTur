import streamlit as st
import sqlite3

# --- Database-funktioner ---
def init_db():
    conn = sqlite3.connect("expenses.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            amount REAL
        )
    """)
    conn.commit()
    conn.close()

def add_expense(user, amount):
    conn = sqlite3.connect("expenses.db")
    c = conn.cursor()
    c.execute("INSERT INTO expenses (user, amount) VALUES (?, ?)", (user, amount))
    conn.commit()
    conn.close()

def get_expenses():
    conn = sqlite3.connect("expenses.db")
    c = conn.cursor()
    c.execute("SELECT user, amount FROM expenses")
    rows = c.fetchall()
    conn.close()
    expenses = {}
    for user, amount in rows:
        if user not in expenses:
            expenses[user] = []
        expenses[user].append(amount)
    return expenses

def get_all_expenses():
    conn = sqlite3.connect("expenses.db")
    c = conn.cursor()
    c.execute("SELECT id, user, amount FROM expenses ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def delete_expense(expense_id):
    conn = sqlite3.connect("expenses.db")
    c = conn.cursor()
    c.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()

# --- Beregning ---
def settle_expenses(expenses):
    if not expenses:
        return []

    totals = {person: sum(beløb) for person, beløb in expenses.items()}
    total_amount = sum(totals.values())
    num_people = len(expenses)
    fair_share = total_amount / num_people
    balances = {person: totals[person] - fair_share for person in totals}

    debtors = [(p, -bal) for p, bal in balances.items() if bal < 0]
    creditors = [(p, bal) for p, bal in balances.items() if bal > 0]

    settlements = []
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        debtor, debt = debtors[i]
        creditor, credit = creditors[j]
        amount = min(debt, credit)
        settlements.append(f"{debtor} skal betale {amount:.2f} kr. til {creditor}")
        debtors[i] = (debtor, debt - amount)
        creditors[j] = (creditor, credit - amount)
        if debtors[i][1] == 0:
            i += 1
        if creditors[j][1] == 0:
            j += 1
    return settlements

# --- Streamlit App ---
st.title("💶 Berlin Tur - Regnskabsapp")
init_db()

# --- Opret bruger automatisk og tilføj udgift ---
st.subheader("Tilføj bruger og udgift")
user = st.text_input("Navn")
amount = st.number_input("Beløb (DKK)", min_value=0.0, step=0.01)

if user:
    expenses = get_expenses()
    if user not in expenses:
        add_expense(user, 0.0)
        st.info(f"{user} er oprettet med 0 kr.")

    # Gem beløb automatisk, hvis > 0
    if amount > 0:
        add_expense(user, amount)
        st.success(f"{user} har lagt ud med {amount:.2f} kr.")

# --- Oversigt ---
expenses = get_expenses()
if expenses:
    st.subheader("Aktuelle udgifter")
    for u, amounts in expenses.items():
        st.write(f"**{u}**: {sum(amounts):.2f} kr. (udlæg: {amounts})")

# --- Beregn afregning ---
if expenses and st.button("Beregn afregning"):
    results = settle_expenses(expenses)
    st.subheader("Afregning")
    if results:
        for r in results:
            st.write(r)
    else:
        st.write("Alle har allerede betalt lige meget ✅")

# --- Slet udgift ---
st.subheader("Slet en udgift")
all_expenses = get_all_expenses()
if all_expenses:
    option = st.selectbox(
        "Vælg en udgift at slette",
        [f"ID {exp_id} | {u} har lagt ud med {amt:.2f} kr." for exp_id, u, amt in all_expenses]
    )
    if option:
        exp_id = int(option.split()[1])
        if st.button("Slet valgt udgift"):
            delete_expense(exp_id)
            st.success(f"Udgift {option} er slettet ✅")
else:
    st.write("Ingen udgifter at slette endnu.")
