from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .utils import calculate_bill_for_car
from .serializers import BillCalculationSerializer, BillResponseSerializer, BillUpdateSerializer, BillListSerializer
from .models import Bill, Car
from decimal import Decimal
from django.http import FileResponse
from .utils_pdf import generate_invoice_pdf
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample, OpenApiParameter
import logging
from django.shortcuts import get_object_or_404
from django.db import transaction
from cars.models import CarServiceRecord, ServiceEntry, InventoryUsage
from django.db.models import Q

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
        description="Calculates the bill for a car, saves or updates it in the database, and returns a downloadable PDF invoice."
    )
    def post(self, request):
        serializer = BillCalculationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            car_id = serializer.validated_data['car_id']
            discount = serializer.validated_data.get('discount', Decimal('0'))
            new_amount_paid = serializer.validated_data.get('amount_paid', Decimal('0'))

            # Check if car exists
            try:
                car = Car.objects.get(id=car_id)
            except Car.DoesNotExist:
                return Response(
                    {"detail": "Car not found."},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Calculate bill (fresh calculation for current costs)
            result = calculate_bill_for_car(car_id, discount, new_amount_paid)
            if result is None:
                return Response(
                    {"detail": "No service record found for this car."},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Check if bill already exists
            bill = Bill.objects.filter(car=car).first()
            if bill:
                # Update existing bill
                bill.amount_paid += new_amount_paid
                bill.discount = discount  # Update if discount is changed
                bill.amount_remaining = bill.total_amount - bill.amount_paid
                bill.save()
            else:
                # Create new bill
                bill = Bill.objects.create(
                    car=car,
                    total_service_cost=result['total_service_cost'],
                    total_inventory_cost=result['total_inventory_cost'],
                    total_amount=result['total_amount'],
                    discount=discount,
                    amount_paid=new_amount_paid,
                    amount_remaining=result['amount_remaining'],
                    entered_by=request.user
                )

            # Add car & bill details for PDF
            result['car'] = {
                'plate_number': car.plate_number,
                'id': car.id
            }
            result['bill_id'] = bill.id
            result['created_at'] = bill.created_at
            result['amount_paid'] = str(bill.amount_paid)
            result['amount_remaining'] = str(bill.amount_remaining)

            # Generate PDF
            pdf_buffer = generate_invoice_pdf(result)
            return FileResponse(
                pdf_buffer,
                as_attachment=True,
                filename=f"invoice_car_{car.plate_number}_{car_id}.pdf",
                content_type='application/pdf'
            )

        except Exception as e:
            logger.error(f"Error generating PDF for car {car_id}: {str(e)}")
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