# Supabase Deployment TODO - Water Billing System
Phased migration: MongoDB (master + per-provider DBs) -> Supabase Postgres + RLS.

## Phase 0: CLI Setup (Critical - Blocked)
- [ ] 0.1 **Manual Windows Install** (npm blocked):
  1. Download ZIP: https://github.com/supabase/cli/releases/latest/download/supabase_1.208.4_windows_amd64.zip
  2. Extract `supabase.exe` to `C:\supabase\`
  3. Add `C:\supabase` to PATH (Win+R sysdm.cpl > Advanced > Env Vars > Path > New > Restart terminal)
  4. Verify: `supabase --version`
- [ ] 0.2 `supabase login` (Access Token from supabase.com/account/tokens)
- [ ] 0.3 `supabase init` && `supabase link --project-ref dnynpdlpdcyorqvvtqxa`
- [ ] 0.4 Add to .env:
   ```
   SUPABASE_URL=https://dnynpdlpdcyorqvvtqxa.supabase.co
   SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1Ni... (full)
   SUPABASE_SERVICE_ROLE_KEY=sb... (full)
   DATABASE_URL=postgresql://postgres:[PWD]@db.[ref].supabase.co:5432/postgres
   ```
- [x] 0.5 File analysis complete (Mongo CRUD, multi-tenant master/provider DBs, frontend APIs).

## Phase 1: Backend Migration (Postgres + SQLAlchemy)
- [ ] 1.1 Create app/requirements.txt:
  ```
  fastapi
  uvicorn
  sqlalchemy==2.0.35
  alembic
  psycopg2-binary
  supabase
  python-dotenv
  passlib[bcrypt]
  python-jose[cryptography]
  ```
  `pip install -r app/requirements.txt`
- [ ] 1.2 New app/models_sql.py (SQLAlchemy tables mirroring Mongo: customers(id Serial PK, provider_id FK), readings, invoices etc.)
- [ ] 1.3 app/database.py (async_sessionmaker)
- [ ] 1.4 Port app/crud.py -> crud_sql.py (mongo ops -> SQL)
- [ ] 1.5 Update main.py, replace mongodb -> SQL CRUD
- [ ] 1.6 Migration script mongo->postgres (preserve IDs via raw SQL)

## Phase 2: Supabase Config
- [ ] 2.1 `supabase migration new create_tables` -> db push (schemas/indexes)
- [ ] 2.2 Auth setup + redirect URLs
- [ ] 2.3 RLS policies (provider_slug = auth.jwt()->>'provider_slug')
- [ ] 2.4 Edge Functions: reminder_cron (port APScheduler)

## Phase 3: Frontend
- [ ] 3.1 npm i @supabase/supabase-js (frontend)
- [ ] 3.2 src/lib/supabase.js client
- [ ] 3.3 Replace api/adminApi.js fetch -> supabase.from() + RPC

## Phase 4: Deploy
- [ ] 4.1 Backend Railway/Render
- [ ] 4.2 Frontend Vercel
- [ ] 4.3 Data migrate + test

**Status:** Blocked Phase 0.1. Multi-tenant: Single DB + RLS on provider_slug.

**Next:** Install CLI manual, provide full keys, confirm Railway.

