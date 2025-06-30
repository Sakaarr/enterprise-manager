from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .models import Bill, BillLineItem, Payment
from .serializers import BillSerializer, BillLineItemSerializer, PaymentSerializer
from django.utils.dateparse import parse_date
from django.db.models import Sum
from rest_framework.views import APIView


@extend_schema(tags=["Billing"])
class BillViewSet(viewsets.ModelViewSet):
    queryset = Bill.objects.all().select_related("service_record").prefetch_related("line_items", "payments")
    serializer_class = BillSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        queryset = self.queryset
        from_date = self.request.query_params.get("from_date")
        to_date = self.request.query_params.get("to_date")
        is_fully_paid = self.request.query_params.get("is_fully_paid")

        if from_date:
            queryset = queryset.filter(created_at__date__gte=parse_date(from_date))
        if to_date:
            queryset = queryset.filter(created_at__date__lte=parse_date(to_date))
        if is_fully_paid in ["true", "false"]:
            queryset = queryset.filter(is_fully_paid=(is_fully_paid == "true"))

        return queryset

@extend_schema(tags=["Billing Line Items"])
class BillLineItemViewSet(viewsets.ModelViewSet):
    queryset = BillLineItem.objects.all()
    serializer_class = BillLineItemSerializer
    permission_classes = [IsAuthenticated]

@extend_schema(tags=["Payments"])
class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        # Optional: update bill.amount_paid automatically
        payment = Payment.objects.get(id=response.data["id"])
        bill = payment.bill
        bill.amount_paid += payment.paid_amount
        bill.save()
        return response

@extend_schema(tags=["Billing"])
class BillSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from_date = request.query_params.get("from_date")
        to_date = request.query_params.get("to_date")

        bills = Bill.objects.all()
        if from_date:
            bills = bills.filter(created_at__date__gte=parse_date(from_date))
        if to_date:
            bills = bills.filter(created_at__date__lte=parse_date(to_date))

        data = {
            "total_billed": bills.aggregate(total=Sum("total_amount"))["total"] or 0,
            "total_paid": bills.aggregate(paid=Sum("amount_paid"))["paid"] or 0,
            "total_due": (bills.aggregate(total=Sum("total_amount"))["total"] or 0)
                         - (bills.aggregate(paid=Sum("amount_paid"))["paid"] or 0)
        }

        return Response(data)