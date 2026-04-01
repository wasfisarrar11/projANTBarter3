/**
 * API base URL: set window.__APP_CONFIG__.apiBaseUrl in a prior script (build/deploy step).
 * Same-origin: leave unset to call /api/... on the current host (reverse-proxy the API).
 * Never embed secrets or environment-specific credentials in this file.
 */
function getApiBaseUrl() {
  if (typeof window.__APP_CONFIG__ === "object" && window.__APP_CONFIG__.apiBaseUrl) {
    return String(window.__APP_CONFIG__.apiBaseUrl).replace(/\/$/, "");
  }
  return "";
}

function apiUrl(path) {
  const base = getApiBaseUrl();
  const p = path.startsWith("/") ? path : `/${path}`;
  if (!base) {
    return p;
  }
  return `${base}${p}`;
}

function getSessionNegotiationIds() {
  if (typeof sessionStorage === "undefined") {
    return {
      userId: "anon",
      listingId: "pending",
      counterpartyListingId: "pending",
    };
  }
  let sid = sessionStorage.getItem("antbarter_session_id");
  if (!sid) {
    sid =
      typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : String(Date.now());
    sessionStorage.setItem("antbarter_session_id", sid);
  }
  return {
    userId: sessionStorage.getItem("antbarter_user_id") || `anon-${sid.slice(0, 12)}`,
    listingId: sessionStorage.getItem("antbarter_listing_id") || "pending",
    counterpartyListingId:
      sessionStorage.getItem("antbarter_counterparty_listing_id") || "pending",
  };
}

const negotiationState = {
  messages: [],
};

function appendChatMessage(role, text) {
  const chatLog = document.getElementById("aiChatLog");
  if (!chatLog) return;

  const el = document.createElement("div");
  el.className = `ai-message ${role}`;
  el.textContent = text;
  chatLog.appendChild(el);
  chatLog.scrollTop = chatLog.scrollHeight;
}

async function sendNegotiationMessage() {
  const input = document.getElementById("aiChatInput");
  if (!input) return;

  const message = input.value.trim();
  if (!message) return;
  input.value = "";

  appendChatMessage("user", message);

  const priorMessages = negotiationState.messages.filter((m) => m.role !== "system");
  negotiationState.messages.push({ role: "user", content: message });

  const ids = getSessionNegotiationIds();
  const includeMp = document.getElementById("includeMarketplaceContext")?.checked;
  const countryRaw = document.getElementById("marketplaceCountry")?.value?.trim().toUpperCase() || "";
  const country = countryRaw.length === 2 ? countryRaw : undefined;

  const body = {
    user_id: ids.userId,
    listing_id: ids.listingId,
    counterparty_listing_id: ids.counterpartyListingId,
    latest_user_message: message,
    messages: priorMessages,
  };

  if (includeMp) {
    body.marketplace_search_query = message.slice(0, 200);
    if (country) {
      body.marketplace_listing_country_iso2 = country;
    }
  }

  try {
    const res = await fetch(apiUrl("/api/ai/negotiate"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      throw new Error(`Request failed: ${res.status}`);
    }

    const data = await res.json();
    const aiReply =
      data.ai_response || "I could not generate a response right now.";
    appendChatMessage("assistant", aiReply);
    negotiationState.messages.push({ role: "assistant", content: aiReply });
  } catch (error) {
    console.error(error);
    appendChatMessage(
      "system",
      "The assistant is temporarily unavailable. Please try again later."
    );
  }
}

async function generateAgreement() {
  const ids = getSessionNegotiationIds();
  const jurisdiction =
    document.getElementById("jurisdictionInput")?.value?.trim() || "";
  const includeMp = document.getElementById("includeMarketplaceContext")?.checked;
  const countryRaw = document.getElementById("marketplaceCountry")?.value?.trim().toUpperCase() || "";
  const country = countryRaw.length === 2 ? countryRaw : undefined;
  const lastUser = negotiationState.messages
    .filter((m) => m.role === "user")
    .pop();
  const mpQuery = includeMp && lastUser ? String(lastUser.content).slice(0, 200) : undefined;

  const body = {
    user_id: ids.userId,
    listing_id: ids.listingId,
    counterparty_listing_id: ids.counterpartyListingId,
    messages: negotiationState.messages.filter((m) => m.role !== "system"),
  };
  if (jurisdiction) {
    body.jurisdiction = jurisdiction;
  }
  if (mpQuery) {
    body.marketplace_search_query = mpQuery;
    if (country) {
      body.marketplace_listing_country_iso2 = country;
    }
  }

  try {
    const res = await fetch(apiUrl("/api/agreements/generate"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      throw new Error(`Request failed: ${res.status}`);
    }

    const data = await res.json();
    appendChatMessage("assistant", data.agreement_text || "No agreement returned.");
  } catch (error) {
    console.error(error);
    appendChatMessage(
      "system",
      "Agreement generation is temporarily unavailable. Please try again later."
    );
  }
}

window.addEventListener("DOMContentLoaded", () => {
  const sendBtn = document.getElementById("aiSendBtn");
  const input = document.getElementById("aiChatInput");
  const agreementBtn = document.getElementById("generateAgreementBtn");

  if (sendBtn) sendBtn.addEventListener("click", sendNegotiationMessage);
  if (agreementBtn) agreementBtn.addEventListener("click", generateAgreement);

  if (input) {
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        sendNegotiationMessage();
      }
    });
  }
});
