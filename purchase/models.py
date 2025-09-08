# purchases/models.py
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from users.models import User
from inventory.models import Supplier, InventoryItem
from django.utils import timezone


class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent to Supplier'),
        ('confirmed', 'Confirmed'),
        ('partial', 'Partially Received'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('partial', 'Partially Paid'),
        ('paid', 'Fully Paid'),
    ]

    po_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    
    order_date = models.DateField(auto_now_add=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    notes = models.TextField(blank=True, null=True)
    terms_and_conditions = models.TextField(blank=True, null=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_purchase_orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Purchase Order'
        verbose_name_plural = 'Purchase Orders'

    def __str__(self):
        return f"PO-{self.po_number} ({self.supplier.name})"

    def save(self, *args, **kwargs):
        if not self.po_number:
            # Use today's date if order_date is not yet set
            order_year = (self.order_date or timezone.now().date()).year
            prefix = f"PO{order_year}"

            # Find last PO with the same year prefix
            last_po = PurchaseOrder.objects.filter(
                po_number__startswith=prefix
            ).order_by('-po_number').first()

            if last_po and last_po.po_number[len(prefix):].isdigit():
                last_number = int(last_po.po_number[len(prefix):])
                new_number = last_number + 1
            else:
                new_number = 1

            self.po_number = f"{prefix}{new_number:04d}"  # Example: PO20250001

        super().save(*args, **kwargs)

    @property
    def total_items(self):
        return self.items.count()

    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items.all())

    def calculate_totals(self):
        self.subtotal = sum(item.total_cost for item in self.items.all())
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
        self.save()


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    
    notes = models.TextField(blank=True, null=True)
    
    received_quantity = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('purchase_order', 'inventory_item')
        verbose_name = 'Purchase Order Item'
        verbose_name_plural = 'Purchase Order Items'

    def __str__(self):
        return f"{self.inventory_item.name} - {self.quantity} {self.inventory_item.unit}"

    def save(self, *args, **kwargs):
        self.total_cost = self.quantity * self.unit_price
        super().save(*args, **kwargs)
        # Update PO totals
        self.purchase_order.calculate_totals()

    @property
    def is_fully_received(self):
        return self.received_quantity >= self.quantity

    @property
    def pending_quantity(self):
        return max(0, self.quantity - self.received_quantity)


class PurchaseReceipt(models.Model):
    RECEIPT_STATUS_CHOICES = [
        ('received', 'Received'),
        ('quality_check', 'Quality Check'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('partial_accepted', 'Partially Accepted'),
    ]

    receipt_number = models.CharField(max_length=50, unique=True)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='receipts')
    
    receipt_date = models.DateField(auto_now_add=True)
    supplier_invoice_number = models.CharField(max_length=100, blank=True, null=True)
    supplier_invoice_date = models.DateField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=RECEIPT_STATUS_CHOICES, default='received')
    
    received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='received_purchases')
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Purchase Receipt'
        verbose_name_plural = 'Purchase Receipts'

    def __str__(self):
        return f"Receipt-{self.receipt_number} (PO: {self.purchase_order.po_number})"

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            # Generate receipt number automatically
            last_receipt = PurchaseReceipt.objects.filter(
                receipt_number__startswith=f"RCP{self.receipt_date.year}"
            ).order_by('-receipt_number').first()
            
            if last_receipt:
                last_number = int(last_receipt.receipt_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.receipt_number = f"RCP{self.receipt_date.year}-{new_number:06d}"
        
        super().save(*args, **kwargs)


class PurchaseReceiptItem(models.Model):
    ITEM_STATUS_CHOICES = [
        ('received', 'Received'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('damaged', 'Damaged'),
    ]

    receipt = models.ForeignKey(PurchaseReceipt, on_delete=models.CASCADE, related_name='items')
    purchase_order_item = models.ForeignKey(PurchaseOrderItem, on_delete=models.CASCADE)
    
    received_quantity = models.PositiveIntegerField()
    accepted_quantity = models.PositiveIntegerField(default=0)
    rejected_quantity = models.PositiveIntegerField(default=0)
    
    status = models.CharField(max_length=20, choices=ITEM_STATUS_CHOICES, default='received')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    notes = models.TextField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Purchase Receipt Item'
        verbose_name_plural = 'Purchase Receipt Items'

    def __str__(self):
        return f"{self.purchase_order_item.inventory_item.name} - Received: {self.received_quantity}"

    def save(self, *args, **kwargs):
        # Ensure accepted + rejected = received
        if self.accepted_quantity + self.rejected_quantity > self.received_quantity:
            raise ValueError("Accepted + Rejected quantity cannot exceed received quantity")
        
        super().save(*args, **kwargs)
        
        # Update inventory if accepted
        if self.accepted_quantity > 0 and self.status == 'accepted':
            inventory_item = self.purchase_order_item.inventory_item
            inventory_item.quantity_in_stock += self.accepted_quantity
            inventory_item.save()
        
        # Update purchase order item received quantity
        self.purchase_order_item.received_quantity += self.received_quantity
        self.purchase_order_item.save()


class PurchasePayment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('credit_card', 'Credit Card'),
        ('upi', 'UPI'),
    ]

    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='payments')
    
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    paid_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date']
        verbose_name = 'Purchase Payment'
        verbose_name_plural = 'Purchase Payments'

    def __str__(self):
        return f"Payment for PO-{self.purchase_order.po_number} - ₹{self.amount}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update purchase order payment status
        self.update_po_payment_status()

    def update_po_payment_status(self):
        po = self.purchase_order
        total_paid = sum(payment.amount for payment in po.payments.all())
        
        if total_paid >= po.total_amount:
            po.payment_status = 'paid'
        elif total_paid > 0:
            po.payment_status = 'partial'
        else:
            po.payment_status = 'pending'
        
        po.save()


class PurchaseReturn(models.Model):
    RETURN_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('processed', 'Processed'),
        ('rejected', 'Rejected'),
    ]

    return_number = models.CharField(max_length=50, unique=True)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='returns')
    
    return_date = models.DateField(auto_now_add=True)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=RETURN_STATUS_CHOICES, default='pending')
    
    total_return_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='requested_returns')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_returns')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Purchase Return'
        verbose_name_plural = 'Purchase Returns'

    def __str__(self):
        return f"Return-{self.return_number} (PO: {self.purchase_order.po_number})"

    def save(self, *args, **kwargs):
        if not self.return_number:
            # Generate return number automatically
            last_return = PurchaseReturn.objects.filter(
                return_number__startswith=f"RTN{self.return_date.year}"
            ).order_by('-return_number').first()
            
            if last_return:
                last_number = int(last_return.return_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.return_number = f"RTN{self.return_date.year}-{new_number:06d}"
        
        super().save(*args, **kwargs)


class PurchaseReturnItem(models.Model):
    purchase_return = models.ForeignKey(PurchaseReturn, on_delete=models.CASCADE, related_name='items')
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    
    reason = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Return: {self.inventory_item.name} - {self.quantity}"

    def save(self, *args, **kwargs):
        self.total_amount = self.quantity * self.unit_price
        super().save(*args, **kwargs)
        
        # Update return total
        self.purchase_return.total_return_amount = sum(
            item.total_amount for item in self.purchase_return.items.all()
        )
        self.purchase_return.save()
        
        # Update inventory if return is processed
        if self.purchase_return.status == 'processed':
            self.inventory_item.quantity_in_stock -= self.quantity
            self.inventory_item.save()