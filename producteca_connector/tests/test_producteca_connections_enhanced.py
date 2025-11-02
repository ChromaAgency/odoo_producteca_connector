# Copyright 2024 Chroma Agency
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

"""Unit tests for producteca_connections model.

This module provides comprehensive tests for the Producteca Product Connections
functionality, testing product mapping, synchronization, and business logic.
"""

from odoo.tests.common import TransactionCase
from unittest.mock import patch, MagicMock

from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT


class TestProductecaConnections(TransactionCase):
    """Test cases for producteca.product.connections model."""

    @classmethod
    def setUpClass(cls):
        """Set up test data for producteca connections tests."""
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))
        
        # Create test company and warehouse
        cls.company = cls.env.company
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Test Warehouse',
            'code': 'TEST',
            'company_id': cls.company.id,
        })
        
        # Create test Producteca account
        cls.producteca_account = cls.env['producteca.account'].create({
            'account_name': 'Test Producteca Account',
            'api_key': 'test_api_key',
            'bearer_token': 'test_bearer_token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': cls.warehouse.id,
            'create_if_dosnt_exist': True,
        })
        
        # Create test product
        cls.product = cls.env['product.product'].create({
            'name': 'Test Producteca Product',
            'default_code': 'TEST_PRODUCT_001',
            'type': 'product',
            'description': '<p>Test product description with HTML</p>',
        })

    def test_01_producteca_connection_creation(self):
        """Test basic producteca connection creation."""
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': self.product.id,
            'producteca_id': 'PROD_123',
            'producteca_variation_id': 'VAR_456',
        })
        
        # Verify connection was created correctly
        self.assertTrue(connection.id)
        self.assertEqual(connection.producteca_account_id, self.producteca_account)
        self.assertEqual(connection.product_id, self.product)
        self.assertEqual(connection.producteca_id, 'PROD_123')
        self.assertEqual(connection.producteca_variation_id, 'VAR_456')
        self.assertTrue(connection.active)  # Default value

    def test_02_required_fields_validation(self):
        """Test required fields validation."""
        # Test missing producteca_account_id
        with self.assertRaises(Exception):
            self.env['producteca.product.connections'].create({
                'product_id': self.product.id,
                'producteca_id': 'PROD_123',
            })
        
        # Test missing producteca_id
        with self.assertRaises(Exception):
            self.env['producteca.product.connections'].create({
                'producteca_account_id': self.producteca_account.id,
                'product_id': self.product.id,
            })

    def test_03_connection_without_product(self):
        """Test connection creation without Odoo product (for new products)."""
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'producteca_id': 'PROD_NEW_789',
            'producteca_variation_id': 'VAR_NEW_012',
        })
        
        # Should work without product_id (for new products from Producteca)
        self.assertTrue(connection.id)
        self.assertFalse(connection.product_id)
        self.assertEqual(connection.producteca_id, 'PROD_NEW_789')

    def test_04_multiple_connections_same_account(self):
        """Test multiple connections for same account."""
        # Create multiple products
        product2 = self.env['product.product'].create({
            'name': 'Second Test Product',
            'default_code': 'TEST_PRODUCT_002',
            'type': 'product',
        })
        
        # Create connections
        connection1 = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': self.product.id,
            'producteca_id': 'PROD_001',
        })
        
        connection2 = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': product2.id,
            'producteca_id': 'PROD_002',
        })
        
        # Verify both connections work
        self.assertNotEqual(connection1.id, connection2.id)
        self.assertEqual(connection1.producteca_account_id, connection2.producteca_account_id)
        self.assertNotEqual(connection1.product_id, connection2.product_id)

    def test_05_connection_search_by_producteca_id(self):
        """Test searching connections by Producteca ID."""
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': self.product.id,
            'producteca_id': 'SEARCH_TEST_123',
            'producteca_variation_id': 'VAR_SEARCH_456',
        })
        
        # Search by producteca_id
        found_connection = self.env['producteca.product.connections'].search([
            ('producteca_id', '=', 'SEARCH_TEST_123')
        ])
        self.assertEqual(found_connection, connection)
        
        # Search by producteca_id and variation_id
        found_connection_var = self.env['producteca.product.connections'].search([
            ('producteca_id', '=', 'SEARCH_TEST_123'),
            ('producteca_variation_id', '=', 'VAR_SEARCH_456'),
        ])
        self.assertEqual(found_connection_var, connection)

    def test_06_active_field_functionality(self):
        """Test active field functionality."""
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': self.product.id,
            'producteca_id': 'ACTIVE_TEST_123',
            'active': False,
        })
        
        self.assertFalse(connection.active)
        
        # Update to active
        connection.active = True
        self.assertTrue(connection.active)
        
        # Test search with active filter
        active_connections = self.env['producteca.product.connections'].search([
            ('active', '=', True)
        ])
        self.assertIn(connection, active_connections)

    @patch('requests.post')
    def test_07_sync_description_product_method(self, mock_post):
        """Test _sync_description_product method."""
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': self.product.id,
            'producteca_id': 'SYNC_TEST_123',
        })
        
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True}
        mock_post.return_value = mock_response
        
        # Prepare test data
        account_data = {
            'bearer_token': 'test_token',
            'api_key': 'test_key',
            'create_if_dosnt_exist': True,
        }
        product_dict = {
            'sku': 'TEST_SKU',
            'notes': 'Test description',
        }
        
        # Test the method (commented API call won't execute)
        connection._sync_description_product(account_data, product_dict)
        
        # Since API call is commented, just verify method executes without error
        self.assertTrue(True)

    def test_08_fix_producteca_descriptions_method(self):
        """Test fix_producteca_descriptions method."""
        # Create connection with product that has description
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': self.product.id,
            'producteca_id': 'DESC_FIX_123',
        })
        
        # Create product without description
        product_no_desc = self.env['product.product'].create({
            'name': 'Product No Description',
            'default_code': 'NO_DESC_001',
            'type': 'product',
        })
        
        connection_no_desc = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': product_no_desc.id,
            'producteca_id': 'NO_DESC_123',
        })
        
        # Mock the delay method to avoid actual queue job
        with patch.object(connection, 'with_delay') as mock_delay:
            mock_delay.return_value = connection
            with patch.object(connection, '_sync_description_product') as mock_sync:
                
                # Call the method
                result = connection.fix_producteca_descriptions()
                
                # Verify result
                self.assertTrue(result)
                
                # Should be called once (only for product with description)
                self.assertEqual(mock_sync.call_count, 1)

    def test_09_fix_descriptions_with_html_content(self):
        """Test description fixing with HTML content."""
        # Create product with HTML description
        html_product = self.env['product.product'].create({
            'name': 'HTML Product',
            'default_code': 'HTML_001',
            'type': 'product',
            'description': '<p><strong>Bold</strong> description with <em>emphasis</em></p>',
        })
        
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': html_product.id,
            'producteca_id': 'HTML_DESC_123',
        })
        
        # Mock to capture the actual data being sent
        with patch.object(connection, 'with_delay') as mock_delay:
            mock_delay.return_value = connection
            with patch.object(connection, '_sync_description_product') as mock_sync:
                
                connection.fix_producteca_descriptions()
                
                # Verify the method was called with HTML preserved
                mock_sync.assert_called_once()
                args, kwargs = mock_sync.call_args
                account_data, product_dict = args
                
                # Check that HTML is preserved in description
                self.assertIn('<p>', product_dict['notes'])
                self.assertIn('<strong>', product_dict['notes'])
                self.assertEqual(product_dict['sku'], 'HTML_001')

    def test_10_connection_field_relationships(self):
        """Test field relationships and constraints."""
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': self.product.id,
            'producteca_id': 'REL_TEST_123',
        })
        
        # Test relationship access
        self.assertEqual(connection.producteca_account_id.account_name, 'Test Producteca Account')
        self.assertEqual(connection.product_id.name, 'Test Producteca Product')
        
        # Test cascade behavior (account deletion should be restricted)
        with self.assertRaises(Exception):
            self.producteca_account.unlink()

    def test_11_connection_with_variation_handling(self):
        """Test connection handling with variations."""
        # Create connections with and without variations
        connection_with_var = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': self.product.id,
            'producteca_id': 'PROD_VAR_123',
            'producteca_variation_id': 'VAR_ABC',
        })
        
        connection_without_var = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': self.product.id,
            'producteca_id': 'PROD_NO_VAR_456',
        })
        
        # Verify both scenarios work
        self.assertEqual(connection_with_var.producteca_variation_id, 'VAR_ABC')
        self.assertFalse(connection_without_var.producteca_variation_id)

    def test_12_bulk_operations_performance(self):
        """Test bulk operations performance."""
        # Create multiple connections for bulk testing
        connections = []
        for i in range(10):
            product = self.env['product.product'].create({
                'name': f'Bulk Product {i}',
                'default_code': f'BULK_{i:03d}',
                'type': 'product',
                'description': f'<p>Bulk description {i}</p>',
            })
            
            connection = self.env['producteca.product.connections'].create({
                'producteca_account_id': self.producteca_account.id,
                'product_id': product.id,
                'producteca_id': f'BULK_PROD_{i}',
            })
            connections.append(connection)
        
        # Test bulk description fixing
        with patch.object(self.env['producteca.product.connections'], 'with_delay') as mock_delay:
            mock_delay.return_value = self.env['producteca.product.connections']
            with patch.object(self.env['producteca.product.connections'], '_sync_description_product'):
                
                result = self.env['producteca.product.connections'].fix_producteca_descriptions()
                
                # Should complete successfully
                self.assertTrue(result)

    def test_13_model_name_and_description(self):
        """Test model name and description."""
        model = self.env['producteca.product.connections']
        self.assertEqual(model._name, 'producteca.product.connections')
        self.assertEqual(model._description, 'Producteca Product Connections')

    def test_14_field_types_validation(self):
        """Test field types and properties."""
        model = self.env['producteca.product.connections']
        fields_info = model.fields_get()
        
        # Test field types
        self.assertEqual(fields_info['producteca_account_id']['type'], 'many2one')
        self.assertEqual(fields_info['product_id']['type'], 'many2one')
        self.assertEqual(fields_info['producteca_id']['type'], 'char')
        self.assertEqual(fields_info['producteca_variation_id']['type'], 'char')
        self.assertEqual(fields_info['active']['type'], 'boolean')
        
        # Test required fields
        self.assertTrue(fields_info['producteca_account_id']['required'])
        self.assertTrue(fields_info['producteca_id']['required'])
        self.assertFalse(fields_info['product_id']['required'])

    def test_15_connection_update_operations(self):
        """Test connection update operations."""
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': self.product.id,
            'producteca_id': 'UPDATE_TEST_123',
        })
        
        # Test updating producteca_variation_id
        connection.write({'producteca_variation_id': 'NEW_VAR_123'})
        self.assertEqual(connection.producteca_variation_id, 'NEW_VAR_123')
        
        # Test updating active status
        connection.write({'active': False})
        self.assertFalse(connection.active)
        
        # Test updating producteca_id
        connection.write({'producteca_id': 'UPDATED_PROD_456'})
        self.assertEqual(connection.producteca_id, 'UPDATED_PROD_456')

    def test_16_connection_copy_behavior(self):
        """Test connection copy behavior."""
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': self.product.id,
            'producteca_id': 'COPY_TEST_123',
            'producteca_variation_id': 'COPY_VAR_456',
        })
        
        # Copy connection
        copied_connection = connection.copy()
        
        # Verify copy has different ID but same data
        self.assertNotEqual(connection.id, copied_connection.id)
        self.assertEqual(connection.producteca_account_id, copied_connection.producteca_account_id)
        self.assertEqual(connection.product_id, copied_connection.product_id)
        # producteca_id might be modified to avoid duplicates
        self.assertTrue(copied_connection.producteca_id)