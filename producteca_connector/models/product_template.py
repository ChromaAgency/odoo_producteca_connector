from odoo import models, fields, api, Command
from producteca.products.search_products import SearchProductParams
import logging

_logger = logging.getLogger(__name__)


def filter_empty_values(d):
    return {k: v for k, v in d.items() if v is not None and v != ''}


class ProductTemplate(models.Model):
    """Extended Product Template for Producteca integration.
    
    This model extends the standard Odoo product template to support integration
    with Producteca marketplace. It manages the complete product lifecycle for
    Producteca synchronization at the template level.
    
    Business Logic:
    - Manages template-level Producteca product information
    - Handles connections to Producteca marketplace products
    - Tracks synchronization status for marketplace operations
    - Supports batch operations for product synchronization
    
    Key Features:
    - Direct Producteca product status tracking
    - Synchronization state management
    - Connection management with Producteca marketplace
    - Template-level marketplace integration
    """
    _inherit = 'product.template'

    # Producteca Integration Fields
    is_producteca_product = fields.Boolean(
        string="Is Producteca Product",
        help="Indicates if this product template is synchronized with Producteca marketplace."
    )
    is_already_sync = fields.Boolean(
        string="Is Already Sync", 
        readonly=True, 
        copy=False,
        help="Indicates if this product template has been synchronized to Producteca at least once."
    )
    producteca_connection_ids = fields.One2many(
        'producteca.product.connections', 
        'product_tmpl_id', 
        string="Producteca Connections",
        help="Connections between this product template and Producteca marketplace products."
    )

    def _handle_producteca_attribute_dict(self, producteca_response, odoo_template):
        """Handle product attributes from Producteca response.
        
        Creates or updates attribute lines on the product template based on
        attributes provided by Producteca marketplace.
        
        Args:
            producteca_response (dict): Response from Producteca API containing attributes
            odoo_template (product.template): Existing template to update, or False for new products
            
        Returns:
            list: Command list for attribute_line_ids field operations
        """
        existing_lines = odoo_template.attribute_line_ids if odoo_template else []
        
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

    def _handle_producteca_tags_dict(self, producteca_response):
        """Handle product tags from Producteca response.
        
        Creates or finds existing product tags based on Producteca data.
        
        Args:
            producteca_response (dict): Response from Producteca API containing tags
            
        Returns:
            list: Command list for product_tag_ids field operations
        """
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

    def _handle_producteca_connection_ids(self, producteca_response, odoo_template, account):
        """Handle Producteca connections for product template.
        
        Creates or updates connections between Odoo template and Producteca product.
        Links all product variants to the connection for SKU tracking.
        
        Args:
            producteca_response (dict): Response from Producteca API
            odoo_template (product.template): Existing template, or False for new products
            account (producteca.account): Producteca account for this connection
            
        Returns:
            list: Command list for producteca_connection_ids field operations
        """
        if not account and not producteca_response.get('account_id'):
            return []

        producteca_account = account.id if account else producteca_response.get('account_id')
        
        existing_connection = self.env['producteca.product.connections'].sudo().search([
            ('producteca_account_id', '=', producteca_account),
            ('producteca_id', '=', str(producteca_response.get('id'))),
            ('product_tmpl_id', '=', odoo_template.id if odoo_template else False)
        ], limit=1)
        
        # We'll update product_variant_ids after template and variants are created/updated
        # This is just to create/identify the connection
        if existing_connection:
            return []
            
        if odoo_template and odoo_template.producteca_connection_ids:
            connection_exists = False
            for connection in odoo_template.producteca_connection_ids:
                if (connection.producteca_account_id.id == producteca_account and
                    connection.producteca_id == str(producteca_response.get('id'))):
                    connection_exists = True
                    break
            
            if not connection_exists:
                return [Command.create({
                    "producteca_account_id": producteca_account,
                    "producteca_id": producteca_response.get('id'),
                })]
            return []
        else:
            return [Command.create({
                "producteca_account_id": producteca_account,
                "producteca_id": producteca_response.get('id'),
            })]
    
    def _update_connection_variants(self, template, account, producteca_id):
        """Update the product_variant_ids in the connection after variants are created.
        
        This is called after template and variants are created/updated to ensure
        the connection has references to all variants with SKUs from Producteca.
        
        If the connection doesn't exist yet, it will be created. This handles cases
        where we find an existing Odoo template/variant by SKU but it wasn't previously
        connected to Producteca.
        
        Args:
            template (product.template): Template with variants
            account (producteca.account): Producteca account
            producteca_id (str|int): Producteca product ID (template level)
        """
        if not producteca_id:
            _logger.warning(f"Cannot update connection variants: producteca_id is missing for template {template.name} (ID: {template.id})")
            return
            
        connection = self.env['producteca.product.connections'].sudo().search([
            ('producteca_account_id', '=', account.id),
            ('producteca_id', '=', str(producteca_id)),
            ('product_tmpl_id', '=', template.id)
        ], limit=1)
        
        if not connection:
            # Connection doesn't exist yet, create it
            # This can happen when we find an existing product by SKU from sale_order
            _logger.info(f"Creating new connection for template {template.name} (ID: {template.id}) with Producteca ID {producteca_id}")
            connection = self.env['producteca.product.connections'].sudo().create({
                'producteca_account_id': account.id,
                'producteca_id': str(producteca_id),
                'product_tmpl_id': template.id,
            })
        
        # Link all variants that have SKUs
        variants_with_sku = template.product_variant_ids.filtered(lambda v: v.default_code)
        if variants_with_sku:
            connection.sudo().write({
                'product_variant_ids': [(6, 0, variants_with_sku.ids)]
            })
        else:
            _logger.warning(f"Template {template.name} (ID: {template.id}) has no variants with SKU to link to connection")

    def _prepare_producteca_to_odoo_product_dict(self, producteca_response, odoo_template, account):
        """Prepare data dictionary for creating/updating product template from Producteca.
        
        Converts Producteca API response into Odoo product.template field values.
        Handles template-level data and prepares for variant creation.
        
        Args:
            producteca_response (dict): Complete product data from Producteca API
            odoo_template (product.template): Existing template to update, or False for new
            account (producteca.account): Producteca account configuration
            
        Returns:
            dict: Field values for product.template create/write
            
        Raises:
            Exception: If product name is missing for new products
        """
        producteca_response = filter_empty_values(producteca_response)
        _logger.info(producteca_response)
        vals = {
            'is_producteca_product': True,
        }
        connection_ids = self._handle_producteca_connection_ids(producteca_response, odoo_template, account)
        if connection_ids:
            vals['producteca_connection_ids'] = connection_ids
        if account.is_producteca_able_to_modified_products or not odoo_template:
            vals.update({
                'description': producteca_response.get('notes'),
                'is_producteca_product': True,
                'is_already_sync': True,
            })
            if not odoo_template:
                name = producteca_response.get('name', False)
                if not name:
                    raise Exception("El producto de Producteca no tiene nombre asignado. Por favor, verifique en Producteca.")
                vals['name'] = name
                vals['type'] = 'consu'  # Consumable product (Odoo 18 compatible)
                # default_code se asigna a las variantes, no al template
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
                vals['attribute_line_ids'] = self._handle_producteca_attribute_dict(producteca_response, odoo_template)

            dimensions = producteca_response.get('dimensions', {})
            if dimensions:
                vals.update({
                    'weight': dimensions.get('weight'),
                })
        
        return vals

    def _find_or_create_variant_by_sku(self, template, sku, variation_data):
        """Find existing variant by SKU or create new one.
        
        Searches for existing product.product with matching SKU. If found, returns it.
        Otherwise, creates a new variant for the template.
        
        Args:
            template (product.template): Template to create variant for
            sku (str): SKU to search/assign
            variation_data (dict): Producteca variation data including barcode
            
        Returns:
            product.product: Found or created variant
        """
        if sku:
            existing_variant = self.env['product.product'].sudo().search([
                ('default_code', '=', sku)
            ], limit=1)
            if existing_variant:
                return existing_variant
        
        # Create new variant
        variant_vals = {
            'product_tmpl_id': template.id,
        }
        if sku:
            variant_vals['default_code'] = sku
        if variation_data.get('barcode'):
            variant_vals['barcode'] = variation_data['barcode']
            
        # Match attributes if provided
        if variation_data.get('attributes'):
            # Odoo creates variants automatically based on attribute_line_ids
            # We just need to find the right combination
            for variant in template.product_variant_ids:
                match = True
                for attr in variation_data['attributes']:
                    attr_name = attr.get('key')
                    attr_value = attr.get('value')
                    variant_attr = variant.product_template_variant_value_ids.filtered(
                        lambda v: v.attribute_id.name == attr_name and v.name == attr_value
                    )
                    if not variant_attr:
                        match = False
                        break
                if match:
                    # Update SKU and barcode on matching variant
                    update_vals = {}
                    if sku:
                        update_vals['default_code'] = sku
                    if variation_data.get('barcode'):
                        update_vals['barcode'] = variation_data['barcode']
                    if update_vals:
                        variant.sudo().write(update_vals)
                    return variant
        
        # If no match found and we have no attributes, create default variant
        return self.env['product.product'].sudo().create(variant_vals)

    def _create_product_from_producteca(self, account, producteca_body):
        """Create new product template and variants from Producteca data.
        
        Creates a product.template from Producteca API data and then creates
        or updates product.product variants based on Producteca variations.
        
        Args:
            account (producteca.account): Account configuration
            producteca_body (dict): Complete Producteca product data
            
        Returns:
            product.template: Created template with variants
            
        Raises:
            Exception: If account doesn't allow product creation
        """
        if not account.is_producteca_able_to_create_products:
            raise Exception(
                "No se pudo crear la orden porque la cuenta no permite creación de productos. "
                f"Cree el producto con ID {producteca_body.get('id')} manualmente, relaciónelo y luego reencole el proceso."
            )
        producteca_body.update({
            "account_id": account.id
        })
        template_vals = self._prepare_producteca_to_odoo_product_dict(producteca_body, False, account)
        try:
            _logger.info(template_vals)
            template = self.env['product.template'].sudo().create(template_vals)
        except Exception as e:
            _logger.error(f"Error creating template: {e}")
            raise
        
        # Create/update variants from Producteca variations
        if producteca_body.get('variations'):
            for variation in producteca_body['variations']:
                self._find_or_create_variant_by_sku(
                    template, 
                    variation.get('sku'), 
                    variation
                )
        
        # Update connection with all variants that have SKUs
        self._update_connection_variants(template, account, producteca_body.get('id'))
        
        return template

    def _update_product_from_producteca(self, account, producteca_body, odoo_template):
        """Update existing product template from Producteca data.
        
        Updates template fields and manages variants based on Producteca variations.
        ALWAYS updates the connection (for tracking), but only modifies product
        data if account permissions allow it.
        
        Args:
            account (producteca.account): Account configuration
            producteca_body (dict): Complete Producteca product data
            odoo_template (product.template): Template to update
            
        Returns:
            bool: True if successful
        """
        # Prepare product data (respects account.is_producteca_able_to_modified_products)
        product_dict = self._prepare_producteca_to_odoo_product_dict(producteca_body, odoo_template, account)
        template_write = True
        
        # Only update product data if there are changes to apply
        if product_dict:
            template_write = odoo_template.sudo().write(product_dict)
        
        # Update variants ONLY if account allows modification
        if account.is_producteca_able_to_modified_products and producteca_body.get('variations'):
            for variation in producteca_body['variations']:
                self._find_or_create_variant_by_sku(
                    odoo_template, 
                    variation.get('sku'), 
                    variation
                )
        
        # ALWAYS update connection (for tracking purposes)
        # This doesn't modify product data, just maintains the link
        self._update_connection_variants(odoo_template, account, producteca_body.get('id'))
        
        return template_write

    def get_product_from_producteca_and_create(self, account, producteca_id):
        """Fetch product from Producteca API and create/update in Odoo.
        
        Retrieves complete product data from Producteca including variations,
        then creates or updates the corresponding template and variants in Odoo.
        
        Args:
            account (producteca.account): Account to use for API calls
            producteca_id (str): Producteca product ID to fetch
        """
        client = account.get_client()
        product_service = client.Product
        product_service.create_if_it_doesnt_exist = account.create_if_dosnt_exist
        product = product_service.get(producteca_id)
        
        product_dict = product.to_dict()
        
        # Check if template connection exists
        connection = self.env['producteca.product.connections'].sudo().search([
            ('producteca_id', '=', str(product.id)), 
            ('producteca_account_id', '=', account.id)
        ], limit=1)
        
        if connection and connection.product_tmpl_id:
            # Update existing template
            self._update_product_from_producteca(account, product_dict, connection.product_tmpl_id)
        else:
            # Try to find by SKU from first variation
            if product_dict.get('variations') and product_dict['variations']:
                first_sku = product_dict['variations'][0].get('sku')
                if first_sku:
                    existing_variant = self.env['product.product'].sudo().search([
                        ('default_code', '=', first_sku)
                    ], limit=1)
                    if existing_variant and existing_variant.product_tmpl_id:
                        self._update_product_from_producteca(account, product_dict, existing_variant.product_tmpl_id)
                        return
            
            # Create new template
            self._create_product_from_producteca(account, product_dict)

    def _create_product_in_producteca(self, account, producteca_body):
        """Create or update product in Producteca marketplace.
        
        Synchronizes template data to Producteca, creating connection if needed.
        
        Args:
            account (producteca.account): Account for API calls
            producteca_body (dict): Product data to send
            
        Returns:
            producteca.product.connections: Created or existing connection
        """
        client = account.get_client()
        product_service = client.Product
        product_service.create_if_it_doesnt_exist = account.create_if_dosnt_exist,
        product = product_service.synchronize(producteca_body)
        
        # Use _update_connection_variants which will create connection if it doesn't exist
        # and update variants
        self._update_connection_variants(self, account, str(product.id))
        
        # Return the connection
        connection = self.env['producteca.product.connections'].sudo().search([
            ('product_tmpl_id', '=', self.id), 
            ('producteca_id', '=', str(product.id)), 
            ('producteca_account_id', '=', account.id)
        ], limit=1)
        
        return connection if connection else self.env['producteca.product.connections']

    def _obtain_pricelist_for_product(self, template, account):
        """Get price lists for product template to send to Producteca.
        
        Producteca manages prices at template level, not variant level.
        
        Args:
            template (product.template): Template to get prices for
            account (producteca.account): Account configuration
            
        Returns:
            list: List of price dictionaries for Producteca API
        """        
        if not account.is_odoo_able_to_update_producteca_prices:
            return []            
        product_prices = []      
        
        if account.default_pricelist_id:
            # Use first variant for price calculation if template has variants
            product_for_price = template.product_variant_ids[0] if template.product_variant_ids else template
            price = account.default_pricelist_id._get_product_price(product_for_price, 1)
            pricelist_name = account.default_pricelist_id._get_producteca_pricelist_name(account)
            if price and pricelist_name:
                product_prices.append({
                    'amount': price,
                    'currency': account.default_pricelist_id.currency_id.name,
                    'priceList': pricelist_name
                })
        else:            
            if template.list_price:
                product_prices.append({
                    'amount': template.list_price,
                    'currency': template.currency_id.name if template.currency_id else account.company_id.currency_id.name,
                    'priceList': 'Default'
                })
        
        for pricelist in account.pricelist_ids:
            pricelist_name = pricelist._get_producteca_pricelist_name(account)
            if pricelist_name:
                product_for_price = template.product_variant_ids[0] if template.product_variant_ids else template
                price = pricelist._get_product_price(product_for_price, 1)
                if price:
                    product_prices.append({
                        'amount': price,
                        'currency': pricelist.currency_id.name,
                        'priceList': pricelist_name
                    })
            
        return product_prices

    def _obtain_stocks_for_product(self, template, account):
        """Get stock quantities for all variants of template.
        
        Producteca manages stock at variant level (by SKU).
        Returns stock data for each variant separately.
        
        Args:
            template (product.template): Template to get stock for
            account (producteca.account): Account configuration with warehouses
            
        Returns:
            list: Stock data grouped by variant SKU
        """
        all_stocks = []
        
        for variant in template.product_variant_ids:
            if not variant.default_code:  # Skip variants without SKU
                continue
                
            stock_by_warehouse = self.env['stock.quant'].search([
                ('product_id', '=', variant.id), 
                ('location_id.usage', '=', 'internal'), 
                ('warehouse_id', 'in', account.warehouse_ids.ids)
            ])
            
            if stock_by_warehouse:
                all_stocks.append({
                    'sku': variant.default_code,
                    'stocks': stock_by_warehouse
                })
        
        return all_stocks

    def _prepare_producteca_product_dict(self, template, account):
        """Prepare product template data for sending to Producteca API.
        
        Converts Odoo template and variants into Producteca API format.
        Includes template-level data and all variations.
        
        Args:
            template (product.template): Template to convert
            account (producteca.account): Account configuration
            
        Returns:
            dict: Product data in Producteca API format
        """
        pricelists = self._obtain_pricelist_for_product(template, account)
        stocks_data = self._obtain_stocks_for_product(template, account)
        
        # Use first variant for main image, or template if no variants
        image_product = template.product_variant_ids[0] if template.product_variant_ids else template
        image_url = f"{self.env['ir.config_parameter'].sudo().get_param('web.base.url')}/producteca/image/{image_product.id}"
        deals = None
        
        product_data = {
            "code": str(template.id),
            "name": template.name,
            "category": template.categ_id.complete_name if template.categ_id else None,
            "brand": template.product_brand_id.name if template.product_brand_id else None,
            "notes": template.description if template.description else None,
            "pictures": [{"url": image_url}] if image_url else []
        }
        
        # Add template tags if any
        if template.product_tag_ids:
            product_data["tags"] = [tag.name for tag in template.product_tag_ids]
        
        # Add weight if set
        if template.weight:
            product_data["dimensions"] = {
                "weight": template.weight if template.weight else 0,
            }
        
        # Add variations (variants)
        variations = []
        for variant in template.product_variant_ids:
            variation_dict = {
                "sku": variant.default_code,
                "barcode": variant.barcode or None,
            }
            
            # Add variant attributes
            if variant.product_template_variant_value_ids:
                variation_dict["attributes"] = [
                    {"key": variant_value.attribute_id.name, "value": variant_value.name}
                    for variant_value in variant.product_template_variant_value_ids
                ]
            
            # Add variant-specific stocks
            variant_stocks = [s for s in stocks_data if s['sku'] == variant.default_code]
            if variant_stocks and variant_stocks[0]['stocks']:
                variation_dict["stocks"] = [
                    {
                        "quantity": stock.quantity,
                        "availableQuantity": stock.available_quantity,
                        "warehouse": stock.warehouse_id.producteca_warehouse_name if stock.warehouse_id else None
                    } for stock in variant_stocks[0]['stocks']
                ]
            
            variations.append(variation_dict)
        
        if variations:
            product_data["variations"] = variations
        
        if deals:
            product_data["deals"] = deals
        if pricelists:
            product_data["prices"] = pricelists
            
        return {k: v for k, v in product_data.items() if v is not None}

    def create_product_in_producteca_queue(self):
        """Queue product template synchronization to Producteca.
        
        Creates background jobs to sync all unsynchronized templates to Producteca.
        """
        producteca_account_ids = self.env['producteca.account'].sudo().search([
            ('active', '=', True), 
            ('company_id', '=', self.env.company.id)
        ])
        if not producteca_account_ids:
            return False
        
        templates = self.env['product.template'].sudo().search([
            ('is_producteca_product', '=', True), 
            ('is_already_sync', '=', False)
        ])
        if not templates:
            return False
        
        for template in templates:
            for account in producteca_account_ids:
                if not account.create_if_dosnt_exist:
                    continue
                product_dict = self._prepare_producteca_product_dict(template, account)
                self.with_delay()._create_product_in_producteca(account, product_dict)
        
        templates.write({'is_already_sync': True})
        return True

    def sync_all_products_from_producteca(self):
        """Synchronize all products from Producteca to Odoo.
        
        Fetches all products from Producteca marketplace and creates/updates
        corresponding templates and variants in Odoo.
        """
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
