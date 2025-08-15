from decimal import Decimal, ROUND_HALF_UP
from cars.models import CarServiceRecord, ServiceEntry, InventoryUsage
import logging
from .models import Bill

logger = logging.getLogger(__name__)

def calculate_bill_for_car(car_id, new_discount=0, new_amount_paid=0):
    """
    Calculate and update bill for a car, keeping discounts & payments cumulative.
    """
    try:
        record = CarServiceRecord.objects.get(car_id=car_id)
    except CarServiceRecord.DoesNotExist:
        logger.warning(f"No service record found for car ID: {car_id}")
        return None

    # Get or create persistent bill record
    bill, _ = Bill.objects.get_or_create(
        car_id=car_id,
        defaults={"discount": Decimal('0.00'), "amount_paid": Decimal('0.00')}
    )

    services = ServiceEntry.objects.filter(service_record=record).select_related('service')
    inventories = InventoryUsage.objects.filter(service_record=record).select_related('product')

    total_service = Decimal('0.00')
    total_inventory = Decimal('0.00')

    service_lines = []
    product_lines = []

    for s in services:
        rate = Decimal(str(s.service.standard_rate or 0))
        total_service += rate
        service_lines.append({
            "name": s.service.name,
            "rate": str(rate),
            "performed_at": s.performed_at.strftime('%Y-%m-%d') if s.performed_at else "",
            "remarks": s.remarks or ""
        })

    for i in inventories:
        rate = Decimal(str(i.product.standard_rate or 0))
        qty = Decimal(str(i.quantity_used))
        line_total = rate * qty
        total_inventory += line_total
        product_lines.append({
            "name": i.product.name,
            "rate": str(rate),
            "quantity": str(qty),
            "total": str(line_total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            "used_at": i.used_at.strftime('%Y-%m-%d') if i.used_at else ""
        })

    # Update cumulative discount and amount paid
    bill.discount += Decimal(str(new_discount))
    bill.amount_paid += Decimal(str(new_amount_paid))

    # Recalculate totals
    bill.total_service_cost = total_service
    bill.total_inventory_cost = total_inventory
    bill.total_amount = total_service + total_inventory - bill.discount
    bill.amount_remaining = bill.total_amount - bill.amount_paid
    bill.save()

    return {
        "car_id": car_id,
        "total_service_cost": bill.total_service_cost.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        "total_inventory_cost": bill.total_inventory_cost.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        "total_amount": bill.total_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        "discount": bill.discount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        "amount_paid": bill.amount_paid.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        "amount_remaining": bill.amount_remaining.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        "service_lines": service_lines,
        "product_lines": product_lines
    }
