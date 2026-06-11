# AntBarter Launch Runbook (Wed 06/10 → Sat 06/20)

This is the step-by-step playbook for the work that has to happen on the
Azure VM, on third-party dashboards (Stripe, Namecheap, Anthropic Console),
or in your phone — i.e. the steps I couldn't do from your laptop. Code-side
work is already on `main` of this repo; see "What I already changed" at the
bottom.

> **Security ground rules — re-read before each session.**
> 1. Never paste secrets (API keys, JWT secrets, Stripe keys) into HTML, JS,
>    git commits, screenshots, Slack messages, or Claude chats. They belong
>    in `~/AntBarter-AI-Test/src/backend/python/.env` only.
> 2. `chmod 600 ~/AntBarter-AI-Test/src/backend/python/.env` after editing.
> 3. Use the Stripe **test** key (`sk_test_…`) until you confirm SSL is on
>    your real domain. Live mode without SSL is a PCI violation.
> 4. Never open port 8000 on the Azure NSG. Nginx is the only thing that
>    talks to the outside world.

---

## 0. Push my code to your VM (5 min, do this first)

I edited files in this repo. You need to ship them to the VM before any of
the steps below.

```powershell
# On your laptop, in this repo:
git status
git add -A
git commit -m "Pre-launch: paywall, copy, mobile, categories"
git push origin main
```

```bash
# Then on the VM (SSH in first):
cd ~/AntBarter-AI-Test
git pull origin main
cd src/backend/python
source .venv/bin/activate     # or however you activate it
pip install -r requirements.txt   # picks up `stripe`
sudo systemctl restart antbarter-backend
sudo systemctl status antbarter-backend --no-pager
```

If `systemctl status` is green, move on.

---

## 1. Tonight (Wed 06/10) — Confirm the chatbot works (~30 min)

The original Tue 06/09 fix was: the homepage was calling
`http://<your-IP>:8000/api/ai/negotiate` directly instead of going through
Nginx. **I already fixed that** in `src/frontend/pages/AB_Home_UI2_Update.html`
— production now uses relative paths.

### 1a. Verify Claude key is real

```bash
cd ~/AntBarter-AI-Test/src/backend/python
grep ANTHROPIC_API_KEY .env
```

- If you see `ANTHROPIC_API_KEY=your_anthropic_api_key` or
  `sk-ant-your-key-here`: it's a placeholder. Go to
  https://console.anthropic.com → API keys → Create Key. Copy it once
  (you can't see it again).
- Paste it into `.env`:
  ```bash
  nano .env
  # Replace the placeholder line with:
  # ANTHROPIC_API_KEY=sk-ant-...   (your real key)
  ```
- Lock down permissions:
  ```bash
  chmod 600 .env
  ```
- Restart:
  ```bash
  sudo systemctl restart antbarter-backend
  ```

### 1b. End-to-end smoke test

Open Chrome on your laptop → `http://20.125.58.254` → F12 → Console tab.
Click "Start Trading Now" / scroll to the AI section. Send:

> Hi, I'm a licensed plumber in Phoenix looking to trade work

**Expected:** Within ~5s, a reply starting with `AntBarter Assistant (AI):`.

**If you see an error**, check Console + Network tab and look at the
`/api/ai/negotiate` request:

| What you see | What it means | Fix |
|---|---|---|
| `Failed to fetch` to `localhost:8000` | Old HTML cached | Hard refresh (Ctrl+Shift+R). If still bad, `curl http://20.125.58.254/api/ai/negotiate -X POST -H "Content-Type: application/json" -d '{}'` from your laptop to bypass cache. |
| `404` on `/api/ai/negotiate` | Nginx not proxying `/api/` | See §1c below |
| `502 Bad Gateway` | Backend isn't listening on 127.0.0.1:8000 | `sudo systemctl status antbarter-backend` and `sudo journalctl -u antbarter-backend -n 100 --no-pager` |
| `CORS policy` error | Origin not in allowed list | See §2 (Tue work, moved here) |
| `500` with "ANTHROPIC_API_KEY is not configured" | Key not loaded | Re-check §1a, restart the service |

### 1c. Sanity-check Nginx proxy (if 404 on /api/)

```bash
sudo cat /etc/nginx/sites-available/antbarter
```

You should see a block like:

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

If `location /api/` is missing, edit the file with `sudo nano`, add the
block inside the `server { … }` block, then:

```bash
sudo nginx -t           # MUST say "syntax is ok" before reloading
sudo systemctl reload nginx
```

### 1d. CORS (only if you saw a CORS error in §1b)

```bash
nano ~/AntBarter-AI-Test/src/backend/python/.env
```

Add (or uncomment):

```
CORS_ALLOW_ORIGINS=http://20.125.58.254
```

Then:

```bash
sudo systemctl restart antbarter-backend
```

When you cut over to your domain (Friday), change this to your domain. Do
**not** use `*` in production.

---

## 2. Wed (today) part 2 — Conversation quality test (~45 min)

Send these one at a time and write down each response:

1. "Hi, I'm a licensed plumber in Phoenix looking to trade work"
2. "I can do pipe repair, water heater installs, and drain clearing"
3. "I need someone who can do drywall patching after I open walls"
4. "I'm in Phoenix, AZ 85001 and available weekends"
5. "Can you draw up a trade record?"

Check:
- [ ] Every reply starts with `AntBarter Assistant (AI):`
- [ ] Replies are 1–3 sentences (no walls of text)
- [ ] Trade record has the seven sections: Parties, Services Offered, Scope of Work, Exchange Logistics, Timing, Dispute Process, Acknowledgement
- [ ] Trade record is titled `Trade Record (Draft -- not a legal contract)`

If responses violate any of the above, tell me what you saw — that's a
system prompt issue, not a connection issue.

---

## 3. Thu 06/11 — Confirm copy update is live (~15 min)

I already rewrote `AB_Home_UI2_Update.html` and added `AB_trade_categories.js`.
After you push (§0), refresh the homepage and verify:

- Hero: **"Trade Your Skills for What You Need — No Money Required"**
- Subtitle mentions plumbers / electricians / carpenters / contractors
- Search placeholder: "Search for plumbing, electrical, roofing, lawn care..."
- Category buttons: Plumbing, Electrical, Carpentry, HVAC, Landscaping, Handyman

Open it on your phone too (`http://20.125.58.254`). Mobile responsiveness
fixes I added: the AI chat input stacks Send vertically; category buttons
become a 2-column grid; all tap targets are ≥44px.

---

## 4. Fri 06/12 — Domain + SSL (~1 hr) — **YOU MUST DO THIS**

### 4a. Buy the domain (15 min)
Go to **Namecheap** or **Cloudflare Registrar** (Cloudflare is usually
cheaper, no upsells). Try in this order:
- `antbarter.com`
- `antbarterapp.com`
- `tradeantbarter.com`
- `antbarter.io`

Under $20/yr is fine. Turn ON WHOIS privacy.

### 4b. Point DNS at the VM (15 min)
In the registrar's DNS tab create **two A records**:

| Type | Host | Value | TTL |
|---|---|---|---|
| A | @ | 20.125.58.254 | Auto |
| A | www | 20.125.58.254 | Auto |

Wait 5–30 min, then on your laptop:

```powershell
nslookup yourdomain.com
nslookup www.yourdomain.com
```

Both must resolve to `20.125.58.254` before you proceed.

### 4c. Open ports 80 and 443 on Azure NSG (5 min)
Azure Portal → your VM → Networking → Inbound port rules.
Make sure 80/tcp and 443/tcp are open from `Any`. Do **not** open 8000.

### 4d. Install Let's Encrypt SSL (15 min)

```bash
sudo apt update
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

Answer the prompts:
- Email: your real email (used for expiry warnings)
- Agree to ToS: Yes
- Share email with EFF: optional
- Redirect HTTP to HTTPS: **option 2 (redirect)** — required for Stripe

Certbot installs a renewal timer automatically. Verify:

```bash
sudo systemctl list-timers | grep certbot
sudo certbot renew --dry-run
```

### 4e. Update Nginx `server_name` and CORS

```bash
sudo nano /etc/nginx/sites-available/antbarter
# Change:  server_name 20.125.58.254;
# To:      server_name yourdomain.com www.yourdomain.com;
sudo nginx -t
sudo systemctl reload nginx
```

Then update CORS:

```bash
nano ~/AntBarter-AI-Test/src/backend/python/.env
# Change CORS_ALLOW_ORIGINS to:
# CORS_ALLOW_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
sudo systemctl restart antbarter-backend
```

Test: `https://yourdomain.com` loads with a padlock, AI chat still works.

---

## 5. Sat 06/13 — Stripe (~3 hrs) — **YOU MUST DO THIS**

**I already wrote the backend (`app/billing.py`, `/api/subscribe`,
`/api/subscription-status`, `/api/stripe/webhook`) and the frontend modal.**
Your job: create the Stripe account, get the keys, paste them into `.env`,
flip `BILLING_ENFORCED=true`.

### 5a. Create the Stripe product (15 min)
- https://dashboard.stripe.com → Sign up (or log in).
- **Stay in test mode** for now (top-right toggle). Switch to live mode only after §5e succeeds.
- Products → Add product:
  - Name: `AntBarter AI`
  - Pricing model: Standard / Recurring / Monthly / $5.00 USD
  - Save. Copy the **Price ID** (looks like `price_1OABCxyz…`).
- Developers → API keys:
  - Copy the **Secret key** (`sk_test_…`).

### 5b. Set up the webhook (10 min)
Stripe → Developers → Webhooks → Add endpoint:
- Endpoint URL: `https://yourdomain.com/api/stripe/webhook`
- Events:
  - `checkout.session.completed`
  - `customer.subscription.created`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
- Save. Copy the **Signing secret** (`whsec_…`).

### 5c. Paste keys into `.env` (5 min)

```bash
nano ~/AntBarter-AI-Test/src/backend/python/.env
```

Add (test keys first — see §5e for live mode flip):

```
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PRICE_ID=price_1...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_SUCCESS_URL=https://yourdomain.com/?subscribed=1
STRIPE_CANCEL_URL=https://yourdomain.com/?subscribed=0
BILLING_ENFORCED=true
```

```bash
chmod 600 .env
sudo systemctl restart antbarter-backend
```

### 5d. Test mode end-to-end (30 min)
1. Open `https://yourdomain.com` in an incognito window.
2. Sign in (or use the dev token — see §6).
3. Send a chat message. Expected: the paywall modal pops up.
4. Click "Subscribe for $5/month" → redirected to Stripe Checkout.
5. Test card: `4242 4242 4242 4242`, any future date, any CVC, any zip.
6. After redirect back to your site, send another chat message — should
   go through.
7. Check the DB: `sqlite3 ~/AntBarter-AI-Test/src/backend/python/antbarter_local.db "SELECT * FROM subscriptions;"`
   Status should be `active`.
8. Check Stripe → Developers → Webhooks → Recent deliveries — all 2xx.

If any step fails, do not flip to live mode. Tell me what you saw.

### 5e. Switch to live mode (15 min) — only after §5d is green
- Stripe dashboard: top-right toggle → Live mode.
- Create the same Product and Price again (test/live are separate).
- Get the live Secret key, Price ID, Webhook secret (set up the webhook
  again in live mode with the same URL).
- Replace the three values in `.env` (`sk_live_…`, the live `price_…`,
  the live `whsec_…`). Keep `BILLING_ENFORCED=true`.
- `sudo systemctl restart antbarter-backend`
- Do **one** real $5 charge on your own card. Refund yourself from
  Stripe → Payments → ... → Refund.

---

## 6. Sun 06/14 — Sign-up / login flow (~3 hrs) — **partly you**

This depends on which auth path you pick. The backend already has a JWT
verifier (`app/auth.py`) and a "dev token" mode for local testing. The
frontend currently has `AB_SignIn.html` + `AB_SignUp_pg1.html` wired to
Node servers (`AB_signin_server.js`, `AB_user_auth_server.js`).

**Recommended cheapest path to launch:**
1. Add two endpoints to the FastAPI backend: `POST /api/auth/signup` and
   `POST /api/auth/login` that store a user row and return a JWT signed
   with `AUTH_JWT_SECRET`. Frontend saves the JWT to `sessionStorage`
   under the key `antbarter_auth_token` — the chatbot JS already reads
   from there.
2. Generate a strong secret: `openssl rand -hex 64` → paste into `.env` as
   `AUTH_JWT_SECRET=...`, then `AUTH_REQUIRED=true`,
   `AUTH_DEV_TOKENS_ALLOWED=false`. Restart.
3. Retire the Node auth servers (`AB_signin_server.js`,
   `AB_user_auth_server.js`) — running two stacks for auth is the #1
   security footgun.

When you're ready to do this, tell me and I'll write the endpoints. It's
~40 min of work that I can do on Sunday in this conversation.

End-to-end test path (walk it yourself, the way a stranger would):

1. Anonymous user → `https://yourdomain.com`
2. Click Sign Up → fill form → redirected to confirmation
3. Sign In → JWT lands in sessionStorage
4. Try to chat → paywall modal
5. Subscribe (test card) → Stripe Checkout → redirect back
6. Chat again → AI responds
7. Sign out → sessionStorage cleared, chat is paywalled again
8. Sign back in → status persists, no re-checkout

Write down every step that breaks. We fix them Monday.

---

## 7. Mon 06/15 — Fix Sunday's bugs (1 hr)
Priority order: (a) anything that crashes the page, (b) anything that
blocks payment, (c) anything that confuses the user.

## 8. Tue 06/16 — Mobile responsiveness (1 hr)
I already added the iPhone SE / 12 fixes. On Tuesday: open
`https://yourdomain.com` on your actual phone (not just DevTools) and
walk the full flow. Note any text that overflows, any button you can't
tap, any time the keyboard hides the input.

## 9. Wed 06/17 — Error handling + analytics (1 hr)
- I already added friendly errors (`friendlyErrorForStatus` in
  `AB_ai_chatbot.js` maps 401/402/413/429/5xx to plain English).
- Analytics: I added `scripts/antbarter_daily_stats.sh`. Drop it on the VM:
  ```bash
  cp ~/AntBarter-AI-Test/scripts/antbarter_daily_stats.sh ~/daily_stats.sh
  chmod +x ~/daily_stats.sh
  ./daily_stats.sh
  ```
  Run it manually each morning, or cron it:
  ```bash
  crontab -e
  # add:
  # 0 8 * * * /home/<user>/daily_stats.sh >> /home/<user>/antbarter-stats.log 2>&1
  ```

## 10. Thu 06/18 — Trade keywords + auto-shutdown
- I already added `src/backend/python/app/trade_categories.py` and the JS
  mirror. They're wired into the homepage.
- **Auto-shutdown (you must do this):**
  Azure Portal → your VM → Auto-shutdown → On → 11:00 PM your time →
  Email me at shutdown → Save.
  This saves 40–50% on compute. Manual start in the morning takes ~30s.

## 11. Fri 06/19 — Final E2E + launch posts
- Walk the flow one more time on your phone using a real $5 charge,
  then refund yourself from Stripe.
- Draft posts for: a Phoenix-area contractor Facebook group, Nextdoor,
  r/Contractors, r/HVAC, LinkedIn. Don't post yet.

## 12. Sat 06/20 — Launch day
- Final preflight: `https://yourdomain.com` loads with padlock, chat
  works, Stripe is live mode, DB writes succeed.
- Tail logs: `sudo tail -f /var/log/nginx/access.log` in one window,
  `sudo journalctl -u antbarter-backend -f` in another.
- Post to the 5 communities; text 5 contractors you know personally.
- Watch for the first real user — the first bug will appear within an
  hour. Fix it inline.

---

## What I already changed in the repo

| File | What I did | Maps to |
|---|---|---|
| `src/frontend/pages/AB_Home_UI2_Update.html` | Removed `localhost:8000`/`:8000` fallback; rewrote hero copy + search placeholder + category buttons for contractors; loaded shared category JS | Tue 06/09 Action 1, Thu 06/11 |
| `src/frontend/js/AB_ai_chatbot.js` | Added subscription pre-check, Stripe Checkout modal, friendly per-status error handling, bearer-token forwarding | Sat 06/13 paywall, Wed 06/17 error handling |
| `src/backend/python/app/billing.py` (new) | Stripe Checkout Session + webhook verification | Sat 06/13 |
| `src/backend/python/app/main.py` | `POST /api/subscribe`, `GET /api/subscription-status`, `POST /api/stripe/webhook`, paywall gate (402) on `/api/ai/negotiate` | Sat 06/13 |
| `src/backend/python/app/models.py` | `Subscription` table | Sat 06/13 |
| `src/backend/python/app/config.py` | `STRIPE_*` env vars, `BILLING_ENFORCED` flag | Sat 06/13 |
| `src/backend/python/app/schemas.py` | `SubscribeResponse`, `SubscriptionStatusResponse` | Sat 06/13 |
| `src/backend/python/app/trade_categories.py` (new) | Canonical blue-collar trade keyword map + `categorize_text()` | Thu 06/18 |
| `src/frontend/js/AB_trade_categories.js` (new) | JS mirror of the keyword map | Thu 06/18 |
| `src/frontend/css/AB_home2_update.css` | iPhone SE / 12 fixes: AI chat input row stacks, category 2-col grid, 44px tap targets | Tue 06/16 |
| `scripts/antbarter_daily_stats.sh` (new) | Daily SQLite stats runner | Wed 06/17 |
| `src/backend/python/.env.example` | Documents the new Stripe env vars | Sat 06/13 |
| `src/backend/python/requirements.txt` | Added `stripe` | Sat 06/13 |

### What I did NOT change
- The Anthropic key (you must paste your own; never let me see it).
- The Stripe keys (you must paste your own; same rule).
- Anything on the VM itself — file edits, systemctl, nginx, certbot.
- DNS, registrar, Azure portal config, the Stripe dashboard.
- The actual sign-up/login endpoints (depends on the choice in §6).
