# Bugs found and fixed

## 1. Cross-tenant data leak (Client B privacy issue)
- Cause: Redis cache key was `revenue:{property_id}`. `prop-001` exists for both tenants, so one client could read the other's cached numbers.
- Fix: key is now `revenue:{tenant_id}:{property_id}` (`backend/app/services/cache.py`).

## 2. Wrong monthly totals (Client A, March)
- Cause: month boundaries were built without the property's timezone (naive datetimes), and the monthly function was a stub returning 0.
- Fix: `calculate_monthly_revenue` loads the property's timezone and queries `[first day 00:00, next month 00:00)` in that timezone. Exposed as `month`/`year` params on `/dashboard/summary`.
- Example: reservation `res-tz-1` (2024-02-29 23:30 UTC) is 1 March 00:30 in Paris, so it belongs to March, not February.

## 3. Totals off by a few cents
- Cause: amounts are stored with 3 decimals and were converted with `float()` and rounded in the browser.
- Fix: sum in the database (NUMERIC), round once with `Decimal.quantize(0.01, ROUND_HALF_UP)` in the API.

## 4. Database connection was broken (silent mock data)
- Cause: `database_pool.py` built its URL from settings that did not exist, used a sync pool class with the async engine, had an `async def get_session`, and `asyncpg`/`greenlet` were missing. Errors were swallowed and mock data was returned.
- Fix: use `DATABASE_URL`, shared engine, sync `get_session`, added `asyncpg` and `greenlet` to requirements.

## 5. Property dropdown was hardcoded
- Cause: the frontend listed Sunset's properties for every client.
- Fix: new endpoint `GET /api/v1/dashboard/properties` returns only the caller's tenant properties; the dropdown uses it.
