# Water Billing System TODO Tracker

## Frontend CORS/Fetch Fix (In Progress)
- [x] 1. Updated vite.config.js with /api proxy to backend
- [x] 2. Changed httpClient.js API_BASE_URL to '/api' 
- [x] 3. Backend running (:8000), frontend deps up-to-date. CORS fixed via proxy.
- [x] 4. /health OK; expect 404 on /api/admin/customers until provider created (normal).

## 404 Provider Fix
- [ ] 1. Create 'celebration-water' provider via /setup
- [ ] 2. Test API with X-Provider-Slug header
- [ ] 3. Update localStorage provider_slug

## Deploy
- [x] Railpack.json & requirements.txt
- [ ] Resolve git merge conflict (app/railpack.json)
- [ ] gh pr create & merge
- [ ] Railway vars & deploy

**Next: Run frontend/backend, test fetches.**

