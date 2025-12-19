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



    def _get_or_create_product_attribute(self, attribute_key):
        """Get or create a product.attribute for a Producteca attribute key.
        
        Normalizes attribute name to title case to avoid duplicates.
        Always searches for or creates attributes with create_variant='dynamic'.
        Will NOT reuse attributes with create_variant='always'.
        
        Args:
            attribute_key (str): Attribute name from Producteca
            
        Returns:
            product.attribute: Attribute record
        """
        normalized_key = attribute_key.strip().title() if attribute_key else ''
        if not normalized_key:
            return None
        
        attribute = self.env['product.attribute'].sudo().search([
            ('name', '=', normalized_key),
            ('create_variant', '=', 'dynamic')
        ], limit=1)
        
        if not attribute:
            attribute = self.env['product.attribute'].sudo().create({
                'name': normalized_key,
                'create_variant': 'dynamic'
            })
        
        return attribute

    def _get_or_create_attribute_value(self, attribute, value_name):
        """Get or create a product.attribute.value for a Producteca attribute value.
        
        Args:
            attribute (product.attribute): Attribute record
            value_name (str): Value name from Producteca
            
        Returns:
            product.attribute.value: Attribute value record or None if invalid
        """
        if not attribute or not value_name:
            return None
        
        normalized_value = str(value_name).strip()
        if not normalized_value:
            return None
        
        attr_value = self.env['product.attribute.value'].sudo().search([
            ('attribute_id', '=', attribute.id),
            ('name', '=', normalized_value)
        ], limit=1)
        
        if not attr_value:
            attr_value = self.env['product.attribute.value'].sudo().create({
                'attribute_id': attribute.id,
                'name': normalized_value
            })
        
        return attr_value

    def _prepare_template_attribute_lines(self, variations):
        """Prepare attribute lines for template from Producteca variations.
        
        Analyzes all variations to extract unique attributes and their values.
        Skips attributes with empty keys or values.
        
        Args:
            variations (list): List of Producteca variations
            
        Returns:
            list: Command list for attribute_line_ids
        """
        if not variations:
            return []
        
        attributes_dict = {}
        
        for variation in variations:
            if not variation.get('attributes'):
                continue
                
            for attr in variation['attributes']:
                key = attr.get('key', '').strip()
                value = attr.get('value', '').strip() if attr.get('value') else ''
                
                # Skip attributes with empty key or value
                if not key or not value:
                    continue
                
                # Normalize key to title case
                normalized_key = key.title()
                
                if normalized_key not in attributes_dict:
                    attributes_dict[normalized_key] = set()
                attributes_dict[normalized_key].add(value)
        
        if not attributes_dict:
            return []
        
        attribute_lines = []
        for attr_key, attr_values in attributes_dict.items():
            attribute = self._get_or_create_product_attribute(attr_key)
            if not attribute:
                continue
            
            value_ids = []
            for value_name in attr_values:
                attr_value = self._get_or_create_attribute_value(attribute, value_name)
                if attr_value:
                    value_ids.append(attr_value.id)
            
            if value_ids:
                attribute_lines.append(Command.create({
                    'attribute_id': attribute.id,
                    'value_ids': [Command.set(value_ids)]
                }))
        
        return attribute_lines

    def _get_variant_attribute_values(self, template, variation):
        """Get product.template.attribute.value IDs for a variation.
        
        Args:
            template (product.template): Template to search PTAVs from
            variation (dict): Producteca variation data
            
        Returns:
            list: IDs of product.template.attribute.value records
        """
        if not variation.get('attributes'):
            return []
        
        value_ids = []
        for attr in variation['attributes']:
            key = attr.get('key', '').strip()
            value = attr.get('value', '').strip() if attr.get('value') else ''
            
            if not key or not value:
                continue
            
            attribute = self._get_or_create_product_attribute(key)
            if not attribute:
                continue
                
            attr_value = self._get_or_create_attribute_value(attribute, value)
            if not attr_value:
                continue
            
            ptav = template.attribute_line_ids.product_template_value_ids.filtered(
                lambda p: p.attribute_id == attribute and p.product_attribute_value_id == attr_value
            )
            
            if ptav:
                value_ids.append(ptav.id)
        
        return value_ids

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
        
        CRITICAL: This ALWAYS creates/updates connections regardless of account permissions,
        because connections are ESSENTIAL for all Producteca processes (orders, shipments, stock, etc.).
        Even if variation_id is not known yet, the connection is created and can be updated later.
        
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
            else:
                vals.update({
                    'product_id': variant.id,
                    'producteca_account_id': account.id,
                })
                self.env['producteca.product.connections'].sudo().create(vals)

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
        vals = {
            'is_producteca_product': True,
        }
        
        if account.is_producteca_able_to_modified_products or not odoo_template:
            vals.update({
                'is_producteca_product': True,
                'is_already_sync': True,
            })
            
            if producteca_response.get('notes'):
                if not odoo_template or odoo_template.description != producteca_response.get('notes'):
                    vals['description'] = producteca_response.get('notes')
            
            if not odoo_template:
                name = producteca_response.get('name', False)
                if not name:
                    raise Exception("El producto de Producteca no tiene nombre asignado. Por favor, verifique en Producteca.")
                vals['name'] = name
                vals['type'] = 'consu'
                vals['is_storable'] = True
                
                if producteca_response.get('variations'):
                    attribute_lines = self._prepare_template_attribute_lines(producteca_response['variations'])
                    if attribute_lines:
                        vals['attribute_line_ids'] = attribute_lines
            
            if producteca_response.get('product_price', False):
                if account.is_product_price_modified_by_producteca:
                    price = float(producteca_response.get('product_price'))
                    if not odoo_template or odoo_template.list_price != price:
                        vals['list_price'] = price
            
            if producteca_response.get('brand'):
                brand = self.env['product.brand'].sudo().search([('name', '=', producteca_response.get('brand'))], limit=1)
                if not brand:
                    brand = self.env['product.brand'].sudo().create({'name': producteca_response.get('brand')})
                
                if not odoo_template or odoo_template.product_brand_id != brand:
                    vals['product_brand_id'] = brand.id
            
            if producteca_response.get('tags'):
                vals['product_tag_ids'] = self._handle_producteca_tags_dict(producteca_response)

            dimensions = producteca_response.get('dimensions', {})
            if dimensions and dimensions.get('weight'):
                weight = dimensions.get('weight')
                if not odoo_template or odoo_template.weight != weight:
                    vals['weight'] = weight
        
        return vals

    def _update_or_create_variants_from_producteca(self, template, variations, account):
        """Update or create variants from Producteca variations.
        
        ALWAYS ensures at least one variant has a SKU assigned.
        For products with attributes, creates variants with specific combinations.
        For products without attributes, assigns SKU to the default variant.
        
        Args:
            template (product.template): Template to update variants for
            variations (list): List of Producteca variations
            account (producteca.account): Account configuration
        """
        if not variations:
            return
        
        valid_variations = [v for v in variations if v.get('sku') and v.get('sku') != 'null']
        if not valid_variations:
            return
        
        has_single_variation = len(valid_variations) == 1
        
        if not has_single_variation and not account.is_producteca_able_to_create_products and not account.is_producteca_able_to_modified_products:
            return
        
        for variation in valid_variations:
            sku = variation.get('sku')
            
            existing_variant = template.product_variant_ids.filtered(lambda v: v.default_code == sku)
            if existing_variant:
                if has_single_variation or account.is_producteca_able_to_modified_products:
                    existing_variant[0].sudo().write({'default_code': sku})
                continue
            
            ptav_ids = self._get_variant_attribute_values(template, variation)
            
            if ptav_ids:
                variant = template.product_variant_ids.filtered(
                    lambda v: set(v.product_template_variant_value_ids.ids) == set(ptav_ids)
                )
                if variant:
                    if has_single_variation or account.is_producteca_able_to_modified_products:
                        variant[0].sudo().write({'default_code': sku})
                elif account.is_producteca_able_to_create_products:
                    new_variant = self.env['product.product'].sudo().create({
                        'product_tmpl_id': template.id,
                        'product_template_attribute_value_ids': [Command.set(ptav_ids)],
                        'default_code': sku,
                    })
            else:
                default_variant = template.product_variant_ids[:1]
                if default_variant and (has_single_variation or account.is_producteca_able_to_modified_products):
                    default_variant.sudo().write({'default_code': sku})
    
    def _update_variant_from_variation(self, variant, variation_data):
        """Update a single variant with data from Producteca variation.
        
        Args:
            variant (product.product): Variant to update
            variation_data (dict): Producteca variation data
        """
        if variation_data.get('sku'):
            variant.sudo().write({'default_code': variation_data['sku']})

    def _find_or_create_variant_by_sku(self, template, sku, variation_data, account):
        """Find existing variant by SKU or create new one.
        
        Args:
            template (product.template): Template to create variant for
            sku (str): SKU to search/assign
            variation_data (dict): Producteca variation data
            account (producteca.account): Account configuration for permissions
            
        Returns:
            product.product: Found or created variant, or None if no permissions
        """
        if not sku or sku == 'null':
            return None
        
        existing_variant = template.product_variant_ids.filtered(lambda v: v.default_code == sku)
        
        if existing_variant:
            return existing_variant[0]
        
        if not account.is_producteca_able_to_create_products:
            return None
        
        new_variant = self.env['product.product'].sudo().create({
            'product_tmpl_id': template.id,
            'default_code': sku,
        })
        return new_variant

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
            template = self.env['product.template'].sudo().create(template_vals)
            template.flush_recordset()
            template.invalidate_recordset()
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
        
        self._update_connection_variants(odoo_template, account, producteca_body.get('id'), producteca_body)
        
        return template_write

    def get_product_from_producteca_and_create(self, account, producteca_id):
        """Fetch product from Producteca API and create/update in Odoo.
        
        Checks if product already exists BEFORE calling API to avoid duplicates.
        
        Args:
            account (producteca.account): Account to use for API calls
            producteca_id (str): Producteca product ID to fetch
        """
        connection = self.env['producteca.product.connections'].sudo().search([
            ('producteca_id', '=', str(producteca_id)), 
            ('producteca_account_id', '=', account.id)
        ], limit=1)
        
        if connection and connection.product_tmpl_id:
            client = account.get_client()
            product_service = client.Product
            product_service.create_if_it_doesnt_exist = account.create_if_dosnt_exist
            product = product_service.get(producteca_id)
            product_dict = product.to_dict()
            self._update_product_from_producteca(account, product_dict, connection.product_tmpl_id)
            return
        
        client = account.get_client()
        product_service = client.Product
        product_service.create_if_it_doesnt_exist = account.create_if_dosnt_exist
        product = product_service.get(producteca_id)
        product_dict = product.to_dict()
        
        if product_dict.get('variations'):
            for variation in product_dict['variations']:
                sku = variation.get('sku')
                if sku and sku != 'null':
                    existing_variant = self.env['product.product'].sudo().search([
                        ('default_code', '=', sku)
                    ], limit=1)
                    if existing_variant and existing_variant.product_tmpl_id:
                        self._update_product_from_producteca(account, product_dict, existing_variant.product_tmpl_id)
                        return
        
        self._create_product_from_producteca(account, product_dict)

    def _update_product_price_from_sale_line(self, product, line, account):
        if not account.is_product_price_modified_by_producteca:
            return
        
        unit_price = line.get('price', 0) / line.get('quantity', 1)
        if product.taxes_id:
            tax_id = product.taxes_id[0]
            unit_price = unit_price / (1 + (tax_id.amount/100))
        product.lst_price = unit_price

    def get_or_create_product_from_sale_line(self, line, account):
        product_data = line.get('product', {})
        variation_data = line.get('variation', {})
        
        producteca_id = product_data.get('id')
        variation_id = variation_data.get('id')
        sku = line.get('sku') or variation_data.get('sku')
        
        connection = self.env['producteca.product.connections'].sudo().search([
            ('producteca_variation_id', '=', str(variation_id)),
            ('producteca_account_id', '=', account.id)
        ], limit=1)
        
        if connection:
            product = connection.product_id
            self._update_product_price_from_sale_line(product, line, account)
            return product
        
        template_connection = self.env['producteca.product.connections'].sudo().search([
            ('producteca_id', '=', str(producteca_id)),
            ('producteca_account_id', '=', account.id)
        ], limit=1)
        
        if template_connection:
            variant = template_connection.product_tmpl_id.product_variant_ids.filtered(
                lambda v: v.default_code == sku
            )
            if variant:
                product = variant
                self._update_product_price_from_sale_line(product, line, account)
                return product
            
            if not account.is_producteca_able_to_create_products:
                raise Exception(
                    f"No se pudo procesar la orden porque el producto con SKU '{sku}' no existe "
                    f"y la cuenta de Producteca no permite la creación de productos."
                )
            
            self.get_product_from_producteca_and_create(account, producteca_id)
            
            variant = template_connection.product_tmpl_id.product_variant_ids.filtered(
                lambda v: v.default_code == sku
            )
            if not variant:
                raise Exception(
                    f"No se pudo encontrar la variante con SKU '{sku}' después de sincronizar. "
                    f"Producteca ID: {producteca_id}, Variation ID: {variation_id}"
                )
            
            product = variant
            self._update_product_price_from_sale_line(product, line, account)
            return product
        
        variant_by_sku = self.env['product.product'].search([('default_code', '=', sku)], limit=1)
        
        if variant_by_sku:
            self.get_product_from_producteca_and_create(account, producteca_id)
            
            product = variant_by_sku
            self._update_product_price_from_sale_line(product, line, account)
            return product
        
        if not account.is_producteca_able_to_create_products:
            raise Exception(
                f"No se pudo procesar la orden porque el producto con SKU '{sku}' no existe en Odoo "
                f"y la cuenta de Producteca no permite la creación de productos."
            )
        
        self.get_product_from_producteca_and_create(account, producteca_id)
        
        connection = self.env['producteca.product.connections'].sudo().search([
            ('producteca_variation_id', '=', str(variation_id)),
            ('producteca_account_id', '=', account.id)
        ], limit=1)
        
        if not connection:
            raise Exception(
                f"No se pudo encontrar la variante después de crearla. "
                f"Producteca ID: {producteca_id}, Variation ID: {variation_id}, SKU: {sku}"
            )
        
        product = connection.product_id
        self._update_product_price_from_sale_line(product, line, account)
        return product

    def _create_product_in_producteca(self, account, producteca_body):
        """Create or update product in Producteca marketplace.
        
        Synchronizes template data to Producteca, creating connection if needed.
        This is called when pushing a product FROM Odoo TO Producteca.
        
        Args:
            account (producteca.account): Account for API calls
            producteca_body (dict): Product data to send (already prepared, single variation or simple product)
            
        Returns:
            bool: True if successful
        """
        client = account.get_client()
        product_service = client.Product
        product_service.create_if_it_doesnt_exist = account.create_if_dosnt_exist
        
        product_response = product_service.synchronize(producteca_body)
        
        product_dict = None
        if hasattr(product_response, 'model_dump'):
            product_dict = product_response.model_dump(by_alias=True, exclude_none=True)
        elif hasattr(product_response, 'to_dict'):
            product_dict = product_response.to_dict()
        elif isinstance(product_response, dict):
            product_dict = product_response
        else:
            _logger.error(f"Unexpected product_response type: {type(product_response)}")
            return False
        
        if product_dict:
            template_id = int(producteca_body.get('code'))
            template = self.env['product.template'].sudo().browse(template_id)
            if template.exists():
                self._handle_producteca_connection_ids(product_dict, template, account)
        
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
        
        image_array = []
        if template.product_variant_ids:
            for variant in template.product_variant_ids:
                image_array.append({
                    "url": f"{self.env['ir.config_parameter'].sudo().get_param('web.base.url')}/producteca/image/variant/{variant.id}"
                })
        else:
            image_product = template
            image_array.append({
                "url": f"{self.env['ir.config_parameter'].sudo().get_param('web.base.url')}/producteca/image/{image_product.id}"
            })
        deals = None
        
        product_data = {
            "code": str(template.id),
            "name": template.name,
            "category": template.categ_id.complete_name if template.categ_id else None,
            "brand": template.product_brand_id.name if template.product_brand_id else None,
            "notes": template.description if template.description else None,
        }

        if image_array:
            product_data["pictures"] = image_array
        
        
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
                variation_dict["stocks"] = []
                for stock in variant_stocks[0]['stocks']:
                    warehouse_name = stock.warehouse_id._get_producteca_warehouse_name(account) if stock.warehouse_id else None
                    stock_dict = {"warehouse": warehouse_name}
                    stock_dict["quantity"] = stock.quantity
                    variation_dict["stocks"].append(stock_dict)
            
            if variation_dict.get("stocks") and variation_dict["stocks"][-1].get('warehouse') is None:
                continue
            
            variations.append(variation_dict)
        
        if variations:
            product_data["variations"] = variations
        else:
            if template.default_code:
                product_data["sku"] = template.default_code
        
        # if deals:
        #     product_data["deals"] = deals
        if pricelists:
            product_data["prices"] = pricelists
            
        return {k: v for k, v in product_data.items() if v is not None}

    def _prepare_variation_payload(self, variation, product_dict):
        """Prepare the payload for a single product variation.
        
        Args:
            variation: Dictionary with variation data from product_dict['variations']
            product_dict: Base product data dictionary
            
        Returns:
            Dictionary ready to send to Producteca API
        """
        variation_payload = {
            'sku': variation.get('sku'),
            'code': product_dict.get('code'),
            'barcode': variation.get('barcode'),
            'name': product_dict.get('name'),
            'category': product_dict.get('category'),
            'brand': product_dict.get('brand'),
            'notes': product_dict.get('notes'),
            'variationAttributes': variation.get('attributes', []),
            'stocks': variation.get('stocks', []),
            'prices': product_dict.get('prices', []),
            'pictures': product_dict.get('pictures', []),
            'dimensions': product_dict.get('dimensions'),
            'tags': product_dict.get('tags'),
        }
        return {k: v for k, v in variation_payload.items() if v is not None and v != []}

    def create_product_in_producteca_queue(self):
        """Queue product template synchronization to Producteca.
        
        Creates background jobs to sync all unsynchronized templates to Producteca.
        For products with variations, queues each variation separately.
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
            if template.attribute_line_ids and not template.product_variant_ids:
                template._create_variant_ids()
            
            for account in producteca_account_ids:
                if not account.create_if_dosnt_exist:
                    continue
                    
                product_dict = self._prepare_producteca_product_dict(template, account)
                
                if product_dict.get('variations'):
                    for variation in product_dict['variations']:
                        variation_payload = self._prepare_variation_payload(variation, product_dict)
                        self.with_delay()._create_product_in_producteca(account, variation_payload)
                else:
                    self.with_delay()._create_product_in_producteca(account, product_dict)
                
                template.write({'is_already_sync': True})
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
                batch_size = len(products_response.results)
                
                for result in products_response.results:
                    product_id = result.id
                    if not product_id:
                        continue
                    
                    self.with_delay().get_product_from_producteca_and_create(account, product_id)
                
                processed += batch_size
                
                if processed >= total_products or batch_size == 0:
                    break
                
                params.skip = processed
                products_response = client.Product.search(params=params)
                    
        return True

    def write(self, vals):
        list_price_changed = 'list_price' in vals
        
        templates_to_sync = []
        if list_price_changed:
            for template in self:
                if template.producteca_connection_ids:
                    templates_to_sync.append(template.id)
        
        result = super(ProductTemplate, self).write(vals)
        
        if list_price_changed and templates_to_sync:
            self._trigger_list_price_sync(templates_to_sync)
        
        return result

    def _trigger_list_price_sync(self, template_ids):
        ProductPricelist = self.env['product.pricelist']
        
        for template_id in template_ids:
            template = self.browse(template_id)
            
            _logger.info(
                f"Disparando sincronización de precios para template '{template.name}' "
                f"debido a cambio en list_price"
            )
            
            for variant in template.product_variant_ids:
                if variant.producteca_connection_ids:
                    ProductPricelist._sync_product_price_on_change(variant.id)
