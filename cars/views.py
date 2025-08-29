from rest_framework import viewsets, filters, permissions, serializers
from .models import Car, JobEntry, Service, CarServiceRecord, InventoryUsage, ServiceEntry
from .serializers import CarSerializer, JobEntrySerializer, ServiceSerializer, CarServiceRecordSerializer, InventoryUsageSerializer, ServiceEntrySerializer
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiParameter
from rest_framework.decorators import action
from django.utils.dateparse import parse_date
from django.db.models import Sum
from rest_framework.response import Response
from .filters import CarFilter
from common.viewsets import StandardizedModelViewSet
from drf_spectacular.types import OpenApiTypes
from django.http import HttpResponse
from rest_framework.views import APIView
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle, Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

@extend_schema_view(
    list=extend_schema(tags=["Car"]),
    create=extend_schema(tags=["Car"]),
    retrieve=extend_schema(tags=["Car"]),
    update=extend_schema(tags=["Car"]),
    partial_update=extend_schema(tags=["Car"]),
    destroy=extend_schema(tags=["Car"]),
)
class CarViewSet(viewsets.ModelViewSet):
    queryset = Car.objects.all()
    serializer_class = CarSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CarFilter
    search_fields = ['plate_number', 'owner_name', 'model', 'brand']
    ordering_fields = ['plate_number', 'owner_name']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


@extend_schema_view(
    list=extend_schema(tags=["JobEntry"]),
    create=extend_schema(tags=["JobEntry"]),
    retrieve=extend_schema(tags=["JobEntry"]),
    update=extend_schema(tags=["JobEntry"]),
    partial_update=extend_schema(tags=["JobEntry"]),
    destroy=extend_schema(tags=["JobEntry"]),
)
class JobEntryViewSet(viewsets.ModelViewSet):
    queryset = JobEntry.objects.all()
    serializer_class = JobEntrySerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = {
        'car__plate_number': ['exact'],
        'car__owner_name': ['icontains'],
        'entry_date': ['date', 'date__gte', 'date__lte'],
    }
    ordering_fields = ['entry_date', 'manual_book_number']

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

@extend_schema(tags=["Services"])
class ServiceViewSet(StandardizedModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'standard_rate']

    # def get_permissions(self):
    #     if self.action in ['create', 'update', 'partial_update']:
    #         return [IsAuthenticated]
    #     return super().get_permissions()

@extend_schema(tags=["Car Service Records"])
class CarServiceRecordViewSet(StandardizedModelViewSet):
    queryset = CarServiceRecord.objects.all().select_related('car').prefetch_related('service_entries__service')
    serializer_class = CarServiceRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['car__plate_number', 'car__owner_name']
    ordering_fields = ['created_at', 'car__plate_number']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @extend_schema(
    methods=['post'],
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'car_id': {'type': 'integer'},
                'service_id': {'type': 'integer'},
                'remarks': {'type': 'string', 'required': False}
            },
            'required': ['car_id', 'service_id']
        }
    },
    responses={201: ServiceEntrySerializer}
)
    @action(detail=False, methods=['post'], url_path='add_service')
    def add_service(self, request):
        """Add a new service entry by car_id (creates record if not exists)"""
        car_id = request.data.get('car_id')
        service_id = request.data.get('service_id')
        remarks = request.data.get('remarks', '')

        if not car_id or not service_id:
            return Response({'error': 'Both car_id and service_id are required.'}, status=400)

        try:
            car = Car.objects.get(id=car_id)
        except Car.DoesNotExist:
            return Response({'error': 'Car not found'}, status=404)

        # Check or create CarServiceRecord for the car
        service_record, created = CarServiceRecord.objects.get_or_create(
            car=car,
            defaults={'created_by': request.user}
        )

        try:
            service = Service.objects.get(id=service_id)
        except Service.DoesNotExist:
            return Response({'error': 'Service not found'}, status=404)

        # Create new service entry
        service_entry = ServiceEntry.objects.create(
            service_record=service_record,
            service=service,
            remarks=remarks,
            created_by=request.user
        )

        serializer = ServiceEntrySerializer(service_entry)
        return Response(serializer.data, status=201)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='car_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by car ID'
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        """List all car service records with optional car filtering"""
        car_id = request.query_params.get('car_id')
        if car_id:
            self.queryset = self.queryset.filter(car_id=car_id)
        return super().list(request, *args, **kwargs)
    
    @extend_schema(
    methods=['delete'],
    parameters=[
        OpenApiParameter(
            name='entry_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='ID of the service entry to delete'
        )
    ],
    responses={204: None}
)
    @action(detail=True, methods=['delete'])
    def delete_service(self, request, pk=None):
        """Delete a service entry from an existing car service record"""
        service_record = self.get_object()
        entry_id = request.query_params.get('entry_id')

        if not entry_id:
            return Response({'error': 'entry_id is required'}, status=400)

        try:
            service_entry = service_record.service_entries.get(id=entry_id)
        except ServiceEntry.DoesNotExist:
            return Response({'error': 'ServiceEntry not found'}, status=404)

        service_entry.delete()
        return Response(status=204)
    
    @extend_schema(
    methods=['get'],
    parameters=[
        OpenApiParameter(
            name='car_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='ID of the car to fetch service record(s) for',
            required=True,
        ),
    ],
    responses={200: CarServiceRecordSerializer(many=True)}
)
    @action(detail=False, methods=['get'], url_path='get_by_car')
    def get_by_car(self, request):
        """Retrieve service record(s) by car_id"""
        car_id = request.query_params.get('car_id')

        if not car_id:
            return Response({'error': 'car_id is required'}, status=400)

        records = CarServiceRecord.objects.filter(car_id=car_id).select_related('car').prefetch_related('service_entries__service')

        if not records.exists():
            return Response({'error': 'No service records found for the given car_id'}, status=404)

        serializer = self.get_serializer(records, many=True)
        return Response(serializer.data, status=200)
    

@extend_schema(tags=["Inventory Usage"])
class InventoryUsageViewSet(StandardizedModelViewSet):
    queryset = InventoryUsage.objects.all()
    serializer_class = InventoryUsageSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['service_record', 'product', 'used_at']
    ordering_fields = ['used_at', 'quantity_used']
    search_fields = ['product__name']

    
    def perform_create(self, serializer):
        usage = serializer.save(created_by=self.request.user)

        product = usage.product
        if product.quantity_in_stock < usage.quantity_used:
            raise serializers.ValidationError("Not enough stock!")

        product.quantity_in_stock -= usage.quantity_used
        product.save()
    
    def perform_update(self, serializer):
    # Get the existing record before updating
        instance = self.get_object()
        old_quantity_used = instance.quantity_used

        # Save the updated instance
        updated_instance = serializer.save()

        # Compute the difference
        new_quantity_used = updated_instance.quantity_used
        diff = old_quantity_used - new_quantity_used  # positive if we're reducing usage

        # Update the stock
        product = updated_instance.product
        new_stock = product.quantity_in_stock + diff

        if new_stock < 0:
            raise serializers.ValidationError("Stock cannot go below zero!")

        product.quantity_in_stock = new_stock
        product.save()
        
    @extend_schema(
    summary="Get inventory usage for a specific car",
    tags=["Inventory Usage"],
    parameters=[
        OpenApiParameter(
            name='car_id',
            type=int,
            location=OpenApiParameter.QUERY,
            required=True,
            description='ID of the car to filter inventory usage'
        ),
    ]
)
    @action(detail=False, methods=['get'], url_path='by-car')
    def usage_by_car(self, request):
        car_id = request.query_params.get('car_id')
        if not car_id:
            return Response({
                "status_code": 400,
                "message": "car_id query parameter is required"
            }, status=400)

        try:
            car_id = int(car_id)
        except ValueError:
            return Response({
                "status_code": 400,
                "message": "car_id must be an integer"
            }, status=400)

        # Filter usage records through related service_record -> car
        queryset = self.filter_queryset(
            self.get_queryset().filter(service_record__car_id=car_id)
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "status_code": 200,
            "message": f"Inventory usage for car ID {car_id}",
            "data": serializer.data
        })
    @extend_schema(
    summary="Get usage summary",
    tags=["Inventory Usage"],
    parameters=[
        OpenApiParameter(
            name='date_from',
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description='Start date for usage summary filter (YYYY-MM-DD)'
        ),
        OpenApiParameter(
            name='date_to',
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description='End date for usage summary filter (YYYY-MM-DD)'
        ),
    ]
)
    @action(detail=False, methods=['get'])
    def usage_summary(self, request):
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        queryset = self.filter_queryset(self.get_queryset())
        if date_from:
            queryset = queryset.filter(used_at__date__gte=parse_date(date_from))
        if date_to:
            queryset = queryset.filter(used_at__date__lte=parse_date(date_to))

        summary = queryset.values('product__name','product__quantity_in_stock').annotate(total_used=Sum('quantity_used')).order_by('-total_used')
        readable_summary = [
        {
            "Product Name": item["product__name"],
            "Remaining Stock": item["product__quantity_in_stock"],
            "Total Used till now": item["total_used"],
        }
        for item in summary
        ]
        return Response({
            "status_code": 200,
            "message": "Usage summary generated",
            "description": "Summary of inventory usage by product",
            "data": list(readable_summary)
        })
        
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
import qrcode
import io
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics import renderPDF
class GatePassPDFView(APIView):
    permission_classes = [IsAuthenticated]
    
    def create_header_section(self, job_entry, car):
        """Create modern header with company branding"""
        story = []
        
        # Company header (customize with your company details)
        header_style = ParagraphStyle(
            'CompanyHeader',
            fontSize=12,
            textColor=colors.HexColor("#4a5568"),
            alignment=TA_CENTER,
            spaceAfter=10
        )
        
        story.append(Paragraph("AUTOGARDEN PVT. LTD.", header_style))
        story.append(Paragraph("📍 Hakim Chowk, Chitwan, Nepal | ☎️ (+977) 9864280345", 
                              ParagraphStyle('CompanyInfo', fontSize=9, textColor=colors.HexColor("#718096"), alignment=TA_CENTER, spaceAfter=20)))
        
        # Modern title with accent
        title_style = ParagraphStyle(
            'ModernTitle',
            fontSize=28,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor("#1a202c"),
            alignment=TA_CENTER,
            spaceBefore=20,
            spaceAfter=10
        )
        
        story.append(Paragraph("VEHICLE GATE PASS", title_style))
        
        # # Subtitle with gate pass number
        # subtitle_style = ParagraphStyle(
        #     'SubtitleStyle',
        #     fontSize=10,
        #     textColor=colors.HexColor("#4299e1"),
        #     alignment=TA_CENTER,
        #     spaceAfter=30,
        #     fontName='Helvetica-Bold'
        # )
        
        # story.append(Paragraph(f"Pass No. GP-{job_entry.id:04d}", subtitle_style))
        
        return story

    def create_info_cards(self, job_entry, car):
        """Create modern card-style information layout"""
        story = []
        
        # Vehicle Details Card
        story.append(Paragraph("🚗 Vehicle Details", 
                              ParagraphStyle('CardTitle', fontSize=12, fontName='Helvetica-Bold', 
                                           textColor=colors.HexColor("#2d3748"), spaceAfter=10)))
        
        vehicle_info = [
            ["License Plate", car.plate_number, "Entry Date", job_entry.entry_date.strftime("%d %B %Y")],
            ["Make & Model", f"{car.brand} {car.model}", "Entry Time", job_entry.entry_date.strftime("%I:%M %p")],
            ["Color", car.color or "Not specified", "Service Type", car.get_service_type_display()],
            ["Year", str(car.year) if car.year else "N/A", "Odometer", f"{car.kms_reading} km" if car.kms_reading else "N/A"],
        ]

        vehicle_table = Table(vehicle_info, colWidths=[100, 120, 100, 120])
        vehicle_table.setStyle(TableStyle([
            # Modern card styling
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            
            # Label styling
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor("#4a5568")),
            ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor("#4a5568")),
            
            # Value styling
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor("#1a202c")),
            ('TEXTCOLOR', (3, 0), (3, -1), colors.HexColor("#1a202c")),
            
            # Layout
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            
            # Borders and colors
            ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor("#e2e8f0")),
            ('LINEBELOW', (0, 0), (-1, 0), 0, colors.white),
            ('LINEBETWEEN', (0, 1), (-1, -2), 0.5, colors.HexColor("#f1f5f9")),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.HexColor("#f8f9fa"), colors.white]),
        ]))

        story.append(vehicle_table)
        story.append(Spacer(1, 0.3 * inch))

        # Owner Details Card
        story.append(Paragraph("👤 Owner Information", 
                              ParagraphStyle('CardTitle', fontSize=12, fontName='Helvetica-Bold', 
                                           textColor=colors.HexColor("#2d3748"), spaceAfter=10)))

        owner_info = [
            ["Full Name", car.owner_name or "Not provided"],
            ["Phone Number", car.owner_contact or "Not provided"],
            ["Email Address", car.owner_email or "Not provided"],
        ]

        owner_table = Table(owner_info, colWidths=[120, 320])
        owner_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor("#4a5568")),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor("#1a202c")),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor("#e2e8f0")),
            ('LINEBETWEEN', (0, 0), (-1, -2), 0.5, colors.HexColor("#f1f5f9")),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.HexColor("#f8f9fa"), colors.white]),
        ]))

        story.append(owner_table)
        
        return story

    def get(self, request, jobentry_id):
        try:
            job_entry = JobEntry.objects.select_related("car").get(id=jobentry_id)
            car = job_entry.car
        except JobEntry.DoesNotExist:
            return HttpResponse("Job Entry not found", status=404)

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename=gate_pass_{job_entry.id}.pdf'

        doc = SimpleDocTemplate(
            response, 
            pagesize=A4,
            rightMargin=40,
            leftMargin=40,
            topMargin=50,
            bottomMargin=50
        )

        story = []
        
        # Add header section
        story.extend(self.create_header_section(job_entry, car))
        
        # Add information cards
        story.extend(self.create_info_cards(job_entry, car))

        # Notes section
        if job_entry.notes:
            story.append(Spacer(1, 0.3 * inch))
            story.append(Paragraph("📝 Special Instructions", 
                                  ParagraphStyle('NotesHeader', fontSize=12, fontName='Helvetica-Bold', 
                                               textColor=colors.HexColor("#2d3748"), spaceAfter=10)))
            
            notes_style = ParagraphStyle(
                'ModernNotes',
                fontSize=10,
                leftIndent=20,
                rightIndent=20,
                spaceBefore=5,
                spaceAfter=20,
                borderColor=colors.HexColor("#fbb6ce"),
                borderWidth=1,
                borderPadding=10,
                backColor=colors.HexColor("#fef5e7"),
                textColor=colors.HexColor("#744210")
            )
            story.append(Paragraph(job_entry.notes, notes_style))

        # Security and validity footer
        story.append(Spacer(1, 0.5 * inch))
        
        # Security notice
        security_style = ParagraphStyle(
            'SecurityStyle',
            fontSize=10,
            textColor=colors.HexColor("#1a202c"),
            alignment=TA_CENTER,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        )
        
        story.append(Paragraph("🔒 SECURITY VERIFIED DOCUMENT", security_style))
        
        # Footer information
        footer_info = f"""
        <para align="center" fontSize="8" textColor="#718096">
        This gate pass is electronically generated and valid for the specified vehicle only.<br/>
        Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')} | Document ID: GP-{job_entry.id:04d}<br/>
        For verification or inquiries, contact workshop administration.
        </para>
        """
        styles = getSampleStyleSheet()
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(footer_info, styles['Normal']))

        # Custom page styling function
        def modern_page_style(canvas, doc):
            """Add modern page styling"""
            canvas.saveState()
            
            # Subtle gradient effect (top border)
            canvas.setFillColor(colors.HexColor("#4299e1"))
            canvas.rect(0, A4[1]-20, A4[0], 20, fill=1, stroke=0)
            
            # Side accent
            canvas.setFillColor(colors.HexColor("#63b3ed"))
            canvas.rect(0, 0, 8, A4[1], fill=1, stroke=0)
            
            # Bottom border
            canvas.setStrokeColor(colors.HexColor("#e2e8f0"))
            canvas.setLineWidth(1)
            canvas.line(30, 40, A4[0]-30, 40)
            
            canvas.restoreState()

        # Build the PDF
        doc.build(story, onFirstPage=modern_page_style, onLaterPages=modern_page_style)

        return response