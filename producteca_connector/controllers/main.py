from odoo.addons.web.controllers.binary import Binary
from odoo.http import request
from odoo import http
import base64
import logging
import json
_logger = logging.getLogger(__name__)

class ProductecaImageController(http.Controller):

    def _process_product_webhook(self, account_id, resource_id):
        return request.env['product.product'].with_delay().get_product_from_producteca_and_create(account_id, resource_id)
    
    def _process_sale_webhook(self, client, account_id, resource_id):
        sale_order = client.SalesOrder.get(resource_id)
        return request.env['sale.order'].with_delay()._upset_saleorder_from_producteca(account_id, sale_order.to_dict())

    @http.route(['/producteca/webhooks'], type='http', auth='none', methods=['POST'], csrf=False)
    def webhooks(self, **post):
        json_body = request.httprequest.data
        _logger.info(f"Webhook recibido: {post}, {json_body}")
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

    @http.route(['/producteca/image/<int:product_id>'], type='http', auth="public", csrf=False, cors="*")
    def get_product_image(self, product_id, **kw):
        try:
            product = request.env['product.product'].sudo().browse(product_id).exists()
            if not product:
                _logger.info(f"Producto no encontrado para la imagen: ID {product_id}")
                return request.not_found()
                
            if not product.image_1920:
                _logger.info(f"Imagen no disponible para el producto: ID {product_id}")
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

    @http.route(['/facturas/<int:invoice_id>/<string:invoice_access_token>/factura_producteca.pdf'], cors="*", type="http", auth="public") 
    def get_invoice_pdf(self, invoice_id, invoice_access_token, **kwargs):
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
                _logger.info(f"El contenido del PDF (invoice_pdf_report_file) para la factura ID {invoice_id} está vacío o no se pudo decodificar. Intentando generar el informe.")
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