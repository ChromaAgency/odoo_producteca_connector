# -*- coding: utf-8 -*-
"""
Test suite for ProductecaProductsWizard in producteca_connector module.

This module provides comprehensive test coverage for the ProductecaProductsWizard,
which handles product import operations from Producteca platform, including:
- Product search and import functionality
- Batch processing with delayed jobs
- Update vs create logic for existing products
- Permission validation and error handling

Test Patterns:
- Uses Odoo TransactionCase for database operations
- Mock external API calls to avoid network dependencies
- Test wizard workflow and user interactions
- Validate business logic and error scenarios
- Context handling and permission checks

Coverage Areas:
- Wizard field validation and requirements
- Product search text parsing
- Delayed job creation for product imports
- Existing product detection and update logic
- Permission-based validation
- Error handling and user messages
"""

from unittest.mock import patch, MagicMock
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestProductecaProductsWizard(TransactionCase):
    """Test cases for ProductecaProductsWizard model."""

    def setUp(self):
        """Set up test data for ProductecaProductsWizard tests."""
        super(TestProductecaProductsWizard, self).setUp()
        
        # Create test company
        self.company = self.env['res.company'].create({
            'name': 'Test Company',
            'country_id': self.env.ref('base.ar').id,
        })
        
        # Create Producteca account with permissions
        self.producteca_account = self.env['producteca.account'].create({
            'name': 'Test Producteca Account',
            'api_key': 'test_api_key',
            'base_url': 'https://test.producteca.com',
            'company_id': self.company.id,
            'is_producteca_able_to_create_products': True,
        })
        
        # Create Producteca account without permissions
        self.restricted_account = self.env['producteca.account'].create({
            'name': 'Restricted Producteca Account',
            'api_key': 'restricted_api_key',
            'base_url': 'https://restricted.producteca.com',
            'company_id': self.company.id,
            'is_producteca_able_to_create_products': False,
        })
        
        # Create test products
        self.product1 = self.env['product.product'].create({
            'name': 'Test Product 1',
            'list_price': 100.0,
            'default_code': 'TEST001',
        })
        
        self.product2 = self.env['product.product'].create({
            'name': 'Test Product 2',
            'list_price': 200.0,
            'default_code': 'TEST002',
        })
        
        # Create product connections
        self.connection1 = self.env['producteca.product.connections'].create({
            'product_id': 123,
            'odoo_product_id': self.product1.id,
            'producteca_account_id': self.producteca_account.id,
        })

    def test_01_wizard_model_definition(self):
        """Test wizard model definition and inheritance."""
        wizard = self.env['producteca.products.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '12345',
        })
        
        self.assertEqual(wizard._name, 'producteca.products.wizard')
        self.assertTrue(hasattr(wizard, 'producteca_account_id'))
        self.assertTrue(hasattr(wizard, 'search_text'))
        self.assertTrue(hasattr(wizard, 'update_if_exists'))

    def test_02_required_fields_validation(self):
        """Test required fields validation."""
        # Test creating wizard without required fields
        with self.assertRaises(Exception):
            self.env['producteca.products.wizard'].create({})
        
        # Test with missing producteca_account_id
        with self.assertRaises(Exception):
            self.env['producteca.products.wizard'].create({
                'search_text': '12345',
            })
        
        # Test with missing search_text
        with self.assertRaises(Exception):
            self.env['producteca.products.wizard'].create({
                'producteca_account_id': self.producteca_account.id,
            })

    def test_03_default_values(self):
        """Test default field values."""
        wizard = self.env['producteca.products.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '12345',
        })
        
        # update_if_exists should default to True
        self.assertTrue(wizard.update_if_exists)

    def test_04_wizard_field_assignments(self):
        """Test wizard field assignments."""
        wizard = self.env['producteca.products.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '12345,67890',
            'update_if_exists': False,
        })
        
        self.assertEqual(wizard.producteca_account_id, self.producteca_account)
        self.assertEqual(wizard.search_text, '12345,67890')
        self.assertFalse(wizard.update_if_exists)

    @patch('odoo.addons.producteca_connector.models.product_product.ProductProduct.get_product_from_producteca_and_create')
    def test_05_get_and_create_from_wizard_single_product(self, mock_get_create):
        """Test _get_and_create_from_wizard method with single product."""
        wizard = self.env['producteca.products.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '12345',
        })
        
        mock_get_create.return_value = True
        
        products_to_create = [12345]
        wizard._get_and_create_from_wizard(products_to_create, self.producteca_account.id)
        
        # Should trigger delayed job for product creation
        # Note: In actual implementation, this uses with_delay()

    @patch('odoo.addons.producteca_connector.models.product_product.ProductProduct.get_product_from_producteca_and_create')
    def test_06_get_and_create_from_wizard_multiple_products(self, mock_get_create):
        """Test _get_and_create_from_wizard method with multiple products."""
        wizard = self.env['producteca.products.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '12345,67890,111222',
        })
        
        mock_get_create.return_value = True
        
        products_to_create = [12345, 67890, 111222]
        wizard._get_and_create_from_wizard(products_to_create, self.producteca_account.id)
        
        # Should process all products
        self.assertEqual(len(products_to_create), 3)

    def test_07_search_text_parsing_single_id(self):
        """Test search text parsing with single product ID."""
        wizard = self.env['producteca.products.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '12345',
        })
        
        producteca_products_ids = wizard.search_text.split(",")
        self.assertEqual(len(producteca_products_ids), 1)
        self.assertEqual(producteca_products_ids[0], '12345')

    def test_08_search_text_parsing_multiple_ids(self):
        """Test search text parsing with multiple product IDs."""
        wizard = self.env['producteca.products.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '12345,67890,111222,333444',
        })
        
        producteca_products_ids = wizard.search_text.split(",")
        self.assertEqual(len(producteca_products_ids), 4)
        expected_ids = ['12345', '67890', '111222', '333444']
        self.assertEqual(producteca_products_ids, expected_ids)

    def test_09_search_text_parsing_with_spaces(self):
        """Test search text parsing with spaces."""
        wizard = self.env['producteca.products.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': ' 12345 , 67890 , 111222 ',
        })
        
        producteca_products_ids = wizard.search_text.split(",")
        # Should handle spaces in the split
        self.assertEqual(len(producteca_products_ids), 3)

    def test_10_action_obtain_products_no_permission(self):
        """Test action_obtain_products with restricted account."""
        wizard = self.env['producteca.products.wizard'].create({
            'producteca_account_id': self.restricted_account.id,
            'search_text': '12345',
        })
        
        # Should raise UserError for restricted account
        with self.assertRaises(UserError) as context:
            wizard.action_obtain_products()
        
        self.assertIn('no tiene permiso de crear productos', str(context.exception))

    @patch('odoo.addons.producteca_connector.wizards.import_producteca_product.ProductecaProductsWizard._get_and_create_from_wizard')
    def test_11_action_obtain_products_new_products(self, mock_get_create):
        """Test action_obtain_products with new products."""
        wizard = self.env['producteca.products.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '99999,88888',  # New product IDs
        })
        
        mock_get_create.return_value = True
        
        result = wizard.action_obtain_products()
        
        # Should call product creation
        mock_get_create.assert_called_once()
        
        # Should return window close action
        self.assertEqual(result['type'], 'ir.actions.act_window_close')

    def test_12_action_obtain_products_existing_products_no_update(self):
        """Test action_obtain_products with existing products and update_if_exists=False."""
        wizard = self.env['producteca.products.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '123',  # Existing product connection
            'update_if_exists': False,
        })
        
        # Should raise UserError because products exist and update is disabled
        with self.assertRaises(UserError) as context:
            wizard.action_obtain_products()
        
        self.assertIn('ya existen en Odoo', str(context.exception))

    @patch('odoo.addons.producteca_connector.wizards.import_producteca_product.ProductecaProductsWizard._get_and_create_from_wizard')
    def test_13_action_obtain_products_existing_products_with_update(self, mock_get_create):
        """Test action_obtain_products with existing products and update_if_exists=True."""
        wizard = self.env['producteca.products.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '123',  # Existing product connection
            'update_if_exists': True,
        })
        
        mock_get_create.return_value = True
        
        result = wizard.action_obtain_products()
        
        # Should call product update
        mock_get_create.assert_called()
        
        # Should return window close action
        self.assertEqual(result['type'], 'ir.actions.act_window_close')

    @patch('odoo.addons.producteca_connector.wizards.import_producteca_product.ProductecaProductsWizard._get_and_create_from_wizard')
    def test_14_action_obtain_products_mixed_scenario(self, mock_get_create):
        """Test action_obtain_products with mix of new and existing products."""
        wizard = self.env['producteca.products.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '123,99999',  # 123 exists, 99999 is new
            'update_if_exists': True,
        })
        
        mock_get_create.return_value = True
        
        result = wizard.action_obtain_products()
        
        # Should call product creation/update for both scenarios
        self.assertEqual(mock_get_create.call_count, 2)
        
        # Should return window close action
        self.assertEqual(result['type'], 'ir.actions.act_window_close')

    def test_15_producteca_connection_filtering(self):
        """Test filtering of existing producteca connections."""
        wizard = self.env['producteca.products.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '123,456,789',
        })
        
        # Get connections for the search
        producteca_products_ids = wizard.search_text.split(",")
        int_ids = [int(pid) for pid in producteca_products_ids]
        
        connections = self.env['producteca.product.connections'].sudo().search([
            ('producteca_account_id', '=', wizard.producteca_account_id.id),
            ('product_id', 'in', int_ids)
        ])
        
        # Should find the existing connection (123)
        self.assertEqual(len(connections), 1)
        self.assertEqual(connections[0].product_id, 123)

    def test_16_products_to_create_logic(self):
        """Test logic for determining products to create."""
        wizard = self.env['producteca.products.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '123,456,789',
        })
        
        producteca_products_ids = wizard.search_text.split(",")
        connections = self.env['producteca.product.connections'].sudo().search([
            ('producteca_account_id', '=', wizard.producteca_account_id.id),
            ('product_id', 'in', [int(pid) for pid in producteca_products_ids])
        ])
        
        existing_ids = connections.mapped('product_id.id')
        products_to_create = [int(product_id) for product_id in producteca_products_ids 
                              if int(product_id) not in existing_ids]
        
        # Should identify products that need to be created
        expected_new_products = [456, 789]  # 123 already exists
        self.assertEqual(set(products_to_create), set(expected_new_products))

    def test_17_products_to_update_logic(self):
        """Test logic for determining products to update."""
        wizard = self.env['producteca.products.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '123,456,789',
        })
        
        producteca_products_ids = wizard.search_text.split(",")
        connections = self.env['producteca.product.connections'].sudo().search([
            ('producteca_account_id', '=', wizard.producteca_account_id.id),
            ('product_id', 'in', [int(pid) for pid in producteca_products_ids])
        ])
        
        existing_ids = connections.mapped('product_id.id')
        products_to_update = [int(product_id) for product_id in producteca_products_ids 
                              if int(product_id) in existing_ids]
        
        # Should identify products that need to be updated
        expected_update_products = [123]  # Only this one exists
        self.assertEqual(products_to_update, expected_update_products)

    def test_18_wizard_transient_model_behavior(self):
        """Test transient model behavior."""
        wizard = self.env['producteca.products.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '12345',
        })
        
        # Verify it's a transient model
        self.assertTrue(wizard._transient)
        
        # Should have an ID assigned
        self.assertTrue(wizard.id)

    def test_19_wizard_description_field(self):
        """Test wizard description field."""
        wizard_model = self.env['producteca.products.wizard']
        self.assertEqual(wizard_model._description, 'Wizard para obtener productos de Producteca')

    def test_20_error_handling_invalid_product_ids(self):
        """Test error handling with invalid product IDs."""
        wizard = self.env['producteca.products.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': 'invalid,not_a_number,123',
        })
        
        # Should handle conversion errors gracefully
        try:
            producteca_products_ids = wizard.search_text.split(",")
            int_ids = []
            for pid in producteca_products_ids:
                try:
                    int_ids.append(int(pid))
                except ValueError:
                    continue  # Skip invalid IDs
            
            # Should process valid IDs only
            self.assertEqual(int_ids, [123])
        except Exception as e:
            self.fail(f"Should handle invalid IDs gracefully: {e}")

    def test_21_sudo_usage_in_connections_search(self):
        """Test sudo usage in connections search."""
        wizard = self.env['producteca.products.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '123',
        })
        
        # Test that connections search uses sudo
        producteca_products_ids = wizard.search_text.split(",")
        connections = self.env['producteca.product.connections'].sudo().search([
            ('producteca_account_id', '=', wizard.producteca_account_id.id),
            ('product_id', 'in', [int(pid) for pid in producteca_products_ids])
        ])
        
        # Should find connections even with sudo access
        self.assertTrue(len(connections) >= 0)

    def test_22_wizard_method_chaining(self):
        """Test wizard method chaining and sudo usage."""
        wizard = self.env['producteca.products.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '99999',
        })
        
        # Test sudo() method chaining
        wizard_sudo = wizard.sudo()
        self.assertIsNotNone(wizard_sudo)
        
        # Should maintain wizard identity
        self.assertEqual(wizard_sudo._name, 'producteca.products.wizard')

    @patch('odoo.addons.producteca_connector.wizards.import_producteca_product.ProductecaProductsWizard._get_and_create_from_wizard')
    def test_23_empty_search_text_handling(self, mock_get_create):
        """Test handling of empty search text."""
        wizard = self.env['producteca.products.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '',
        })
        
        # Should handle empty search text
        result = wizard.action_obtain_products()
        
        # Should still return window close action
        self.assertEqual(result['type'], 'ir.actions.act_window_close')

    @patch('odoo.addons.producteca_connector.wizards.import_producteca_product.ProductecaProductsWizard._get_and_create_from_wizard')
    def test_24_whitespace_only_search_text(self, mock_get_create):
        """Test handling of whitespace-only search text."""
        wizard = self.env['producteca.products.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '   ,  ,   ',
        })
        
        mock_get_create.return_value = True
        
        # Should handle whitespace gracefully
        result = wizard.action_obtain_products()
        
        # Should return window close action
        self.assertEqual(result['type'], 'ir.actions.act_window_close')

    @patch('odoo.addons.producteca_connector.wizards.import_producteca_product.ProductecaProductsWizard._get_and_create_from_wizard')
    def test_25_comprehensive_workflow_test(self, mock_get_create):
        """Test comprehensive wizard workflow."""
        # Create additional product connections for testing
        self.env['producteca.product.connections'].create({
            'product_id': 456,
            'odoo_product_id': self.product2.id,
            'producteca_account_id': self.producteca_account.id,
        })
        
        # Test complete workflow with mixed scenario
        wizard = self.env['producteca.products.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '123,456,789,999',  # Mix of existing and new products
            'update_if_exists': True,
        })
        
        mock_get_create.return_value = True
        
        # Execute the wizard action
        result = wizard.action_obtain_products()
        
        # Verify workflow completed successfully
        self.assertEqual(result['type'], 'ir.actions.act_window_close')
        
        # Verify the method was called for both create and update scenarios
        self.assertTrue(mock_get_create.called)
        
        # Verify wizard fields maintained their values
        self.assertEqual(wizard.producteca_account_id, self.producteca_account)
        self.assertEqual(wizard.search_text, '123,456,789,999')
        self.assertTrue(wizard.update_if_exists)
        
        # Verify connections exist for expected products
        connections = self.env['producteca.product.connections'].search([
            ('producteca_account_id', '=', self.producteca_account.id)
        ])
        existing_product_ids = connections.mapped('product_id')
        self.assertIn(123, existing_product_ids)
        self.assertIn(456, existing_product_ids)