# LinkPulse — Enterprise URL Shortener & Real-Time Analytics Platform

> Built for Competitive College Hackathon (Round 2: Implementation)

LinkPulse is a production-grade link management, intelligent redirection, and real-time analytics platform. Engineered with a premium SaaS design aesthetic (Midnight Navy sidebar, crisp light workspace, and electric blue/cyan accents), LinkPulse handles the complete link lifecycle: collision-resistant short code generation, rule-based redirection, atomic click tracking, bot filtering, dynamic QR code generation, bulk CSV ingestion, and administrative safety governance.

Every dashboard KPI, trend chart, and table is powered by **actual MySQL database records**—zero mocked or hardcoded statistics.

---

## 🚀 Key Features

* **Instant Link Shortening & 2-Step Creation Wizard:**
  * Alphanumeric, collision-resistant code generation.
  * Custom alias availability checks and keyword reservation.
  * Destination URL safety validation (HTTP/HTTPS scheme enforcement & centralized domain blocklist).
  * Marketing campaign association and multi-tag categorization.
* **Intelligent Redirection Engine (`/r/<short_code>`):**
  * Evaluates status in strict sequence: Not Found $\to$ Disabled $\to$ Expired $\to$ Click Limit Reached $\to$ Password Verification $\to$ Redirect.
  * Atomic click counter increments preventing race conditions under high concurrent traffic.
  * Cryptographic password gates that never leak destination URLs prior to verification.
* **Real-Time Click Tracking & Audience Analytics:**
  * Ingests timestamps, referrers, browser engines, operating systems, device categories, and locations.
  * Automated user-agent bot classification and filtering.
  * Privacy-preserving unique visitor estimations using daily salted hashes (no invasive cookies).
  * Interactive Chart.js visualizations (Clicks over time, device distribution doughnut, browser breakdown bar chart, referrers list).
* **Dynamic QR Code Studio:**
  * Generates high-resolution PNG QR assets dynamically resolving to the configured public short URL.
  * Direct PNG asset downloads and live scan verification.
* **High-Speed CSV Bulk Ingestion:**
  * Drag-and-drop file upload with row-level validation.
  * Catches invalid URLs, duplicate aliases, and past expiry dates with detailed line-by-line reporting.
  * Downloadable sample CSV template (`/api/v1/sample-csv`).
* **Enterprise Administrative Governance (`/admin`):**
  * Platform-wide link and click metrics.
  * User directory with instant account deactivation and role management.
  * Global link moderation and one-click takedown controls.
  * Centralized domain blocklist that automatically disables associated abusive links.
  * Immutable security audit log feed.

---

## 🛠️ Technology Stack

* **Frontend:** HTML5, Modern CSS3 (CSS Variables Design Tokens), Vanilla JavaScript (ES6+), Chart.js (v4), Lucide Icons.
* **Backend:** Python 3 (Flask), Flask Blueprints, Flask Sessions (HttpOnly, SameSite=Lax), Werkzeug Password Hashing.
* **Database:** MySQL 8.0 (Flask-SQLAlchemy ORM + PyMySQL connector).
* **Utilities:** Python `qrcode` & Pillow, `Flask-Limiter` (rate limiting), `Flask-WTF`, `user-agents` (classifier).
* **Testing:** `pytest` automated test suite with in-memory SQLite and MySQL verification.

---

## 📊 Normalized Database Schema

```mermaid
erDiagram
    users ||--o{ links : owns
    users ||--o{ campaigns : creates
    users ||--o{ tags : creates
    campaigns ||--o{ links : groups
    links ||--o{ click_events : tracks
    links }o--o{ link_tags : has
    tags }o--o{ link_tags : categorizes
    users ||--o{ blocked_domains : registers
    users ||--o{ admin_logs : generates

    users {
        int id PK
        string username UK
        string email UK
        string password_hash
        string role "user | admin"
        boolean is_active
        datetime created_at
    }

    links {
        int id PK
        int user_id FK
        int campaign_id FK
        string short_code UK
        string custom_alias UK
        text destination_url
        string title
        boolean is_active
        string password_hash
        datetime expires_at
        int max_clicks
        int clicks_count
        datetime created_at
    }

    click_events {
        int id PK
        int link_id FK
        datetime timestamp
        string ip_address
        string country
        string city
        string referrer
        string referrer_domain
        string browser
        string os
        string device_category
        boolean is_bot
        string visitor_hash
    }

    campaigns {
        int id PK
        int user_id FK
        string name
        text description
        string color_code
        datetime created_at
    }

    tags {
        int id PK
        int user_id FK
        string name
        string color_code
    }

    blocked_domains {
        int id PK
        string domain UK
        string reason
        boolean is_active
        datetime created_at
    }
```

---

## 💻 Local Windows Setup Guide

### 1. Prerequisites
* Python 3.10+ installed.
* MySQL Server 8.0 running locally on port 3306.

### 2. Clone and Setup Environment
```powershell
# Navigate to directory
cd "d:\hackathon r1 26\LinkPulse"

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Configure Database Credentials
Create a `.env` file in the project root:
```ini
FLASK_APP=run.py
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=linkpulse_hackathon_demo_key_9837498172948719
DATABASE_URL=mysql+pymysql://root:1234@127.0.0.1:3306/linkpulse_db
BASE_URL=http://localhost:5000
```

### 4. Seed Demonstration Data
Initialize the database tables and populate realistic demo links, campaigns, and click events:
```powershell
python seed_data.py
```
> **Pre-configured Demo Accounts:**
> * **Standard User:** `demo@linkpulse.io` / `demo123`
> * **Administrator:** `admin@linkpulse.io` / `admin123`

### 5. Run the Application
```powershell
python run.py
```
Open your browser and navigate to **`http://localhost:5000`**.

---

## 🧪 Automated Testing

LinkPulse includes an automated test suite verifying 16 test cases covering auth, rules, redirects, rate limits, CSV import, and security gates:
```powershell
python -m pytest -v
```

---

## ⏱️ Five-Minute Hackathon Demo Script

### Scenario 1: Short Link Creation $\to$ Redirection $\to$ Real-Time Click Attribution
1. **Sign In:** Go to `/auth/login` and click the **"⚡ Demo User"** instant credential button.
2. **Review Dashboard:** Notice the live KPI counters, Clicks Over Time chart, and Device distribution.
3. **Launch Wizard:** Click **"+ Create Link"**:
   * *Step 1:* Enter Destination `https://github.com/explore`, custom alias `gh-spotlight`, select campaign `Developer Outreach 2026`.
   * *Step 2:* Set Expiry (e.g. 7 days out) and Max Clicks (e.g. 100). Click **"Publish Short Link"**.
4. **Inspect Success Screen:** Observe the generated short URL `http://localhost:5000/r/gh-spotlight` and dynamic QR code asset.
5. **Trigger Redirect:** Open `http://localhost:5000/r/gh-spotlight` in a new tab. Verify that the redirect takes you directly to GitHub.
6. **Live Analytics:** Return to `/dashboard` or open `/links`. Notice that total clicks immediately incremented by 1 and a new click event was recorded with your device and browser!

### Scenario 2: Bulk CSV Ingestion $\to$ Safety Moderation $\to$ Preserved Analytics
1. **Bulk Ingestion:** Navigate to **"Bulk Import"** (`/import`).
2. **Download Sample:** Click **"Download Sample CSV"** to inspect format.
3. **Upload CSV:** Drag and drop the sample CSV.
4. **Inspect Row-Level Feedback:** Observe the results dashboard showing valid rows imported with generated short codes, and any rejected rows flagged with explicit reasons.
5. **Link Disabling:** Go to **"Links"** (`/links`). Click the pause button on any active link to toggle it to `disabled`.
6. **Redirection Blocked:** Open that link's short URL. Observe the LinkPulse branded **403 Link Disabled** error page.
7. **Analytics Preservation:** Open that disabled link's analytics detail page (`/links/<id>`). Confirm that all historical click records, trend charts, and device graphs remain intact!

---

## 🌐 Production Deployment Guide

### Deploying to Render / Railway / AWS / DigitalOcean
1. **Managed MySQL:** Provision a MySQL database instance (e.g., PlanetScale, Aiven, AWS RDS, or Railway MySQL).
2. **Environment Variables:** Set in hosting dashboard:
   * `DATABASE_URL`: `mysql+pymysql://<user>:<password>@<host>:<port>/<dbname>`
   * `SECRET_KEY`: A strong, randomly generated 32+ character key.
   * `BASE_URL`: Your custom public domain (e.g. `https://linkpulse.io`).
3. **Build Command:**
   ```bash
   pip install -r requirements.txt && python seed_data.py
   ```
4. **Start Command:**
   ```bash
   gunicorn run:app --bind 0.0.0.0:$PORT
   ```
5. **Health Check:** Point uptime monitoring to `/health` (returns HTTP 200 and `{ "status": "ok", "database": "healthy" }`).

---

## 🔮 Future Roadmap

1. **Custom Branded Domains:** Allow enterprise tenants to map `go.brand.com` with automatic Let's Encrypt SSL provisioning.
2. **Geo & Device Dynamic Routing:** Route iOS visitors to App Store, Android to Google Play, and desktop to web landing pages via a single link.
3. **Asynchronous Stream Processing:** Offload high-velocity click stream logging to Redis queue and Celery workers for 100,000+ clicks/second throughput.
4. **Public REST & GraphQL API:** Developer API keys with scoped permissions for programmatic short link creation and webhook notifications.
testing my first commit from VS Code