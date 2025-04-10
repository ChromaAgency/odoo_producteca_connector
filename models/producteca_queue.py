from odoo import models, fields, api


class ProductecaQueue(models.Model):
    _name = "producteca.queue"
    _description = "Producteca Queue"

    active = fields.Boolean(string="Active", default=True)
    producteca_account_id = fields.Many2one(
        "producteca.account", string="Producteca Account"
    )
    producteca_body = fields.Text(string="Producteca Body")
    producteca_method = fields.Selection(
        [("get", "Get"), ("post", "Post"), ("put", "Put"), ("delete", "Delete")],
        string="Producteca Method",
    )
    producteca_url = fields.Char(string="Producteca URL")
    producteca_response = fields.Text(string="Producteca Response")

    def queue_to_create_products_in_producteca(self, products):
        vals_to_create = []
        for product in products:
            producteca_product_dict = self._prepare_producteca_product_dict(product) #Is this too much processing? We should move it to the prompt? how?
            vals_to_create.append(producteca_product_dict)
        queue_products = self.create(vals_to_create)
        return queue_products

    def get_dimensions_from_volume(self, volume, aspect_ratio=1.0):
        #This is an AI func should be tested
        if volume <= 0:
            return 0, 0, 0
        
        # Para simplificar, suponemos que el producto es un cubo
        side = volume ** (1/3)  # Raíz cúbica del volumen
        
        # Si queremos mantener una relación de aspecto específica
        if aspect_ratio != 1.0:
            # Ajustamos las dimensiones para mantener la relación de aspecto
            length = side * aspect_ratio
            width = side
            height = volume / (length * width)
        else:
            # Si no hay relación de aspecto específica, usamos un cubo
            length = width = height = side
        
        return length, width, height

    #Product product
    def _obtain_pricelist_for_product(self, product):
        """Obtiene la lista de precios para el producto"""
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

    def _obtain_stocks_for_product(self, product):
        stock_by_warehouse = self.env['stock.quant'].search([('product_id', '=', product.id), ('location_id.usage', '=', 'internal')])
        return stock_by_warehouse

    def _prepare_producteca_product_dict(self, product):
        length, width, height = self.get_dimensions_from_volume(product.volume)
        pricelists = self._obtain_pricelist_for_product(product)
        stock_by_warehouse = self._obtain_stocks_for_product(product)
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
                "width": width,
                "height": height,
                "length": length,
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


#    config: Optional[ConfigProducteca] = Field(default=None, exclude=True)
#     create_if_not_exist: bool = False
#     product_id: Optional[int] = None
#     sku: str = ''
#     variation_id: Optional[int] = None
#     code: str = ''
#     name: str = ''
#     barcode: str = ''
#     attributes: List[Attributes] = []
#     tags: List[Tags] = []
#     buying_price: Optional[float] = None
#     dimensions: Optional[dict] = None
#     category: Optional[Category] = None
#     brand: str = ''
#     notes: str = ''
#     deals: List[Deals] = []
#     stocks: List[Stocks] = []
#     prices: List[Prices] = []
#     pictures: List[Pictures] = []
#     integrations: Optional[List[Integrations]] = None
#     variations: Optional[List[Variation]] = None
#     is_simple: Optional[bool] = None
#     has_variations: Optional[bool] = None
#     thumbnail: Optional[str] = None
#     is_archived: Optional[bool] = None
#     metadata: Optional[List[str]] = None
#     is_original: Optional[bool] = None
#     id: Optional[int] = None
#     attributes_hash: Optional[str] = None
#     primary_color: Optional[str] = None
#     has_custom_shipping_costs: Optional[bool] = None
#     shipping: Optional[Shipping] = None
#     mshops_shipping: Optional[MShopsShipping] = None
#     add_free_shipping_cost_to_price: Optional[bool] = None
#     attribute_completion: Optional[AttributeCompletion] = None
#     catalog_products: Optional[List[str]] = None
#     warranty: Optional[str] = None
#     domain: Optional[str] = None
#     listing_type_id: Optional[str] = None
#     catalog_products_status: Optional[str] = None
#     tags_list: Optional[List[str]] = None
