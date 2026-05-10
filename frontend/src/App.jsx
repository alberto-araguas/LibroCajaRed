import { useEffect, useMemo, useState } from "react";
import {
  ArrowDownCircle,
  ArrowUpCircle,
  BookOpen,
  FileDown,
  LayoutDashboard,
  Mail,
  Moon,
  Pencil,
  Plus,
  Printer,
  RefreshCw,
  Save,
  Search,
  Sun,
  Tags,
  Trash2,
  Users,
  X,
} from "lucide-react";

import { api } from "./services/api";
import "./styles.css";

const today = new Date().toISOString().slice(0, 10);

const emptyForm = {
  account_code: "cash",
  counterparty_name: "",
  concept_name: "",
  type: "income",
  amount: "",
  transaction_date: today,
  notes: "",
};

function normalizeText(value) {
  return value
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, " ");
}

function findReferenceByName(items, value) {
  const normalizedValue = normalizeText(value);
  return items.find((item) => normalizeText(item.name) === normalizedValue);
}

const moneyFormatter = new Intl.NumberFormat("es-ES", {
  style: "currency",
  currency: "EUR",
});

function formatMoney(value) {
  return moneyFormatter.format(Number(value ?? 0));
}

function formatDate(value) {
  return new Intl.DateTimeFormat("es-ES").format(new Date(`${value}T00:00:00`));
}

function App() {
  const [activeView, setActiveView] = useState("dashboard");
  const [theme, setTheme] = useState(() => localStorage.getItem("theme") ?? "light");
  const [accounts, setAccounts] = useState([]);
  const [balances, setBalances] = useState({});
  const [transactions, setTransactions] = useState([]);
  const [counterparties, setCounterparties] = useState([]);
  const [concepts, setConcepts] = useState([]);
  const [filters, setFilters] = useState({
    date_from: "",
    date_to: "",
    account_code: "",
    type: "",
    counterparty: "",
    concept: "",
  });
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isSendingEmail, setIsSendingEmail] = useState(false);
  const [emailDialogOpen, setEmailDialogOpen] = useState(false);
  const [emailReport, setEmailReport] = useState({ type: "cashbook", transactionId: null });
  const [emailForm, setEmailForm] = useState({
    recipient: "",
    subject: "Libro de caja",
    message: "Adjunto encontrarás el informe del libro de caja en PDF.",
  });
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("theme", theme);
  }, [theme]);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData(nextFilters = filters) {
    setIsLoading(true);
    setError("");
    try {
      const [accountsData, balancesData, transactionsData, counterpartiesData, conceptsData] =
        await Promise.all([
          api.accounts(),
          api.balances(),
          api.transactions({ ...nextFilters, limit: 200 }),
          api.counterparties({ limit: 500 }),
          api.concepts({ limit: 500 }),
        ]);
      setAccounts(accountsData);
      setBalances(balancesData);
      setTransactions(transactionsData);
      setCounterparties(counterpartiesData);
      setConcepts(conceptsData);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }

  async function refreshAfterChange(message) {
    await loadData();
    setNotice(message);
  }

  function updateForm(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function updateFilter(field, value) {
    setFilters((current) => ({ ...current, [field]: value }));
  }

  async function applyFilters(event) {
    event.preventDefault();
    await loadData(filters);
  }

  async function clearFilters() {
    const cleanFilters = {
      date_from: "",
      date_to: "",
      account_code: "",
      type: "",
      counterparty: "",
      concept: "",
    };
    setFilters(cleanFilters);
    await loadData(cleanFilters);
  }

  function startEdit(transaction) {
    setEditingId(transaction.id);
    setForm({
      account_code: transaction.account.code,
      counterparty_name: transaction.counterparty.name,
      concept_name: transaction.concept.name,
      type: transaction.type,
      amount: transaction.amount,
      transaction_date: transaction.transaction_date,
      notes: transaction.notes ?? "",
    });
    setActiveView("cashbook");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function cancelEdit() {
    setEditingId(null);
    setForm(emptyForm);
  }

  async function saveTransaction(event) {
    event.preventDefault();
    setIsSaving(true);
    setError("");
    setNotice("");

    const selectedCounterparty = findReferenceByName(counterparties, form.counterparty_name);
    const selectedConcept = findReferenceByName(concepts, form.concept_name);

    if (!selectedCounterparty || !selectedConcept) {
      setError("Selecciona un nombre o empresa y un concepto existentes.");
      setIsSaving(false);
      return;
    }

    const payload = {
      ...form,
      counterparty_name: selectedCounterparty.name,
      concept_name: selectedConcept.name,
      amount: String(form.amount).replace(",", "."),
      notes: form.notes.trim() || null,
    };

    try {
      if (editingId) {
        await api.updateTransaction(editingId, payload);
        cancelEdit();
        await refreshAfterChange("Movimiento actualizado.");
      } else {
        await api.createTransaction(payload);
        setForm(emptyForm);
        await refreshAfterChange("Movimiento creado.");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function deleteTransaction(id) {
    if (!window.confirm("¿Eliminar este movimiento?")) {
      return;
    }
    setError("");
    setNotice("");
    try {
      await api.deleteTransaction(id);
      await refreshAfterChange("Movimiento eliminado.");
    } catch (err) {
      setError(err.message);
    }
  }

  const totalBalance = useMemo(
    () =>
      Object.values(balances).reduce((sum, account) => sum + Number(account.balance ?? 0), 0),
    [balances],
  );

  const recentTransactions = transactions.slice(0, 6);

  function printCashbook() {
    setActiveView("cashbook");
    window.setTimeout(() => window.print(), 100);
  }

  function exportCashbookPdf() {
    window.open(api.cashbookPdfUrl(filters), "_blank", "noopener,noreferrer");
  }

  function printMovementReport(transactionId) {
    window.open(api.movementPdfUrl(transactionId, { download: false }), "_blank", "noopener,noreferrer");
  }

  function exportMovementPdf(transactionId) {
    window.open(api.movementPdfUrl(transactionId), "_blank", "noopener,noreferrer");
  }

  function openCashbookEmailDialog() {
    setEmailReport({ type: "cashbook", transactionId: null });
    setEmailForm({
      recipient: "",
      subject: "Libro de caja",
      message: "Adjunto encontrarás el informe del libro de caja en PDF.",
    });
    setEmailDialogOpen(true);
  }

  function openMovementEmailDialog(transactionId) {
    setEmailReport({ type: "movement", transactionId });
    setEmailForm({
      recipient: "",
      subject: `Informe de movimiento ${transactionId}`,
      message: "Adjunto encontrarás el informe del movimiento en PDF.",
    });
    setEmailDialogOpen(true);
  }

  function updateEmailForm(field, value) {
    setEmailForm((current) => ({ ...current, [field]: value }));
  }

  async function sendReportEmail(event) {
    event.preventDefault();
    setIsSendingEmail(true);
    setError("");
    setNotice("");
    try {
      if (emailReport.type === "movement") {
        await api.emailMovementReport(emailReport.transactionId, emailForm);
      } else {
        const emailFilters = Object.fromEntries(
          Object.entries(filters).filter(([, value]) => value !== undefined && value !== null && value !== ""),
        );
        await api.emailCashbookReport({
          ...emailForm,
          filters: emailFilters,
        });
      }
      setEmailDialogOpen(false);
      setNotice("Informe enviado por email.");
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSendingEmail(false);
    }
  }

  return (
    <div className="app-layout">
      <Sidebar activeView={activeView} setActiveView={setActiveView} />

      <main className="main-area">
        <header className="topbar">
          <div>
            <p className="section-kicker">Libro de caja</p>
            <h1>{viewTitle(activeView)}</h1>
          </div>
          <div className="topbar-actions">
            <button className="icon-button" type="button" onClick={() => loadData()} title="Actualizar">
              <RefreshCw size={18} />
            </button>
            <button
              className="theme-toggle"
              type="button"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            >
              {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
              <span>{theme === "dark" ? "Modo claro" : "Modo oscuro"}</span>
            </button>
          </div>
        </header>

        {error && (
          <div className="alert alert-error" role="alert">
            {error}
          </div>
        )}
        {notice && (
          <div className="alert alert-success" role="status">
            {notice}
          </div>
        )}

        {activeView === "dashboard" && (
          <Dashboard
            balances={balances}
            totalBalance={totalBalance}
            recentTransactions={recentTransactions}
            setActiveView={setActiveView}
            isLoading={isLoading}
          />
        )}

        {activeView === "cashbook" && (
          <Cashbook
            accounts={accounts}
            balances={balances}
            counterparties={counterparties}
            concepts={concepts}
            transactions={transactions}
            filters={filters}
            form={form}
            editingId={editingId}
            isLoading={isLoading}
            isSaving={isSaving}
            updateFilter={updateFilter}
            clearFilters={clearFilters}
            applyFilters={applyFilters}
            updateForm={updateForm}
            saveTransaction={saveTransaction}
            cancelEdit={cancelEdit}
            startEdit={startEdit}
            deleteTransaction={deleteTransaction}
            printCashbook={printCashbook}
            exportCashbookPdf={exportCashbookPdf}
            printMovementReport={printMovementReport}
            exportMovementPdf={exportMovementPdf}
            openCashbookEmailDialog={openCashbookEmailDialog}
            openMovementEmailDialog={openMovementEmailDialog}
          />
        )}

        {activeView === "counterparties" && (
          <CounterpartyManager
            items={counterparties}
            createItem={api.createCounterparty}
            updateItem={api.updateCounterparty}
            deleteItem={api.deleteCounterparty}
            reload={() => refreshAfterChange("Listado actualizado.")}
          />
        )}

        {activeView === "concepts" && (
          <ReferenceManager
            title="Conceptos"
            singular="concepto"
            items={concepts}
            createItem={api.createConcept}
            updateItem={api.updateConcept}
            deleteItem={api.deleteConcept}
            reload={() => refreshAfterChange("Listado actualizado.")}
          />
        )}

        {emailDialogOpen && (
          <EmailDialog
            emailForm={emailForm}
            emailReport={emailReport}
            isSendingEmail={isSendingEmail}
            updateEmailForm={updateEmailForm}
            sendReportEmail={sendReportEmail}
            close={() => setEmailDialogOpen(false)}
          />
        )}
      </main>
    </div>
  );
}

function viewTitle(activeView) {
  const titles = {
    dashboard: "Panel",
    cashbook: "Movimientos",
    counterparties: "Nombres y empresas",
    concepts: "Conceptos",
  };
  return titles[activeView];
}

function Sidebar({ activeView, setActiveView }) {
  const items = [
    { id: "dashboard", label: "Panel", icon: LayoutDashboard },
    { id: "cashbook", label: "Movimientos", icon: BookOpen },
    { id: "counterparties", label: "Nombres y empresas", icon: Users },
    { id: "concepts", label: "Conceptos", icon: Tags },
  ];

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">LC</div>
        <div>
          <strong>Libro Caja</strong>
          <span>Control diario</span>
        </div>
      </div>
      <nav className="side-nav" aria-label="Navegación principal">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              className={activeView === item.id ? "active" : ""}
              type="button"
              onClick={() => setActiveView(item.id)}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
    </aside>
  );
}

function Dashboard({ balances, totalBalance, recentTransactions, setActiveView, isLoading }) {
  return (
    <div className="content-grid">
      <section className="balance-grid">
        <BalanceCard label="Efectivo" value={balances.cash?.balance} tone="cash" />
        <BalanceCard label="Tarjeta" value={balances.card?.balance} tone="card" />
        <BalanceCard label="Total" value={totalBalance} tone="total" />
      </section>

      <section className="panel-block">
        <div className="block-heading">
          <div>
            <h2>Últimos movimientos</h2>
            <p>{isLoading ? "Cargando..." : `${recentTransactions.length} movimientos recientes`}</p>
          </div>
          <button className="primary-button" type="button" onClick={() => setActiveView("cashbook")}>
            <Plus size={18} />
            Nuevo movimiento
          </button>
        </div>
        <TransactionTable
          transactions={recentTransactions}
          startEdit={() => setActiveView("cashbook")}
          deleteTransaction={null}
          compact
        />
      </section>
    </div>
  );
}

function BalanceCard({ label, value, tone }) {
  return (
    <article className={`balance-card ${tone}`}>
      <span>{label}</span>
      <strong>{formatMoney(value)}</strong>
    </article>
  );
}

function Cashbook(props) {
  const hasSavedMovement = Boolean(props.editingId);

  return (
    <div className="cashbook-layout">
      <section className="panel-block cashbook-movement-panel">
        <div className="block-heading">
          <div>
            <h2>{props.editingId ? "Editar movimiento" : "Nuevo movimiento"}</h2>
            <p>Saldo efectivo: {formatMoney(props.balances.cash?.balance)}</p>
          </div>
          <div className="report-actions movement-actions">
            <button
              className="ghost-button"
              type="button"
              disabled={!hasSavedMovement}
              onClick={() => props.printMovementReport(props.editingId)}
              title={hasSavedMovement ? "Abrir informe del movimiento" : "Guarda o selecciona un movimiento"}
            >
              <Printer size={18} />
              Imprimir
            </button>
            <button
              className="primary-button"
              type="button"
              disabled={!hasSavedMovement}
              onClick={() => props.exportMovementPdf(props.editingId)}
              title={hasSavedMovement ? "Exportar informe del movimiento" : "Guarda o selecciona un movimiento"}
            >
              <FileDown size={18} />
              Exportar PDF
            </button>
            <button
              className="primary-button"
              type="button"
              disabled={!hasSavedMovement}
              onClick={() => props.openMovementEmailDialog(props.editingId)}
              title={hasSavedMovement ? "Enviar informe del movimiento" : "Guarda o selecciona un movimiento"}
            >
              <Mail size={18} />
              Enviar email
            </button>
            {props.editingId && (
              <button className="ghost-button" type="button" onClick={props.cancelEdit}>
                <X size={18} />
                Cancelar
              </button>
            )}
          </div>
        </div>

        <TransactionForm
          accounts={props.accounts}
          counterparties={props.counterparties}
          concepts={props.concepts}
          form={props.form}
          editingId={props.editingId}
          isSaving={props.isSaving}
          updateForm={props.updateForm}
          saveTransaction={props.saveTransaction}
        />
      </section>

      <section className="panel-block cashbook-ledger-panel wide-block">
        <div className="block-heading">
          <div>
            <h2>Libro de caja</h2>
            <p>{props.isLoading ? "Cargando..." : `${props.transactions.length} movimientos`}</p>
          </div>
          <div className="report-actions">
            <button className="ghost-button" type="button" onClick={props.printCashbook}>
              <Printer size={18} />
              Imprimir
            </button>
            <button className="primary-button" type="button" onClick={props.exportCashbookPdf}>
              <FileDown size={18} />
              Exportar PDF
            </button>
            <button className="primary-button" type="button" onClick={props.openCashbookEmailDialog}>
              <Mail size={18} />
              Enviar email
            </button>
          </div>
        </div>

        <div className="print-header">
          <h2>Libro de caja</h2>
          <p>Listado de movimientos filtrados</p>
        </div>

        <Filters
          accounts={props.accounts}
          filters={props.filters}
          updateFilter={props.updateFilter}
          applyFilters={props.applyFilters}
          clearFilters={props.clearFilters}
        />

        <TransactionTable
          transactions={props.transactions}
          startEdit={props.startEdit}
          deleteTransaction={props.deleteTransaction}
        />
      </section>
    </div>
  );
}

function TransactionForm({
  accounts,
  counterparties,
  concepts,
  form,
  editingId,
  isSaving,
  updateForm,
  saveTransaction,
}) {
  return (
    <form className="transaction-form" onSubmit={saveTransaction}>
      <div className="form-grid">
        <div className="segmented movement-type-field" aria-label="Tipo de movimiento">
          <button
            className={form.type === "income" ? "selected" : ""}
            type="button"
            onClick={() => updateForm("type", "income")}
          >
            <ArrowUpCircle size={18} />
            Entrada
          </button>
          <button
            className={form.type === "expense" ? "selected" : ""}
            type="button"
            onClick={() => updateForm("type", "expense")}
          >
            <ArrowDownCircle size={18} />
            Retirada
          </button>
        </div>

        <label className="movement-compact-field">
          Cuenta
          <select value={form.account_code} onChange={(event) => updateForm("account_code", event.target.value)}>
            {accounts.map((account) => (
              <option key={account.code} value={account.code}>
                {account.name}
              </option>
            ))}
          </select>
        </label>

        <label className="movement-compact-field">
          Fecha
          <input
            type="date"
            value={form.transaction_date}
            onChange={(event) => updateForm("transaction_date", event.target.value)}
            required
          />
        </label>

        <label className="movement-compact-field">
          Cantidad
          <input
            type="text"
            inputMode="decimal"
            value={form.amount}
            onChange={(event) => updateForm("amount", event.target.value)}
            required
          />
        </label>

        <label className="movement-wide-field">
          Nombre o empresa
          <ReferenceAutocomplete
            items={counterparties}
            value={form.counterparty_name}
            onChange={(value) => updateForm("counterparty_name", value)}
            placeholder="Busca un nombre o empresa"
            required
          />
        </label>

        <label className="movement-wide-field">
          Concepto
          <ReferenceAutocomplete
            items={concepts}
            value={form.concept_name}
            onChange={(value) => updateForm("concept_name", value)}
            placeholder="Busca un concepto"
            required
          />
        </label>

        <label className="full-field">
          Notas
          <textarea value={form.notes} onChange={(event) => updateForm("notes", event.target.value)} rows="3" />
        </label>
      </div>

      <button className="primary-button submit-button" type="submit" disabled={isSaving}>
        <Save size={18} />
        {editingId ? "Guardar cambios" : "Crear movimiento"}
      </button>
    </form>
  );
}

function scoreReference(item, query) {
  const normalizedName = normalizeText(item.name);
  const normalizedQuery = normalizeText(query);

  if (!normalizedQuery) {
    return 0;
  }
  if (normalizedName === normalizedQuery) {
    return 1000;
  }
  if (normalizedName.startsWith(normalizedQuery)) {
    return 800 - normalizedName.length;
  }
  if (normalizedName.includes(normalizedQuery)) {
    return 600 - normalizedName.indexOf(normalizedQuery);
  }

  const words = normalizedQuery.split(" ");
  if (words.every((word) => normalizedName.includes(word))) {
    return 400 - normalizedName.length;
  }

  return -1;
}

function getReferenceMatches(items, query) {
  return items
    .map((item) => ({ item, score: scoreReference(item, query) }))
    .filter(({ score }) => score >= 0)
    .sort((left, right) => right.score - left.score || left.item.name.localeCompare(right.item.name))
    .slice(0, 8)
    .map(({ item }) => item);
}

function ReferenceAutocomplete({ items, value, onChange, placeholder, required = false }) {
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const matches = useMemo(() => getReferenceMatches(items, value), [items, value]);
  const hasExactMatch = Boolean(findReferenceByName(items, value));
  const showValidation = value.trim() !== "" && !hasExactMatch;

  function selectItem(item) {
    onChange(item.name);
    setIsOpen(false);
    setHighlightedIndex(0);
  }

  function updateValue(nextValue) {
    onChange(nextValue);
    setIsOpen(true);
    setHighlightedIndex(0);
  }

  function handleKeyDown(event) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setIsOpen(true);
      setHighlightedIndex((current) => Math.min(current + 1, Math.max(matches.length - 1, 0)));
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlightedIndex((current) => Math.max(current - 1, 0));
    }

    if (event.key === "Enter" && isOpen && matches[highlightedIndex]) {
      event.preventDefault();
      selectItem(matches[highlightedIndex]);
    }

    if (event.key === "Escape") {
      setIsOpen(false);
    }
  }

  return (
    <div className="reference-autocomplete">
      <input
        aria-invalid={showValidation}
        autoComplete="off"
        className={showValidation ? "invalid" : ""}
        onBlur={() => window.setTimeout(() => setIsOpen(false), 120)}
        onChange={(event) => updateValue(event.target.value)}
        onFocus={() => setIsOpen(true)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        required={required}
        value={value}
      />
      {isOpen && (
        <div className="autocomplete-menu" role="listbox">
          {matches.length > 0 ? (
            matches.map((item, index) => (
              <button
                className={index === highlightedIndex ? "highlighted" : ""}
                key={item.id}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => selectItem(item)}
                role="option"
                type="button"
              >
                {item.name}
              </button>
            ))
          ) : (
            <div className="autocomplete-empty">Sin coincidencias</div>
          )}
        </div>
      )}
      {showValidation && <span className="field-hint">Debe coincidir con un registro existente.</span>}
    </div>
  );
}

function Filters({ accounts, filters, updateFilter, applyFilters, clearFilters }) {
  return (
    <form className="filters" onSubmit={applyFilters}>
      <label>
        Desde
        <input
          type="date"
          value={filters.date_from}
          onChange={(event) => updateFilter("date_from", event.target.value)}
        />
      </label>
      <label>
        Hasta
        <input
          type="date"
          value={filters.date_to}
          onChange={(event) => updateFilter("date_to", event.target.value)}
        />
      </label>
      <label>
        Cuenta
        <select value={filters.account_code} onChange={(event) => updateFilter("account_code", event.target.value)}>
          <option value="">Todas</option>
          {accounts.map((account) => (
            <option key={account.code} value={account.code}>
              {account.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Tipo
        <select value={filters.type} onChange={(event) => updateFilter("type", event.target.value)}>
          <option value="">Todos</option>
          <option value="income">Entrada</option>
          <option value="expense">Retirada</option>
        </select>
      </label>
      <label>
        Nombre o empresa
        <input value={filters.counterparty} onChange={(event) => updateFilter("counterparty", event.target.value)} />
      </label>
      <label>
        Concepto
        <input value={filters.concept} onChange={(event) => updateFilter("concept", event.target.value)} />
      </label>
      <div className="filter-actions">
        <button className="primary-button" type="submit">
          <Search size={18} />
          Filtrar
        </button>
        <button className="ghost-button" type="button" onClick={clearFilters}>
          <X size={18} />
          Limpiar
        </button>
      </div>
    </form>
  );
}

function TransactionTable({ transactions, startEdit, deleteTransaction, compact = false }) {
  if (!transactions.length) {
    return <div className="empty-state">No hay movimientos.</div>;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Fecha</th>
            <th>Tipo</th>
            <th>Cuenta</th>
            <th>Nombre o empresa</th>
            <th>Concepto</th>
            <th className="amount-cell">Cantidad</th>
            {!compact && <th className="actions-cell">Acciones</th>}
          </tr>
        </thead>
        <tbody>
          {transactions.map((transaction) => (
            <tr key={transaction.id}>
              <td>{formatDate(transaction.transaction_date)}</td>
              <td>
                <span className={`type-pill ${transaction.type}`}>
                  {transaction.type === "income" ? "Entrada" : "Retirada"}
                </span>
              </td>
              <td>{transaction.account.name}</td>
              <td>{transaction.counterparty.name}</td>
              <td>{transaction.concept.name}</td>
              <td className={`amount-cell ${transaction.type}`}>
                {transaction.type === "expense" ? "-" : ""}
                {formatMoney(transaction.amount)}
              </td>
              {!compact && (
                <td className="actions-cell">
                  <button className="icon-button" type="button" onClick={() => startEdit(transaction)} title="Editar">
                    <Pencil size={17} />
                  </button>
                  <button
                    className="icon-button danger"
                    type="button"
                    onClick={() => deleteTransaction(transaction.id)}
                    title="Eliminar"
                  >
                    <Trash2 size={17} />
                  </button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const emptyCounterpartyForm = {
  name: "",
  dni_cif: "",
  address: "",
  phone: "",
  email: "",
};

function cleanCounterpartyPayload(form) {
  return {
    name: form.name.trim(),
    dni_cif: form.dni_cif.trim() || null,
    address: form.address.trim() || null,
    phone: form.phone.trim() || null,
    email: form.email.trim() || null,
  };
}

function CounterpartyManager({ items, createItem, updateItem, deleteItem, reload }) {
  const [form, setForm] = useState(emptyCounterpartyForm);
  const [query, setQuery] = useState("");
  const [editing, setEditing] = useState(null);
  const [localError, setLocalError] = useState("");

  const visibleItems = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) {
      return items;
    }
    return items.filter((item) =>
      [item.name, item.dni_cif, item.address, item.phone, item.email]
        .filter(Boolean)
        .some((value) => value.toLowerCase().includes(normalizedQuery)),
    );
  }, [items, query]);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function resetForm() {
    setForm(emptyCounterpartyForm);
    setEditing(null);
  }

  async function submit(event) {
    event.preventDefault();
    setLocalError("");
    try {
      const payload = cleanCounterpartyPayload(form);
      if (editing) {
        await updateItem(editing.id, payload);
      } else {
        await createItem(payload);
      }
      resetForm();
      await reload();
    } catch (err) {
      setLocalError(err.message);
    }
  }

  async function remove(item) {
    if (!window.confirm("¿Eliminar nombre o empresa?")) {
      return;
    }
    setLocalError("");
    try {
      await deleteItem(item.id);
      await reload();
    } catch (err) {
      setLocalError(err.message);
    }
  }

  function startEdit(item) {
    setEditing(item);
    setForm({
      name: item.name ?? "",
      dni_cif: item.dni_cif ?? "",
      address: item.address ?? "",
      phone: item.phone ?? "",
      email: item.email ?? "",
    });
  }

  return (
    <section className="panel-block">
      <div className="block-heading">
        <div>
          <h2>Nombres y empresas</h2>
          <p>{visibleItems.length} registros</p>
        </div>
      </div>

      {localError && (
        <div className="alert alert-error" role="alert">
          {localError}
        </div>
      )}

      <form className="counterparty-form" onSubmit={submit}>
        <label>
          Nombre o empresa
          <input value={form.name} onChange={(event) => updateField("name", event.target.value)} required />
        </label>
        <label>
          DNI/CIF
          <input value={form.dni_cif} onChange={(event) => updateField("dni_cif", event.target.value)} />
        </label>
        <label className="full-field">
          Dirección
          <input value={form.address} onChange={(event) => updateField("address", event.target.value)} />
        </label>
        <label>
          Teléfono
          <input value={form.phone} onChange={(event) => updateField("phone", event.target.value)} />
        </label>
        <label>
          Email
          <input
            type="text"
            inputMode="email"
            value={form.email}
            onChange={(event) => updateField("email", event.target.value)}
          />
        </label>
        <div className="form-actions full-field">
          <button className="primary-button" type="submit">
            {editing ? <Save size={18} /> : <Plus size={18} />}
            {editing ? "Guardar cambios" : "Crear"}
          </button>
          {editing && (
            <button className="ghost-button" type="button" onClick={resetForm}>
              <X size={18} />
              Cancelar
            </button>
          )}
        </div>
      </form>

      <label className="search-box">
        Buscar
        <input value={query} onChange={(event) => setQuery(event.target.value)} />
      </label>

      <div className="reference-list">
        {visibleItems.map((item) => (
          <div className="reference-row counterparty-row" key={item.id}>
            <div>
              <strong>{item.name}</strong>
              <div className="reference-details">
                <span>DNI/CIF: {item.dni_cif || "Sin indicar"}</span>
                <span>Dirección: {item.address || "Sin indicar"}</span>
                <span>Teléfono: {item.phone || "Sin indicar"}</span>
                <span>Email: {item.email || "Sin indicar"}</span>
              </div>
            </div>
            <div className="row-actions">
              <button className="icon-button" type="button" onClick={() => startEdit(item)} title="Editar">
                <Pencil size={17} />
              </button>
              <button className="icon-button danger" type="button" onClick={() => remove(item)} title="Eliminar">
                <Trash2 size={17} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function ReferenceManager({ title, singular, items, createItem, updateItem, deleteItem, reload }) {
  const [name, setName] = useState("");
  const [query, setQuery] = useState("");
  const [editing, setEditing] = useState(null);
  const [localError, setLocalError] = useState("");

  const visibleItems = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) {
      return items;
    }
    return items.filter((item) => item.name.toLowerCase().includes(normalizedQuery));
  }, [items, query]);

  async function submit(event) {
    event.preventDefault();
    setLocalError("");
    try {
      if (editing) {
        await updateItem(editing.id, { name });
      } else {
        await createItem({ name });
      }
      setName("");
      setEditing(null);
      await reload();
    } catch (err) {
      setLocalError(err.message);
    }
  }

  async function remove(item) {
    if (!window.confirm(`¿Eliminar ${singular}?`)) {
      return;
    }
    setLocalError("");
    try {
      await deleteItem(item.id);
      await reload();
    } catch (err) {
      setLocalError(err.message);
    }
  }

  return (
    <section className="panel-block">
      <div className="block-heading">
        <div>
          <h2>{title}</h2>
          <p>{visibleItems.length} registros</p>
        </div>
      </div>

      {localError && (
        <div className="alert alert-error" role="alert">
          {localError}
        </div>
      )}

      <form className="reference-form" onSubmit={submit}>
        <label>
          {editing ? "Editar" : "Nuevo"}
          <input value={name} onChange={(event) => setName(event.target.value)} required />
        </label>
        <button className="primary-button" type="submit">
          {editing ? <Save size={18} /> : <Plus size={18} />}
          {editing ? "Guardar" : "Crear"}
        </button>
        {editing && (
          <button
            className="ghost-button"
            type="button"
            onClick={() => {
              setEditing(null);
              setName("");
            }}
          >
            <X size={18} />
            Cancelar
          </button>
        )}
      </form>

      <label className="search-box">
        Buscar
        <input value={query} onChange={(event) => setQuery(event.target.value)} />
      </label>

      <div className="reference-list">
        {visibleItems.map((item) => (
          <div className="reference-row" key={item.id}>
            <div>
              <strong>{item.name}</strong>
              <span>{item.normalized_name}</span>
            </div>
            <div className="row-actions">
              <button
                className="icon-button"
                type="button"
                onClick={() => {
                  setEditing(item);
                  setName(item.name);
                }}
                title="Editar"
              >
                <Pencil size={17} />
              </button>
              <button className="icon-button danger" type="button" onClick={() => remove(item)} title="Eliminar">
                <Trash2 size={17} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function EmailDialog({ emailForm, emailReport, isSendingEmail, updateEmailForm, sendReportEmail, close }) {
  const isMovementReport = emailReport.type === "movement";

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal-panel" role="dialog" aria-modal="true" aria-labelledby="email-title">
        <div className="block-heading">
          <div>
            <h2 id="email-title">Enviar informe</h2>
            <p>
              {isMovementReport
                ? "Se adjuntará el PDF del movimiento seleccionado."
                : "Se adjuntará el PDF con los filtros actuales."}
            </p>
          </div>
          <button className="icon-button" type="button" onClick={close} title="Cerrar">
            <X size={18} />
          </button>
        </div>

        <form className="email-form" onSubmit={sendReportEmail}>
          <label>
            Destinatario
            <input
              type="text"
              inputMode="email"
              value={emailForm.recipient}
              onChange={(event) => updateEmailForm("recipient", event.target.value)}
              required
            />
          </label>
          <label>
            Asunto
            <input
              value={emailForm.subject}
              onChange={(event) => updateEmailForm("subject", event.target.value)}
              required
            />
          </label>
          <label>
            Mensaje
            <textarea
              rows="5"
              value={emailForm.message}
              onChange={(event) => updateEmailForm("message", event.target.value)}
            />
          </label>
          <div className="modal-actions">
            <button className="ghost-button" type="button" onClick={close}>
              <X size={18} />
              Cancelar
            </button>
            <button className="primary-button" type="submit" disabled={isSendingEmail}>
              <Mail size={18} />
              {isSendingEmail ? "Enviando..." : "Enviar"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

export default App;
