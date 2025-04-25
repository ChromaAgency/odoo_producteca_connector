from odoo import models, fields, api
from ..utils.products.products import Product
from ..utils.config.config import ConfigProducteca
from ..utils.search.search_sale_orders import SearchSalesOrder, SearchSalesOrderParams
from ..utils.sales_orders.sales_orders import SaleOrder
import logging
from datetime import datetime, timedelta
import urllib.parse
from odoo.tools.safe_eval import safe_eval
ACCEPTATION_CODES = [200, 201, 202, 205, 206, 207]
_logger = logging.getLogger(__name__)

class ProductecaQueue(models.Model):
    _name = "producteca.queue"
    _description = "Producteca Queue"

    active = fields.Boolean(string="Active", default=True)
    producteca_account_id = fields.Many2one(
        "producteca.account", string="Producteca Account"
    )
    producteca_body = fields.Text(string="Producteca Body")
    producteca_method = fields.Selection(
        [("create", "Create"),("update", "Update"), ("get", "Get"), ("post", "Post"), ("put", "Put"), ("delete", "Delete"), ("odoo_create", "Odoo Create")],
        string="Producteca Method",
    )
    model = fields.Char(string="Model")
    producteca_response = fields.Text(string="Producteca Response")
    odoo_item_id = fields.Integer(string="Odoo Item ID", readonly=True)
    response_status = fields.Char(string="Producteca Response Status")
    internal_process_error_msg = fields.Text(string="Internal Process Error Message")

    ##### Products #####

    #### Obtain Product Dict ####

    def _obtain_pricelist_for_product(self, product):
        pricelists = self.env['product.pricelist'].search([('company_id', '=', product.company_id.id), ('active', '=', True), ('currency_id', '=', product.currency_id.id)])
        product_in_pricelist = []
        if not pricelists:
            return []
        for item in pricelists.item_ids:
            if item.display_applied_on == '1_product' and product.product_tmpl_id.id == item.product_tmpl_id.id:
                product_in_pricelist.append(item)
            elif item.display_applied_on == '2_product_category' and product.categ_id.id == item.categ_id.id:
                product_in_pricelist.append(item)
            else:
                continue
        return product_in_pricelist

    def _obtain_stocks_for_product(self, product, account):
        stock_by_warehouse = self.env['stock.quant'].search([('product_id', '=', product.id), ('location_id.usage', '=', 'internal'), ('warehouse_id', 'in', account.warehouse_ids.ids)])
        return stock_by_warehouse

    def _prepare_producteca_product_dict(self, product, account):
        pricelists = self._obtain_pricelist_for_product(product)
        stock_by_warehouse = self._obtain_stocks_for_product(product, account)
        image_url = f"{self.env['ir.config_parameter'].sudo().get_param('web.base.url')}/producteca/image/{product.id}"
        deals = None #TODO
        product_data = {
            "sku": product.default_code or None,
            "code": str(product.id),
            "name": product.name,
            "barcode": product.barcode or None,
            "attributes": [{"key": variant.attribute_id.name, "value": variant.name} for variant in product.product_template_variant_value_ids] if product.product_template_variant_value_ids else None,
            "tags": [tag.name for tag in product.product_tag_ids] if product.product_tag_ids else None,
            "buyingPrice": product.list_price,
            "category": product.categ_id.complete_name,
            "brand": product.product_brand_id.name if product.product_brand_id else None,
            "notes": product.description if product.description else None,
            "pictures": [{"url": image_url}] if image_url else None
        }
        if product.weight:
            product_data.update({
                "dimensions": {
                "weight": product.weight if product.weight else 0,
                "width": 0,
                "height": 0,
                "length": 0, #TODO
                "pieces": 0,
            }})
        if stock_by_warehouse:
            product_data.update({
                "stocks": [{"quantity": stock.quantity,"availableQuantity": stock.available_quantity,"warehouse": stock.warehouse_id.producteca_warehouse_name if stock.warehouse_id else None} for stock in stock_by_warehouse]
            })
        if deals:
            product_data.update({
                "deals": deals
            })
        if pricelists:
            product_data.update({
                "prices": [{"amount": item.fixed_price, "currency": item.currency_id.name, "priceList": item.pricelist_id.name} for item in pricelists]
            })
        return {k: v for k, v in product_data.items() if v is not None}


    #### Create in Producteca ####

    def process_product_create_queue(self):
        queue_records = self.search([('producteca_method', '=', 'create'), ('active', '=', True), ('model', '=', 'product.product')])
        connection_array_dict = []
        for queue_record in queue_records:
            config = ConfigProducteca(
                token=queue_record.producteca_account_id.bearer_token,
                api_key=queue_record.producteca_account_id.api_key
            )
            body_dict = safe_eval(queue_record.producteca_body)
            product = Product(
                config=config,
                create_if_it_doesnt_exist=queue_record.producteca_account_id.create_if_dosnt_exist,
                **body_dict
            )
            product_response, response_status = product.create()
            queue_record.producteca_response = product_response
            queue_record.response_status = response_status
            if response_status in ACCEPTATION_CODES:
                queue_record.active = False
                connection_array_dict.append({
                    "producteca_account_id": queue_record.producteca_account_id.id,
                    "product_id": queue_record.odoo_item_id,
                    "producteca_id": product_response.get('id'),
                    "producteca_variation_id": product_response.get('variations')[0].get('id')
                })
        self.env['producteca.connections'].create(connection_array_dict)


    def create_product_in_producteca_queue(self):
        producteca_account_ids = self.env['producteca.account'].sudo().search([('active', '=', True),('company_id', '=', self.env.company.id)])
        if not producteca_account_ids:
            return False
        products = self.env['product.product'].sudo().search([('is_producteca_product', '=', True), ('is_already_sync', '=', False)])
        if not products:
            return False
        queue_records = []
        for product in products:
            for account in producteca_account_ids:
                if not account.create_if_dosnt_exist:
                    continue
                product_dict = self._prepare_producteca_product_dict(product, account)
                queue_records.append({
                    "producteca_account_id": account.id,
                    "producteca_body": product_dict,
                    "producteca_method": "create",
                    "model": "product.product",
                    "odoo_item_id": product.id
            })
        self.create(queue_records)
        products.write({'is_already_sync': True})
        return True

    #### Update producteca product ####

    def process_product_update_queue(self):
        queue_records = self.search([('producteca_method', '=', 'update'), ('active', '=', True), ('model', '=', 'product.product')])
        if not queue_records:
            return False
        product_ids_in_queue = [record.odoo_item_id for record in queue_records]
        producteca_connections = self.env['producteca.connections'].sudo().search([('product_id', 'in', product_ids_in_queue)])
        queue_info = {record.odoo_item_id: record for record in queue_records}
        if not producteca_connections:
            return False
        for connection in producteca_connections:
            queue_record = queue_info.get(connection.product_id.id)
            if not queue_record:
                continue
            config = ConfigProducteca(
                token=connection.producteca_account_id.bearer_token,
                api_key=connection.producteca_account_id.api_key
            )
            body_dict = {
                "code":str(connection.product_id.id),
                "prices": [{"amount": queue_record.producteca_body, "currency": connection.product_id.currency_id.name, "priceList": "Product Default"}]
            }
            product = Product(
                config=config,
                create_if_it_doesnt_exist=connection.producteca_account_id.create_if_dosnt_exist,
                **body_dict
            )
            product_response, response_status = product.update()
            queue_record.producteca_response = product_response
            queue_record.response_status = response_status
            if response_status in ACCEPTATION_CODES:
                queue_record.active = False

    #### Update product stock ####

    def process_product_stock_queue(self):
        queue_records = self.search([('producteca_method', '=', 'update'), ('active', '=', True), ('model', '=', 'stock.quant')])
        if not queue_records:
            return False
        product_ids_in_queue = [record.odoo_item_id for record in queue_records]
        producteca_connections = self.env['producteca.connections'].sudo().search([('product_id', 'in', product_ids_in_queue)])
        queue_info = {record.odoo_item_id: record for record in queue_records}
        if not producteca_connections:
            return False
        for connection in producteca_connections:
            queue_record = queue_info.get(connection.product_id.id)
            if not queue_record:
                continue
            config = ConfigProducteca(
                token=connection.producteca_account_id.bearer_token,
                api_key=connection.producteca_account_id.api_key
            )
            body_dict = safe_eval(queue_record.producteca_body)
            body_dict.update({
                "variation_id": int(connection.producteca_variation_id)
            })
            product = Product(
                config=config,
                create_if_it_doesnt_exist=connection.producteca_account_id.create_if_dosnt_exist,
                **body_dict
            )
            product_response, response_status = product.update()
            queue_record.producteca_response = product_response
            queue_record.response_status = response_status
            if response_status in ACCEPTATION_CODES:
                queue_record.active = False

    ### Obtain products from producteca ###

    def create_obtain_from_producteca_queue(self, products_to_create, producteca_account_id):
        queue_to_create = []
        for product in products_to_create:
            queue_to_create.append({
                "producteca_account_id": producteca_account_id.id,
                "producteca_method": "get",
                "model": "product.product",
                "producteca_body": product
            })
        return self.create(queue_to_create)

    def filter_empty_values(self, d):
        return {k: v for k, v in d.items() if v is not None and v != ''}

    def _handle_producteca_attribute_dict(self, producteca_response, odoo_product):
        existing_lines = odoo_product.attribute_line_ids if odoo_product else []
        
        existing_lines_dict = {line.attribute_id.name: line for line in existing_lines}
        
        attribute_line_ops = []
        
        for attr in producteca_response['attributes']:
            attribute_id = self.env['product.attribute'].sudo().search([('name', '=', attr['key'])], limit=1)
            
            if attribute_id:
                if attribute_id.name in existing_lines_dict:
                    existing_line = existing_lines_dict[attribute_id.name]
                    
                    existing_value = existing_line.value_ids.filtered(lambda v: v.name == attr['value'])
                    
                    if not existing_value:
                        attribute_line_ops.append((1, existing_line.id, {
                            'value_ids': [(0, 0, {'name': attr['value']})]
                        }))
                    else:
                        continue
                else:
                    attribute_line_ops.append((0, 0, {
                        'attribute_id': attribute_id.id,
                        'value_ids': [(0, 0, {'name': attr['value']})]
                    }))
        
        if attribute_line_ops:
            return [(5, 0, 0)] + attribute_line_ops
        return []

    def _handle_producteca_tags_dict(self, producteca_response):
        tag_model = self.env['product.tag']
        tag_names = producteca_response['tags']
        existing_tags = tag_model.search([('name', 'in', tag_names)])
        new_tags = tag_model.create([
                {'name': name}
                for name in tag_names
                if name not in existing_tags.mapped('name')
            ])
        all_tags = existing_tags + new_tags
        return [(6, 0, all_tags.ids)] 

    def _prepare_odoo_product_dict(self, producteca_response, odoo_product):
        producteca_response = self.filter_empty_values(producteca_response)
        vals = {
            'name': producteca_response.get('name'),
            'default_code': producteca_response.get('sku'),
            'barcode': producteca_response.get('barcode'),
            'list_price': producteca_response.get('buyingPrice'),
            'product_brand_id': producteca_response.get('brand'),
            'description': producteca_response.get('notes'),
            'is_producteca_product': True,
        }
        
        if producteca_response.get('tags'):
            vals['product_tag_ids'] = self._handle_producteca_tags_dict(producteca_response)
        if producteca_response.get('attributes') and not odoo_product:
            vals['attribute_line_ids'] = self._handle_producteca_attribute_dict(producteca_response, False)

        if producteca_response.get('attributes') and odoo_product:
            vals['attribute_line_ids'] = self._handle_producteca_attribute_dict(producteca_response, odoo_product)
        
        dimensions = producteca_response.get('dimensions', {})
        if dimensions:
            vals.update({
                'weight': dimensions.get('weight'),
                # 'width': dimensions.get('width'), #TODO with packages
                # 'height': dimensions.get('height'),
                # 'depth': dimensions.get('length')
            })
        
        return vals

    def obtain_producteca_products_process_queue(self):
        queue_records = self.search([('producteca_method', '=', 'get'), ('active', '=', True), ('model', '=', 'product.product')])
        if not queue_records:
            return False
        producteca_ids = [int(record.producteca_body) for record in queue_records]
        connections = self.env['producteca.connections'].sudo().search([('producteca_id', 'in', producteca_ids)])
        products_to_create = []
        for queue_record in queue_records:
            config = ConfigProducteca(
                token=queue_record.producteca_account_id.bearer_token,
                api_key=queue_record.producteca_account_id.api_key
            )
            product = Product(  
                config=config,
                create_if_it_doesnt_exist=queue_record.producteca_account_id.create_if_dosnt_exist
            )
            product_response, response_status = product.get(config=config, product_id = queue_record.producteca_body)
            queue_record.producteca_response = product_response
            queue_record.response_status = response_status
            if response_status in ACCEPTATION_CODES:
                queue_record.active = False
                product_connection = connections.filtered(lambda x: x.producteca_id == queue_record.producteca_body) if connections else False
                if product_connection:
                    odoo_product = product_connection.product_id
                    product_dict = self._prepare_odoo_product_dict(product_response, odoo_product)
                    odoo_product.sudo().write(product_dict)
                else:
                    products_to_create.append(self._prepare_odoo_product_dict(product_response, False))
        if products_to_create:
            self.env['product.product'].sudo().create(products_to_create)


    ##### Sale orders #####

    ### Create Sale orders Queue ###

    def enqueue_last_7_days_orders_from_producteca(self):
        producteca_accounts = self.env['producteca.account'].sudo().search([('active', '=', True)])
        queue_records_create = []
        
        for account in producteca_accounts:
            config = ConfigProducteca(
                token=account.bearer_token,
                api_key=account.api_key
            )
            today = datetime.now()
            seven_days_ago = today - timedelta(days=7)
            
            filter_str = (
                f"paymentStatus eq 'Approved' and "
                f"date gt {seven_days_ago.isoformat()}"
            )
            
            params = SearchSalesOrderParams(
                top=100,
                skip=0,
                filter=filter_str
            )
            
            saleorder_response, response_status = SearchSalesOrder.search_saleorder(config=config, params=params)
            _logger.info(saleorder_response)
            _logger.info(response_status)
            if response_status in ACCEPTATION_CODES:
                for saleorder in saleorder_response.get('results', []):
                    queue_records_create.append({
                        'producteca_method': 'get',
                        'producteca_body': saleorder,
                        'producteca_account_id': account.id,
                        'model': 'sale.order'
                })
        _logger.info(queue_records_create)
        if queue_records_create:
            return self.create(queue_records_create)
        return False

    ### Process Sale orders Queue ###

    def process_producteca_order_queue(self):
        queue_records = self.search([
            ('producteca_method', '=', 'get'),
            ('active', '=', True),
            ('model', '=', 'sale.order'),
        ])
        _logger.info(queue_records)
        if not queue_records:
            return False

        seven_days_ago = (datetime.now() - timedelta(days=7)).date()
        sale_orders = self.env['sale.order'].sudo().search([('create_date', '>=', seven_days_ago)])
        existing_sale_orders = [sale_order.producteca_id for sale_order in sale_orders]
        connections = self.env['producteca.connections'].sudo().search([])
        quotation_status_sale_orders = []
        draft_invoice_status_sale_orders = []
        confirm_status_sale_orders = []
        carts = self.env['sale.order.cart'].sudo().search([])

        for queue_record in queue_records:
            body = safe_eval(queue_record.producteca_body)
            _logger.info('body %s', body)
            order_id = body.get('id')
            _logger.info('order_id %s', order_id)
            if not order_id or (order_id in existing_sale_orders):
                continue
            account = queue_record.producteca_account_id
            lines = body.get('lines', [])
            _logger.info('lines %s', lines)

            sale_order_lines = []
            missing_products = {}

            for line in lines:
                product_id = line.get('product', {}).get('id')
                _logger.info('product_id %s', product_id)                
                variation_id = line.get('variation', {}).get('id')
                _logger.info('variation_id %s', variation_id)
                connection = connections.filtered(lambda x: (x.producteca_id == str(product_id) or x.producteca_variation_id == str(variation_id)) and x.producteca_account_id == account)
                _logger.info('connection %s', connection)

                if not connection:
                    _logger.info('connection not found')
                    missing_products.update({product_id: line})
                    continue

                product = connection.product_id
                _logger.info('product %s', product)
                sale_order_lines.append((0, 0, {
                    'product_id': product.id,
                    'product_uom_qty': line.get('quantity', 0),
                    'price_unit': line.get('price', 0),
                    'name': product.display_name,
                }))
            _logger.info('missing_product_ids %s', missing_products)
            _logger.info('sale_order_lines %s', sale_order_lines)

            if missing_products:
                self._create_producteca_queue_for_missing_products(queue_record, account, missing_products)
                continue

            sale_order_dict = {
                'partner_id': account.company_id.partner_id.id,  # Placeholder
                'order_line': sale_order_lines,
                'producteca_id': order_id,
                'company_id': account.company_id.id,
                'cart_id': carts.filtered(lambda x: x.producteca_id == body.get('cartId')).id,
                'warehouse_id': account.warehouse_ids.filtered(lambda x: x.name == body.get('warehouseId')).id
            }
            _logger.info(sale_order_dict)
            if account.imported_sale_action == 'quotation' and sale_order_dict:
                quotation_status_sale_orders.append(sale_order_dict)
            elif account.imported_sale_action == 'draft_invoice' and sale_order_dict:
                draft_invoice_status_sale_orders.append(sale_order_dict)
            elif account.imported_sale_action == 'confirm' and sale_order_dict:
                confirm_status_sale_orders.append(sale_order_dict)
            queue_record.active = False

        if quotation_status_sale_orders:
            _logger.info(quotation_status_sale_orders)
            created_sale_orders = self.env['sale.order'].sudo().create(quotation_status_sale_orders)
            created_sale_orders.action_confirm()
        if draft_invoice_status_sale_orders:
            _logger.info(draft_invoice_status_sale_orders)
            created_sale_orders = self.env['sale.order'].sudo().create(draft_invoice_status_sale_orders)
            created_sale_orders.action_confirm()
            created_sale_orders._create_invoices()
        if confirm_status_sale_orders:
            _logger.info(confirm_status_sale_orders)
            created_sale_orders = self.env['sale.order'].sudo().create(confirm_status_sale_orders)
            created_sale_orders.action_confirm()
            moves = created_sale_orders._create_invoices()
            for move in moves:
                move.action_post()

    ### Create Queue products in odoo ###

    def _create_producteca_queue_for_missing_products(self, queue_record, account, missing_products):
        if account.is_producteca_able_to_create_products:
            for line in missing_products.values():
                producteca_body_queue = line.get('variation') | line.get('product')
                producteca_body_queue.update({
                    "variation_id": int(line.get('variation', {}).get('id'))
                })
                self.create({
                    'producteca_account_id': account.id,                    
                    'producteca_body': producteca_body_queue,
                    'model': 'product.product',
                    'producteca_method': 'odoo_create'
                })
            queue_record.internal_process_error_msg = (
                f"No se completo la orden porque los productos {', '.join(map(str, missing_products.keys()))} no existen en Odoo. Pero se han puesto en cola para ser creados y se reprocesará"
            )
        else:
            queue_record.internal_process_error_msg = (
                "No se pudo crear la orden porque la cuenta no permite creación de productos y el/los producto(s) "
                f"{', '.join(map(str, missing_products.keys()))} no existen en Odoo."
            )

    def process_queue_product_create_in_odoo(self):
        queue_records = self.search([
            ('producteca_method', '=', 'odoo_create'),
            ('active', '=', True),
            ('model', '=', 'product.product')
        ])
        if not queue_records:
            return False
        products_to_create = []
        connection_dict_of_dicts = {} ##TODO Tengo un problema aca, deberia crear la conexion pero no tengo el product_id a menos que haga el create de 1 por 1 pero despues de crearlo no tengo el producteca id
        connection_array_dict = []
        for queue_record in queue_records:
            producteca_body = safe_eval(queue_record.producteca_body)
            products_to_create.append(self._prepare_odoo_product_dict(producteca_body, False))
            connection_dict_of_dicts[producteca_body.get('id')] = {
                "producteca_account_id": queue_record.producteca_account_id.id,
                "producteca_id": producteca_body.get('id'),
                "producteca_variation_id": producteca_body.get('variation_id')
            }
            queue_record.active = False
        if products_to_create:
            self.env['product.product'].sudo().create(products_to_create)
            self.env['producteca.connections'].sudo().create(connection_array_dict)
        return True
        