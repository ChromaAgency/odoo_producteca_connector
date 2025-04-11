from odoo import models, fields, api
from ..utils.products.products import Product
from ..utils.config.config import ConfigProducteca

class ProductecaQueue(models.Model):
    _name = "producteca.queue"
    _description = "Producteca Queue"

    active = fields.Boolean(string="Active", default=True)
    producteca_account_id = fields.Many2one(
        "producteca.account", string="Producteca Account"
    )
    producteca_body = fields.Text(string="Producteca Body")
    producteca_method = fields.Selection(
        [("create", "Create"), ("get", "Get"), ("post", "Post"), ("put", "Put"), ("delete", "Delete")],
        string="Producteca Method",
    )
    model = fields.Char(string="Model")
    producteca_response = fields.Text(string="Producteca Response")
    odoo_item_id = fields.Integer(string="Odoo Item ID", readonly=True)

    def process_product_create_queue(self):
        queue_records = self.search([('producteca_method', '=', 'create'), ('active', '=', True), ('model', '=', 'product')])
        connection_array_dict = []
        for queue_record in queue_records:
            config = ConfigProducteca(queue_record.producteca_account_id.api_key, queue_record.producteca_account_id.bearer_token)
            product = Product(config=config, create_if_not_exist=queue_record.producteca_account_id.create_if_dosnt_exist, **queue_record.producteca_body)
            product_response = product.create()
            queue_record.producteca_response = product_response.model_dump_json(exclude_none=True)
            connection_array_dict.append({
                "producteca_account_id": queue_record.producteca_account_id,
                "product_id": queue_record.odoo_item_id,
                "producteca_id": product_response.product_id
            })
        self.env['producteca.connections'].create(connection_array_dict)


    def create_product_in_producteca_queue(self):
        producteca_account_ids = self.env['producteca.account'].sudo().search([('active', '=', True),('company_id', '=', self.env.company.id), ('is_producteca_able_to_create_products', '=', True)])
        if not producteca_account_ids:
            return False
        products = self.env['product.product'].sudo().search([('is_producteca_product', '=', True), ('is_already_sync', '=', False)])
        if not products:
            return False
        queue_records = []
        for product in products:
            for account in producteca_account_ids:
                product_dict = self._obtain_pricelist_for_product(product, account)
                queue_records.append({
                    "producteca_account_id": account,
                    "producteca_body": product_dict,
                    "producteca_method": "create",
                    "model": "product",
                    "odoo_item_id": product.id
            })
        self.create(queue_records)
        return True



    def _obtain_pricelist_for_product(self, product):
        pricelists = self.env['product.pricelist'].search([('company_id', '=', product.company_id.id), ('active', '=', True), ('currency_id', '=', product.currency_id.id)])
        product_in_pricelist = []
        if not pricelists:
            return []
        for item in pricelists.item_ids:
            if item.display_applied_on == '1_product' and product.product_tmpl_id in item.product_tmpl_id:
                product_in_pricelist.append(item)
            elif item.display_applied_on == '2_product_category' and product.categ_id in item.categ_id:
                product_in_pricelist.append(item)
            else:
                continue
        return product_in_pricelist

    def _obtain_stocks_for_product(self, product, account):
        stock_by_warehouse = self.env['stock.quant'].search([('product_id', '=', product.id), ('location_id.usage', '=', 'internal'), ('location_id', 'in', account.warehouse_location_ids)])
        return stock_by_warehouse

    def _prepare_producteca_product_dict(self, product, account):
        pricelists = self._obtain_pricelist_for_product(product)
        stock_by_warehouse = self._obtain_stocks_for_product(product, account)
        product_data = {
            "sku": product.default_code or '',
            "variationId": product.id,
            "code": product.default_code or '',
            "name": product.name,
            "barcode": product.barcode or '',
            "attributes": [{"key": variant.attribute_id.name, "value": variant.name} for variant in product.product_template_variant_value_ids],
            "tags": [tag.name for tag in product.tag_ids],
            "buyingPrice": product.lst_price,
            "dimensions": {
                "weight": product.weight if product.weight else 0,
                "width": 0,
                "height": 0,
                "length": 0, #TODO
                "pieces": 0,
            },
            "category": product.categ_id.complete_name,
            "brand": product.product_brand_id.name,
            "notes": product.description,
            "deals": [], #TODO
            "stocks": [{"quantity": stock_by_warehouse.quantity, "availableQuantity": stock_by_warehouse.available_quantity, "warehouse": stock_by_warehouse.warehouse_id.name}],
            "prices": [{"amount": item.fixed_price, "currency": item.currency_id.name, "priceList": item.pricelist_id.name} for item in pricelists],
            "pictures": [{}],# TODO ?
        }

        return {k: v for k, v in product_data.items() if v is not None}
