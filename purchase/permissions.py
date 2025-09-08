# purchases/permissions.py
from rest_framework import permissions
from django.contrib.auth.models import Group


class PurchaseOrderPermission(permissions.BasePermission):
    """
    Custom permission for Purchase Orders.
    
    - Anyone can view purchase orders
    - Only authenticated users can create purchase orders
    - Only the creator or managers can modify draft orders
    - Only managers can delete orders
    - Only managers can change order status
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions
        if request.method == 'DELETE':
            return self.is_manager(request.user) and obj.status == 'draft'
        
        # Update permissions
        if request.method in ['PUT', 'PATCH']:
            # Only draft orders can be fully modified
            if obj.status == 'draft':
                return obj.created_by == request.user or self.is_manager(request.user)
            # Non-draft orders can only be modified by managers
            return self.is_manager(request.user)
        
        return False
    
    def is_manager(self, user):
        """Check if user is a manager."""
        return user.is_superuser or user.groups.filter(name='Purchase Managers').exists()


class PurchaseReceiptPermission(permissions.BasePermission):
    """
    Custom permission for Purchase Receipts.
    
    - Anyone can view receipts
    - Only warehouse staff can create/modify receipts
    - Only managers can approve/reject items
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_authenticated and (
            self.is_warehouse_staff(request.user) or self.is_manager(request.user)
        )
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Only warehouse staff or managers can modify receipts
        return (self.is_warehouse_staff(request.user) or 
                self.is_manager(request.user))
    
    def is_warehouse_staff(self, user):
        """Check if user is warehouse staff."""
        return user.groups.filter(name__in=['Warehouse Staff', 'Purchase Managers']).exists()
    
    def is_manager(self, user):
        """Check if user is a manager."""
        return user.is_superuser or user.groups.filter(name='Purchase Managers').exists()


class PurchasePaymentPermission(permissions.BasePermission):
    """
    Custom permission for Purchase Payments.
    
    - Anyone can view payments
    - Only finance staff can create payments
    - No updates or deletes allowed (audit trail)
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        if request.method == 'POST':
            return request.user and request.user.is_authenticated and (
                self.is_finance_staff(request.user) or self.is_manager(request.user)
            )
        
        # No updates or deletes
        return False
    
    def is_finance_staff(self, user):
        """Check if user is finance staff."""
        return user.groups.filter(name__in=['Finance Staff', 'Purchase Managers']).exists()
    
    def is_manager(self, user):
        """Check if user is a manager."""
        return user.is_superuser or user.groups.filter(name='Purchase Managers').exists()


class PurchaseReturnPermission(permissions.BasePermission):
    """
    Custom permission for Purchase Returns.
    
    - Anyone can view returns
    - Anyone can create return requests
    - Only managers can approve/reject returns
    - Only the creator can modify pending returns
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Only pending returns can be modified
        if obj.status != 'pending' and request.method in ['PUT', 'PATCH']:
            return False
        
        # Creator can modify pending returns
        if request.method in ['PUT', 'PATCH']:
            return obj.requested_by == request.user or self.is_manager(request.user)
        
        return False
    
    def is_manager(self, user):
        """Check if user is a manager."""
        return user.is_superuser or user.groups.filter(name='Purchase Managers').exists()


class PurchaseAnalyticsPermission(permissions.BasePermission):
    """
    Custom permission for Purchase Analytics.
    
    - Only managers and authorized users can view analytics
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            self.is_manager(request.user) or 
            self.has_analytics_permission(request.user)
        )
    
    def is_manager(self, user):
        """Check if user is a manager."""
        return user.is_superuser or user.groups.filter(name='Purchase Managers').exists()
    
    def has_analytics_permission(self, user):
        """Check if user has analytics permission."""
        return user.groups.filter(name__in=[
            'Purchase Analysts', 'Finance Staff', 'Warehouse Staff'
        ]).exists()