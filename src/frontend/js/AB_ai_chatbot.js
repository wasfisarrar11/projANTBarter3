const AI_API_BASE_URL =
  window.AI_API_BASE_URL || "http://localhost:8000";

const negotiationState = {
  userId: "demo-user",
  listingId: "demo-listing",
  counterpartyListingId: "demo-counterparty",
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
  negotiationState.messages.push({ role: "user", content: message });

  try {
    const res = await fetch(`${AI_API_BASE_URL}/api/ai/negotiate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...negotiationState,
        latest_user_message: message,
      }),
    });

    if (!res.ok) {
      throw new Error(`Negotiation request failed: ${res.status}`);
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
      "AI service is unavailable. Please verify backend/API deployment."
    );
  }
}

async function generateAgreement() {
  try {
    const res = await fetch(`${AI_API_BASE_URL}/api/agreements/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...negotiationState,
        jurisdiction: "Arizona, USA",
      }),
    });

    if (!res.ok) {
      throw new Error(`Agreement request failed: ${res.status}`);
    }

    const data = await res.json();
    appendChatMessage("assistant", data.agreement_text || "No agreement returned.");
  } catch (error) {
    console.error(error);
    appendChatMessage(
      "system",
      "Agreement generation failed. Try again after backend setup."
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
