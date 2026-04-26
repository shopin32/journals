const state = {
  journals: [],
  search: "",
  index: "all",
  quartile: "all",
};

const rows = document.querySelector("#journal-rows");
const emptyState = document.querySelector("#empty-state");
const count = document.querySelector("#journal-count");
const searchInput = document.querySelector("#search");
const indexFilter = document.querySelector("#index-filter");
const quartileFilter = document.querySelector("#quartile-filter");

function normalize(value) {
  return String(value || "").trim().toLowerCase();
}

function formatDate(value) {
  if (!value) return "Unknown";
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(date);
}

function formatPrice(price) {
  if (!price || price.type === "unknown") return "Unknown";
  if (price.type === "free") return "Free";
  const value = price.value ?? "";
  const currency = price.currency ?? "";
  return `${value} ${currency}`.trim() || "Unknown";
}

function journalMatchesIndex(journal) {
  const indexes = journal.indexes || {};
  if (state.index === "all") return true;
  if (state.index === "both") return indexes.scopus && indexes.web_of_science;
  return Boolean(indexes[state.index]);
}

function journalMatchesSearch(journal) {
  if (!state.search) return true;
  const haystack = [
    journal.title,
    journal.publisher,
    journal.issn,
    journal.eissn,
    formatPrice(journal.price),
    journal.quartile,
    journal.notes,
    ...(journal.subjects || []),
  ].map(normalize).join(" ");
  return haystack.includes(state.search);
}

function filteredJournals() {
  return state.journals.filter((journal) => {
    const quartile = journal.quartile || "Unranked";
    return journalMatchesSearch(journal)
      && journalMatchesIndex(journal)
      && (state.quartile === "all" || quartile === state.quartile);
  });
}

function badge(label, className = "") {
  const span = document.createElement("span");
  span.className = `badge ${className}`.trim();
  span.textContent = label;
  return span;
}

function renderRows() {
  const journals = filteredJournals();
  rows.replaceChildren();
  count.textContent = journals.length;
  emptyState.hidden = journals.length > 0;

  for (const journal of journals) {
    const tr = document.createElement("tr");
    const title = document.createElement("td");
    const titleLink = document.createElement(journal.url ? "a" : "strong");
    titleLink.textContent = journal.title;
    if (journal.url) {
      titleLink.href = journal.url;
      titleLink.rel = "noreferrer";
    }
    title.append(titleLink);

    if (journal.publisher) {
      const publisher = document.createElement("div");
      publisher.className = "publisher";
      publisher.textContent = journal.publisher;
      title.append(publisher);
    }

    if (journal.notes) {
      const notes = document.createElement("div");
      notes.className = "notes";
      notes.textContent = journal.notes;
      title.append(notes);
    }

    const indexes = document.createElement("td");
    const indexBadges = document.createElement("div");
    indexBadges.className = "badge-list";
    indexBadges.append(
      badge("Scopus", journal.indexes?.scopus ? "indexed" : "missing"),
      badge("Web of Science", journal.indexes?.web_of_science ? "indexed" : "missing"),
    );
    indexes.append(indexBadges);

    const issn = document.createElement("td");
    issn.innerHTML = [
      journal.issn ? `ISSN ${journal.issn}` : "",
      journal.eissn ? `eISSN ${journal.eissn}` : "",
    ].filter(Boolean).join("<br>");

    const price = document.createElement("td");
    price.textContent = formatPrice(journal.price);

    const quartile = document.createElement("td");
    quartile.textContent = journal.quartile || "Unranked";

    const subjects = document.createElement("td");
    const subjectBadges = document.createElement("div");
    subjectBadges.className = "badge-list";
    for (const subject of journal.subjects || []) {
      subjectBadges.append(badge(subject));
    }
    subjects.append(subjectBadges);

    const updated = document.createElement("td");
    updated.textContent = formatDate(journal.updated_at);

    tr.append(title, indexes, issn, price, quartile, subjects, updated);
    rows.append(tr);
  }
}

function renderQuartileOptions() {
  const quartiles = Array.from(new Set(
    state.journals.map((journal) => journal.quartile || "Unranked"),
  )).sort();

  for (const quartile of quartiles) {
    const option = document.createElement("option");
    option.value = quartile;
    option.textContent = quartile;
    quartileFilter.append(option);
  }
}

async function loadJournals() {
  const response = await fetch("data/journals.json");
  if (!response.ok) {
    throw new Error(`Could not load journals: ${response.status}`);
  }
  state.journals = await response.json();
  state.journals.sort((a, b) => a.title.localeCompare(b.title));
  renderQuartileOptions();
  renderRows();
}

searchInput.addEventListener("input", (event) => {
  state.search = normalize(event.target.value);
  renderRows();
});

indexFilter.addEventListener("change", (event) => {
  state.index = event.target.value;
  renderRows();
});

quartileFilter.addEventListener("change", (event) => {
  state.quartile = event.target.value;
  renderRows();
});

loadJournals().catch((error) => {
  rows.replaceChildren();
  emptyState.hidden = false;
  emptyState.textContent = error.message;
});
