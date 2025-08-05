from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def generate_invoice_pdf(data):
    """
    Generate a PDF invoice from bill data.
    
    Args:
        data (dict): Bill calculation data
        
    Returns:
        BytesIO: PDF buffer
    """
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )
        
        styles = getSampleStyleSheet()
        elements = []

        # Header
        elements.append(Paragraph("CAR SERVICE INVOICE", styles['Title']))
        elements.append(Spacer(1, 12))

        # Invoice details
        car_info = data.get('car', {})
        elements.append(Paragraph(f"<b>Car ID:</b> {data['car_id']}", styles['Normal']))
        if car_info.get('plate_number'):
            elements.append(Paragraph(f"<b>Plate Number:</b> {car_info['plate_number']}", styles['Normal']))
        elements.append(Paragraph(f"<b>Invoice Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        elements.append(Spacer(1, 20))

        # Services section
        if data.get('service_lines'):
            elements.append(Paragraph("SERVICES PROVIDED", styles['Heading2']))
            service_data = [['Service Name', 'Rate', 'Date Performed', 'Remarks']]
            
            for service in data['service_lines']:
                service_data.append([
                    service['name'],
                    f"${service['rate']}",
                    service['performed_at'],
                    service['remarks'][:50] + '...' if len(service['remarks']) > 50 else service['remarks']
                ])
            
            service_table = Table(service_data, colWidths=[2.5*inch, 1*inch, 1.2*inch, 2*inch])
            service_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ALIGN', (1, 1), (1, -1), 'RIGHT'),  # Align rates to right
            ]))
            elements.append(service_table)
            elements.append(Spacer(1, 20))

        # Products section
        if data.get('product_lines'):
            elements.append(Paragraph("PRODUCTS USED", styles['Heading2']))
            product_data = [['Product Name', 'Rate', 'Quantity', 'Total', 'Date Used']]
            
            for product in data['product_lines']:
                product_data.append([
                    product['name'],
                    f"${product['rate']}",
                    product['quantity'],
                    f"${product['total']}",
                    product['used_at']
                ])
            
            product_table = Table(product_data, colWidths=[2.2*inch, 1*inch, 0.8*inch, 1*inch, 1.5*inch])
            product_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ALIGN', (1, 1), (1, -1), 'RIGHT'),  # Align rates to right
                ('ALIGN', (3, 1), (3, -1), 'RIGHT'),  # Align totals to right
            ]))
            elements.append(product_table)
            elements.append(Spacer(1, 20))

        # Summary section
        elements.append(Paragraph("BILL SUMMARY", styles['Heading2']))
        summary_data = [
            ['Total Service Cost:', f"${data['total_service_cost']}"],
            ['Total Inventory Cost:', f"${data['total_inventory_cost']}"],
            ['Subtotal:', f"${data['total_amount']}"],
            ['Discount:', f"${data['discount']}"],
            ['Amount Paid:', f"${data['amount_paid']}"],
            ['Amount Remaining:', f"${data['amount_remaining']}"]
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),  # Highlight final amount
        ]))
        elements.append(summary_table)

        # Footer
        elements.append(Spacer(1, 30))
        elements.append(Paragraph("Thank you for your business!", styles['Normal']))

        doc.build(elements)
        buffer.seek(0)
        return buffer

    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        raise e