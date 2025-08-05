from decimal import Decimal, ROUND_HALF_UP
from cars.models import CarServiceRecord, ServiceEntry, InventoryUsage
import logging

logger = logging.getLogger(__name__)


def calculate_bill_for_car(car_id, discount=0, amount_paid=0):
    """
    Calculate bill for a car including services and inventory usage.
    
    Args:
        car_id (int): The car ID
        discount (Decimal): Discount amount
        amount_paid (Decimal): Amount already paid
        
    Returns:
        dict: Bill calculation result or None if no service record found
    """
    try:
        record = CarServiceRecord.objects.get(car_id=car_id)
    except CarServiceRecord.DoesNotExist:
        logger.warning(f"No service record found for car ID: {car_id}")
        return None

    try:
        services = ServiceEntry.objects.filter(service_record=record).select_related('service')
        inventories = InventoryUsage.objects.filter(service_record=record).select_related('product')

        total_service = Decimal('0')
        total_inventory = Decimal('0')

        service_lines = []
        product_lines = []

        # Calculate service costs
        for service_entry in services:
            rate = Decimal(str(service_entry.service.standard_rate or 0))
            total_service += rate
            service_lines.append({
                "name": service_entry.service.name,
                "rate": str(rate),
                "performed_at": service_entry.performed_at.strftime('%Y-%m-%d') if service_entry.performed_at else "",
                "remarks": service_entry.remarks or ""
            })

        # Calculate inventory costs
        for inventory_usage in inventories:
            rate = Decimal(str(inventory_usage.product.standard_rate or 0))
            qty = Decimal(str(inventory_usage.quantity_used))
            line_total = rate * qty
            total_inventory += line_total
            
            product_lines.append({
                "name": inventory_usage.product.name,
                "rate": str(rate),
                "quantity": str(qty),
                "total": str(line_total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                "used_at": inventory_usage.used_at.strftime('%Y-%m-%d') if inventory_usage.used_at else ""
            })

        # Calculate totals
        total = total_service + total_inventory
        discount_decimal = Decimal(str(discount))
        amount_paid_decimal = Decimal(str(amount_paid))
        amount_remaining = total - discount_decimal - amount_paid_decimal

        return {
            "car_id": car_id,
            "total_service_cost": total_service.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            "total_inventory_cost": total_inventory.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            "total_amount": total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            "discount": discount_decimal,
            "amount_paid": amount_paid_decimal,
            "amount_remaining": amount_remaining.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            "service_lines": service_lines,
            "product_lines": product_lines
        }

    except Exception as e:
        logger.error(f"Error calculating bill for car {car_id}: {str(e)}")
        return None