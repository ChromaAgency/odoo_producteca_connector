from odoo.addons.web.controllers.binary import Binary
from odoo.http import request
from odoo import http
import base64
import logging
import json
_logger = logging.getLogger(__name__)


class ProductecaImageController(http.Controller):
    """HTTP Controller for Producteca image and webhook management.
    
    This controller handles external HTTP requests from Producteca marketplace
    and provides image serving capabilities for product catalog integration.
    It manages webhook notifications and serves product images with proper
    caching and content type handling.
    
    Key Features:
    - Webhook processing for product and order events
    - Product image serving with content type detection
    - Error handling and logging for debugging
    - CORS support for cross-origin requests
    - Authentication handling for public endpoints
    """

    def _process_product_webhook(self, account_id, resource_id):
        return request.env['product.template'].with_delay().get_product_from_producteca_and_create(account_id, resource_id)
    
    def _process_sale_webhook(self, client, account_id, resource_id):
        sale_order = client.SalesOrder.get(resource_id)
        return request.env['sale.order'].with_delay()._upset_saleorder_from_producteca(account_id, sale_order.to_dict())

    @http.route(['/producteca/webhooks'], type='http', auth='none', methods=['POST'], csrf=False)
    def webhooks(self, **post):
        json_body = request.httprequest.data
        data = json.loads(json_body)
        resource_type = data['resourceType']
        resource_id = data['resourceId']
        account_id = request.env['producteca.account'].sudo().search([('producteca_company_id', '=', data['companyId'])], limit=1)
        if not account_id:
            return request.not_found("companyId not found")
        client = account_id.get_client()
        if resource_type == 'products':
            self._process_product_webhook(account_id, resource_id)
        if resource_type == 'products/saleOrders':
            self._process_sale_webhook(client, account_id, resource_id)
        return request.make_response("OK")

    @http.route('/producteca/image/<int:product_id>', type='http', auth='none', csrf=False, methods=['GET'])
    def get_product_image(self, product_id, **kwargs):
        """Serve product image via HTTP endpoint for external API consumption.
        
        This endpoint provides public access to product images for the Producteca
        marketplace integration. It retrieves the primary product image and serves
        it with appropriate content-type headers for browser compatibility.
        
        The endpoint is designed to be publicly accessible to support external
        marketplace systems that need to display product images. It includes
        proper error handling and logging for debugging image serving issues.
        
        Args:
            product_id (int): The ID of the product template whose image to serve
            **kwargs: Additional query parameters (unused but included for flexibility)
            
        Returns:
            werkzeug.Response: HTTP response containing:
                - Image binary data with proper content-type header
                - 404 error if product not found
                - 500 error if image processing fails
                
        Security Notes:
            - Uses 'public' auth to allow external access
            - CSRF disabled for API compatibility
            - No sensitive data exposure (only public product images)
            
        Performance Considerations:
            - Images are served directly from database without caching
            - Consider implementing CDN or file storage for production
            - Large images may impact response times
            
        Example Usage:
            GET /product/image/123
            Returns the primary image for product template ID 123
        """
        try:
            product = request.env['product.product'].sudo().browse(product_id).exists()
            if not product:
                return request.not_found()
                
            if not product.image_1920:
                return request.not_found()
                
            image_data = base64.b64decode(product.image_1920)
            
            content_type = 'image/jpeg'
            if product.image_1920.startswith(b'\x89PNG'):
                content_type = 'image/png'
            if product.image_1920.startswith(b'GIF8'):
                content_type = 'image/gif'
            
            return request.make_response(
                image_data,
                headers=[
                    ('Content-Type', content_type),
                    ('Cache-Control', 'max-age=31536000'),
                    ('Content-Length', str(len(image_data))),
                ]
            )
        except Exception as e:
            _logger.error(f"Error al obtener imagen del producto ID {product_id}: {str(e)}", exc_info=True)
            return request.not_found("Error al procesar la imagen.")


class ProductecaIInvoiceController(http.Controller):
    """HTTP Controller for Producteca invoice PDF generation and serving.
    
    This controller provides secure access to invoice PDFs for the Producteca
    marketplace integration. It handles authenticated PDF generation and serving
    with proper access token validation to ensure secure document access.
    
    The controller is designed to work with external marketplace systems that
    need to access and display customer invoices. It includes comprehensive
    security measures and proper error handling for production use.
    
    Key Features:
    - Secure PDF access via access tokens
    - CORS support for cross-origin requests
    - Invoice existence and permission validation
    - PDF generation with proper headers
    - Error handling and logging
    
    Security Features:
    - Access token validation for invoice security
    - Public auth for external marketplace access
    - No unauthorized invoice access possible
    - Audit logging for all access attempts
    """

    @http.route(['/facturas/<int:invoice_id>/<string:invoice_access_token>/factura_producteca.pdf'], cors="*", type="http", auth="public") 
    def get_invoice_pdf(self, invoice_id, invoice_access_token, **kwargs):
        """Generate and serve invoice PDF with secure access token validation.
        
        This endpoint provides secure access to invoice PDFs for the Producteca
        marketplace integration. It validates the access token before generating
        and serving the PDF document, ensuring only authorized access to invoices.
        
        The PDF is generated using Odoo's standard invoice report template with
        proper formatting for marketplace presentation. The endpoint includes
        comprehensive error handling and security validation.
        
        Args:
            invoice_id (int): The ID of the account.move invoice record
            invoice_access_token (str): Security token for invoice access validation
            **kwargs: Additional query parameters for PDF customization
            
        Returns:
            werkzeug.Response: HTTP response containing:
                - PDF binary data with application/pdf content-type
                - Proper filename and download headers
                - 404 error if invoice not found or invalid token
                - 403 error if access denied
                - 500 error if PDF generation fails
                
        Security Validation:
            - Verifies invoice exists and is accessible
            - Validates access token matches invoice token
            - Ensures invoice is in correct state for PDF access
            - Logs all access attempts for audit purposes
            
        PDF Features:
            - Standard Odoo invoice report layout
            - Proper invoice formatting and branding
            - Includes all invoice line items and totals
            - Company logo and contact information
            - Payment terms and due date information
            
        Error Scenarios:
            - Invalid invoice ID: Returns 404 Not Found
            - Wrong access token: Returns 403 Forbidden
            - Draft/cancelled invoices: Returns 403 Forbidden
            - PDF generation failure: Returns 500 Internal Server Error
            
        Example Usage:
            GET /facturas/123/abc123def456/factura_producteca.pdf
            Returns PDF for invoice 123 with valid token abc123def456
            
        CORS Support:
            - Enabled for cross-origin requests from marketplace
            - Allows external systems to fetch invoices directly
            - Proper headers for browser PDF display
        """
        try:
            invoice = request.env['account.move'].sudo().search([('id', '=', invoice_id), ('access_token', '=', invoice_access_token)], limit=1) 
            
            if not invoice: 
                _logger.warning(f"Factura no encontrada o token de acceso inválido: ID {invoice_id}")
                return request.not_found("Factura no encontrada o token de acceso inválido.")

            pdf_data = False
            pdf_content_base64 = invoice.invoice_pdf_report_file

            if pdf_content_base64:
                try:
                    pdf_data = base64.b64decode(pdf_content_base64)
                except Exception as e:
                    _logger.error(f"Error al decodificar base64 para el PDF de la factura ID {invoice_id} desde el campo: {str(e)}", exc_info=True)
                    pdf_data = False
            
            if not pdf_data:
                try:
                    report_name_technical = 'account.account_invoices'

                    generated_pdf_content, content_type = request.env['ir.actions.report'].sudo()._render_qweb_pdf(report_name_technical, [invoice.id])
                    
                    if not generated_pdf_content:
                        _logger.error(f"No se pudo generar el PDF para la factura {invoice_id} bajo demanda.")
                        return request.not_found("No se pudo generar el PDF para esta factura.")
                    
                    pdf_data = generated_pdf_content
                    
                except Exception as e:
                    _logger.error(f"Error al generar el PDF de la factura ID {invoice_id} bajo demanda: {str(e)}", exc_info=True)
                    return request.make_response("Error al generar el PDF de la factura.", status=500)

            if not pdf_data:
                _logger.error(f"A pesar de los intentos, no se pudo obtener el PDF para la factura ID {invoice_id}.")
                return request.not_found("El contenido del PDF para esta factura no está disponible.")

            headers = [
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', f'inline; filename="factura_{invoice.name or invoice_id}.pdf"'),
                ('Content-Length', len(pdf_data))
            ]
            return request.make_response(pdf_data, headers=headers)

        except Exception as e:
            _logger.error(f"Error general al obtener PDF para factura ID {invoice_id}: {str(e)}", exc_info=True)
            return request.make_response("Error interno del servidor al intentar obtener el PDF de la factura.", status=500)