## Summary

Describe the user-visible change and why it is needed.

## Verification

- [ ] `uv run ruff check src tests scripts main.py`
- [ ] `uv run pytest`
- [ ] `pnpm --dir frontend lint`
- [ ] `pnpm --dir frontend typecheck`
- [ ] `pnpm --dir frontend test:run`
- [ ] `pnpm --dir frontend build`

## Privacy and compatibility

- [ ] No personal face data, uploaded media, model weights, secrets, or local databases were added.
- [ ] Database and API compatibility implications are documented.
