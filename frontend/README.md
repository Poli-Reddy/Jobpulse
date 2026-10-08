# JobPulse frontend

React dashboard powered by Vite. The browser communicates only with the
FastAPI service; it does not connect to PostgreSQL.

## Local development

Start PostgreSQL and the API on port `8000` using the root project instructions.
Then:

```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Open `http://localhost:3000`. Set `VITE_API_URL` in `frontend/.env` when the API
is hosted at another address. The API must allow this frontend origin through
its `CORS_ORIGINS` setting.

Build a production bundle with `npm run build`.
