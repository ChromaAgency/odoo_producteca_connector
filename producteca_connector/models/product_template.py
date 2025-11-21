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
        """Handle Producteca connections for product variants.
        
        Creates or updates connections between Odoo variants and Producteca variations.
        Each variation in Producteca gets its own connection to the corresponding Odoo variant.
        This is called AFTER variants are created to establish the connections.
        
        ALWAYS creates/updates connections even if account doesn't allow modifications,
        because connections are needed for tracking and synchronization.
        
        Args:
            producteca_response (dict): Response from Producteca API with variations[]
            odoo_template (product.template): Template with created variants
            account (producteca.account): Producteca account for this connection
            
        Returns:
            None - Connections are created directly, not via Commands
        """
        if not account and not producteca_response.get('account_id'):
            _logger.error("Cannot handle connections: no account provided")
            return
        
        if not odoo_template:
            _logger.error("Cannot handle connections: no odoo_template provided")
            return
        
        if not account:
            account = self.env['producteca.account'].browse(producteca_response.get('account_id'))

        producteca_id = str(producteca_response.get('id'))
        variations = producteca_response.get('variations', [])
        
        for variation in variations:
            sku = variation.get('sku')
            variation_id = str(variation.get('id'))
            
            if not sku:
                _logger.warning(f"Variation {variation_id} has no SKU, skipping connection creation")
                continue
            
            variant = odoo_template.product_variant_ids.filtered(
                lambda v: v.default_code == sku
            )
            
            if not variant:
                _logger.warning(f"No variant found with SKU {sku} for template {odoo_template.name}")
                continue
            
            target_variant = variant[0] if len(variant) > 1 else variant
            
            existing_connection = self.env['producteca.product.connections'].sudo().search([
                ('product_id', '=', target_variant.id),
                ('producteca_account_id', '=', account.id)
            ], limit=1)
            
            if existing_connection:
                existing_connection.sudo().write({
                    'producteca_id': producteca_id,
                    'producteca_variation_id': variation_id,
                })
            else:
                self.env['producteca.product.connections'].sudo().create({
                    'product_id': target_variant.id,
                    'producteca_account_id': account.id,
                    'producteca_id': producteca_id,
                    'producteca_variation_id': variation_id,
                })
    
    def _update_connection_variants(self, template, account, producteca_id, producteca_body=None):
        """Create or update connections for each variant.
        
        This is called after template and variants are created/updated to ensure
        each variant has its own connection with the proper producteca_variation_id.
        
        ALWAYS creates/updates connections even if variation_id is not known yet,
        because connections are needed for tracking. The variation_id can be updated later.
        
        Args:
            template (product.template): Template with variants
            account (producteca.account): Producteca account
            producteca_id (str|int): Producteca product ID (template level)
            producteca_body (dict): Optional - Full producteca data with variations[]
        """
        if not producteca_id:
            _logger.warning(f"Cannot update connection variants: producteca_id is missing for template {template.name} (ID: {template.id})")
            return
        
        if not account:
            _logger.error("Cannot update connection variants: no account provided")
            return
        
        variations = producteca_body.get('variations', []) if producteca_body else []
        variations_by_sku = {v.get('sku'): v for v in variations if v.get('sku')}
        
        variants_with_sku = template.product_variant_ids.filtered(lambda v: v.default_code)
        
        if not variants_with_sku:
            _logger.warning(f"Template {template.name} (ID: {template.id}) has no variants with SKU, cannot create connections")
            return
        
        for variant in variants_with_sku:
            existing_connection = self.env['producteca.product.connections'].sudo().search([
                ('product_id', '=', variant.id),
                ('producteca_account_id', '=', account.id)
            ], limit=1)
            
            variation_data = variations_by_sku.get(variant.default_code, {})
            variation_id = str(variation_data.get('id')) if variation_data.get('id') else None
            
            vals = {'producteca_id': str(producteca_id)}
            if variation_id:
                vals['producteca_variation_id'] = variation_id
            
            if existing_connection:
                existing_connection.sudo().write(vals)
                _logger.info(f"Updated connection for variant {variant.default_code} (ID: {variant.id})")
            else:
                vals.update({
                    'product_id': variant.id,
                    'producteca_account_id': account.id,
                })
                self.env['producteca.product.connections'].sudo().create(vals)
                if variation_id:
                    _logger.info(f"Created connection for variant {variant.default_code} with variation_id {variation_id}")
                else:
                    _logger.warning(f"Created connection for variant {variant.default_code} without variation_id (will be updated later)")

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
                vals['type'] = 'consu'
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

            dimensions = producteca_response.get('dimensions', {})
            if dimensions:
                vals.update({
                    'weight': dimensions.get('weight'),
                })
        
        return vals

    def _update_or_create_variants_from_producteca(self, template, variations, account):
        """Update or create variants from Producteca variations.
        
        Handles the special case where Odoo automatically creates an empty variant
        when a template is created. If the product has only 1 variation and the template
        has a variant without SKU, we update that variant instead of creating a new one.
        
        Args:
            template (product.template): Template to update variants for
            variations (list): List of Producteca variations
            account (producteca.account): Account configuration
        """
        if not variations:
            return
        
        empty_variant = template.product_variant_ids.filtered(lambda v: not v.default_code)
        
        if len(variations) == 1:
            if empty_variant and len(empty_variant) == 1 and account.is_producteca_able_to_modified_products:
                variation = variations[0]
                _logger.info(f"Found empty variant for template {template.name}, updating with SKU {variation.get('sku')}")
                self._update_variant_from_variation(empty_variant, variation)
                return
        
        if len(variations) > 1 and empty_variant and len(empty_variant) == 1:
            if account.is_producteca_able_to_modified_products:
                first_variation = variations[0]
                _logger.info(f"Multiple variations detected, updating empty variant with first SKU {first_variation.get('sku')}")
                self._update_variant_from_variation(empty_variant, first_variation)
                
                for variation in variations[1:]:
                    self._find_or_create_variant_by_sku(
                        template,
                        variation.get('sku'),
                        variation,
                        account
                    )
                return
        
        for variation in variations:
            self._find_or_create_variant_by_sku(
                template,
                variation.get('sku'),
                variation,
                account
            )
    
    def _update_variant_from_variation(self, variant, variation_data):
        """Update a single variant with data from Producteca variation.
        
        Args:
            variant (product.product): Variant to update
            variation_data (dict): Producteca variation data
        """
        update_vals = {}
        if variation_data.get('sku'):
            update_vals['default_code'] = variation_data['sku']
        if variation_data.get('barcode'):
            update_vals['barcode'] = variation_data['barcode']
        
        if update_vals:
            try:
                variant.sudo().write(update_vals)
                _logger.info(f"Updated variant with SKU {variation_data.get('sku')}")
            except Exception as e:
                _logger.warning(f"Error updating variant with barcode {variation_data.get('barcode')}: {e}")
                if 'barcode' in update_vals:
                    update_vals.pop('barcode')
                    try:
                        variant.sudo().write(update_vals)
                        _logger.info(f"Updated variant with SKU {variation_data.get('sku')} without barcode")
                    except Exception as e2:
                        _logger.error(f"Error updating variant even without barcode: {e2}")

    def _find_or_create_variant_by_sku(self, template, sku, variation_data, account):
        """Find existing variant by SKU or create new one.
        
        Searches for existing product.product with matching SKU in this template. 
        If found, updates it (ONLY if account.is_producteca_able_to_modified_products). 
        Otherwise, creates a new variant (ONLY if account.is_producteca_able_to_create_products).
        
        Args:
            template (product.template): Template to create variant for
            sku (str): SKU to search/assign
            variation_data (dict): Producteca variation data including barcode
            account (producteca.account): Account configuration for permissions
            
        Returns:
            product.product: Found or created variant, or None if no permissions
        """
        if not sku:
            _logger.warning(f"Variation without SKU, cannot create/update variant")
            return None
        
        existing_variant = template.product_variant_ids.filtered(lambda v: v.default_code == sku)
        
        if existing_variant:
            existing_variant = existing_variant[0]
            if account.is_producteca_able_to_modified_products:
                update_vals = {}
                if variation_data.get('barcode') and not existing_variant.barcode:
                    update_vals['barcode'] = variation_data['barcode']
                if update_vals:
                    try:
                        existing_variant.sudo().write(update_vals)
                        _logger.info(f"Updated variant {sku} with barcode")
                    except Exception as e:
                        _logger.warning(f"Error updating variant {sku} with barcode: {e}")
            else:
                _logger.info(f"Variant {sku} exists but account doesn't have modification permissions")
            return existing_variant
        
        if not account.is_producteca_able_to_create_products:
            _logger.warning(f"Cannot create variant {sku}: account doesn't have creation permissions")
            return None
        
        variant_vals = {
            'product_tmpl_id': template.id,
            'default_code': sku,
        }
        if variation_data.get('barcode'):
            variant_vals['barcode'] = variation_data['barcode']
        
        try:
            new_variant = self.env['product.product'].sudo().create(variant_vals)
            _logger.info(f"Created new variant {sku} for template {template.name}")
            return new_variant
        except Exception as e:
            _logger.warning(f"Error creating variant {sku} with barcode {variant_vals.get('barcode')}: {e}")
            if 'barcode' in variant_vals:
                variant_vals.pop('barcode')
                try:
                    new_variant = self.env['product.product'].sudo().create(variant_vals)
                    _logger.info(f"Created new variant {sku} without barcode")
                    return new_variant
                except Exception as e2:
                    _logger.error(f"Error creating variant {sku} even without barcode: {e2}")
                    raise

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
        
        if producteca_body.get('variations'):
            self._update_or_create_variants_from_producteca(
                template, 
                producteca_body['variations'], 
                account
            )
        
        self._handle_producteca_connection_ids(producteca_body, template, account)
        
        return template

    def _update_product_from_producteca(self, account, producteca_body, odoo_template):
        """Update existing product template from Producteca data.
        
        Updates template fields and manages variants based on Producteca variations.
        
        Args:
            account (producteca.account): Account configuration
            producteca_body (dict): Complete Producteca product data
            odoo_template (product.template): Template to update
            
        Returns:
            bool: True if successful
        """
        product_dict = self._prepare_producteca_to_odoo_product_dict(producteca_body, odoo_template, account)
        template_write = True
        
        if product_dict:
            template_write = odoo_template.sudo().write(product_dict)
        
        if producteca_body.get('variations'):
            if account.is_producteca_able_to_create_products or account.is_producteca_able_to_modified_products:
                self._update_or_create_variants_from_producteca(
                    odoo_template, 
                    producteca_body['variations'], 
                    account
                )
            else:
                _logger.warning(f"Skipping variant sync for template {odoo_template.name}: account has no creation or modification permissions")
        
        self._handle_producteca_connection_ids(producteca_body, odoo_template, account)
        
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
        
        connection = self.env['producteca.product.connections'].sudo().search([
            ('producteca_id', '=', str(product.id)), 
            ('producteca_account_id', '=', account.id)
        ], limit=1)
        
        if connection and connection.product_tmpl_id:
            self._update_product_from_producteca(account, product_dict, connection.product_tmpl_id)
        else:
            if product_dict.get('variations') and product_dict['variations']:
                first_sku = product_dict['variations'][0].get('sku')
                if first_sku:
                    existing_variant = self.env['product.product'].sudo().search([
                        ('default_code', '=', first_sku)
                    ], limit=1)
                    if existing_variant and existing_variant.product_tmpl_id:
                        self._update_product_from_producteca(account, product_dict, existing_variant.product_tmpl_id)
                        return
            
            self._create_product_from_producteca(account, product_dict)

    def _create_product_in_producteca(self, account, producteca_body):
        """Create or update product in Producteca marketplace.
        
        Synchronizes template data to Producteca, creating connection if needed.
        This is called when pushing a product FROM Odoo TO Producteca.
        
        Args:
            account (producteca.account): Account for API calls
            producteca_body (dict): Product data to send
            
        Returns:
            bool: True if successful
        """
        client = account.get_client()
        product_service = client.Product
        product_service.create_if_it_doesnt_exist = account.create_if_dosnt_exist
        
        product_response = product_service.synchronize(producteca_body)
        
        if hasattr(product_response, 'to_dict'):
            product_dict = product_response.to_dict()
        elif isinstance(product_response, dict):
            product_dict = product_response
        else:
            _logger.error(f"Unexpected product_response type: {type(product_response)}")
            return False
        
        if product_dict:
            self._handle_producteca_connection_ids(product_dict, self, account)
        
        return True

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
            
            all_warehouses = account.warehouse_ids | account.default_warehouse_id
            stock_by_warehouse = self.env['stock.quant'].search([
                ('product_id', '=', variant.id), 
                ('location_id.usage', '=', 'internal'), 
                ('warehouse_id', 'in', all_warehouses.ids)
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
        
        
        if template.product_tag_ids:
            product_data["tags"] = [tag.name for tag in template.product_tag_ids]
        
        
        if template.weight:
            product_data["dimensions"] = {
                "weight": template.weight if template.weight else 0,
            }
        
        
        variations = []
        for variant in template.product_variant_ids:
            variation_dict = {
                "sku": variant.default_code,
                "barcode": variant.barcode or None,
            }
            
            
            if variant.product_template_variant_value_ids:
                variation_dict["attributes"] = [
                    {"key": variant_value.attribute_id.name, "value": variant_value.name}
                    for variant_value in variant.product_template_variant_value_ids
                ]
            
            
            variant_stocks = [s for s in stocks_data if s['sku'] == variant.default_code]
            if variant_stocks and variant_stocks[0]['stocks']:
                variation_dict["stocks"] = [
                    {
                        "quantity": stock.quantity,
                        "availableQuantity": stock.available_quantity,
                        "warehouse": stock.warehouse_id._get_producteca_warehouse_name(account) if stock.warehouse_id else None
                    } for stock in variant_stocks[0]['stocks']
                ]
            if variation_dict.get("stocks") and variation_dict["stocks"][-1].get('warehouse') is None:
                continue
            
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
            processed = 0
            
            while processed < total_products:
                for result in products_response.results:
                    product_id = result.id
                    _logger.info(f"Processing product ID: {product_id}")
                    if not product_id:
                        continue
                    
                    self.with_delay().get_product_from_producteca_and_create(account, product_id)
                
                processed += len(products_response.results)
                
                if processed >= total_products or len(products_response.results) == 0:
                    break
                
                params.skip = processed
                    
        return True
