from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from app.services.cache import get_revenue_summary
from app.core.auth import authenticate_request as get_current_user

router = APIRouter()


def _get_tenant_id(user: Any) -> str:
    # current_user may be a dict or an object; getattr on a dict never finds the key.
    if isinstance(user, dict):
        tenant_id = user.get("tenant_id")
    else:
        tenant_id = getattr(user, "tenant_id", None)
    return tenant_id or "default_tenant"


@router.get("/dashboard/summary")
async def get_dashboard_summary(
    property_id: str,
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:

    tenant_id = _get_tenant_id(current_user)

    if month is not None and year is not None:
        if not 1 <= month <= 12:
            raise HTTPException(status_code=422, detail="month must be between 1 and 12")
        from app.services.reservations import calculate_monthly_revenue
        revenue_data = await calculate_monthly_revenue(property_id, month, year, tenant_id)
    else:
        revenue_data = await get_revenue_summary(property_id, tenant_id)

    # Round money with Decimal (half-up to cents) before converting for JSON.
    total = Decimal(str(revenue_data['total'])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return {
        "property_id": revenue_data['property_id'],
        "total_revenue": float(total),
        "currency": revenue_data['currency'],
        "reservations_count": revenue_data['count']
    }
