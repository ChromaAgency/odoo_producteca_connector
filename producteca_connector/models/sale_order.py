from odoo import models, fields, api
from producteca.sales_orders.sales_orders import SaleOrder as ProductecaApiSaleOrder
from producteca.config.config import ConfigProducteca
from odoo.exceptions import UserError
from ..models.producteca_queue import ACCEPTATION_CODES
import logging
from odoo.addons.base.models.res_users import Command
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    producteca_id = fields.Char(string="Producteca ID")
    cart_id = fields.Many2one("sale.order.cart", string="Cart")
    origin_platform = fields.Char(string="Origin Platform")
    invoice_integration_producteca_id = fields.Char(string="Invoice Integration Producteca ID")
    producteca_app_id = fields.Integer(string="Producteca App ID")
    producteca_shipment_data = fields.Text(string="Información del envío")
    producteca_payments_data = fields.Text(string="Información de los pagos")
    producteca_account_id = fields.Many2one('producteca.account', string='Producteca Account')
    has_existing_producteca_invoice = fields.Boolean(string="Invoice already exists")

    def _obtain_carrier_id(self, carrier_name):
        carrier = self.env['delivery.carrier'].search([('name', '=', carrier_name)]).id
        if not carrier:
            delivery_product = self.env['product.product'].create({
                'name': f'Servicio de Entrega: {carrier_name}',
                'type': 'service',
                'invoice_policy': 'order',
            })
            
            carrier = self.env['delivery.carrier'].create({
                'name': carrier_name,
                'product_id': delivery_product.id,
            }).id
        return carrier
    
    def _process_picking_with_shipment(self, picking, picking_data):
        products = {product_line.get('product'): product_line.get('quantity') for product_line in picking_data.get('products')}
        status = picking_data.get('method').get('status')
        raw_date = picking_data.get('date')
        if raw_date:
            cleaned_date = raw_date.split('.')[0].replace('T', ' ')
            parsed_date = fields.Datetime.to_datetime(cleaned_date)
        else:
            parsed_date = fields.Datetime.now()
        if status == 'Done':
            for line in picking.move_line_ids:
                line.qty_done = products.get(line.product_id.producteca_connection_ids.filtered(lambda x: x.producteca_account_id == self.producteca_account_id).producteca_id)
            picking.date_done = parsed_date
            picking.scheduled_date = parsed_date
            picking.action_confirm()
        else:
            for line in picking.move_line_ids:
                line.quantity = products.get(line.product_id.producteca_connection_ids.filtered(lambda x: x.producteca_account_id == self.producteca_account_id).producteca_id)
            picking.scheduled_date = parsed_date
            picking.carrier_tracking_ref = picking_data.get('method').get('trackingNumber')
        if picking_data.get('integration'):
            picking.producteca_shipment_id = picking_data.get('integration').get('integrationId')
        if picking_data.get('method'):
            picking.carrier_id = self._obtain_carrier_id(picking_data.get('method').get('courier'))
    
    def _create_producteca_dict_for_picking(self, picking):
        date_value = picking.date_done if picking.state == 'done' else picking.scheduled_date
        content_dict = {
            "date": date_value.isoformat() if date_value else None,
            "method": {
                "trackingNumber": picking.carrier_tracking_ref if picking.carrier_tracking_ref else '',
                "trackingUrl": '',
                "courier": picking.carrier_id.name if picking.carrier_id else 'Unknown',
                "status": "Done" if picking.state == 'done' else "PickingPending",
            }
        }
        product_dict = [
            {
                "product": line.product_id.producteca_connection_ids.filtered(lambda x: x.producteca_account_id == self.producteca_account_id).producteca_id,
                "variation": line.product_id.producteca_connection_ids.filtered(lambda x: x.producteca_account_id == self.producteca_account_id).producteca_variation_id,
                "quantity": line.qty_done if picking.state == 'done' else line.quantity,
            }
            for line in picking.move_line_ids
        ] 
        if product_dict:
            content_dict.update({"products": product_dict})
        return content_dict

    def action_confirm(self):
        _ = super().action_confirm()
        for rec in self:
            if rec.producteca_id and rec.picking_ids and rec.producteca_shipment_data:
                shipment_data = safe_eval(rec.producteca_shipment_data)
                shipment_per_picking = {shipment.get('id'): shipment for shipment in shipment_data}
                vals_to_send_to_producteca = []
                
                for picking in rec.picking_ids:
                    if picking.producteca_shipment_id:
                        picking_data = shipment_per_picking.get(picking.producteca_shipment_id)
                        if picking_data:
                            rec._process_picking_with_shipment(picking, picking_data)
                            if picking.producteca_shipment_id in shipment_per_picking:
                                del shipment_per_picking[picking.producteca_shipment_id]
                
                for picking in rec.picking_ids:
                    if not picking.producteca_shipment_id:
                        if shipment_per_picking:
                            shipment_id, picking_data = next(iter(shipment_per_picking.items()))
                            picking.producteca_shipment_id = shipment_id
                            rec._process_picking_with_shipment(picking, picking_data)
                            del shipment_per_picking[shipment_id]
                        else:
                            producteca_dict = rec._create_producteca_dict_for_picking(picking)
                            vals_to_send_to_producteca.append({
                                "producteca_method": "create",
                                "producteca_body": producteca_dict,
                                "model": "stock.picking",
                                "odoo_item_id": rec.producteca_id,
                                "producteca_account_id": rec.producteca_account_id.id,
                            })
                
                if vals_to_send_to_producteca:
                    self.env['producteca.queue'].sudo().create(vals_to_send_to_producteca)
            if rec.producteca_id and not rec.producteca_shipment_data:
                rec.action_close_order()
        return _
  
    def action_close_order(self):
        config = ConfigProducteca(
            token=self.producteca_account_id.bearer_token,
            api_key=self.producteca_account_id.api_key
        )
        response_status, _ = ProductecaApiSaleOrder.close(config, int(self.producteca_id))
        if response_status not in ACCEPTATION_CODES:
            raise UserError("No se pudo cerrar la orden en Producteca")

    def action_cancel(self):
        if self.producteca_id and not self.env.context.get('cancel_order_in_producteca', False):
            return {
            'name': 'Confirm Cancel Order',
            'type': 'ir.actions.act_window',
            'res_model': 'confirm.cancel.sale.order',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id
            }
        }
        else:
            return super().action_cancel()

    def _create_invoices(self, grouped=False, final=False, date=None):
        moves = super()._create_invoices(grouped=grouped, final=final, date=date)
        invoices_to_queue = []
        for order in self:
            if order.producteca_id:
                for invoice in order.invoice_ids:
                    invoice.producteca_order_id = order.producteca_id
                    invoice.producteca_account_id = order.producteca_account_id
                    invoice.producteca_invoice_already_exists = order.has_existing_producteca_invoice
                    
                    if not invoice.access_token:
                        invoice._portal_ensure_token()
                    
                    invoice_dict = {
                        "odoo_item_id":order.id,
                        "model": "account.move",
                        "producteca_account_id": invoice.producteca_account_id.id,
                        "producteca_method": "update" if invoice.producteca_invoice_already_exists else "create",
                        "producteca_body":{
                            "id": int(order.producteca_id),
                            "invoiceIntegration": {
                                "documentUrl": f"{self.env['ir.config_parameter'].sudo().get_param('web.base.url')}/facturas/{invoice.id}/{invoice.access_token}/factura_producteca.pdf",
                                "integrationId": str(invoice.name) if invoice.name else str(invoice.id),
                                "app": 249,
                            }
                        }
                    }
                    if order.producteca_payments_data:
                        invoice.producteca_payment_data = order.producteca_payments_data
                        order.producteca_payments_data = False
                    invoices_to_queue.append(invoice_dict)
        if invoices_to_queue:
            self.env['producteca.queue'].sudo().create(invoices_to_queue)
        return moves
    
    def write(self, vals):
        _ = super().write(vals)
        for rec in self:
            if rec.producteca_id and ('note' in vals or 'tag_ids' in vals) and not self.env.context.get('creation_from_queue', False):
                config = ConfigProducteca(
                    token=rec.producteca_account_id.producteca_account_id.bearer_token,
                    api_key=rec.producteca_account_id.producteca_account_id.api_key
                )
                update_dict = {
                    "id": int(rec.producteca_id),
                    "note": rec.note if 'note' in vals else None,
                    "tags": [tag.name for tag in rec.tag_ids] if 'tag_ids' in vals else None
                }
                sale_order = ProductecaApiSaleOrder(config=config, **update_dict)
                response_status, _ = sale_order.synchronize(config, sale_order)
                if response_status not in ACCEPTATION_CODES:
                    raise UserError("No se pudo actualizar la orden en Producteca")
        return _
        
    def _compute_delivery_price(self, body):
        has_delivery = body.get('hasAnyShipments', False)
        if has_delivery:
            delivery_price = body.get('totalShippingCost', 0)
            carrier_product_name = f"Servicio de Entrega: {body.get('shipments')[0].get('method').get('courier')}"
            delivery_product = self.env['product.product'].sudo().search([('name', '=', carrier_product_name)], limit=1)
            if delivery_product:
                product_tax = delivery_product.taxes_id
                if product_tax:
                    tax_id = product_tax[0]
                    delivery_price = delivery_price / (1 + (tax_id.amount/100))
                return Command.create({
                    'product_id': delivery_product.id,
                    'product_uom_qty': 1,
                    'price_unit': delivery_price,
                    'name': delivery_product.display_name,
                })
            else:
                delivery_product = self.env['product.product'].create({
                'name': carrier_product_name,
                'type': 'service',
                'invoice_policy': 'order',
            })
            return Command.create({
                'product_id': delivery_product.id,
                'product_uom_qty': 1,
                'price_unit': delivery_price,
                'name': delivery_product.display_name,
            })
        return

    def _mapped_origin_application(self, sale_channel_id):
        app_mapping = {
            'Agrupate': [401],
            'Amazon': [90],
            'AMEX / Foodies Store': [338],
            'Banco Ciudad': [294],
            'Banco Galicia': [276],
            'Banco Macro': [490],
            'Banco Patagonia': [341],
            'Banco Provincia': [382],
            'Bancolombia': [329],
            'Bancor': [396],
            'BBVA': [140],
            'BNA': [259, 268, 291, 298],
            'Buybuy': [400],
            'Carrefour': [381],
            'Cetrogar': [332],
            'Claroshop': [208],
            'Coppel': [246],
            'Cornershop': [261],
            'Cyberpuerta': [325],
            'Dafiti Chile': [502],  
            'Dafiti Colombia': [286],
            'Diners': [344],
            'Directv': [395],
            'Doto': [392],
            'Elektra': [103],
            'Falabella': [330],
            'Falabella Colombia': [383],
            'Falabella Peru': [351],
            'Fenicio': [347],
            'Fravega': [220],
            'Garbarino': [405],
            'Global Reward Solutions': [411],
            'ICBC': [59],
            'Jumbo Colombia': [447],
            'Juntoz': [394],
            'Kodear': [504],
            'La Marina': [402],
            'Linio Colombia': [279],
            'Linio México': [77],
            'Linio Perú': [284],
            'Liverpool': [262],
            'Magento': [51],
            'Me Gusta': [288],
            'Megatone': [269],
            'Mercado Libre': [2, 272],
            'Necxus': [335],
            'Paris': [250],
            'Paseo Libertad': [293],
            'Prestashop': [391],
            'Quickfit': [375],
            'Rappi': [389],
            'Ripley Chile': [237],
            'Ripley Perú': [297],
            'Sam\'s-DSV': [273],
            'Sears': [314],
            'Shein': [314],  # ¡CONFLICTO! Mismo ID que Sears
            'Shopify': [60, 253, 263, 299],
            'Supervielle': [141],
            'Surtidora Departamental': [452],
            'Tata': [274],
            'Tecnofan': [364],
            'Tienda Clic': [69],
            'Tienda Columbia': [296],
            'Tienda Indigo': [789],
            'Tienda Itaú': [275],
            'Tienda Nube': [345],
            'Uber': [397],
            'Vtex': [33, 398],
            'Walmart': [209, 320, 321],
            'Walmart-DSV': [233],
            'Woocommerce': [393, 439, 442, 4457],
        }
        reverse_mapping = {}
        for app_name, app_ids in app_mapping.items():
            for app_id in app_ids:
                reverse_mapping[app_id] = app_name
        return reverse_mapping.get(sale_channel_id, 'Unknown')

    def _prepare_sale_order_dict(self, body, account, connections, carts, queue_record, process_type, order_lines=False):
        lines = body.get('lines', [])
        sale_order_lines = []
        missing_products = {}
        warehouse_name = body.get('warehouse')
        if warehouse_name == 'Default':
            warehouse = account.default_warehouse_id.id
        else:
            warehouse = account.warehouse_ids.filtered(lambda x: x.name == warehouse_name).id

        for line in lines:
            product_id = line.get('product', {}).get('id')
            variation_id = line.get('variation', {}).get('id')
            connection = connections.filtered(lambda x: (x.producteca_id == str(product_id) or x.producteca_variation_id == str(variation_id)) and x.producteca_account_id == account)
            if not connection:
                missing_products.update({product_id: line})
                continue

            product = connection.product_id
            product_tax = product.taxes_id
            unit_price = line.get('price', 0)
            tax_id = None
            if product_tax:
                tax_id = product_tax[0]
                unit_price = line.get('price', 0) / (1 + (tax_id.amount/100))
            if process_type == 'update' and product.id in order_lines:
                sale_order_lines.append(Command.update(order_lines[product.id], {
                    'product_uom_qty': line.get('quantity', 0),
                    'price_unit': unit_price,
                }))
            else:
                sale_order_lines.append(Command.create({
                    'product_id': product.id,
                    'product_uom_qty': line.get('quantity', 0),
                    'price_unit': unit_price,
                    'name': product.display_name,
                    'warehouse_id': warehouse,
                }))
        if body.get('hasAnyShipments', False) == True:
            sale_order_lines.append(self._compute_delivery_price(body))
        origin_platform = self._mapped_origin_application(body.get('salesChannel'))
        if missing_products:
            self._create_producteca_queue_for_missing_products(queue_record, account, missing_products)
            return False
        partner_id = None
        if not body.get('contactId'):
            partner_id = self.env.ref('producteca_connector.producteca_contact')
        if not partner_id:
            partner_id = self.env['res.partner'].sudo().search([('producteca_id', '=', body.get('contactId')), ('parent_id', '!=', False)], limit=1)
        if not partner_id:
            partner_id = self.env['res.partner']._create_producteca_partner(body.get('orderId'), queue_record.producteca_account_id)
        sale_order_dict = {
            'partner_id': partner_id.id,
            'order_line': sale_order_lines,
            'origin_platform': origin_platform if origin_platform else '',
            'producteca_id': body.get('id'),
            'company_id': account.company_id.id,
            'warehouse_id': warehouse if warehouse else account.default_warehouse_id.id,
            'producteca_shipment_data': body.get('shipments'),
            'producteca_account_id': account.id,
        }
        if body.get('invoiceIntegration', False):
            sale_order_dict.update({
                'has_existing_producteca_invoice': True,
                'invoice_integration_producteca_id': body.get('invoiceIntegration', {}).get('integrationId'),
                'producteca_app_id': body.get('invoiceIntegration', {}).get('app'),                
            })
        if body.get('cartId') != None:
            cart_id = carts.filtered(lambda x: x.producteca_id == body.get('cartId'))
            if not cart_id:
                cart_id = self.env['sale.order.cart'].sudo().create({
                    'producteca_id': body.get('cartId'),
                })
            if cart_id:
                sale_order_dict['cart_id'] = cart_id[:1].id
        if body.get('payments'):
            sale_order_dict['producteca_payments_data'] = body.get('payments'),
        return sale_order_dict
        
    def process_producteca_order_queue(self):
        queue_records = self.search([
            ('producteca_method', '=', 'get'),
            ('active', '=', True),
            ('model', '=', 'sale.order'),
        ])
        if not queue_records:
            return False

        seven_days_ago = (datetime.now() - timedelta(days=7)).date()
        sale_orders = self.env['sale.order'].sudo().search([('create_date', '>=', seven_days_ago)])
        existing_sale_orders = [sale_order.producteca_id for sale_order in sale_orders]
        connections = self.env['producteca.connections'].sudo().search([('product_id', '!=', False)])
        quotation_status_sale_orders = []
        draft_invoice_status_sale_orders = []
        confirm_status_sale_orders = []
        carts = self.env['sale.order.cart'].sudo().search([])

        for queue_record in queue_records:
            body = safe_eval(queue_record.producteca_body)
            order_id = body.get('id')
            if not order_id:
                queue_record.internal_process_error_msg = "No se encontro el id de la orden"
                queue_record.active = False
                continue
            if order_id in existing_sale_orders:
                queue_record.internal_process_error_msg = "La orden ya existe"
                queue_record.active = False
                continue
            account = queue_record.producteca_account_id
            sale_order_dict = self._prepare_sale_order_dict(body, account, connections, carts, queue_record, 'create')
            if not sale_order_dict:
                continue
            if account.imported_sale_action == 'quotation' and sale_order_dict:
                quotation_status_sale_orders.append(sale_order_dict)
            elif account.imported_sale_action == 'draft_invoice' and sale_order_dict:
                draft_invoice_status_sale_orders.append(sale_order_dict)
            elif account.imported_sale_action == 'confirm' and sale_order_dict:
                confirm_status_sale_orders.append(sale_order_dict)
            queue_record.active = False

        if quotation_status_sale_orders:
            created_sale_orders = self.env['sale.order'].sudo().create(quotation_status_sale_orders)
            created_sale_orders.order_line._compute_tax_id()
            created_sale_orders.with_context(update_from_confirm=True).action_confirm()
        if draft_invoice_status_sale_orders:
            created_sale_orders = self.env['sale.order'].sudo().create(draft_invoice_status_sale_orders)
            created_sale_orders.with_context(update_from_confirm=True).action_confirm()
            for order in created_sale_orders:
                order._create_invoices()
        if confirm_status_sale_orders:
            created_sale_orders = self.env['sale.order'].sudo().create(confirm_status_sale_orders)
            created_sale_orders.with_context(update_from_confirm=True).action_confirm()
            for order in created_sale_orders:
                moves = order._create_invoices()
                for move in moves:
                    move.action_post()

    def process_update_producteca_saleorder(self):
        queue_records = self.search([
            ('producteca_method', '=', 'update'),
            ('active', '=', True),
            ('model', '=', 'sale.order')
        ])
        if not queue_records:
            return False
        connections = self.env['producteca.connections'].sudo().search([('product_id', '!=', False)])
        carts = self.env['sale.order.cart'].sudo().search([])
        for queue_record in queue_records:
            producteca_body = safe_eval(queue_record.producteca_body)
            sale_order = self.env['sale.order'].sudo().browse(queue_record.odoo_item_id)
            order_lines = {line.product_id.id: line.id for line in sale_order.order_line}
            update_dict = self._prepare_sale_order_dict(producteca_body, queue_record.producteca_account_id, connections, carts, queue_record, 'update', order_lines)
            sale_order.sudo().write(update_dict)
            queue_record.active = False

    def enqueue_last_x_days_orders_from_producteca(self):
        producteca_accounts = self.env['producteca.account'].sudo().search([('active', '=', True)])
        queue_records_create = []
        
        for account in producteca_accounts:
            config = ConfigProducteca(
                token=account.bearer_token,
                api_key=account.api_key
            )
            today = datetime.now()
            x_days_ago = (today - timedelta(days=account.get_orders_from_last_days)).strftime('%Y-%m-%d')
            filter_str = (
                f"paymentStatus eq 'Approved' and "
                f"date gt {x_days_ago}"
            )
            
            encoded_filter = quote(filter_str)
            
            params = SearchSalesOrderParams(
                top=100,
                skip=0,
                **{"$filter": encoded_filter}
            )            
            saleorder_response, response_status = SearchSalesOrder.search_saleorder(config=config, params=params)
            if response_status in ACCEPTATION_CODES:
                for result in saleorder_response.get('results', []):
                    sale_order_id = result.get('orderId', False)
                    _logger.info(sale_order_id)
                    if not sale_order_id:
                        continue
                    config = ConfigProducteca(
                    token=account.bearer_token,
                    api_key=account.api_key
                    )
                    sale_order_obj = SaleOrder.get(config, sale_order_id)
                    sale_order_dict = sale_order_obj.model_dump()
                    queue_records_create.append({
                        'producteca_method': 'get',
                        'producteca_body': sale_order_dict,
                        'producteca_account_id': account.id,
                        'model': 'sale.order'
                })
        if queue_records_create:
            return self.create(queue_records_create)
        return False


class SaleOrderCart(models.Model):
    _name = "sale.order.cart"
    _description = "Sale Order Cart"
    _rec_name = "producteca_id"

    producteca_id = fields.Char(string="Producteca ID")
    order_ids = fields.One2many("sale.order", "cart_id", string="Orders")


