# Water Billing System - Railpack Deploy Fix Plan
Approved plan implementation steps:

## Steps to Complete:

- [ ] 1. Update railpack.json: Full replacement with provided JSON content.
- [ ] 2. Update app/main_multitenant.py: Replace health_check endpoint block with safe version.
- [ ] 3. Update .gitignore: Append '/app/venv' line.
- [ ] 4. Git: Create and switch to branch 'fix/deploy-multitenant-railpack'.
- [ ] 5. Check if app/venv is git tracked; if yes, git rm --cached and re-add .gitignore.
- [ ] 6. Git add files and commit with messages: "railpack: conditional frontend build; switch deploy to multi-tenant; harden health endpoint; ignore app/venv"
- [ ] 7. If app/venv rm needed, separate commit: "Remove committed virtualenv and ignore it"
- [ ] 8. Git push origin fix/deploy-multitenant-railpack
- [ ] 9. Verify changes and open PR to main.

Current progress: Starting implementation.

