import streamlit as st
import sqlite3
import hashlib

# --- Database-funktioner ---
def init_db():
    conn = sqlite3.connect("expenses.db")
    c = conn.cursor()

    # Opret tabel for udgifter
    c.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            amount REAL
        )
    """)

    # Tjek kolonner
    c.execute("PRAGMA table_info(expenses)")
    columns = [info[1] for info in c.fetchall()]

    if 'paid_by' not in columns:
        c.execute("ALTER TABLE expenses ADD COLUMN paid_by TEXT")
        c.execute("UPDATE expenses SET paid_by = user")

    if 'payers' not in columns:
        c.execute("ALTER TABLE expenses ADD COLUMN payers TEXT")
        c.execute("UPDATE expenses SET payers = user")

    # Tjek om settlements-tabel findes
    c.execute("""
        CREATE TABLE IF NOT EXISTS settlements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            debtor TEXT,
            creditor TEXT,
            amount REAL,
            paid INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def add_expense(paid_by, amount, payers):
    payers_str = ",".join(payers)
    conn = sqlite3.connect("expenses.db")
    c = conn.cursor()
    c.execute("INSERT INTO expenses (paid_by, amount, payers) VALUES (?, ?, ?)", (paid_by, amount, payers_str))
    conn.commit()
    conn.close()

def get_expenses():
    conn = sqlite3.connect("expenses.db")
    c = conn.cursor()
    c.execute("SELECT id, paid_by, amount, payers FROM expenses")
    rows = c.fetchall()
    conn.close()
    expenses = {}
    for exp_id, paid_by, amount, payers in rows:
        if paid_by not in expenses:
            expenses[paid_by] = []
        expenses[paid_by].append((exp_id, amount, payers))
    return expenses

def get_all_expenses():
    conn = sqlite3.connect("expenses.db")
    c = conn.cursor()
    c.execute("SELECT id, paid_by, amount, payers FROM expenses ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def delete_expense(expense_id):
    conn = sqlite3.connect("expenses.db")
    c = conn.cursor()
    c.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()

# --- Afregning ---
def settle_expenses(expenses):
    if not expenses:
        return []

    totals = {person: sum([amt for _, amt, _ in vals]) for person, vals in expenses.items()}
    total_amount = sum(totals.values())
    num_people = len(expenses)
    fair_share = total_amount / num_people
    balances = {person: totals[person] - fair_share for person in totals}

    debtors = [(p, -bal) for p, bal in balances.items() if bal < 0]
    creditors = [(p, bal) for p, bal in balances.items() if bal > 0]

    settlements_list = []
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        debtor, debt = debtors[i]
        creditor, credit = creditors[j]
        amount = min(debt, credit)
        settlements_list.append(f"{debtor} skal betale {amount:.2f} kr. til {creditor}")
        debtors[i] = (debtor, debt - amount)
        creditors[j] = (creditor, credit - amount)
        if debtors[i][1] == 0:
            i += 1
        if creditors[j][1] == 0:
            j += 1
    return settlements_list

def save_settlements(expenses):
    conn = sqlite3.connect("expenses.db")
    c = conn.cursor()
    c.execute("DELETE FROM settlements")
    conn.commit()

    results = settle_expenses(expenses)
    for r in results:
        parts = r.split(" skal betale ")
        debtor = parts[0]
        rest = parts[1].split(" kr. til ")
        amount = float(rest[0])
        creditor = rest[1]
        c.execute("INSERT INTO settlements (debtor, creditor, amount, paid) VALUES (?, ?, ?, 0)", (debtor, creditor, amount))
    conn.commit()
    conn.close()

def mark_settlement_paid(settlement_id):
    conn = sqlite3.connect("expenses.db")
    c = conn.cursor()
    c.execute("UPDATE settlements SET paid = 1 WHERE id = ?", (settlement_id,))
    conn.commit()
    conn.close()

# --- Farvefunktion ---
def get_color_from_name(name):
    hash_int = int(hashlib.md5(name.encode()).hexdigest(), 16)
    hue = hash_int % 360
    return f"hsl({hue}, 70%, 70%)"

# --- Streamlit App ---
st.title("💶 Berlin Tur - Regnskabsapp")
init_db()

# --- Opret bruger ---
st.subheader("Tilføj bruger")
user = st.text_input("Navn", key="user_input")
if user:
    expenses = get_expenses()
    if user not in expenses:
        add_expense(user, 0.0, [user])
        st.info(f"{user} er oprettet med 0 kr.")

# --- Tilføj udgift ---
st.subheader("Tilføj udgift")
all_users = list(get_expenses().keys())
if all_users:
    with st.form(key="expense_form"):
        paid_by = st.selectbox("Hvem har lagt ud?", all_users)
        amount = st.number_input("Beløb (DKK)", min_value=0.0, step=0.01, value=0.0)
        payers = st.multiselect("Vælg hvem, der skal betale", all_users, default=[paid_by])
        submitted = st.form_submit_button("Tilføj udgift")
        if submitted:
            if amount > 0 and payers:
                split_amount = amount / len(payers)
                for payer in payers:
                    add_expense(paid_by, split_amount, payers)
                st.success(f"Udgift på {amount:.2f} kr. lagt af {paid_by} og delt mellem: {', '.join(payers)}")
            else:
                st.error("Indtast beløb > 0 og vælg mindst én person")

# --- Oversigt med badges ---
expenses = get_expenses()
if expenses:
    st.subheader("Aktuelle udgifter")
    for paid_by, vals in expenses.items():
        total = sum([amt for _, amt, _ in vals])
        st.write(f"**{paid_by} har lagt ud:** {total:.2f} kr.")
        for _, amt, payers_str in vals:
            payer_list = payers_str.split(",")
            badges_html = ""
            for payer in payer_list:
                color = get_color_from_name(payer)
                badges_html += f"<span style='background-color:{color}; color:black; padding:3px 6px; border-radius:5px; margin-right:3px;'>{payer}: {amt:.2f} kr.</span>"
            st.markdown(badges_html, unsafe_allow_html=True)

# --- Beregn afregning ---
if expenses and st.button("Beregn afregning"):
    save_settlements(expenses)
    st.subheader("Afregning")
    conn = sqlite3.connect("expenses.db")
    c = conn.cursor()
    c.execute("SELECT id, debtor, creditor, amount, paid FROM settlements ORDER BY id")
    rows = c.fetchall()
    conn.close()

    for settlement_id, debtor, creditor, amount, paid in rows:
        label = f"{debtor} skal betale {amount:.2f} kr. til {creditor}"
        if paid:
            st.markdown(f"✅ {label}")
        else:
            if st.checkbox(f"Betalt? {label}", key=f"settlement_{settlement_id}"):
                mark_settlement_paid(settlement_id)
                st.success(f"Betalingen er markeret som gennemført ✅")

# --- Slet udgift ---
st.subheader("Slet en udgift")
all_expenses = get_all_expenses()
if all_expenses:
    option = st.selectbox(
        "Vælg en udgift at slette",
        [f"ID {exp_id} | {paid_by} har lagt ud med {amount:.2f} kr. ({payers})" for exp_id, paid_by, amount, payers in all_expenses]
    )
    if option:
        exp_id = int(option.split()[1])
        if st.button("Slet valgt udgift"):
            delete_expense(exp_id)
            st.success(f"Udgift {option} er slettet ✅")
else:
    st.write("Ingen udgifter at slette endnu.")

# --- RESET APP (kun administrator) ---
st.markdown("---")
st.subheader("⚠️ Administrator: Nulstil app")
st.markdown(
    "Denne funktion sletter **alle udgifter og brugere**. Brug kun hvis du er administrator!"
)
if st.button("NULSTIL APP"):
    conn = sqlite3.connect("expenses.db")
    c = conn.cursor()
    c.execute("DELETE FROM expenses")
    c.execute("DELETE FROM settlements")
    conn.commit()
    conn.close()
    st.success("Appen er nulstillet ✅ Alle udgifter og brugere er slettet.")



st.subheader("COPYRIGHT CHRISTIAN LOFT CONSULTANCY AND BIG MONEY")
