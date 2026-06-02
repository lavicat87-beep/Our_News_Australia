OurNews Flask Starter

This project now includes:
- Multi-page site: Home, About, Contact, News
- Blog/news post model using SQLAlchemy
- Admin login and dashboard for publishing
- PostgreSQL-ready configuration through environment variables
- Australia -> State -> Region -> Town navigation
- Dedicated town pages with local stories, events, and local organizations
- Contributor account registration and profile pages
- Community story submissions with moderation queue
- Town expansion request workflow (residents can request new town pages)
- Searchable archive filtered by town and category

Local development in VS Code

1. Create virtual environment
   py -m venv .venv

2. Activate environment (PowerShell)
   .\.venv\Scripts\Activate.ps1

3. Install dependencies
   pip install -r requirements.txt

4. Set environment variables (PowerShell example)
   $env:SECRET_KEY="replace-with-a-strong-secret"
   $env:DATABASE_URL="sqlite:///ournews.db"
   $env:ADMIN_USERNAME="admin"
   $env:ADMIN_PASSWORD="admin123"

5. Initialize database and default admin
   flask --app app init-db

6. Run app
   python app.py

7. Open browser
   http://127.0.0.1:5000

If you already ran an older schema in sqlite, remove the old database before reinitializing:
   Remove-Item .\instance\ournews.db -ErrorAction SilentlyContinue
   Remove-Item .\ournews.db -ErrorAction SilentlyContinue
Then run init-db again.

Routes

- / (Home)
- /about
- /contact
- /news
- /news/<slug>
- /australia
- /state/<slug>
- /region/<slug>
- /town/<slug>
- /archive
- /register
- /login
- /profile/<username>
- /submit
- /expansion/apply
- /admin/login
- /admin

PostgreSQL setup

1. Create a PostgreSQL database.
2. Set DATABASE_URL in this format:
   postgresql+psycopg2://username:password@host:5432/dbname
3. Run database init:
   flask --app app init-db

Deploy option (Render)

1. Push this project to GitHub.
2. In Render: New + -> Web Service -> connect repo.
3. Build command: pip install -r requirements.txt
4. Start command: gunicorn app:app
5. Add environment variables in Render dashboard:
   - SECRET_KEY
   - DATABASE_URL (from Render PostgreSQL or external PostgreSQL)
   - ADMIN_USERNAME
   - ADMIN_PASSWORD
6. Run one-time shell command after deploy:
   flask --app app init-db

Connect GoDaddy domain

1. In Render custom domains, add your domain first.
2. In GoDaddy DNS, add exactly the records Render provides:
   - CNAME for www
   - A record or ALIAS/ANAME for root (@), if requested
3. Wait for DNS propagation.
4. Verify HTTPS is active.
