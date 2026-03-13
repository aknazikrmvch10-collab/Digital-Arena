from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from database import get_db
from models import Admin, Club, Booking, Payment, BarOrder, BarItem
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
from utils.timezone import now_tashkent

router = APIRouter(tags=["Club Admin"])

# --- Schemas ---
class ClubInfoUpdate(BaseModel):
    description: Optional[str] = None
    image_url: Optional[str] = None
    wifi_speed: Optional[str] = None

# --- Dependency: Require Club Admin ---
async def get_current_club_admin(
    x_admin_tg_id: int = Header(...),
    db: AsyncSession = Depends(get_db)
) -> Admin:
    result = await db.execute(select(Admin).where(Admin.tg_id == x_admin_tg_id))
    admin = result.scalar_one_or_none()
    
    if not admin:
        raise HTTPException(status_code=403, detail="Not an admin")
    
    # Super admins (club_id is None) can access everything, 
    # but for club-specific logic we might need to handle them differently.
    # We'll return the admin object.
    return admin

# --- Endpoints ---

@router.get("/club-admin/me")
async def get_admin_info(admin: Admin = Depends(get_current_club_admin), db: AsyncSession = Depends(get_db)):
    club_name = "System Admin"
    if admin.club_id:
        result = await db.execute(select(Club).where(Club.id == admin.club_id))
        club = result.scalar_one_or_none()
        club_name = club.name if club else "Unknown Club"
    
    return {
        "tg_id": admin.tg_id,
        "club_id": admin.club_id,
        "club_name": club_name,
        "is_super_admin": admin.club_id is None
    }

@router.get("/club-admin/stats")
async def get_club_stats(
    club_id: Optional[int] = None, 
    admin: Admin = Depends(get_current_club_admin), 
    db: AsyncSession = Depends(get_db)
):
    # Security check: if not super-admin, must use their own club_id
    target_club_id = admin.club_id
    if admin.club_id is None: # Super Admin
        target_club_id = club_id
    
    if not target_club_id:
        raise HTTPException(status_code=400, detail="Club ID required")
    
    # 1. Revenue Today
    today_start = now_tashkent().replace(hour=0, minute=0, second=0, microsecond=0)
    rev_result = await db.execute(
        select(func.sum(Payment.amount))
        .join(Booking, Payment.booking_id == Booking.id)
        .where(Booking.club_id == target_club_id)
        .where(Payment.status == "completed")
        .where(Payment.paid_at >= today_start)
    )
    revenue_today = rev_result.scalar() or 0
    
    # 2. Bookings Today
    book_result = await db.execute(
        select(func.count(Booking.id))
        .where(Booking.club_id == target_club_id)
        .where(Booking.start_time >= today_start)
    )
    bookings_today = book_result.scalar() or 0
    
    # 3. Pending Orders
    order_result = await db.execute(
        select(func.count(BarOrder.id))
        .where(BarOrder.club_id == target_club_id)
        .where(BarOrder.status == "pending")
    )
    pending_orders = order_result.scalar() or 0
    
    return {
        "revenue_today": revenue_today,
        "bookings_today": bookings_today,
        "pending_orders": pending_orders,
        "club_id": target_club_id
    }

@router.get("/club-admin/orders")
async def get_pending_orders(
    admin: Admin = Depends(get_current_club_admin), 
    db: AsyncSession = Depends(get_db)
):
    if not admin.club_id and not admin.club_id == 0: # Handle super admin later if needed
        # For super admin without club_id specified, this might need a param
        raise HTTPException(status_code=400, detail="Only for specific club admins")
        
    result = await db.execute(
        select(BarOrder, BarItem.name)
        .join(BarItem, BarOrder.item_id == BarItem.id)
        .where(BarOrder.club_id == admin.club_id)
        .where(BarOrder.status == "pending")
        .order_by(BarOrder.created_at.asc())
    )
    
    orders = []
    for order, item_name in result:
        orders.append({
            "id": order.id,
            "item_name": item_name,
            "computer_name": order.computer_name,
            "quantity": order.quantity,
            "status": order.status,
            "created_at": order.created_at
        })
    return orders

@router.post("/club-admin/orders/{order_id}/complete")
async def complete_order(
    order_id: int,
    admin: Admin = Depends(get_current_club_admin), 
    db: AsyncSession = Depends(get_db)
):
    # Verify owner
    result = await db.execute(select(BarOrder).where(BarOrder.id == order_id))
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if admin.club_id and order.club_id != admin.club_id:
        raise HTTPException(status_code=403, detail="Not your club's order")
    
    order.status = "completed"
    await db.commit()
    return {"status": "ok"}

@router.patch("/club-admin/info")
async def update_club_info(
    data: ClubInfoUpdate,
    admin: Admin = Depends(get_current_club_admin), 
    db: AsyncSession = Depends(get_db)
):
    if not admin.club_id:
        raise HTTPException(status_code=403, detail="Super admin should use superadmin panel")
        
    update_data = data.dict(exclude_unset=True)
    if not update_data:
        return {"status": "no changes"}
        
    await db.execute(
        update(Club)
        .where(Club.id == admin.club_id)
        .values(**update_data)
    )
    await db.commit()
    return {"status": "ok", "updated": list(update_data.keys())}
