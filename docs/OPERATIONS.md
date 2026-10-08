# Operations runbook

## Pipeline is failing
1. Inspect the Docker worker logs (`docker compose logs --tail 200 worker`) or the GitHub Actions workflow run.
2. Check `/pipeline/status` and `/sources/status`.
3. If one source is failing, disable it with `JOBICY_ENABLED=false` or `ARBEITNOW_ENABLED=false`.
4. Fix the connector, then trigger one run manually.

## Database unavailable
- Verify PostgreSQL health (`docker compose ps` locally).
- Check connection string and security group.
- Never delete raw data as a recovery step.

## API rate limited
- Increase interval between scheduled pulls.
- Respect `Retry-After` where provided.
- Reduce page size/count.

## Bad schema from source
- Connector normalization should absorb provider-specific changes.
- Preserve the raw payload.
- Add a regression fixture under `tests/fixtures` before changing the mapper.

## Data is stale
Check:
- Worker or GitHub Actions schedule is running (scheduled runs are best-effort).
- Source health has a recent successful observation.
- dbt build succeeded.
- PostgreSQL has sufficient storage/connections.
