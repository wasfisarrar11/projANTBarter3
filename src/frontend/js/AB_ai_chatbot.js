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

function getAuthHeaders() {
  // Reads the bearer token saved by the sign-in flow. Never reads it from a
  // global / window object that a third-party script could overwrite.
  try {
    const tok = sessionStorage.getItem("antbarter_auth_token") || "";
    return tok ? { Authorization: `Bearer ${tok}` } : {};
  } catch (_) {
    return {};
  }
}

function friendlyErrorForStatus(s) {
  if (s === 401) return "Please sign in to continue.";
  if (s === 402) return "Subscribe to use the AI assistant.";
  if (s === 413) return "That message is too long. Please shorten it.";
  if (s === 429) return "You've hit today's free limit. Try again tomorrow.";
  if (s >= 500) return "Something went wrong on our end. Try again in a minute.";
  return "Couldn't send that. Check your connection and try again.";
}

async function fetchSubscriptionStatus() {
  try {
    const res = await fetch(apiUrl("/api/subscription-status"), {
      method: "GET",
      headers: { ...getAuthHeaders() },
    });
    if (!res.ok) return { subscribed: false, status: "unknown" };
    return await res.json();
  } catch (_) {
    return { subscribed: false, status: "unknown" };
  }
}

function ensurePaywallModal() {
  let modal = document.getElementById("antbarterPaywallModal");
  if (modal) return modal;
  modal = document.createElement("div");
  modal.id = "antbarterPaywallModal";
  modal.setAttribute("role", "dialog");
  modal.setAttribute("aria-modal", "true");
  modal.setAttribute("aria-labelledby", "antbarterPaywallTitle");
  modal.style.cssText =
    "position:fixed;inset:0;background:rgba(0,0,0,0.55);" +
    "display:none;align-items:center;justify-content:center;z-index:9999;";
  modal.innerHTML =
    '<div style="background:#fff;max-width:420px;width:92%;padding:28px;' +
    'border-radius:12px;box-shadow:0 12px 32px rgba(0,0,0,0.25);' +
    'font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;">' +
    '<h2 id="antbarterPaywallTitle" style="margin:0 0 12px 0;font-size:1.3em;color:#222;">Subscribe to AntBarter AI</h2>' +
    '<p style="margin:0 0 18px 0;color:#444;line-height:1.5;">' +
    '$5/month for unlimited trade negotiation. Cancel anytime.</p>' +
    '<button id="antbarterPaywallSubBtn" style="width:100%;padding:12px 16px;' +
    'background:#e94e77;color:#fff;border:0;border-radius:8px;font-size:1em;' +
    'font-weight:600;cursor:pointer;">Subscribe for $5/month</button>' +
    '<button id="antbarterPaywallCancelBtn" style="width:100%;margin-top:10px;' +
    'padding:10px 16px;background:transparent;color:#666;border:0;' +
    'cursor:pointer;">Not now</button>' +
    '<p id="antbarterPaywallError" style="color:#c0392b;margin:12px 0 0 0;' +
    'min-height:1.2em;font-size:0.9em;"></p>' +
    "</div>";
  document.body.appendChild(modal);
  modal.querySelector("#antbarterPaywallCancelBtn").addEventListener("click", () => {
    modal.style.display = "none";
  });
  modal.querySelector("#antbarterPaywallSubBtn").addEventListener("click", async () => {
    const btn = modal.querySelector("#antbarterPaywallSubBtn");
    const err = modal.querySelector("#antbarterPaywallError");
    btn.disabled = true;
    btn.textContent = "Redirecting...";
    err.textContent = "";
    try {
      const res = await fetch(apiUrl("/api/subscribe"), {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
      });
      if (res.status === 401) {
        err.textContent = "Please sign in first, then try again.";
        return;
      }
      if (!res.ok) {
        err.textContent = friendlyErrorForStatus(res.status);
        return;
      }
      const data = await res.json();
      if (data && data.checkout_url) {
        // Stripe Checkout is hosted by Stripe; full top-level navigation.
        window.location.assign(data.checkout_url);
      } else {
        err.textContent = "Couldn't start checkout. Try again in a minute.";
      }
    } catch (_) {
      err.textContent = "Network error. Check your connection and try again.";
    } finally {
      btn.disabled = false;
      btn.textContent = "Subscribe for $5/month";
    }
  });
  return modal;
}

function showPaywall() {
  ensurePaywallModal().style.display = "flex";
}

async function sendNegotiationMessage() {
  const input = document.getElementById("aiChatInput");
  if (!input) return;

  const message = input.value.trim();
  if (!message) return;

  // Paywall pre-check. We still gate server-side (402) — this is just to
  // avoid bouncing the user through a refusal round-trip when we already
  // know they're not subscribed.
  const status = await fetchSubscriptionStatus();
  if (!status.subscribed && status.status !== "unknown") {
    showPaywall();
    return;
  }

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
      headers: { "Content-Type": "application/json", ...getAuthHeaders() },
      body: JSON.stringify(body),
    });

    if (res.status === 402) {
      showPaywall();
      return;
    }

    if (!res.ok) {
      appendChatMessage("system", friendlyErrorForStatus(res.status));
      return;
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
      "Couldn't reach the assistant. Check your connection and try again."
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
      headers: { "Content-Type": "application/json", ...getAuthHeaders() },
      body: JSON.stringify(body),
    });

    if (res.status === 402) {
      showPaywall();
      return;
    }

    if (!res.ok) {
      appendChatMessage("system", friendlyErrorForStatus(res.status));
      return;
    }

    const data = await res.json();
    appendChatMessage("assistant", data.agreement_text || "No agreement returned.");
  } catch (error) {
    console.error(error);
    appendChatMessage(
      "system",
      "Couldn't generate the agreement. Try again in a minute."
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
