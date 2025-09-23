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

st.subheader("Tilføj udgift")
user = st.text_input("Navn")
amount = st.number_input("Beløb (DKK)", min_value=0.0, step=0.01)

if st.button("Gem udgift"):
    if user and amount > 0:
        add_expense(user, amount)
        st.success(f"{user} har lagt ud med {amount:.2f} kr.")
    else:
        st.error("Indtast navn og et beløb > 0")

expenses = get_expenses()

# --- Oversigt ---
if expenses:
    st.subheader("Aktuelle udgifter")
    for u, amounts in expenses.items():
        st.write(f"**{u}**: {sum(amounts):.2f} kr. (udlæg: {amounts})")

# --- Beregn afregning ---
if st.button("Beregn afregning") and expenses:
    results = settle_expenses(expenses)
    st.subheader("Afregning")
    if results:
        for r in results:
            st.write(r)
    else:
        st.write("Alle har allerede betalt lige meget ✅")
