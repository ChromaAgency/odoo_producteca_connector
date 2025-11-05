from odoo import models, fields, api, Command
from producteca.products.search_products import SearchProductParams
import logging

_logger = logging.getLogger(__name__)


def filter_empty_values(d):
    return {k: v for k, v in d.items() if v is not None and v != ''}


class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_producteca_product = fields.Boolean(string="Is Producteca Product")
    is_already_sync = fields.Boolean(string="Is Already Sync", readonly=True, copy=False)
    producteca_connection_ids = fields.One2many('producteca.product.connections', 'product_id', string="Producteca Connection")

    # TODO: Change this for produceteca_response
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
                            'value_ids': [(0, 0, {'name': attr['value'], 'attribute_id': attribute_id.id})]
                        }))
                    else:
                        continue
                else:
                    attribute_line_ops.append((0, 0, {
                        'attribute_id': attribute_id.id,
                        'value_ids': [(0, 0, {'name': attr['value'], 'attribute_id': attribute_id.id})]
                    }))
        
        if attribute_line_ops:
            return [(5, 0, 0)] + attribute_line_ops
        return []

    # TODO: Change this for produceteca_response
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

    # TODO: Change this for produceteca_response
    def _handle_producteca_connection_ids(self, producteca_response, odoo_product, account):
        if not account and not producteca_response.get('account_id'):
            return []

        producteca_account = account.id if account else producteca_response.get('account_id')
        existing_connection = self.env['producteca.product.connections'].sudo().search([
            ('producteca_account_id', '=', producteca_account),
            ('producteca_id', '=', str(producteca_response.get('id'))),
            ('producteca_variation_id', '=', str(producteca_response.get('variation_id'))),
            ('product_id', '=', odoo_product.id if odoo_product else False)
        ], limit=1)
        
        if existing_connection:
            return []
            
        if odoo_product and odoo_product.producteca_connection_ids:
            connection_exists = False
            for connection in odoo_product.producteca_connection_ids:
                if (connection.producteca_account_id.id == producteca_account and
                    connection.producteca_id == str(producteca_response.get('id')) and
                    connection.producteca_variation_id == str(producteca_response.get('variation_id'))):
                    connection_exists = True
                    break
            
            if not connection_exists:
                return [Command.link(0)] + [Command.create({
                    "producteca_account_id":producteca_account,
                    "producteca_id": producteca_response.get('id'),
                    "producteca_variation_id": producteca_response.get('variation_id')
                })]
            return []
        else:
            return [Command.create({
                "producteca_account_id":producteca_account,
                "producteca_id": producteca_response.get('id'),
                "producteca_variation_id": producteca_response.get('variation_id')
            })]

    # TODO: Change this for produceteca_response
    def _prepare_producteca_to_odoo_product_dict(self, producteca_response, odoo_product, account):
        producteca_response = filter_empty_values(producteca_response)
        _logger.info(producteca_response)
        vals = {
            'is_producteca_product': True,
        }
        connection_ids = self._handle_producteca_connection_ids(producteca_response, odoo_product, account)
        if connection_ids:
            vals['producteca_connection_ids'] = connection_ids
        if not account.is_producteca_able_to_modified_products:
            return vals
        if account.is_producteca_able_to_modified_products or not odoo_product:
            vals = {
                'description': producteca_response.get('notes'),
                'is_producteca_product': True,
                'is_already_sync': True,
            }
            if not odoo_product:
                vals['default_code'] = producteca_response['sku']
                name = producteca_response.get('name', False)
                if not name:
                    name = 'Unnamed Producteca Product with ID ' + str(producteca_response.get('id'))
                vals['name'] = name
                vals['is_storable'] = True
            if producteca_response.get('product_price', False):            
                vals['list_price'] = float(producteca_response.get('product_price'))
            if producteca_response.get('brand'):
                brand = self.env['product.brand'].sudo().search([('name', '=', producteca_response.get('brand'))], limit=1)
                if brand:
                    vals['product_brand_id'] = brand.id
                else:
                    vals['product_brand_id'] = self.env['product.brand'].sudo().create({'name': producteca_response.get('brand')}).id
            
            if producteca_response.get('tags'):
                vals['product_tag_ids'] = self._handle_producteca_tags_dict(producteca_response)
            if producteca_response.get('attributes'):
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

    def _create_product_from_producteca(self, account, producteca_body):
        if not account.is_producteca_able_to_create_products:
            raise Exception(
                "No se pudo crear la orden porque la cuenta no permite creación de productos y el/los producto(s) Creelos manualmente, relacionelos y luego reencole el proceso"
                f"{', '.join(map(str, producteca_body.keys()))} no existen en Odoo."
            )
        producteca_body.update({
            "account_id": account.id
        })
        products_to_create = self._prepare_producteca_to_odoo_product_dict(producteca_body, False, account)
        try:
            _logger.info(products_to_create)
            products = self.env['product.product'].sudo().create(products_to_create)
        except:
            products_to_create.pop('barcode', None)
            products = self.env['product.product'].sudo().create(products_to_create)
        return products

    def _update_product_from_producteca(self, account, producteca_body, odoo_product):
        product_dict = self._prepare_producteca_to_odoo_product_dict(producteca_body, odoo_product, account)
        try:
            product_write = odoo_product.sudo().write(product_dict)
        except:
            product_dict.pop('barcode', None)
            product_write = odoo_product.sudo().write(product_dict)
        return product_write

    def get_product_from_producteca_and_create(self, account, producteca_id):
        #TODO Refactor this
        client = account.get_client()
        product_service = client.Product
        product_service.create_if_it_doesnt_exist = account.create_if_dosnt_exist
        product = product_service.get(producteca_id)
        for variation in product.variations:
            variation_dict = self._prepare_dict_from_product_endpoint(variation, product.to_dict())
            connection = self.env['producteca.product.connections'].sudo().search([('producteca_id', '=', product.id), ('producteca_variation_id', '=', variation.get('id'))], limit=1)
            if connection:
                self._update_product_from_producteca(account, variation_dict, connection.product_id)
            else:
                if variation.get('sku', False):
                    odoo_product = self.env['product.product'].sudo().search([('default_code', '=', variation.get('sku'))], limit=1)
                    if odoo_product:
                        self._update_product_from_producteca(account, variation_dict, odoo_product)
                        continue
                    self._create_product_from_producteca(account, variation_dict)


    def _prepare_dict_from_product_endpoint(self, variation, product_dict):
        product_dict.update({
            "sku": variation.get('sku'),
            "barcode": variation.get('barcode') or None,
            "variation_id": variation.get('id')
        })
        return product_dict

    def _create_product_in_producteca(self, account, producteca_body):
        connection_array_dict = []
        client = account.get_client()
        product_service = client.Product
        product_service.create_if_it_doesnt_exist = account.create_if_dosnt_exist,
        product = product_service.synchronize(producteca_body)
        existing_connection = self.env['producteca.product.connections'].sudo().search([('product_id', '=', self.id), ('producteca_id', '=', product.id), ('account_id', '=', account.id)], limit=1)
        if existing_connection:
            return self.env['producteca.product.connections']
        connection_array_dict.append({
            "producteca_account_id": account.id,
            "product_id": self.id,
            "producteca_id": product.id,
            # TODO: ? What may happend if this slicing fails?
            "producteca_variation_id": product.variations[0].id
        })
        return self.env['producteca.product.connections'].create(connection_array_dict)

    def _obtain_pricelist_for_product(self, product, account):        
        if not account.is_odoo_able_to_update_producteca_prices:
            return []            
        product_prices = []      
        
        if account.default_pricelist_id:
            price = account.default_pricelist_id._get_product_price(product, 1)
            pricelist_name = account.default_pricelist_id._get_producteca_pricelist_name(account)
            if price and pricelist_name:
                product_prices.append({
                    'amount': price,
                    'currency': account.default_pricelist_id.currency_id.name,
                    'priceList': pricelist_name
                })
        else:            
            if product.list_price:
                product_prices.append({
                    'amount': product.list_price,
                    'currency': product.currency_id.name,
                    'priceList': 'Default'
                })
        for pricelist in account.pricelist_ids:
            pricelist_name = pricelist._get_producteca_pricelist_name(account)
            if pricelist_name:  
                price = pricelist._get_product_price(product, 1)
                if price:
                    product_prices.append({
                        'amount': price,
                        'currency': pricelist.currency_id.name,
                        'priceList': pricelist_name
                    })
            
        return product_prices

    def _obtain_stocks_for_product(self, product, account):
        stock_by_warehouse = self.env['stock.quant'].search([('product_id', '=', product.id), ('location_id.usage', '=', 'internal'), ('warehouse_id', 'in', account.warehouse_ids.ids)])
        return stock_by_warehouse

    def _prepare_producteca_product_dict(self, product, account):
        pricelists = self._obtain_pricelist_for_product(product, account)
        stock_by_warehouse = self._obtain_stocks_for_product(product, account)
        image_url = f"{self.env['ir.config_parameter'].sudo().get_param('web.base.url')}/producteca/image/{product.id}"
        deals = None  # TODO: Add deals data based on loyalty modules, or something else.
        product_data = {
            "sku": product.default_code,
            "code": str(product.id),
            "name": product.name,
            "barcode": product.barcode or None,
            "attributes": [
                    {"key": variant.attribute_id.name, "value": variant.name}
                    for variant in product.product_template_variant_value_ids
                        ] if product.product_template_variant_value_ids else None,
            "tags": [
                tag.name for tag in product.product_tag_ids
                    ] if product.product_tag_ids else None,
            "category": product.categ_id.complete_name if product.categ_id else None,
            "brand": product.product_brand_id.name if product.product_brand_id else None,
            "notes": product.description if product.description else None,
            "pictures": [{"url": image_url}] if image_url else []
        }
        if product.weight:
            product_data.update({
                "dimensions": {
                    "weight": product.weight if product.weight else 0,
                    # "width": 0,
                    # "height": 0,
                    # "length": 0,  # TODO: This could be gotten from packs
                    # "pieces": 0,
                }})
        if stock_by_warehouse:
            product_data.update({
                "stocks": [
                    {
                        "quantity": stock.quantity,
                        "availableQuantity": stock.available_quantity,
                        "warehouse": stock.warehouse_id.producteca_warehouse_name if stock.warehouse_id else None
                    } for stock in stock_by_warehouse]
            })
        if deals:
            product_data.update({
                "deals": deals
            })
        if pricelists:
            product_data.update({
                "prices": pricelists
            })
        return {k: v for k, v in product_data.items() if v is not None}

    #TODO: add a create method to trigger this
    def create_product_in_producteca_queue(self):
        producteca_account_ids = self.env['producteca.account'].sudo().search([('active', '=', True), ('company_id', '=', self.env.company.id)])
        if not producteca_account_ids:
            return False
        products = self.env['product.product'].sudo().search([('is_producteca_product', '=', True), ('is_already_sync', '=', False)])
        if not products:
            return False
        for product in products:
            for account in producteca_account_ids:
                if not account.create_if_dosnt_exist:
                    continue
                product_dict = self._prepare_producteca_product_dict(product, account)
                self.with_delay()._create_product_in_producteca(account, product_dict)
        products.write({'is_already_sync': True})
        return True

    def sync_all_products_from_producteca(self):
        producteca_accounts = self.env['producteca.account'].sudo().search([('active', '=', True)])
        
        for account in producteca_accounts:
            client = account.get_client()

            params = SearchProductParams(
                top=100,
                skip=0,
                sales_channel='2'  
            )           
            
            products_response = client.Product.search(params=params)
            total_products = products_response.count if hasattr(products_response, 'count') else 0            
            for result in products_response.results:
                _logger.info(result)
                product_id = result.id
                _logger.info(f"Processing product ID: {product_id}")
                if not product_id:
                    continue                
                
                self.with_delay().get_product_from_producteca_and_create(account, product_id)            
            
            processed = len(products_response.results)
            while processed < total_products:
                params.skip = processed
                products_response = client.Product.search(params=params)
                
                for result in products_response.results:
                    product_id = result.id
                    _logger.info(f"Processing product ID: {product_id}")
                    if not product_id:
                        continue                    
                    
                    self.with_delay().get_product_from_producteca_and_create(account, product_id)
                
                processed += len(products_response.results)                
                
                if len(products_response.results) == 0:
                    break
                    
        return True



