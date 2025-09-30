from odoo import models, fields, api, Command
import logging

_logger = logging.getLogger(__name__)


def filter_empty_values(d):
    return {k: v for k, v in d.items() if v is not None and v != ''}


class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_producteca_product = fields.Boolean(string="Is Producteca Product", related='product_tmpl_id.is_producteca_product', store=True)
    is_already_sync = fields.Boolean(string="Is Already Sync", readonly=True, copy=False)
    producteca_connection_ids = fields.One2many('producteca.product.connections', 'product_id', string="Producteca Connection")

    def _update_product_price(self):
        # TODO: Check why 3 queues are getting generated when running this method
        producteca_connection = self.env['producteca.product.connections'].sudo().search([('product_id', '=', self.id)])
        client = producteca_connection.producteca_account_id.get_client()
        body_dict = {
            "code": str(producteca_connection.product_id.id),
            "prices": [{"amount": self.list_price, "currency": producteca_connection.product_id.currency_id.name, "priceList": "Default"}]
        }
        product_service = client.Product
        product_service.create_if_it_doesnt_exist = producteca_connection.producteca_account_id.create_if_dosnt_exist
        product_service.synchronize(body_dict)

    def write(self, vals):
        _ = super().write(vals)
        for rec in self:
            if rec.is_producteca_product and 'list_price' in vals:
                rec.with_delay()._update_product_price()
        return _

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
    def _handle_producteca_connection_ids(self, producteca_response, odoo_product):
        if not producteca_response.get('account_id'):
            return []
        
        existing_connection = self.env['producteca.product.connections'].sudo().search([
            ('producteca_account_id', '=', producteca_response.get('account_id')),
            ('producteca_id', '=', str(producteca_response.get('id'))),
            ('producteca_variation_id', '=', str(producteca_response.get('variation_id'))),
            ('product_id', '=', odoo_product.id if odoo_product else False)
        ], limit=1)
        
        if existing_connection:
            return []
            
        if odoo_product and odoo_product.producteca_connection_ids:
            connection_exists = False
            for connection in odoo_product.producteca_connection_ids:
                if (connection.producteca_account_id.id == producteca_response.get('account_id') and
                    connection.producteca_id == str(producteca_response.get('id')) and 
                    connection.producteca_variation_id == str(producteca_response.get('variation_id'))):
                    connection_exists = True
                    break
            
            if not connection_exists:
                return [Command.link(0)] + [Command.create({
                    "producteca_account_id": producteca_response.get('account_id'),
                    "producteca_id": producteca_response.get('id'),
                    "producteca_variation_id": producteca_response.get('variation_id')
                })]
            return []
        else:
            return [Command.create({
                "producteca_account_id": producteca_response.get('account_id'),
                "producteca_id": producteca_response.get('id'),
                "producteca_variation_id": producteca_response.get('variation_id')
            })]

    # TODO: Change this for produceteca_response
    def _prepare_producteca_to_odoo_product_dict(self, producteca_response, odoo_product):
        producteca_response = filter_empty_values(producteca_response)
        _logger.info(producteca_response)
        vals = {
            'name': producteca_response.get('name'),
            'default_code': producteca_response.get('sku'),
            'barcode': producteca_response.get('barcode'),
            'list_price': producteca_response.get('buyingPrice'),
            'description': producteca_response.get('notes'),
            'is_producteca_product': True,
        }
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

        connection_ids = self._handle_producteca_connection_ids(producteca_response, odoo_product)
        if connection_ids:
            vals['producteca_connection_ids'] = connection_ids
        
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
        products_to_create = self._prepare_producteca_to_odoo_product_dict(producteca_body, False)
        return self.env['product.product'].sudo().create(products_to_create)

    def _update_product_from_producteca(self, account, producteca_body, odoo_product):
        product_dict = self._prepare_producteca_to_odoo_product_dict(producteca_body, odoo_product)
        return odoo_product.sudo().write(product_dict)

    def get_product_from_producteca_and_create(self, account, producteca_id):
        client = account.get_client()
        product_service = client.Product
        product_service.create_if_it_doesnt_exist = account.create_if_dosnt_exist
        product = product_service.get(producteca_id)
        connection = self.env['producteca.product.connections'].sudo().search([('producteca_id', '=', product.id)], limit=1)
        if connection:
            self._update_product_from_producteca(account, product.to_dict(), connection.product_id)
            return connection.product_id
        else:
            return self._create_product_from_producteca(account, product.to_dict())

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

    def _obtain_pricelist_for_product(self, product):
        pricelists = self.env['product.pricelist'].search([('company_id', '=', product.company_id.id), ('active', '=', True), ('currency_id', '=', product.currency_id.id)])
        product_in_pricelist = []
        if not pricelists:
            return []
        for item in pricelists.item_ids:
            # Change this to compute the pricelist
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
        deals = None  # TODO: Add deals data based on loyalty modules, or something else.
        product_data = {
            "sku": product.default_code or None,
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
                    "length": 0,  # TODO: This could be gotten from packs
                    "pieces": 0,
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
                "prices": [
                    {
                        "amount": item.fixed_price,
                        "currency": item.currency_id.name,
                        "priceList": item.pricelist_id.name
                    } for item in pricelists]
            })
        return {k: v for k, v in product_data.items() if v is not None}

    # TODO: add a create method to trigger this
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



