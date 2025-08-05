from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .utils import calculate_bill_for_car
from .serializers import BillCalculationSerializer, BillResponseSerializer
from .models import Bill, Car
from decimal import Decimal
from django.http import FileResponse
from .utils_pdf import generate_invoice_pdf
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
import logging

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
                response=bytes,  # Use bytes instead of a complex type
            ),
            400: OpenApiResponse(description="Invalid input data."),
            404: OpenApiResponse(description="Car or service record not found."),
            500: OpenApiResponse(description="Error generating PDF."),
        },
        tags=["Billing"],
        summary="Generate PDF Invoice",
        description="Calculates the bill for a car and returns a downloadable PDF invoice with service and inventory breakdown."
    )
    def post(self, request):
        serializer = BillCalculationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            car_id = serializer.validated_data['car_id']
            discount = serializer.validated_data.get('discount', Decimal('0'))
            amount_paid = serializer.validated_data.get('amount_paid', Decimal('0'))

            # Check if car exists
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

            # Add car details to result for PDF
            result['car'] = {
                'plate_number': car.plate_number,
                'id': car.id
            }

            # Generate PDF
            pdf_buffer = generate_invoice_pdf(result)
            response = FileResponse(
                pdf_buffer, 
                as_attachment=True, 
                filename=f"invoice_car_{car.plate_number}_{car_id}.pdf",
                content_type='application/pdf'
            )
            return response

        except Exception as e:
            logger.error(f"Error generating PDF for car {car_id}: {str(e)}")
            return Response(
                {"detail": "An error occurred while generating the PDF."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

