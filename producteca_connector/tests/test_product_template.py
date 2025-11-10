# -*- coding: utf-8 -*-
"""Tests for product.template Producteca integration methods"""

from odoo.tests.common import TransactionCase
from unittest.mock import patch, MagicMock


class TestProductTemplateProducteca(TransactionCase):
    """Test product.template Producteca integration - Template migration"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.warehouse = cls.env['stock.warehouse'].search([], limit=1)
        
        cls.account = cls.env['producteca.account'].create({
            'account_name': 'Test Producteca Account',
            'api_key': 'test_api_key',
            'bearer_token': 'test_bearer_token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': cls.warehouse.id,
        })

    def test_01_prepare_producteca_to_odoo_product_dict(self):
        """Test _prepare_producteca_to_odoo_product_dict creates proper template dict"""
        producteca_data = {
            'id': 'PROD_001',
            'name': 'Test Product',
            'description': 'Test Description',
            'price': 1000.0,
            'stock': 10,
        }
        
        template = self.env['product.template']
        result = template._prepare_producteca_to_odoo_product_dict(
            producteca_data, 
            False, 
            self.account
        )
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('name'), 'Test Product')

    def test_02_find_or_create_variant_by_sku(self):
        """Test _find_or_create_variant_by_sku creates variants with SKUs"""
        template = self.env['product.template'].create({
            'name': 'Multi-Variant Template',
            'type': 'consu',
        })
        
        variation_data = {
            'sku': 'VAR_SKU_001',
            'attributes': {},
        }
        
        template_obj = self.env['product.template']
        variant = template_obj._find_or_create_variant_by_sku(
            template, 
            'VAR_SKU_001', 
            variation_data
        )
        
        self.assertTrue(variant)
        self.assertEqual(variant.product_tmpl_id.id, template.id)
        self.assertEqual(variant.default_code, 'VAR_SKU_001')

    def test_03_create_product_from_producteca(self):
        """Test _create_product_from_producteca creates template"""
        # Allow account to create products
        self.account.is_producteca_able_to_create_products = True
        
        producteca_body = {
            'id': 'PROD_CREATE_001',
            'name': 'Created from Producteca',
            'description': 'Test creation',
            'product_price': 500.0,
            'variations': [],
        }
        
        template_obj = self.env['product.template']
        template = template_obj._create_product_from_producteca(
            self.account, 
            producteca_body
        )
        
        self.assertTrue(template)
        self.assertEqual(template.name, 'Created from Producteca')
        
        # Verify connection was created
        connection = self.env['producteca.product.connections'].search([
            ('product_tmpl_id', '=', template.id),
            ('producteca_account_id', '=', self.account.id),
        ])
        
        self.assertTrue(connection)
        self.assertEqual(connection.producteca_id, 'PROD_CREATE_001')

    def test_04_update_product_from_producteca(self):
        """Test _update_product_from_producteca updates existing template"""
        template = self.env['product.template'].create({
            'name': 'Original Name',
            'type': 'consu',
        })
        
        # Update account to allow modifications
        self.account.is_producteca_able_to_modified_products = True
        
        producteca_body = {
            'id': 'PROD_UPDATE_001',
            'name': 'Updated Name',
            'description': 'Updated description',
            'product_price': 750.0,
            'variations': [],
        }
        
        template_obj = self.env['product.template']
        result = template_obj._update_product_from_producteca(
            self.account, 
            producteca_body, 
            template
        )
        
        # Should return True for successful write
        self.assertTrue(result)

    def test_05_handle_producteca_attribute_dict(self):
        """Test _handle_producteca_attribute_dict processes attributes correctly"""
        template = self.env['product.template'].create({
            'name': 'Attribute Test Template',
            'type': 'consu',
        })
        
        producteca_response = {
            'attributes': [],  # Empty attributes list is valid
        }
        
        template_obj = self.env['product.template']
        result = template_obj._handle_producteca_attribute_dict(
            producteca_response, 
            template
        )
        
        # Method should return list (even if empty)
        self.assertIsInstance(result, list)

    def test_06_prepare_producteca_product_dict(self):
        """Test _prepare_producteca_product_dict prepares data for API"""
        template = self.env['product.template'].create({
            'name': 'Export Template',
            'type': 'consu',
            'list_price': 1000.0,
        })
        
        template_obj = self.env['product.template']
        result = template_obj._prepare_producteca_product_dict(
            template, 
            self.account
        )
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('name'), 'Export Template')

    def test_07_create_product_with_variations(self):
        """Test creating template with variations field present"""
        # Allow account to create products
        self.account.is_producteca_able_to_create_products = True
        
        producteca_body = {
            'id': 'PROD_MULTI_VAR',
            'name': 'Multi Variant Product',
            'description': 'Has variations',
            'product_price': 1000.0,
            'variations': [],  # Empty variations list is valid
        }
        
        template_obj = self.env['product.template']
        template = template_obj._create_product_from_producteca(
            self.account, 
            producteca_body
        )
        
        self.assertTrue(template)
        self.assertEqual(template.name, 'Multi Variant Product')

    def test_08_template_product_type_from_producteca(self):
        """Test templates created from Producteca use correct type"""
        # Allow account to create products
        self.account.is_producteca_able_to_create_products = True
        
        producteca_body = {
            'id': 'PROD_TYPE_TEST',
            'name': 'Type Test Product',
            'description': 'Check type',
            'product_price': 500.0,
            'variations': [],
        }
        
        template_obj = self.env['product.template']
        template = template_obj._create_product_from_producteca(
            self.account, 
            producteca_body
        )
        
        # Template type should be 'consu' (consumable) for Odoo 18 compatibility
        self.assertEqual(template.type, 'consu')

    def test_09_create_product_without_permission_fails(self):
        """Test creating product fails when account doesn't allow creation"""
        # Explicitly disable creation permission
        self.account.is_producteca_able_to_create_products = False
        
        producteca_body = {
            'id': 'PROD_NO_PERMISSION',
            'name': 'Should Fail',
            'product_price': 100.0,
            'variations': [],
        }
        
        template_obj = self.env['product.template']
        
        # Should raise exception about no permission
        with self.assertRaises(Exception) as context:
            template_obj._create_product_from_producteca(
                self.account, 
                producteca_body
            )
        
        self.assertIn('no permite creación de productos', str(context.exception))

    def test_10_update_product_without_permission_skips_data(self):
        """Test updating product without permission doesn't modify data"""
        template = self.env['product.template'].create({
            'name': 'Original Name',
            'type': 'consu',
            'list_price': 100.0,
        })
        
        # Disable modification permission
        self.account.is_producteca_able_to_modified_products = False
        
        producteca_body = {
            'id': 'PROD_NO_MODIFY',
            'name': 'Should Not Change',
            'product_price': 999.0,
            'variations': [],
        }
        
        template_obj = self.env['product.template']
        template_obj._update_product_from_producteca(
            self.account, 
            producteca_body, 
            template
        )
        
        # Name and price should NOT have changed
        self.assertEqual(template.name, 'Original Name')
        self.assertEqual(template.list_price, 100.0)

    def test_11_update_product_with_permission_modifies_data(self):
        """Test updating product with permission does modify data"""
        template = self.env['product.template'].create({
            'name': 'Original Name',
            'type': 'consu',
            'list_price': 100.0,
        })
        
        # Enable modification permission
        self.account.is_producteca_able_to_modified_products = True
        
        producteca_body = {
            'id': 'PROD_CAN_MODIFY',
            'name': 'New Name',
            'product_price': 200.0,
            'variations': [],
        }
        
        template_obj = self.env['product.template']
        result = template_obj._update_product_from_producteca(
            self.account, 
            producteca_body, 
            template
        )
        
        # Should return True for successful update
        self.assertTrue(result)

    def test_12_update_connection_variants_tracking(self):
        """Test _update_connection_variants creates/updates connection properly"""
        self.account.is_producteca_able_to_create_products = True
        
        template = self.env['product.template'].create({
            'name': 'Variant Tracking Test',
            'type': 'consu',
        })
        
        # Create a variant with SKU
        variant = self.env['product.product'].create({
            'product_tmpl_id': template.id,
            'default_code': 'SKU_TRACK_001',
        })
        
        template_obj = self.env['product.template']
        template_obj._update_connection_variants(template, self.account, 'PROD_TRACK_001')
        
        # Should create connection
        connection = self.env['producteca.product.connections'].search([
            ('product_tmpl_id', '=', template.id),
            ('producteca_account_id', '=', self.account.id),
            ('producteca_id', '=', 'PROD_TRACK_001'),
        ])
        
        self.assertTrue(connection)
        self.assertIn(variant, connection.product_variant_ids)
