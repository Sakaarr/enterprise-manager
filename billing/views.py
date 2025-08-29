from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, generics
from .utils import calculate_bill_for_car
from .serializers import *
from .models import Bill, PaidBill, ArchivedInventoryUsage, ArchivedServiceEntry
from decimal import Decimal
from django.http import FileResponse
from .utils_pdf import generate_invoice_pdf
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample, OpenApiParameter
import logging
from django.shortcuts import get_object_or_404
from django.db import transaction
from cars.models import CarServiceRecord, ServiceEntry, InventoryUsage, Car
from django.db.models import Q
from django.db.models import Sum, Count, F,Avg, Max, Min    
from django.db.models.functions import TruncDay
from rest_framework.decorators import api_view
from datetime import datetime, timedelta
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncYear, Extract
from cars.models import ServiceEntry, Service

logger = logging.getLogger(__name__)


class BillCalculationAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id="create_bill_calculation",
        request=BillCalculationSerializer,
        responses={
            201: BillResponseSerializer,
            400: OpenApiResponse(
                description="Invalid input data.",
                examples=[
                    OpenApiExample(
                        "Validation Error",
                        value={"car_id": ["This field is required."]},
                        status_codes=["400"]
                    )
                ]
            ),
            404: OpenApiResponse(
                description="Car or service record not found.",
                examples=[
                    OpenApiExample(
                        "Car Not Found",
                        value={"detail": "Car not found."},
                        status_codes=["404"]
                    )
                ]
            ),
            500: OpenApiResponse(description="Internal server error."),
        },
        tags=["Billing"],
        summary="Generate and Save Bill for a Car",
        description="Calculates the total service and inventory cost for a given car, applies discount and amount paid, creates a Bill record, and returns the breakdown."
    )
    def post(self, request):
        serializer = BillCalculationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            car_id = serializer.validated_data['car_id']
            discount = serializer.validated_data.get('discount', Decimal('0'))
            amount_paid = serializer.validated_data.get('amount_paid', Decimal('0'))

            # Check if car exists first
            try:
                car = Car.objects.get(id=car_id)
            except Car.DoesNotExist:
                return Response(
                    {"detail": "Car not found."}, 
                    status=status.HTTP_404_NOT_FOUND
                )

            # Calculate bill
            result = calculate_bill_for_car(car_id, discount, amount_paid)
            if result is None:
                return Response(
                    {"detail": "No service record found for this car."}, 
                    status=status.HTTP_404_NOT_FOUND
                )

            # Create and save the Bill
            bill = Bill.objects.create(
                car=car,
                total_service_cost=result['total_service_cost'],
                total_inventory_cost=result['total_inventory_cost'],
                total_amount=result['total_amount'],
                discount=discount,
                amount_paid=amount_paid,
                amount_remaining=result['amount_remaining'],
                entered_by=request.user
            )

            # Prepare response
            response_data = {
                'bill_id': bill.id,
                'total_service_cost': str(result['total_service_cost']),
                'total_inventory_cost': str(result['total_inventory_cost']),
                'total_amount': str(result['total_amount']),
                'discount': str(discount),
                'amount_paid': str(amount_paid),
                'amount_remaining': str(result['amount_remaining']),
                'created_at': bill.created_at.isoformat()
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating bill for car {car_id}: {str(e)}")
            return Response(
                {"detail": "An error occurred while processing the bill."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class InvoicePDFView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    @extend_schema(
        operation_id="generate_invoice_pdf",
        request=BillCalculationSerializer,
        responses={
            200: OpenApiResponse(
                description="PDF invoice generated and returned.",
                response=bytes,
            ),
            400: OpenApiResponse(description="Invalid input data."),
            404: OpenApiResponse(description="Car or service record not found."),
            500: OpenApiResponse(description="Error generating PDF."),
        },
        tags=["Billing"],
        summary="Generate PDF Invoice & Save/Update Bill",
        description="Recalculates the bill, handles overpayment, moves fully paid bills to archive, and returns PDF."
    )
    

    def post(self, request):
        serializer = BillCalculationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            car_id = serializer.validated_data['car_id']
            add_discount = serializer.validated_data.get('discount', Decimal('0'))
            add_amount_paid = serializer.validated_data.get('amount_paid', Decimal('0'))

            try:
                car = Car.objects.get(id=car_id)
            except Car.DoesNotExist:
                return Response({"detail": "Car not found."}, status=status.HTTP_404_NOT_FOUND)

            bill_data = calculate_bill_for_car(car_id)
            if bill_data is None:
                return Response({"detail": "No service record found for this car."}, status=status.HTTP_404_NOT_FOUND)

            bill, _ = Bill.objects.get_or_create(
                car=car,
                defaults={
                    "discount": Decimal('0'),
                    "amount_paid": Decimal('0'),
                    "total_service_cost": bill_data['total_service_cost'],
                    "total_inventory_cost": bill_data['total_inventory_cost'],
                    "total_amount": bill_data['total_amount'],
                    "amount_remaining": bill_data['total_amount'],
                    "entered_by": request.user
                }
            )

            bill.discount += add_discount
            bill.total_service_cost = bill_data['total_service_cost']
            bill.total_inventory_cost = bill_data['total_inventory_cost']
            bill.total_amount = bill.total_service_cost + bill.total_inventory_cost - bill.discount

            return_to_customer = Decimal('0')
            potential_new_paid = bill.amount_paid + add_amount_paid
            if potential_new_paid > bill.total_amount:
                return_to_customer = potential_new_paid - bill.total_amount
                bill.amount_paid = bill.total_amount
            else:
                bill.amount_paid = potential_new_paid

            bill.amount_remaining = bill.total_amount - bill.amount_paid
            bill.save()

            # If bill is fully paid, archive data & clean up
            if bill.amount_remaining <= 0:
                paid_bill = PaidBill.objects.create(
                    car=car,
                    discount=bill.discount,
                    total_service_cost=bill.total_service_cost,
                    total_inventory_cost=bill.total_inventory_cost,
                    total_amount=bill.total_amount,
                    amount_paid=bill.amount_paid,
                    entered_by=bill.entered_by
                )

                # Archive Service Entries
                service_entries = ServiceEntry.objects.filter(service_record__car=car)
                for se in service_entries:
                    ArchivedServiceEntry.objects.create(
                        paid_bill=paid_bill,
                        service_name=se.service.name,
                        service_description=se.service.description,
                        cost=se.service.standard_rate,
                        remarks=se.remarks,
                        performed_at=se.performed_at,
                        created_at=se.service_record.created_at,
                        updated_at=se.service_record.updated_at
                    )

                # Archive Inventory Usage
                inventory_usages = InventoryUsage.objects.filter(service_record__car=car)
                for iu in inventory_usages:
                    unit_cost = iu.product.standard_rate  # adjust if your InventoryItem uses different field
                    total_cost = unit_cost * iu.quantity_used
                    ArchivedInventoryUsage.objects.create(
                        paid_bill=paid_bill,
                        product_name=iu.product.name,
                        quantity=iu.quantity_used,
                        unit_cost=unit_cost,
                        total_cost=total_cost,
                        used_at=iu.used_at,
                        created_at=iu.service_record.created_at
                    )

                # Clean active records
                service_entries.delete()
                inventory_usages.delete()
                CarServiceRecord.objects.filter(car=car).delete()
                bill.delete()
            bill_data.update({
                "car": {"plate_number": car.plate_number, "id": car.id},
                "bill_id": bill.id if bill.id else None,
                "discount": str(bill.discount),
                "amount_paid": str(bill.amount_paid),
                "amount_remaining": str(bill.amount_remaining),
                "total_amount": str(bill.total_amount),
                "return_to_customer": str(return_to_customer)
            })

            pdf_buffer = generate_invoice_pdf(bill_data)
            return FileResponse(
                pdf_buffer,
                as_attachment=True,
                filename=f"invoice_car_{car.plate_number}_{car_id}.pdf",
                content_type='application/pdf'
            )

        except Exception as e:
            logger.exception(f"Error generating PDF for car {car_id}: {str(e)}")
            return Response(
                {"detail": "An error occurred while generating the PDF."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class BillUpdateAPIView(APIView):
    """
    API to update bill payment information.
    Allows admins to record additional payments and automatically handles
    service record cleanup when full payment is received.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        """Only admin users can update bills"""
        if self.request.method in ['PUT', 'PATCH']:
            return [permissions.IsAuthenticated(), permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]

    @extend_schema(
        operation_id="update_bill_payment",
        request=BillUpdateSerializer,
        responses={
            200: BillResponseSerializer,
            400: OpenApiResponse(description="Invalid input data."),
            403: OpenApiResponse(description="Admin access required."),
            404: OpenApiResponse(description="Bill not found."),
        },
        tags=["Billing"],
        summary="Update Bill Payment Information",
        description="""
        Update bill payment details. When full payment is received (amount_remaining <= 0),
        the associated service entries and inventory usage records will be automatically deleted.
        Only admin users can perform this action.
        """
    )
    def patch(self, request, bill_id):
        try:
            bill = get_object_or_404(Bill, id=bill_id)
            
            serializer = BillUpdateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # Get new payment details
            new_discount = serializer.validated_data.get('discount')
            additional_payment = serializer.validated_data.get('additional_payment', Decimal('0'))
            
            with transaction.atomic():
                # Update discount if provided
                if new_discount is not None:
                    bill.discount = new_discount

                # Add additional payment to existing payment
                if additional_payment > 0:
                    bill.amount_paid += additional_payment

                # Recalculate remaining amount
                bill.amount_remaining = bill.total_amount - bill.discount - bill.amount_paid

                # Ensure amount_remaining doesn't go negative
                if bill.amount_remaining < 0:
                    # If overpaid, adjust amount_paid and set remaining to 0
                    overpayment = abs(bill.amount_remaining)
                    bill.amount_paid -= overpayment
                    bill.amount_remaining = Decimal('0')

                bill.save()

                # Check if bill is fully paid and cleanup service records
                payment_completed = bill.amount_remaining <= 0
                cleanup_performed = False

                if payment_completed:
                    cleanup_result = self._cleanup_service_records(bill.car.id)
                    cleanup_performed = cleanup_result['success']
                    
                    if not cleanup_performed:
                        logger.warning(f"Failed to cleanup service records for bill {bill_id}: {cleanup_result.get('error')}")

                # Prepare response
                response_data = {
                    'bill_id': bill.id,
                    'total_service_cost': str(bill.total_service_cost),
                    'total_inventory_cost': str(bill.total_inventory_cost),
                    'total_amount': str(bill.total_amount),
                    'discount': str(bill.discount),
                    'amount_paid': str(bill.amount_paid),
                    'amount_remaining': str(bill.amount_remaining),
                    'created_at': bill.created_at.isoformat(),
                    'is_fully_paid': payment_completed,
                    'service_records_cleaned': cleanup_performed
                }

                return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error updating bill {bill_id}: {str(e)}")
            return Response(
                {"detail": "An error occurred while updating the bill."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _cleanup_service_records(self, car_id):
        """
        Delete service entries and inventory usage for a car when bill is fully paid.
        Returns dict with success status and optional error message.
        """
        try:
            with transaction.atomic():
                # Get the service record for the car
                try:
                    service_record = CarServiceRecord.objects.get(car_id=car_id)
                except CarServiceRecord.DoesNotExist:
                    return {"success": True, "message": "No service record found to cleanup"}

                # Count records before deletion for logging
                service_entries_count = ServiceEntry.objects.filter(service_record=service_record).count()
                inventory_usage_count = InventoryUsage.objects.filter(service_record=service_record).count()

                # Delete service entries and inventory usage
                ServiceEntry.objects.filter(service_record=service_record).delete()
                InventoryUsage.objects.filter(service_record=service_record).delete()

                # Optionally delete the service record itself if it's empty
                # Uncomment the next line if you want to delete the parent service record too
                # service_record.delete()

                logger.info(f"Cleanup completed for car {car_id}: "
                           f"Deleted {service_entries_count} service entries and "
                           f"{inventory_usage_count} inventory usage records")

                return {
                    "success": True, 
                    "service_entries_deleted": service_entries_count,
                    "inventory_usage_deleted": inventory_usage_count
                }

        except Exception as e:
            logger.error(f"Error during service record cleanup for car {car_id}: {str(e)}")
            return {"success": False, "error": str(e)}


class BillListAPIView(APIView):
    """
    API to list and retrieve bills with filtering options including car ID search.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id="list_bills",
        responses={200: BillListSerializer(many=True)},
        parameters=[
            OpenApiParameter(
                name="car_id",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Filter bills by specific car ID",
                required=False
            ),
            OpenApiParameter(
                name="car_search",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Search bills by car plate number or car ID (partial match supported)",
                required=False
            ),
            OpenApiParameter(
                name="is_paid",
                type=bool,
                location=OpenApiParameter.QUERY,
                description="Filter by payment status (true for fully paid, false for unpaid/partially paid)",
                required=False
            ),
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Page number for pagination (default: 1)",
                required=False
            ),
            OpenApiParameter(
                name="page_size",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Number of items per page (default: 20, max: 100)",
                required=False
            )
        ],
        tags=["Billing"],
        summary="List All Bills with Search and Filters",
        description="""
        Retrieve a paginated list of bills with comprehensive filtering options:
        - Filter by specific car ID or search across car plate numbers
        - Filter by payment status (paid/unpaid)
        - Support for pagination with customizable page size
        """
    )
    def get(self, request):
        try:
            queryset = Bill.objects.select_related('car', 'entered_by').all()

            # Apply car-specific filters
            car_id = request.query_params.get('car_id')
            car_search = request.query_params.get('car_search')
            
            if car_id:
                # Filter by specific car ID
                queryset = queryset.filter(car_id=car_id)
            elif car_search:
                # Search across car ID and plate number (partial match)
                queryset = queryset.filter(
                    Q(car_id__icontains=car_search) |
                    Q(car__plate_number__icontains=car_search)
                )

            # Apply payment status filter
            is_paid = request.query_params.get('is_paid')
            if is_paid is not None:
                if is_paid.lower() == 'true':
                    queryset = queryset.filter(amount_remaining__lte=0)
                else:
                    queryset = queryset.filter(amount_remaining__gt=0)

            # Order by creation date (newest first)
            queryset = queryset.order_by('-created_at')

            # Enhanced pagination
            page = int(request.query_params.get('page', 1))
            page_size = min(int(request.query_params.get('page_size', 20)), 100)  # Max 100 items per page
            start = (page - 1) * page_size
            end = start + page_size
            
            bills = queryset[start:end]
            total_count = queryset.count()

            serializer = BillListSerializer(bills, many=True)
            
            return Response({
                'results': serializer.data,
                'total_count': total_count,
                'page': page,
                'page_size': page_size,
                'has_next': end < total_count,
                'has_previous': page > 1,
                'total_pages': (total_count + page_size - 1) // page_size
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response(
                {"detail": "Invalid page or page_size parameter. Must be integers."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error listing bills: {str(e)}")
            return Response(
                {"detail": "An error occurred while retrieving bills."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BillDetailAPIView(APIView):
    """
    API to retrieve detailed bill information with optional car search functionality.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id="retrieve_bill_detail",
        responses={
            200: BillListSerializer,
            404: OpenApiResponse(description="Bill not found.")
        },
        parameters=[
            OpenApiParameter(
                name="car_id",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Verify that the bill belongs to this specific car ID",
                required=False
            )
        ],
        tags=["Billing"],
        summary="Get Bill Details",
        description="""
        Retrieve detailed information about a specific bill.
        Optionally verify that the bill belongs to a specific car by providing car_id parameter.
        """
    )
    def get(self, request, bill_id):
        try:
            queryset = Bill.objects.select_related('car', 'entered_by')
            
            # Apply car filter if provided
            car_id = request.query_params.get('car_id')
            if car_id:
                queryset = queryset.filter(car_id=car_id)
            
            bill = get_object_or_404(queryset, id=bill_id)
            
            serializer = BillListSerializer(bill)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error retrieving bill {bill_id}: {str(e)}")
            return Response(
                {"detail": "An error occurred while retrieving the bill."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BillDeleteAPIView(APIView):
    """
    API to delete bills with car verification (Admin only).
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    @extend_schema(
        operation_id="delete_bill",
        parameters=[
            OpenApiParameter(
                name="car_id",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Verify that the bill belongs to this specific car ID before deletion",
                required=False
            )
        ],
        responses={
            204: OpenApiResponse(description="Bill deleted successfully."),
            403: OpenApiResponse(description="Admin access required."),
            404: OpenApiResponse(description="Bill not found or doesn't belong to specified car.")
        },
        tags=["Billing"],
        summary="Delete Bill with Car Verification",
        description="""
        Delete a bill record with optional car verification. 
        If car_id is provided, the system will verify that the bill belongs to that car before deletion.
        Only admin users can perform this action.
        """
    )
    def delete(self, request, bill_id):
        try:
            queryset = Bill.objects.all()
            
            # Apply car filter if provided
            car_id = request.query_params.get('car_id')
            if car_id:
                queryset = queryset.filter(car_id=car_id)
            
            bill = get_object_or_404(queryset, id=bill_id)
            
            # Log the deletion for audit purposes
            logger.info(f"Bill {bill_id} for car {bill.car.plate_number} (ID: {bill.car.id}) deleted by user {request.user.id}")
            
            bill.delete()
            
            return Response(status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            logger.error(f"Error deleting bill {bill_id}: {str(e)}")
            return Response(
                {"detail": "An error occurred while deleting the bill."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BillSearchAPIView(APIView):
    """
    Dedicated API endpoint for advanced bill searching with multiple criteria.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id="search_bills",
        responses={200: BillListSerializer(many=True)},
        parameters=[
            OpenApiParameter(
                name="car_id",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Search bills by specific car ID",
                required=False
            ),
            OpenApiParameter(
                name="plate_number",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Search bills by car plate number (partial match supported)",
                required=False
            ),
            OpenApiParameter(
                name="min_amount",
                type=float,
                location=OpenApiParameter.QUERY,
                description="Filter bills with total amount greater than or equal to this value",
                required=False
            ),
            OpenApiParameter(
                name="max_amount",
                type=float,
                location=OpenApiParameter.QUERY,
                description="Filter bills with total amount less than or equal to this value",
                required=False
            ),
            OpenApiParameter(
                name="payment_status",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by payment status: 'paid', 'unpaid', or 'partial'",
                required=False,
                enum=['paid', 'unpaid', 'partial']
            ),
            OpenApiParameter(
                name="date_from",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter bills created from this date (YYYY-MM-DD format)",
                required=False
            ),
            OpenApiParameter(
                name="date_to",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter bills created up to this date (YYYY-MM-DD format)",
                required=False
            ),
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Page number for pagination (default: 1)",
                required=False
            ),
            OpenApiParameter(
                name="page_size",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Number of items per page (default: 20, max: 100)",
                required=False
            )
        ],
        tags=["Billing"],
        summary="Advanced Bill Search",
        description="""
        Advanced search functionality for bills with multiple filter criteria:
        - Search by car ID or plate number
        - Filter by amount range
        - Filter by payment status (paid/unpaid/partial)
        - Filter by date range
        - Support for pagination
        """
    )
    def get(self, request):
        try:
            from datetime import datetime
            
            queryset = Bill.objects.select_related('car', 'entered_by').all()

            # Car-based filters
            car_id = request.query_params.get('car_id')
            plate_number = request.query_params.get('plate_number')
            
            if car_id:
                queryset = queryset.filter(car_id=car_id)
            elif plate_number:
                queryset = queryset.filter(car__plate_number__icontains=plate_number)

            # Amount range filters
            min_amount = request.query_params.get('min_amount')
            max_amount = request.query_params.get('max_amount')
            
            if min_amount:
                queryset = queryset.filter(total_amount__gte=Decimal(min_amount))
            if max_amount:
                queryset = queryset.filter(total_amount__lte=Decimal(max_amount))

            # Payment status filter
            payment_status = request.query_params.get('payment_status')
            if payment_status:
                if payment_status.lower() == 'paid':
                    queryset = queryset.filter(amount_remaining__lte=0)
                elif payment_status.lower() == 'unpaid':
                    queryset = queryset.filter(amount_paid=0)
                elif payment_status.lower() == 'partial':
                    queryset = queryset.filter(amount_paid__gt=0, amount_remaining__gt=0)

            # Date range filters
            date_from = request.query_params.get('date_from')
            date_to = request.query_params.get('date_to')
            
            if date_from:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__gte=date_from_obj)
            if date_to:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__lte=date_to_obj)

            # Order by creation date (newest first)
            queryset = queryset.order_by('-created_at')

            # Pagination
            page = int(request.query_params.get('page', 1))
            page_size = min(int(request.query_params.get('page_size', 20)), 100)
            start = (page - 1) * page_size
            end = start + page_size
            
            bills = queryset[start:end]
            total_count = queryset.count()

            serializer = BillListSerializer(bills, many=True)
            
            return Response({
                'results': serializer.data,
                'total_count': total_count,
                'page': page,
                'page_size': page_size,
                'has_next': end < total_count,
                'has_previous': page > 1,
                'total_pages': (total_count + page_size - 1) // page_size,
                'filters_applied': {
                    'car_id': car_id,
                    'plate_number': plate_number,
                    'min_amount': min_amount,
                    'max_amount': max_amount,
                    'payment_status': payment_status,
                    'date_from': date_from,
                    'date_to': date_to
                }
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response(
                {"detail": f"Invalid parameter format: {str(e)}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error in bill search: {str(e)}")
            return Response(
                {"detail": "An error occurred while searching bills."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
@extend_schema(
    operation_id="list_paid_bills",
    responses={200: PaidBillSerializer(many=True)},
    tags=["Billing"],
    summary="List All Paid Bills",
    description="Retrieve a paginated list of all paid bills with optional filters."
)         
class PaidBillListAPIView(generics.ListAPIView):
    queryset = PaidBill.objects.all()
    serializer_class = PaidBillSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Optional filters
        car_id = self.request.query_params.get('car_id')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if car_id:
            queryset = queryset.filter(car_id=car_id)
        if start_date and end_date:
            queryset = queryset.filter(created_at__date__range=[start_date, end_date])

        return queryset
    
    
    
class RevenueAnalyticsAPIView(APIView):
    """
    API to get revenue analytics over time periods with grouping options.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id="get_revenue_analytics",
        request=DateRangeAnalyticsSerializer,
        responses={
            200: RevenueAnalyticsResponseSerializer(many=True),
            400: OpenApiResponse(description="Invalid date range or parameters"),
        },
        tags=["Analytics"],
        summary="Revenue Analytics Over Time",
        description="""
        Get revenue analytics data grouped by time periods (day, week, month, year).
        Includes total revenue, service revenue, inventory revenue, bill counts, and averages.
        
        Example usage:
        - Daily revenue for last 30 days
        - Monthly revenue for current year
        - Weekly revenue trends
        """
    )
    def post(self, request):
        serializer = DateRangeAnalyticsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            start_date = serializer.validated_data.get('start_date')
            end_date = serializer.validated_data.get('end_date')
            group_by = serializer.validated_data.get('group_by', 'day')

            # Default date range if not provided
            if not end_date:
                end_date = timezone.now().date()
            if not start_date:
                start_date = end_date - timedelta(days=30)

            # Choose truncation function based on group_by
            trunc_func = {
                'day': TruncDay,
                'week': TruncWeek,
                'month': TruncMonth,
                'year': TruncYear
            }[group_by]

            # Query both Bill and PaidBill models
            bills_data = Bill.objects.filter(
                created_at__date__range=[start_date, end_date]
            ).annotate(
                period=trunc_func('created_at')
            ).values('period').annotate(
                total_revenue=Sum('total_amount'),
                service_revenue=Sum('total_service_cost'),
                inventory_revenue=Sum('total_inventory_cost'),
                bills_count=Count('id'),
                average_bill_amount=Avg('total_amount')
            ).order_by('period')

            paid_bills_data = PaidBill.objects.filter(
                created_at__date__range=[start_date, end_date]
            ).annotate(
                period=trunc_func('created_at')
            ).values('period').annotate(
                total_revenue=Sum('total_amount'),
                service_revenue=Sum('total_service_cost'),
                inventory_revenue=Sum('total_inventory_cost'),
                bills_count=Count('id'),
                average_bill_amount=Avg('total_amount')
            ).order_by('period')

            # Combine and aggregate data from both sources
            combined_data = {}
            
            for item in bills_data:
                period_key = item['period'].strftime('%Y-%m-%d' if group_by == 'day' else '%Y-%m-%d')
                combined_data[period_key] = {
                    'period': period_key,
                    'total_revenue': item['total_revenue'] or Decimal('0'),
                    'service_revenue': item['service_revenue'] or Decimal('0'),
                    'inventory_revenue': item['inventory_revenue'] or Decimal('0'),
                    'bills_count': item['bills_count'],
                    'average_bill_amount': item['average_bill_amount'] or Decimal('0')
                }

            for item in paid_bills_data:
                period_key = item['period'].strftime('%Y-%m-%d' if group_by == 'day' else '%Y-%m-%d')
                if period_key in combined_data:
                    combined_data[period_key]['total_revenue'] += item['total_revenue'] or Decimal('0')
                    combined_data[period_key]['service_revenue'] += item['service_revenue'] or Decimal('0')
                    combined_data[period_key]['inventory_revenue'] += item['inventory_revenue'] or Decimal('0')
                    combined_data[period_key]['bills_count'] += item['bills_count']
                    # Recalculate average
                    total_bills = combined_data[period_key]['bills_count']
                    if total_bills > 0:
                        combined_data[period_key]['average_bill_amount'] = combined_data[period_key]['total_revenue'] / total_bills
                else:
                    combined_data[period_key] = {
                        'period': period_key,
                        'total_revenue': item['total_revenue'] or Decimal('0'),
                        'service_revenue': item['service_revenue'] or Decimal('0'),
                        'inventory_revenue': item['inventory_revenue'] or Decimal('0'),
                        'bills_count': item['bills_count'],
                        'average_bill_amount': item['average_bill_amount'] or Decimal('0')
                    }

            # Convert to list and sort
            result_data = sorted(combined_data.values(), key=lambda x: x['period'])
            
            return Response(result_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in revenue analytics: {str(e)}")
            return Response(
                {"detail": "An error occurred while generating revenue analytics."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PaymentAnalyticsAPIView(APIView):
    """
    API to get payment status analytics over time periods.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id="get_payment_analytics",
        request=DateRangeAnalyticsSerializer,
        responses={
            200: PaymentAnalyticsResponseSerializer(many=True),
            400: OpenApiResponse(description="Invalid date range or parameters"),
        },
        tags=["Analytics"],
        summary="Payment Status Analytics",
        description="""
        Get payment status analytics including total payments, payment distributions,
        and outstanding amounts grouped by time periods.
        """
    )
    def post(self, request):
        serializer = DateRangeAnalyticsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            start_date = serializer.validated_data.get('start_date')
            end_date = serializer.validated_data.get('end_date')
            group_by = serializer.validated_data.get('group_by', 'day')

            if not end_date:
                end_date = timezone.now().date()
            if not start_date:
                start_date = end_date - timedelta(days=30)

            trunc_func = {
                'day': TruncDay,
                'week': TruncWeek,
                'month': TruncMonth,
                'year': TruncYear
            }[group_by]

            # Get payment analytics for active bills
            bills_data = Bill.objects.filter(
                created_at__date__range=[start_date, end_date]
            ).annotate(
                period=trunc_func('created_at')
            ).values('period').annotate(
                total_payments=Sum('amount_paid'),
                fully_paid_bills=Count('id', filter=Q(amount_remaining__lte=0)),
                partially_paid_bills=Count('id', filter=Q(amount_paid__gt=0, amount_remaining__gt=0)),
                unpaid_bills=Count('id', filter=Q(amount_paid=0)),
                outstanding_amount=Sum('amount_remaining')
            ).order_by('period')

            # Get payment data for paid bills (all are fully paid)
            paid_bills_data = PaidBill.objects.filter(
                created_at__date__range=[start_date, end_date]
            ).annotate(
                period=trunc_func('created_at')
            ).values('period').annotate(
                total_payments=Sum('amount_paid'),
                fully_paid_bills=Count('id'),
                partially_paid_bills=Count('id', filter=Q(pk__isnull=True)),  # Always 0 for paid bills
                unpaid_bills=Count('id', filter=Q(pk__isnull=True)),  # Always 0 for paid bills
                outstanding_amount=Sum('amount_paid', filter=Q(pk__isnull=True))  # Always 0 for paid bills
            ).order_by('period')

            # Combine data
            combined_data = {}
            
            for item in bills_data:
                period_key = item['period'].strftime('%Y-%m-%d' if group_by == 'day' else '%Y-%m-%d')
                combined_data[period_key] = {
                    'period': period_key,
                    'total_payments': item['total_payments'] or Decimal('0'),
                    'fully_paid_bills': item['fully_paid_bills'],
                    'partially_paid_bills': item['partially_paid_bills'],
                    'unpaid_bills': item['unpaid_bills'],
                    'outstanding_amount': item['outstanding_amount'] or Decimal('0')
                }

            for item in paid_bills_data:
                period_key = item['period'].strftime('%Y-%m-%d' if group_by == 'day' else '%Y-%m-%d')
                if period_key in combined_data:
                    combined_data[period_key]['total_payments'] += item['total_payments'] or Decimal('0')
                    combined_data[period_key]['fully_paid_bills'] += item['fully_paid_bills']
                else:
                    combined_data[period_key] = {
                        'period': period_key,
                        'total_payments': item['total_payments'] or Decimal('0'),
                        'fully_paid_bills': item['fully_paid_bills'],
                        'partially_paid_bills': 0,
                        'unpaid_bills': 0,
                        'outstanding_amount': Decimal('0')
                    }

            result_data = sorted(combined_data.values(), key=lambda x: x['period'])
            
            return Response(result_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in payment analytics: {str(e)}")
            return Response(
                {"detail": "An error occurred while generating payment analytics."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TopCustomersAPIView(APIView):
    """
    API to get top customers by revenue, bill count, or other metrics.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id="get_top_customers",
        parameters=[
            OpenApiParameter(
                name="limit",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Number of top customers to return (default: 10, max: 50)",
                required=False
            ),
            OpenApiParameter(
                name="order_by",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Order by: 'revenue', 'bills_count', 'avg_bill' (default: revenue)",
                required=False
            ),
            OpenApiParameter(
                name="start_date",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Start date for analysis (YYYY-MM-DD)",
                required=False
            ),
            OpenApiParameter(
                name="end_date",
                type=str,
                location=OpenApiParameter.QUERY,
                description="End date for analysis (YYYY-MM-DD)",
                required=False
            )
        ],
        responses={
            200: TopCustomersResponseSerializer(many=True),
            400: OpenApiResponse(description="Invalid parameters"),
        },
        tags=["Analytics"],
        summary="Top Customers Analytics",
        description="""
        Get top customers ranked by various metrics such as total revenue,
        number of bills, or average bill amount within a specified date range.
        """
    )
    def get(self, request):
        try:
            limit = min(int(request.query_params.get('limit', 10)), 50)
            order_by = request.query_params.get('order_by', 'revenue')
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')

            # Parse dates if provided
            date_filter = {}
            if start_date:
                date_filter['created_at__date__gte'] = datetime.strptime(start_date, '%Y-%m-%d').date()
            if end_date:
                date_filter['created_at__date__lte'] = datetime.strptime(end_date, '%Y-%m-%d').date()

            # Query active bills
            bills_by_car = Bill.objects.filter(**date_filter).values(
                'car_id', 'car__plate_number'
            ).annotate(
                total_bills=Count('id'),
                total_revenue=Sum('total_amount'),
                average_bill_amount=Avg('total_amount'),
                last_service_date=Max('created_at')
            )

            # Query paid bills
            paid_bills_by_car = PaidBill.objects.filter(**date_filter).values(
                'car_id', 'car__plate_number'
            ).annotate(
                total_bills=Count('id'),
                total_revenue=Sum('total_amount'),
                average_bill_amount=Avg('total_amount'),
                last_service_date=Max('created_at')
            )

            # Combine data from both sources
            combined_data = {}
            
            for item in bills_by_car:
                car_id = item['car_id']
                combined_data[car_id] = {
                    'car_id': car_id,
                    'car_plate_number': item['car__plate_number'],
                    'total_bills': item['total_bills'],
                    'total_revenue': item['total_revenue'] or Decimal('0'),
                    'average_bill_amount': item['average_bill_amount'] or Decimal('0'),
                    'last_service_date': item['last_service_date']
                }

            for item in paid_bills_by_car:
                car_id = item['car_id']
                if car_id in combined_data:
                    combined_data[car_id]['total_bills'] += item['total_bills']
                    combined_data[car_id]['total_revenue'] += item['total_revenue'] or Decimal('0')
                    # Recalculate average
                    if combined_data[car_id]['total_bills'] > 0:
                        combined_data[car_id]['average_bill_amount'] = combined_data[car_id]['total_revenue'] / combined_data[car_id]['total_bills']
                    # Update last service date if newer
                    if item['last_service_date'] and (not combined_data[car_id]['last_service_date'] or item['last_service_date'] > combined_data[car_id]['last_service_date']):
                        combined_data[car_id]['last_service_date'] = item['last_service_date']
                else:
                    combined_data[car_id] = {
                        'car_id': car_id,
                        'car_plate_number': item['car__plate_number'],
                        'total_bills': item['total_bills'],
                        'total_revenue': item['total_revenue'] or Decimal('0'),
                        'average_bill_amount': item['average_bill_amount'] or Decimal('0'),
                        'last_service_date': item['last_service_date']
                    }

            # Sort based on order_by parameter
            if order_by == 'bills_count':
                sorted_data = sorted(combined_data.values(), key=lambda x: x['total_bills'], reverse=True)
            elif order_by == 'avg_bill':
                sorted_data = sorted(combined_data.values(), key=lambda x: x['average_bill_amount'], reverse=True)
            else:  # default to revenue
                sorted_data = sorted(combined_data.values(), key=lambda x: x['total_revenue'], reverse=True)

            result_data = sorted_data[:limit]
            
            return Response(result_data, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response(
                {"detail": f"Invalid parameter: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error in top customers analytics: {str(e)}")
            return Response(
                {"detail": "An error occurred while generating top customers analytics."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DashboardSummaryAPIView(APIView):
    """
    API to get dashboard summary with key metrics for today and current month.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id="get_dashboard_summary",
        responses={
            200: DashboardSummaryResponseSerializer,
        },
        tags=["Analytics"],
        summary="Dashboard Summary Analytics",
        description="""
        Get key metrics for dashboard display including today's and current month's
        revenue, bill counts, pending payments, and top services.
        """
    )
    def get(self, request):
        try:
            today = timezone.now().date()
            start_of_month = today.replace(day=1)
            
            # Today's metrics from active bills
            today_bills = Bill.objects.filter(created_at__date=today)
            today_revenue = today_bills.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
            today_bills_count = today_bills.count()
            today_avg_bill = today_bills.aggregate(Avg('total_amount'))['total_amount__avg'] or Decimal('0')

            # Today's metrics from paid bills
            today_paid_bills = PaidBill.objects.filter(created_at__date=today)
            today_revenue += today_paid_bills.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
            today_bills_count += today_paid_bills.count()
            
            # Recalculate today's average
            if today_bills_count > 0:
                today_avg_bill = today_revenue / today_bills_count

            # Current month metrics
            month_bills = Bill.objects.filter(created_at__date__gte=start_of_month)
            month_revenue = month_bills.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
            month_bills_count = month_bills.count()

            month_paid_bills = PaidBill.objects.filter(created_at__date__gte=start_of_month)
            month_revenue += month_paid_bills.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
            month_bills_count += month_paid_bills.count()

            # Pending payments (only from active bills)
            pending_data = Bill.objects.filter(amount_remaining__gt=0).aggregate(
                total_pending=Sum('amount_remaining'),
                pending_count=Count('id')
            )

            # Top service today (simplified - would need service data integration)
            # This is a placeholder - you would need to integrate with your service tracking
            top_service_today = None
            try:
                # Get most common service from today's service records
                today_services = ServiceEntry.objects.filter(
                    service_record__carservicerecord__created_at__date=today
                ).values('service__name').annotate(
                    count=Count('id')
                ).order_by('-count').first()
                
                if today_services:
                    top_service_today = today_services['service__name']
            except Exception:
                pass  # Gracefully handle if service data is not available

            summary_data = {
                'total_revenue_today': today_revenue,
                'total_revenue_this_month': month_revenue,
                'total_bills_today': today_bills_count,
                'total_bills_this_month': month_bills_count,
                'pending_payments': pending_data['total_pending'] or Decimal('0'),
                'pending_bills_count': pending_data['pending_count'] or 0,
                'average_bill_amount_today': today_avg_bill,
                'top_service_today': top_service_today
            }

            return Response(summary_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in dashboard summary: {str(e)}")
            return Response(
                {"detail": "An error occurred while generating dashboard summary."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            

class ServiceAnalyticsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id="get_service_analytics",
        parameters=[
            OpenApiParameter(
                name="start_date",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Start date for analysis (YYYY-MM-DD)",
                required=False
            ),
            OpenApiParameter(
                name="end_date",
                type=str,
                location=OpenApiParameter.QUERY,
                description="End date for analysis (YYYY-MM-DD)",
                required=False
            ),
            OpenApiParameter(
                name="limit",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Number of top services to return (default: 10, max: 50)",
                required=False
            )
        ],
        responses={
            200: ServiceAnalyticsResponseSerializer(many=True),
            400: OpenApiResponse(description="Invalid parameters"),
        },
        tags=["Analytics"],
        summary="Service Analytics",
        description="Get analytics for services (live + archived)."
    )
    def get(self, request):
        try:
            from cars.models import ServiceEntry
            from billing.models import ArchivedServiceEntry

            limit = min(int(request.query_params.get('limit', 10)), 50)
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')

            date_filter = {}
            if start_date:
                date_filter['created_at__date__gte'] = datetime.strptime(start_date, '%Y-%m-%d').date()
            if end_date:
                date_filter['created_at__date__lte'] = datetime.strptime(end_date, '%Y-%m-%d').date()

            # --- Live Service Entries ---
            live_services = ServiceEntry.objects.filter(
                **date_filter
            ).values(
                'service__name'
            ).annotate(
                service_count=Count('id'),
                total_revenue=Sum('service__standard_rate'),
                average_price=Avg('service__standard_rate')
            )

            # --- Archived Service Entries ---
            archived_services = ArchivedServiceEntry.objects.filter(
                **date_filter
            ).values(
                'service_name'
            ).annotate(
                service_count=Count('id'),
                total_revenue=Sum('cost'),
                average_price=Avg('cost')
            )

            # --- Merge results ---
            analytics_map = {}

            # Add live
            for item in live_services:
                name = item['service__name']
                analytics_map[name] = {
                    'service_name': name,
                    'service_count': item['service_count'],
                    'total_revenue': item['total_revenue'] or Decimal('0'),
                    'average_price': item['average_price'] or Decimal('0')
                }

            # Add archived
            for item in archived_services:
                name = item['service_name']
                if name in analytics_map:
                    analytics_map[name]['service_count'] += item['service_count']
                    analytics_map[name]['total_revenue'] += item['total_revenue'] or Decimal('0')
                else:
                    analytics_map[name] = {
                        'service_name': name,
                        'service_count': item['service_count'],
                        'total_revenue': item['total_revenue'] or Decimal('0'),
                        'average_price': item['average_price'] or Decimal('0')
                    }

            # Convert to list & sort
            result_data = sorted(
                analytics_map.values(),
                key=lambda x: x['service_count'],
                reverse=True
            )[:limit]

            return Response(result_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in service analytics: {str(e)}")
            return Response(
                {"detail": "An error occurred while generating service analytics."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class InventoryAnalyticsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id="get_inventory_analytics",
        parameters=[ ... ],  # same as before
        responses={ 200: InventoryAnalyticsResponseSerializer(many=True) },
        tags=["Analytics"],
        summary="Inventory Usage Analytics",
        description="Get analytics for inventory/product usage (live + archived)."
    )
    def get(self, request):
        try:
            from cars.models import InventoryUsage
            from billing.models import ArchivedInventoryUsage

            limit = min(int(request.query_params.get('limit', 10)), 50)
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')

            date_filter = {}
            if start_date:
                date_filter['created_at__date__gte'] = datetime.strptime(start_date, '%Y-%m-%d').date()
            if end_date:
                date_filter['created_at__date__lte'] = datetime.strptime(end_date, '%Y-%m-%d').date()

            # --- Live Inventory ---
            live_inventory = InventoryUsage.objects.filter(
                **date_filter
            ).values(
                'product__name'
            ).annotate(
                quantity_used=Sum('quantity_used'),
                total_revenue=Sum('product__standard_rate'),
                average_price=Avg('product__standard_rate')
            )

            # --- Archived Inventory ---
            archived_inventory = ArchivedInventoryUsage.objects.filter(
                **date_filter
            ).values(
                'product_name'
            ).annotate(
                quantity_used=Sum('quantity'),
                total_revenue=Sum('total_cost'),
                average_price=Avg('unit_cost')
            )

            # --- Merge results ---
            analytics_map = {}

            for item in live_inventory:
                name = item['product__name']
                analytics_map[name] = {
                    'product_name': name,
                    'quantity_used': item['quantity_used'] or 0,
                    'total_revenue': item['total_revenue'] or Decimal('0'),
                    'average_price': item['average_price'] or Decimal('0')
                }

            for item in archived_inventory:
                name = item['product_name']
                if name in analytics_map:
                    analytics_map[name]['quantity_used'] += item['quantity_used'] or 0
                    analytics_map[name]['total_revenue'] += item['total_revenue'] or Decimal('0')
                else:
                    analytics_map[name] = {
                        'product_name': name,
                        'quantity_used': item['quantity_used'] or 0,
                        'total_revenue': item['total_revenue'] or Decimal('0'),
                        'average_price': item['average_price'] or Decimal('0')
                    }

            result_data = sorted(
                analytics_map.values(),
                key=lambda x: x['quantity_used'],
                reverse=True
            )[:limit]

            return Response(result_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in inventory analytics: {str(e)}")
            return Response(
                {"detail": "An error occurred while generating inventory analytics."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class MonthlyComparisonAPIView(APIView):
    """
    API to get monthly comparison analytics between current and previous month.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id="get_monthly_comparison",
        responses={
            200: MonthlyComparisonResponseSerializer,
        },
        tags=["Analytics"],
        summary="Monthly Comparison Analytics",
        description="""
        Compare current month's performance with the previous month including
        revenue, bill counts, and growth percentages.
        """
    )
    def get(self, request):
        try:
            today = timezone.now().date()
            
            # Current month dates
            current_month_start = today.replace(day=1)
            if today.month == 12:
                next_month_start = today.replace(year=today.year + 1, month=1, day=1)
            else:
                next_month_start = today.replace(month=today.month + 1, day=1)

            # Previous month dates
            if today.month == 1:
                prev_month_start = today.replace(year=today.year - 1, month=12, day=1)
                prev_month_end = today.replace(day=1) - timedelta(days=1)
            else:
                prev_month_start = today.replace(month=today.month - 1, day=1)
                prev_month_end = current_month_start - timedelta(days=1)

            # Current month analytics (from both Bill and PaidBill)
            current_bills = Bill.objects.filter(
                created_at__date__gte=current_month_start,
                created_at__date__lt=next_month_start
            ).aggregate(
                revenue=Sum('total_amount'),
                count=Count('id'),
                avg_amount=Avg('total_amount')
            )

            current_paid_bills = PaidBill.objects.filter(
                created_at__date__gte=current_month_start,
                created_at__date__lt=next_month_start
            ).aggregate(
                revenue=Sum('total_amount'),
                count=Count('id'),
                avg_amount=Avg('total_amount')
            )

            # Previous month analytics
            prev_bills = Bill.objects.filter(
                created_at__date__gte=prev_month_start,
                created_at__date__lte=prev_month_end
            ).aggregate(
                revenue=Sum('total_amount'),
                count=Count('id'),
                avg_amount=Avg('total_amount')
            )

            prev_paid_bills = PaidBill.objects.filter(
                created_at__date__gte=prev_month_start,
                created_at__date__lte=prev_month_end
            ).aggregate(
                revenue=Sum('total_amount'),
                count=Count('id'),
                avg_amount=Avg('total_amount')
            )

            # Combine current month data
            current_total_revenue = (current_bills['revenue'] or Decimal('0')) + (current_paid_bills['revenue'] or Decimal('0'))
            current_total_count = (current_bills['count'] or 0) + (current_paid_bills['count'] or 0)
            current_avg = current_total_revenue / current_total_count if current_total_count > 0 else Decimal('0')

            # Combine previous month data
            prev_total_revenue = (prev_bills['revenue'] or Decimal('0')) + (prev_paid_bills['revenue'] or Decimal('0'))
            prev_total_count = (prev_bills['count'] or 0) + (prev_paid_bills['count'] or 0)
            prev_avg = prev_total_revenue / prev_total_count if prev_total_count > 0 else Decimal('0')

            # Calculate growth percentages
            def calculate_growth(current, previous):
                if previous == 0:
                    return Decimal('100') if current > 0 else Decimal('0')
                return ((current - previous) / previous) * 100

            revenue_growth = calculate_growth(current_total_revenue, prev_total_revenue)
            count_growth = calculate_growth(Decimal(current_total_count), Decimal(prev_total_count))
            avg_growth = calculate_growth(current_avg, prev_avg)

            result_data = {
                'current_month': {
                    'revenue': current_total_revenue,
                    'bills_count': Decimal(current_total_count),
                    'average_bill_amount': current_avg
                },
                'previous_month': {
                    'revenue': prev_total_revenue,
                    'bills_count': Decimal(prev_total_count),
                    'average_bill_amount': prev_avg
                },
                'growth_percentage': {
                    'revenue_growth': revenue_growth,
                    'bills_count_growth': count_growth,
                    'average_bill_growth': avg_growth
                }
            }

            return Response(result_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in monthly comparison: {str(e)}")
            return Response(
                {"detail": "An error occurred while generating monthly comparison."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PaymentStatusSummaryAPIView(APIView):
    """
    API to get payment status summary across all bills.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id="get_payment_status_summary",
        parameters=[
            OpenApiParameter(
                name="start_date",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Start date for analysis (YYYY-MM-DD)",
                required=False
            ),
            OpenApiParameter(
                name="end_date",
                type=str,
                location=OpenApiParameter.QUERY,
                description="End date for analysis (YYYY-MM-DD)",
                required=False
            )
        ],
        responses={
            200: PaymentStatusSummarySerializer,
        },
        tags=["Analytics"],
        summary="Payment Status Summary",
        description="""
        Get overall payment status summary including counts and percentages
        of paid, partially paid, and unpaid bills.
        """
    )
    def get(self, request):
        try:
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')

            # Parse dates if provided
            date_filter = {}
            if start_date:
                date_filter['created_at__date__gte'] = datetime.strptime(start_date, '%Y-%m-%d').date()
            if end_date:
                date_filter['created_at__date__lte'] = datetime.strptime(end_date, '%Y-%m-%d').date()

            # Get payment status from active bills
            bills_summary = Bill.objects.filter(**date_filter).aggregate(
                total_bills=Count('id'),
                fully_paid=Count('id', filter=Q(amount_remaining__lte=0)),
                partially_paid=Count('id', filter=Q(amount_paid__gt=0, amount_remaining__gt=0)),
                unpaid=Count('id', filter=Q(amount_paid=0)),
                total_outstanding=Sum('amount_remaining')
            )

            # Get count of paid bills (all are fully paid by definition)
            paid_bills_count = PaidBill.objects.filter(**date_filter).count()

            # Combine totals
            total_bills = (bills_summary['total_bills'] or 0) + paid_bills_count
            fully_paid_total = (bills_summary['fully_paid'] or 0) + paid_bills_count
            partially_paid_total = bills_summary['partially_paid'] or 0
            unpaid_total = bills_summary['unpaid'] or 0
            total_outstanding = bills_summary['total_outstanding'] or Decimal('0')

            # Calculate percentages
            fully_paid_percentage = (fully_paid_total / total_bills * 100) if total_bills > 0 else Decimal('0')

            result_data = {
                'total_bills': total_bills,
                'fully_paid': fully_paid_total,
                'partially_paid': partially_paid_total,
                'unpaid': unpaid_total,
                'fully_paid_percentage': fully_paid_percentage,
                'total_outstanding': total_outstanding
            }

            return Response(result_data, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response(
                {"detail": f"Invalid parameter: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error in payment status summary: {str(e)}")
            return Response(
                {"detail": "An error occurred while generating payment status summary."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PeakHoursAnalyticsAPIView(APIView):
    """
    API to get peak hours analytics showing busiest times of day.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id="get_peak_hours_analytics",
        parameters=[
            OpenApiParameter(
                name="start_date",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Start date for analysis (YYYY-MM-DD)",
                required=False
            ),
            OpenApiParameter(
                name="end_date",
                type=str,
                location=OpenApiParameter.QUERY,
                description="End date for analysis (YYYY-MM-DD)",
                required=False
            )
        ],
        responses={
            200: PeakHoursAnalyticsSerializer(many=True),
        },
        tags=["Analytics"],
        summary="Peak Hours Analytics",
        description="""
        Analyze business activity by hours of the day to identify peak hours
        based on bill creation times and revenue.
        """
    )
    def get(self, request):
        try:
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')

            # Parse dates if provided
            date_filter = {}
            if start_date:
                date_filter['created_at__date__gte'] = datetime.strptime(start_date, '%Y-%m-%d').date()
            if end_date:
                date_filter['created_at__date__lte'] = datetime.strptime(end_date, '%Y-%m-%d').date()

            # Get hourly analytics from bills
            bills_hourly = Bill.objects.filter(**date_filter).annotate(
                hour=Extract('created_at', 'hour')
            ).values('hour').annotate(
                bills_count=Count('id'),
                total_revenue=Sum('total_amount')
            ).order_by('hour')

            # Get hourly analytics from paid bills
            paid_bills_hourly = PaidBill.objects.filter(**date_filter).annotate(
                hour=Extract('created_at', 'hour')
            ).values('hour').annotate(
                bills_count=Count('id'),
                total_revenue=Sum('total_amount')
            ).order_by('hour')

            # Combine data by hour
            hourly_data = {}
            for i in range(24):
                hourly_data[i] = {
                    'hour': i,
                    'bills_count': 0,
                    'total_revenue': Decimal('0')
                }

            # Add bills data
            for item in bills_hourly:
                hour = item['hour']
                hourly_data[hour]['bills_count'] += item['bills_count']
                hourly_data[hour]['total_revenue'] += item['total_revenue'] or Decimal('0')

            # Add paid bills data
            for item in paid_bills_hourly:
                hour = item['hour']
                hourly_data[hour]['bills_count'] += item['bills_count']
                hourly_data[hour]['total_revenue'] += item['total_revenue'] or Decimal('0')

            # Convert to list and sort by bills_count (descending)
            result_data = sorted(hourly_data.values(), key=lambda x: x['bills_count'], reverse=True)

            return Response(result_data, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response(
                {"detail": f"Invalid parameter: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error in peak hours analytics: {str(e)}")
            return Response(
                {"detail": "An error occurred while generating peak hours analytics."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CustomerRetentionAPIView(APIView):
    """
    API to get customer retention analytics over time periods.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id="get_customer_retention_analytics",
        request=DateRangeAnalyticsSerializer,
        responses={
            200: CustomerRetentionSerializer(many=True),
            400: OpenApiResponse(description="Invalid date range or parameters"),
        },
        tags=["Analytics"],
        summary="Customer Retention Analytics",
        description="""
        Analyze customer retention by tracking new vs returning customers
        over specified time periods.
        """
    )
    def post(self, request):
        serializer = DateRangeAnalyticsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            start_date = serializer.validated_data.get('start_date')
            end_date = serializer.validated_data.get('end_date')
            group_by = serializer.validated_data.get('group_by', 'month')

            # Default date range if not provided
            if not end_date:
                end_date = timezone.now().date()
            if not start_date:
                start_date = end_date - timedelta(days=90)

            # Choose truncation function based on group_by
            trunc_func = {
                'day': TruncDay,
                'week': TruncWeek,
                'month': TruncMonth,
                'year': TruncYear
            }[group_by]

            # Get all unique cars that had bills in the date range
            cars_in_period = set()
            
            # From active bills
            bills_cars = Bill.objects.filter(
                created_at__date__range=[start_date, end_date]
            ).values_list('car_id', flat=True).distinct()
            cars_in_period.update(bills_cars)

            # From paid bills
            paid_bills_cars = PaidBill.objects.filter(
                created_at__date__range=[start_date, end_date]
            ).values_list('car_id', flat=True).distinct()
            cars_in_period.update(paid_bills_cars)

            # For each period, determine new vs returning customers
            periods_data = {}

            # Get first bill date for each car (to determine if new or returning)
            car_first_bill_dates = {}
            
            # Check first bill dates from Bill model
            first_bills = Bill.objects.values('car_id').annotate(
                first_bill_date=Min('created_at')
            )
            for item in first_bills:
                car_first_bill_dates[item['car_id']] = item['first_bill_date'].date()

            # Check first bill dates from PaidBill model
            first_paid_bills = PaidBill.objects.values('car_id').annotate(
                first_bill_date=Min('created_at')
            )
            for item in first_paid_bills:
                car_id = item['car_id']
                first_date = item['first_bill_date'].date()
                if car_id not in car_first_bill_dates or first_date < car_first_bill_dates[car_id]:
                    car_first_bill_dates[car_id] = first_date

            # Analyze by periods
            bills_by_period = Bill.objects.filter(
                created_at__date__range=[start_date, end_date]
            ).annotate(
                period=trunc_func('created_at')
            ).values('period', 'car_id', 'created_at').order_by('period')

            paid_bills_by_period = PaidBill.objects.filter(
                created_at__date__range=[start_date, end_date]
            ).annotate(
                period=trunc_func('created_at')
            ).values('period', 'car_id', 'created_at').order_by('period')

            # Combine and analyze
            all_bills = list(bills_by_period) + list(paid_bills_by_period)
            
            for bill in all_bills:
                period_key = bill['period'].strftime('%Y-%m-%d')
                car_id = bill['car_id']
                bill_date = bill['created_at'].date()
                
                if period_key not in periods_data:
                    periods_data[period_key] = {
                        'period': period_key,
                        'new_customers': set(),
                        'returning_customers': set()
                    }

                # Determine if new or returning customer
                first_bill_date = car_first_bill_dates.get(car_id)
                if first_bill_date and first_bill_date >= start_date and first_bill_date == bill_date:
                    periods_data[period_key]['new_customers'].add(car_id)
                else:
                    periods_data[period_key]['returning_customers'].add(car_id)

            # Calculate retention rates and format response
            result_data = []
            for period_key, data in sorted(periods_data.items()):
                new_count = len(data['new_customers'])
                returning_count = len(data['returning_customers'])
                total_customers = new_count + returning_count
                
                retention_rate = (returning_count / total_customers * 100) if total_customers > 0 else Decimal('0')
                
                result_data.append({
                    'period': period_key,
                    'new_customers': new_count,
                    'returning_customers': returning_count,
                    'retention_rate': retention_rate
                })

            return Response(result_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in customer retention analytics: {str(e)}")
            return Response(
                {"detail": "An error occurred while generating customer retention analytics."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )