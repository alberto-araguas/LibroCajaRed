const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

function buildQuery(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, value);
    }
  });
  const text = query.toString();
  return text ? `?${text}` : "";
}

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (response.status === 204) {
    return null;
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = data?.detail;
    throw new Error(typeof detail === "string" ? detail : "No se pudo completar la operación.");
  }

  return data;
}

export const api = {
  accounts: () => request("/accounts"),
  balances: () => request("/accounts/balances"),
  transactions: (filters) => request(`/transactions${buildQuery(filters)}`),
  createTransaction: (payload) =>
    request("/transactions", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateTransaction: (id, payload) =>
    request(`/transactions/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deleteTransaction: (id) =>
    request(`/transactions/${id}`, {
      method: "DELETE",
    }),
  counterparties: (params) => request(`/counterparties${buildQuery(params)}`),
  createCounterparty: (payload) =>
    request("/counterparties", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateCounterparty: (id, payload) =>
    request(`/counterparties/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deleteCounterparty: (id) =>
    request(`/counterparties/${id}`, {
      method: "DELETE",
    }),
  concepts: (params) => request(`/concepts${buildQuery(params)}`),
  createConcept: (payload) =>
    request("/concepts", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateConcept: (id, payload) =>
    request(`/concepts/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deleteConcept: (id) =>
    request(`/concepts/${id}`, {
      method: "DELETE",
    }),
  emailCashbookReport: (payload) =>
    request("/reports/cashbook/email", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  cashbookPdfUrl: (filters) => `${API_URL}/reports/cashbook/pdf${buildQuery(filters)}`,
  movementPdfUrl: (transactionId, params) => `${API_URL}/reports/movements/${transactionId}/pdf${buildQuery(params)}`,
  emailMovementReport: (transactionId, payload) =>
    request(`/reports/movements/${transactionId}/email`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
