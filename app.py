import streamlit as st
import sqlite3
import hashlib

# --- Database-funktioner ---
def init_db():
    conn = sqlite3.connect("expenses.db")
    c = conn.cursor()
    # Opret tabel, hvis den ikke findes
    c.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            amount REAL
        )
    """)
    # Tilføj kolonnen 'payers', hvis den ikke findes
    c.execute("PRAGMA table_info(expenses)")
    columns = [info[1] for info in c.fetchall()]
    if 'payers' not in columns:
        c.execute("ALTER TABLE expenses ADD COLUMN payers TEXT")
    conn.commit()
    conn.close()

def add_expense(user, amount, payers=None):
    payers_str = ",".join(payers) if payers else user
    conn = sqlite3.connect("expenses.db")
    c = conn.cursor()
    c.execute("INSERT INTO expenses (user, amount, payers) VALUES (?, ?, ?)", (user, amount, payers_str))
    conn.commit()
    conn.close()

def get_expenses():
    conn = sqlite3.connect("expenses.db")
    c = conn.cursor()
    c.execute("SELECT user, amount, payers FROM expenses")
    rows = c.fetchall()
    conn.close()
    expenses = {}
    for user, amount, payers in rows:
        if user not in expenses:
            expenses[user] = []
        expenses[user].append((amount, payers))
    return expenses

def get_all_expenses():
    conn = sqlite3.connect("expenses.db")
    c = conn.cursor()
    c.execute("SELECT id, user, amount, payers FROM expenses ORDER BY id DESC")
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

    totals = {person: sum([amt for amt, _ in vals]) for person, vals in expenses.items()}
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

# --- Funktion til at generere faste farver ud fra navn ---
def get_color_from_name(name):
    hash_int = int(hashlib.md5(name.encode()).hexdigest(), 16)
    hue = hash_int % 360
    return f"hsl({hue}, 70%, 70%)"

# --- Streamlit App ---
st.title("💶 Berlin Tur - Regnskabsapp")
init_db()

# --- Opret bruger automatisk ---
st.subheader("Tilføj bruger")
user = st.text_input("Navn", key="user_input")
if user:
    expenses = get_expenses()
    if user not in expenses:
        add_expense(user, 0.0)
        st.info(f"{user} er oprettet med 0 kr.")

# --- Tilføj udgift med valgte deltagere ---
st.subheader("Tilføj udgift")
all_users = list(get_expenses().keys())
if all_users:
    payers = st.multiselect("Vælg hvem, der skal betale for udgiften", all_users)
    amount = st.number_input("Beløb (DKK)", min_value=0.0, step=0.01, key="amount_input", value=0.0)
    
    if st.button("Tilføj udgift"):
        if amount > 0 and payers:
            split_amount = amount / len(payers)
            for payer in payers:
                add_expense(payer, split_amount, payers)
            st.success(f"Udgift på {amount:.2f} kr. tilføjet og delt mellem: {', '.join(payers)}")
            # Reset number_input korrekt
            st.session_state['amount_input'] = 0.0
        else:
            st.error("Indtast et beløb > 0 og vælg mindst én person")

# --- Oversigt med farvede badges ---
expenses = get_expenses()
if expenses:
    st.subheader("Aktuelle udgifter")
    for u, vals in expenses.items():
        st.write(f"**{u}**: {sum([amt for amt, _ in vals]):.2f} kr.")
        for amt, payers_str in vals:
            payer_list = payers_str.split(",")
            badges_html = ""
            for payer in payer_list:
                color = get_color_from_name(payer)
                badges_html += f"<span style='background-color:{color}; color:black; padding:3px 6px; border-radius:5px; margin-right:3px;'>{payer}: {amt:.2f} kr.</span>"
            st.markdown(badges_html, unsafe_allow_html=True)

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
        [f"ID {exp_id} | {u} har lagt ud med {amt:.2f} kr. ({payers})" for exp_id, u, amt, payers in all_expenses]
    )
    if option:
        exp_id = int(option.split()[1])
        if st.button("Slet valgt udgift"):
            delete_expense(exp_id)
            st.success(f"Udgift {option} er slettet ✅")
else:
    st.write("Ingen udgifter at slette endnu.")
