# Water Billing System (FastAPI)

Minimal web application to manage customers, meter readings, invoices, and notifications.

Features:
- Manage customers (name, phone, email, location)
- Record meter readings (previous/current)
- Generate invoices based on readings and `RATE_PER_UNIT`
- Send invoices via Email / SMS / WhatsApp (SMTP / Twilio pluggable adapters)
- Automatic status updates and reminder after 5 days of delay
- Uses SQLite (SQLAlchemy) for relational storage

Quick start

1. Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r "c:\water billing system\requirements.txt"
```

2. Copy `.env.example` to `.env` and configure SMTP/Twilio if you want messaging.

3. Create PWA icons (optional but recommended for mobile installation):
   - Create `static/icon-192.png` (192x192 pixels)
   - Create `static/icon-512.png` (512x512 pixels)
   - These can be simple water drop or billing-related icons

4. Run the app:

```powershell
env | Out-File -Encoding ASCII .env # (or set env vars)
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

5. Visit `http://127.0.0.1:8000` to use the mobile-responsive UI. Use the OpenAPI UI at `/docs` for API.

## Mobile & Offline Features

The app is now a Progressive Web App (PWA) with:
- **Mobile-responsive design**: Optimized for phones and tablets
- **Offline caching**: Service worker caches essential files
- **Installable**: Can be installed on mobile devices like a native app
- **Offline data storage**: Uses IndexedDB for local data storage
- **Automatic sync**: Syncs data when connection is restored

Notes
- Twilio/WhatsApp integration requires valid credentials and numbers.
- The scheduler runs inside the app process (APScheduler). For production, use a separate worker.
 
Twilio / Notifications

- To enable Twilio SMS or WhatsApp, set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_NUMBER` in your `.env`.
- For SMS use an E.164 number like `+15551234567`.
- For WhatsApp use the Twilio WhatsApp format: `whatsapp:+15551234567` for both `TWILIO_FROM_NUMBER` and your customer's phone number.
 - For WhatsApp use the Twilio WhatsApp format: `whatsapp:+15551234567` for both `TWILIO_FROM_NUMBER` and your customer's phone number.
 - You can also provide a Twilio Messaging Service SID in `TWILIO_MESSAGING_SERVICE_SID`. If present the app will prefer the Messaging Service to send messages; otherwise it falls back to `TWILIO_FROM_NUMBER`.
 - The app will attempt to send the invoice via email (if `SMTP_*` configured) and via Twilio when `TWILIO_*` values are present.

Example `.env` entries:

```powershell
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=you@example.com
SMTP_PASSWORD=secret
FROM_EMAIL=you@example.com

TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=yyyyyyyyyyyyyyyyyyyyy
TWILIO_FROM_NUMBER=whatsapp:+1415...
```

Rate configuration

- Staff can change the per-unit rate from the web UI on the homepage. Two modes are supported:
	- `fixed`: the `value` is the per-unit price in currency (e.g., `1.5`).
	- `percent`: the `value` is a percentage adjustment relative to `RATE_PER_UNIT` configured in `.env` (e.g., `10` means +10%).

When you change the rate on the UI the effective per-unit rate used in future invoices updates immediately.