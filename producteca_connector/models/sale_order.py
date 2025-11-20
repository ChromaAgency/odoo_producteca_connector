from odoo import models, fields, api, Command
from odoo.exceptions import UserError
import logging
from producteca.sales_orders.search_sale_orders import SearchSalesOrderParams
from odoo.tools.safe_eval import safe_eval
from datetime import datetime, timedelta
from urllib.parse import quote

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    """Extended Sale Order for Producteca marketplace integration.
    
    This model extends the standard Odoo sale order to support comprehensive
    integration with Producteca marketplace. It handles order import, export,
    synchronization, and lifecycle management between Odoo and Producteca.
    
    Business Logic:
    - Imports orders from Producteca marketplace with complete data mapping
    - Manages order synchronization and status updates
    - Handles product mapping and creation during order import
    - Processes shipments and delivery information
    - Manages payment data and invoice integration
    - Supports multi-platform order origin tracking
    - Handles order cancellation and closure workflows
    
    Key Features:
    - Bidirectional order synchronization
    - Automatic product creation and mapping
    - Shipment management integration
    - Payment and invoice processing
    - Multi-warehouse support
    - Platform-specific order handling
    - Queued background processing
    - Error handling and validation
    
    Integration Points:
    - Producteca API for order operations
    - Stock management for shipments
    - Accounting for invoices and payments
    - Product management for catalog sync
    - Partner management for customer data
    """
    _inherit = "sale.order"

    producteca_id = fields.Char(
        string="Producteca ID",
        help="Unique identifier of this order in Producteca marketplace."
    )
    cart_id = fields.Many2one(
        "sale.order.cart", 
        string="Cart",
        help="Shopping cart associated with this order in Producteca."
    )
    origin_platform = fields.Char(
        string="Origin Platform",
        help="Original platform/channel where this order was placed (e.g., MercadoLibre, Amazon, etc.)."
    )
    producteca_shipment_data = fields.Text(
        string="Información del envío",
        help="JSON data containing shipment information from Producteca marketplace."
    )
    producteca_payments_data = fields.Text(
        string="Información de los pagos",
        help="JSON data containing payment information from Producteca marketplace."
    )
    producteca_account_id = fields.Many2one(
        'producteca.account', 
        string='Producteca Account',
        help="Producteca account configuration used for this order's integration."
    )
    has_existing_producteca_invoice = fields.Boolean(
        string="Invoice already exists",
        help="Indicates if an invoice already exists for this order in Producteca marketplace."
    )

    def action_confirm(self):
        _ = super().action_confirm()
        for rec in self:
            if rec.producteca_id and rec.picking_ids:
                rec._process_producteca_shipments()
        return _
    
    def _should_skip_shipment_update(self, shipment_data):
        if not shipment_data:
            return False
        last_shipment = shipment_data[-1] if shipment_data else None
        if last_shipment and last_shipment.get('method', {}).get('status') == 'Done':
            _logger.info(f"Skipping shipment update - last shipment is Done for order {self.name}")
            return True
        return False
    
    def _process_producteca_shipments(self):
        self.picking_ids.producteca_account_id = self.producteca_account_id
        
        if self.producteca_shipment_data:
            shipment_data = safe_eval(self.producteca_shipment_data)
            
            if self._should_skip_shipment_update(shipment_data):
                return
                
            self._sync_existing_shipments(shipment_data)
        else:
            self._create_new_shipments()
    
    def _sync_existing_shipments(self, shipment_data):
        shipment_per_picking = {shipment.get('id'): shipment for shipment in shipment_data}
        synced_shipment_ids = set()
        already_synced_pickings = self.picking_ids.filtered(lambda p: p.producteca_shipment_id in shipment_per_picking.keys())
        for synced_picking in already_synced_pickings:
            picking_data = shipment_per_picking.get(synced_picking.producteca_shipment_id)
            synced_picking._process_picking_with_shipment(picking_data)
            synced_shipment_ids.add(synced_picking.producteca_shipment_id)
        
        unsynced_pickings = self.picking_ids - already_synced_pickings
        unsynced_shipments = list(filter(lambda s: s[0] not in synced_shipment_ids, shipment_per_picking.items()))
        for picking in unsynced_pickings:
            if unsynced_shipments:
                shipment_id, picking_data = unsynced_shipments.pop(0)
                picking.producteca_shipment_id = shipment_id
                picking._process_picking_with_shipment(picking_data)
    
    def _create_new_shipments(self):
        for picking in self.picking_ids:
            picking.with_delay()._create_producteca_shipment()
    
    # TODO: Can shippings be multiple? For example an orden comes from producteca with 3 shippings.abs
    # We should support this.
    # TODO: ! I think we do not want this, close order is only for a very specific case
    # if rec.producteca_id and not rec.producteca_shipment_data:
    #     rec.action_close_order()

    def action_close_order(self):
        client = self.producteca_account_id.get_client()
        try:
            client.SalesOrder(id=self.producteca_id).close()
        except Exception:
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
        for order in self:
            if order.producteca_id:
                for invoice in order.invoice_ids:
                    invoice.producteca_order_id = order.producteca_id
                    invoice.producteca_account_id = order.producteca_account_id
                    invoice.producteca_invoice_already_exists = order.has_existing_producteca_invoice
                    if order.producteca_payments_data:
                        invoice.producteca_payment_data = order.producteca_payments_data
                        order.producteca_payments_data = False
        return moves

    def write(self, vals):
        _ = super().write(vals)
        for rec in self:
            if rec.producteca_id and ('note' in vals or 'tag_ids' in vals):
                client = rec.producteca_account_id.get_client()
                update_dict = {
                    "id": int(rec.producteca_id),
                    "note": rec.note if 'note' in vals else None,
                    "tags": [tag.name for tag in rec.tag_ids] if 'tag_ids' in vals else None
                }
                sale_order = client.SalesOrder(**update_dict)
                try:
                    sale_order.synchronize()
                except Exception:
                    raise UserError("No se pudo actualizar la orden en Producteca")
        return _



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

    def _get_warehouse(self, warehouse_name, account):
        if warehouse_name == 'Default':
            warehouse = account.default_warehouse_id.id
        else:
            warehouse = account.warehouse_ids.filtered(lambda x: x.producteca_warehouse_name == warehouse_name).id
        return warehouse

    def _handle_missing_product(self, line, account):
        """Handle missing product in sale order import.
        
        Attempts to find or create product from sale order line data.
        Line structure from Producteca API:
        {
            "product": {"id": 123, "name": "...", "code": "...", "brand": "..."},
            "variation": {"id": 456, "sku": "ABC", "barcode": "...", "stocks": [...]},
            "price": 100.0,
            "quantity": 2
        }
        
        Args:
            line (dict): Sale order line data from Producteca
            account (producteca.account): Producteca account
            
        Returns:
            product.product: Found or created product variant
        """
        product_data = line.get('product', {})
        variation_data = line.get('variation', {})
        
        producteca_id = product_data.get('id')
        variation_id = variation_data.get('id')
        sku = line.get('sku') or variation_data.get('sku')
        
        producteca_body_queue = {
            'id': producteca_id,
            'name': product_data.get('name'),
            'code': product_data.get('code'),
            'brand': product_data.get('brand'),
        }
        
        if variation_id and sku:
            producteca_body_queue['variations'] = [{
                'id': variation_id,
                'sku': sku,
                'barcode': variation_data.get('barcode'),
            }]
        
        if account.is_product_price_modified_by_producteca:
            unit_price = line.get('price', 0) / line.get('quantity', 1)            
            temp_product = self.env['product.product'].search([('default_code', '=', sku)], limit=1)
            if temp_product and temp_product.taxes_id:
                tax_id = temp_product.taxes_id[0]
                unit_price = unit_price / (1 + (tax_id.amount/100))
            
            producteca_body_queue.update({
                "product_price": float(unit_price)
            })
            _logger.info("producteca product price to sync (after tax calculation): " + str(unit_price))
        
        product = None
        odoo_variant = self.env['product.product'].search([('default_code', '=', sku)], limit=1)
        if odoo_variant:
            template = odoo_variant.product_tmpl_id
            
            if account.is_producteca_able_to_modified_products:
                template._update_product_from_producteca(account, producteca_body_queue, template)
            else:
                template._update_connection_variants(template, account, producteca_id, producteca_body_queue)
                _logger.info(f"Product {template.name} found but not modified (account doesn't allow modifications). Connection updated.")
            
            product = odoo_variant
        
        if not product:
            if not account.is_producteca_able_to_create_products:
                raise Exception(
                    f"No se pudo procesar la orden porque el producto con SKU '{sku}' no existe en Odoo "
                    f"y la cuenta de Producteca no permite la creación de productos. "
                    f"Por favor, cree el producto manualmente o habilite la opción 'Producteca puede crear productos'."
                )
            
            template = self.env['product.template']._create_product_from_producteca(account, producteca_body_queue)
            product = template.product_variant_ids.filtered(lambda v: v.default_code == producteca_body_queue.get('sku'))[:1]
            if not product and template.product_variant_ids:
                product = template.product_variant_ids[0]
        
        return product

    def _process_sale_order_lines(self, lines, warehouse, order_lines, account):
        sale_order_lines = []
        for line in lines:
            _logger.info(line)
            product_id = line.get('product', {}).get('id')
            variation_id = line.get('variation', {}).get('id')
            sku = line.get('sku') or (line.get('variation', {}).get('sku') if line.get('variation') else None)
            
            # Find variant connection by producteca_variation_id
            connection = self.env['producteca.product.connections'].search([
                ('producteca_variation_id', '=', str(variation_id)),
                ('producteca_account_id', '=', account.id)
            ], limit=1)
            
            product = connection.product_id if connection else None
            
            if not product and sku:
                product = self.env['product.product'].search([('default_code', '=', sku)], limit=1)
            
            if not product:
                product = self._handle_missing_product(line, account)

            product_tax = product.taxes_id
            unit_price = line.get('price', 0)
            tax_id = None
            if product_tax:
                tax_id = product_tax[0]
                # TODO: If it is percentage, possibly better to use a compute and calculate this different
                unit_price = line.get('price', 0) / (1 + (tax_id.amount/100))
            if account.is_product_price_modified_by_producteca:
                product.lst_price = unit_price / float(line.get('quantity', 1))
            if product.id in order_lines:
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
        return sale_order_lines

    def _handle_delivery_line(self, body, order_lines):
        carrier_product_name = f"Servicio de Entrega: {body.get('shipments')[0].get('method').get('courier')}"
        delivery_product = self.env['product.product'].sudo().search([('name', '=', carrier_product_name)], limit=1)
        
        if not delivery_product:
            delivery_product = self.env['product.product'].create({
                'name': carrier_product_name,
                'type': 'service',
                'invoice_policy': 'order',
            })
        
        delivery_price = body.get('totalShippingCost', 0)
        product_tax = delivery_product.taxes_id
        if product_tax:
            tax_id = product_tax[0]
            delivery_price = delivery_price / (1 + (tax_id.amount/100))
        
        if delivery_product.id in order_lines:
            return Command.update(order_lines[delivery_product.id], {
                'product_uom_qty': 1,
                'price_unit': delivery_price,
            })
        else:
            return Command.create({
                'product_id': delivery_product.id,
                'product_uom_qty': 1,
                'price_unit': delivery_price,
                'name': delivery_product.display_name,
            })

    def _get_partner_id(self, body, account):
        partner_id = None
        if not body.get('contact'):
            partner_id = self.env.ref('producteca_connector.producteca_contact')
        if not partner_id:
            partner_id = self.env['res.partner'].sudo().search([('producteca_id', '=', body.get('contact')), ('parent_id', '!=', False)], limit=1)
        if not partner_id:
            partner_id = self.env['res.partner']._create_producteca_partner(body.get('id'), account)
        return partner_id
        
    def _get_cart_id(self, body):
        if body.get('cartId') is not None:
            cart = self.env['sale.order.cart'].search([('producteca_id', '=', body.get('cartId'))], limit=1)
            if not cart:
                cart = self.env['sale.order.cart'].sudo().create({
                    'producteca_id': body.get('cartId'),
                })
            return cart.id

    def _prepare_sale_order_dict(self, body, account, order_lines=None):
        if not order_lines: 
            order_lines = []
        lines = body.get('lines', [])
        warehouse = self._get_warehouse(body.get('warehouse'), account)
        sale_order_lines = self._process_sale_order_lines(lines, warehouse, order_lines, account)
        if body.get('hasAnyShipments', False):
            delivery_line = self._handle_delivery_line(body, order_lines)
            if delivery_line:
                sale_order_lines.append(delivery_line)
        origin_platform = self._mapped_origin_application(int(body.get('channel', 0)))
        partner_id = self._get_partner_id(body, account)
        sale_order_dict = {
            'partner_id': partner_id.id,
            'order_line': sale_order_lines,
            'origin_platform': origin_platform if origin_platform else '',
            'producteca_id': body.get('id'),
            'company_id': account.company_id.id,
            # 'warehouse_id': warehouse if warehouse else account.default_warehouse_id.id,
            'producteca_shipment_data': body.get('shipments'),
            'producteca_account_id': account.id,
            'cart_id': self._get_cart_id(body),
            'producteca_payments_data': body.get('payments') if body.get('payments') else False,
            'has_existing_producteca_invoice': True if body.get('invoiceIntegration') else False
        }
        return sale_order_dict

    def _run_quotation_process(self):
        if self.state in ['sale', 'done']:
            return self
        self.order_line._compute_tax_id()
        self.with_context(update_from_confirm=True).action_confirm()
        return self

    def _run_draft_invoice_process(self):
        if self.state not in ['sale', 'done']:
            self.with_context(update_from_confirm=True).action_confirm()
        for order in self:
            order._create_invoices()
        return self

    def _run_confirm_process(self):
        if self.state not in ['sale', 'done']:
            self.with_context(update_from_confirm=True).action_confirm()
        for order in self:
            moves = order._create_invoices()
            for move in moves.filtered(lambda r: r.state != 'post'):
                move.action_post()
        return self

    def _run_import_sale_action(self, account):
        if account.imported_sale_action == 'quotation':
            return self._run_quotation_process()
        elif account.imported_sale_action == 'draft_invoice':
            return self._run_draft_invoice_process()
        elif account.imported_sale_action == 'confirm':
            return self._run_confirm_process()
        raise Exception("unsupported action")

    def _upset_saleorder_from_producteca(self, account, body):
        order_id = body.get('id')
        order = self.env['sale.order'].search([('producteca_id', '=', order_id)])
        if not order_id:
            raise Exception("No se encontro el id de la orden")
        if order:
            order_lines = {line.product_id.id: line.id for line in order.order_line}
            sale_order_dict = self._prepare_sale_order_dict(body, account, order_lines)
            order.sudo().write(sale_order_dict)
        else:
            sale_order_dict = self._prepare_sale_order_dict(body, account)
            order = self.env['sale.order'].sudo().create(sale_order_dict)
        return order._run_import_sale_action(account)

    def enqueue_last_x_days_orders_from_producteca(self):
        producteca_accounts = self.env['producteca.account'].sudo().search([('active', '=', True)])
        for account in producteca_accounts:
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
            client = account.get_client()
            saleorder_response = client.SalesOrder.search(params=params)
            for result in saleorder_response.results:
                sale_order_id = result.order_id
                _logger.info(sale_order_id)
                if not sale_order_id:
                    continue
                sale_order_obj = client.SalesOrder.get(sale_order_id)
                sale_order_dict = sale_order_obj.to_dict()
                self.with_delay()._upset_saleorder_from_producteca(account, sale_order_dict)
        return True
