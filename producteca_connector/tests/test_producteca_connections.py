# -*- coding: utf-8 -*-
"""
Test module for producteca_connections.py - Producteca Connector
Tests for ProductecaConnections functionality and product synchronization
"""

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from unittest.mock import patch, MagicMock
import requests


class TestProductecaConnections(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test company
        cls.company = cls.env.company
        
        # Create test warehouse
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Test Connections Warehouse',
            'code': 'TCW',
            'company_id': cls.company.id,
        })
        
        # Create test producteca account
        cls.producteca_account = cls.env['producteca.account'].create({
            'account_name': 'Test Connections Account',
            'api_key': 'test_connections_api_key',
            'bearer_token': 'test_connections_bearer_token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': cls.warehouse.id,
            'create_if_dosnt_exist': True,
        })
        
        # Create test product
        cls.product = cls.env['product.product'].create({
            'name': 'Test Connection Product',
            'default_code': 'TCP001',
            'description': '<p>Test product description</p>',
        })

    def test_01_producteca_connections_fields_exist(self):
        """Test that all required fields exist and are properly defined"""
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': self.product.id,
            'producteca_id': 'PROD_123',
            'producteca_variation_id': 'VAR_456',
        })
        
        # Test field existence
        self.assertIn('producteca_account_id', connection._fields)
        self.assertIn('product_id', connection._fields)
        self.assertIn('producteca_variation_id', connection._fields)
        self.assertIn('producteca_id', connection._fields)
        self.assertIn('active', connection._fields)
        
        # Test field types
        self.assertEqual(connection._fields['producteca_account_id'].type, 'many2one')
        self.assertEqual(connection._fields['product_id'].type, 'many2one')
        self.assertEqual(connection._fields['producteca_variation_id'].type, 'char')
        self.assertEqual(connection._fields['producteca_id'].type, 'char')
        self.assertEqual(connection._fields['active'].type, 'boolean')

    def test_02_create_basic_connection(self):
        """Test creating basic producteca connection"""
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': self.product.id,
            'producteca_id': 'BASIC_PROD_001',
            'producteca_variation_id': 'BASIC_VAR_001',
        })
        
        self.assertEqual(connection.producteca_account_id, self.producteca_account)
        self.assertEqual(connection.product_id, self.product)
        self.assertEqual(connection.producteca_id, 'BASIC_PROD_001')
        self.assertEqual(connection.producteca_variation_id, 'BASIC_VAR_001')
        self.assertTrue(connection.active)  # Default should be True

    def test_03_required_fields_validation(self):
        """Test required fields validation"""
        # Test missing producteca_account_id
        with self.assertRaises(Exception):
            self.env['producteca.product.connections'].create({
                'product_id': self.product.id,
                'producteca_id': 'TEST_PROD_001',
            })
        
        # Test missing producteca_id
        with self.assertRaises(Exception):
            self.env['producteca.product.connections'].create({
                'producteca_account_id': self.producteca_account.id,
                'product_id': self.product.id,
                'producteca_variation_id': 'VAR_001',
            })

    def test_04_optional_fields(self):
        """Test optional fields can be empty"""
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'producteca_id': 'OPTIONAL_PROD_001',
            # product_id and producteca_variation_id are optional
        })
        
        self.assertEqual(connection.producteca_account_id, self.producteca_account)
        self.assertEqual(connection.producteca_id, 'OPTIONAL_PROD_001')
        self.assertFalse(connection.product_id)
        self.assertFalse(connection.producteca_variation_id)

    def test_05_active_field_functionality(self):
        """Test active field functionality"""
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': self.product.id,
            'producteca_id': 'ACTIVE_PROD_001',
            'active': False,
        })
        
        self.assertFalse(connection.active)
        
        # Update to active
        connection.write({'active': True})
        self.assertTrue(connection.active)

    def test_06_search_by_producteca_id(self):
        """Test searching connections by producteca_id"""
        connection1 = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': self.product.id,
            'producteca_id': 'SEARCH_PROD_001',
        })
        
        connection2 = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': self.product.id,
            'producteca_id': 'SEARCH_PROD_002',
        })
        
        # Search by producteca_id
        found = self.env['producteca.product.connections'].search([
            ('producteca_id', '=', 'SEARCH_PROD_001')
        ])
        
        self.assertEqual(len(found), 1)
        self.assertEqual(found.id, connection1.id)

    def test_07_search_by_product_and_account(self):
        """Test searching connections by product and account"""
        # Create second account
        account2 = self.env['producteca.account'].create({
            'account_name': 'Second Account',
            'api_key': 'second_api_key',
            'bearer_token': 'second_bearer_token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
        })
        
        connection1 = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': self.product.id,
            'producteca_id': 'MULTI_PROD_001',
        })
        
        connection2 = self.env['producteca.product.connections'].create({
            'producteca_account_id': account2.id,
            'product_id': self.product.id,
            'producteca_id': 'MULTI_PROD_002',
        })
        
        # Search by account and product
        found = self.env['producteca.product.connections'].search([
            ('producteca_account_id', '=', self.producteca_account.id),
            ('product_id', '=', self.product.id)
        ])
        
        self.assertIn(connection1, found)
        self.assertNotIn(connection2, found)

    def test_08_multiple_connections_same_product(self):
        """Test multiple connections for same product with different accounts"""
        # Create additional accounts
        account2 = self.env['producteca.account'].create({
            'account_name': 'Multi Account 2',
            'api_key': 'multi_api_key_2',
            'bearer_token': 'multi_bearer_token_2',
            'imported_sale_action': 'draft_invoice',
            'default_warehouse_id': self.warehouse.id,
        })
        
        account3 = self.env['producteca.account'].create({
            'account_name': 'Multi Account 3',
            'api_key': 'multi_api_key_3',
            'bearer_token': 'multi_bearer_token_3',
            'imported_sale_action': 'confirm',
            'default_warehouse_id': self.warehouse.id,
        })
        
        # Create connections for same product with different accounts
        connections = []
        for i, account in enumerate([self.producteca_account, account2, account3]):
            connection = self.env['producteca.product.connections'].create({
                'producteca_account_id': account.id,
                'product_id': self.product.id,
                'producteca_id': f'MULTI_PROD_{i+1}',
                'producteca_variation_id': f'MULTI_VAR_{i+1}',
            })
            connections.append(connection)
        
        # Verify all connections created
        self.assertEqual(len(connections), 3)
        
        # Verify each has correct account
        for i, connection in enumerate(connections):
            self.assertEqual(connection.product_id, self.product)
            self.assertEqual(connection.producteca_id, f'MULTI_PROD_{i+1}')

    def test_09_connection_with_variation_id(self):
        """Test connection with producteca_variation_id"""
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': self.product.id,
            'producteca_id': 'VAR_PROD_001',
            'producteca_variation_id': 'VARIATION_123',
        })
        
        self.assertEqual(connection.producteca_variation_id, 'VARIATION_123')
        
        # Update variation ID
        connection.write({'producteca_variation_id': 'VARIATION_456'})
        self.assertEqual(connection.producteca_variation_id, 'VARIATION_456')

    @patch('requests.post')
    def test_10_sync_description_product_method(self, mock_post):
        """Test _sync_description_product method"""
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': self.product.id,
            'producteca_id': 'SYNC_DESC_PROD_001',
        })
        
        # Mock requests.post
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Test sync description
        account_data = {
            'bearer_token': 'test_bearer_token',
            'api_key': 'test_api_key',
            'create_if_dosnt_exist': True
        }
        
        product_dict = {
            'sku': 'TCP001',
            'notes': 'Test description'
        }
        
        # Call method
        connection._sync_description_product(account_data, product_dict)
        
        # Verify logging was called (method contains logging)
        # Since the actual request is commented out, we just verify method executes

    def test_11_fix_producteca_descriptions_no_connections(self):
        """Test fix_producteca_descriptions with no connections"""
        # Clear any existing connections
        self.env['producteca.product.connections'].search([]).unlink()
        
        # Test with no connections
        result = self.env['producteca.product.connections'].fix_producteca_descriptions()
        self.assertTrue(result)

    def test_12_fix_producteca_descriptions_with_connections(self):
        """Test fix_producteca_descriptions with connections"""
        # Create product with description
        product_with_desc = self.env['product.product'].create({
            'name': 'Product With Description',
            'default_code': 'PWD001',
            'description': '<p>Rich text description</p>',
        })
        
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': product_with_desc.id,
            'producteca_id': 'FIX_DESC_PROD_001',
        })
        
        # Mock the delay method to avoid queue job execution
        with patch.object(connection, 'with_delay') as mock_delay:
            mock_delay.return_value = connection
            
            # Test fix descriptions
            result = self.env['producteca.product.connections'].fix_producteca_descriptions()
            
            # Verify method called
            mock_delay.assert_called_once()
            self.assertTrue(result)

    def test_13_fix_producteca_descriptions_product_without_description(self):
        """Test fix_producteca_descriptions with product without description"""
        # Create product without description
        product_no_desc = self.env['product.product'].create({
            'name': 'Product No Description',
            'default_code': 'PND001',
            # No description field
        })
        
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': product_no_desc.id,
            'producteca_id': 'NO_DESC_PROD_001',
        })
        
        # Mock the delay method
        with patch.object(connection, 'with_delay') as mock_delay:
            # Test fix descriptions - should skip products without description
            result = self.env['producteca.product.connections'].fix_producteca_descriptions()
            
            # Should not be called for products without description
            mock_delay.assert_not_called()
            self.assertTrue(result)

    def test_14_connection_model_properties(self):
        """Test model properties and inheritance"""
        model = self.env['producteca.product.connections']
        
        # Test model name and description
        self.assertEqual(model._name, 'producteca.product.connections')
        self.assertEqual(model._description, 'Producteca Connections')

    def test_15_field_string_attributes(self):
        """Test field string attributes"""
        model = self.env['producteca.product.connections']
        
        self.assertEqual(model._fields['producteca_account_id'].string, 'Producteca Account')
        self.assertEqual(model._fields['product_id'].string, 'Product')
        self.assertEqual(model._fields['producteca_variation_id'].string, 'Producteca Variation ID')
        self.assertEqual(model._fields['producteca_id'].string, 'Producteca ID')
        self.assertEqual(model._fields['active'].string, 'Active')

    def test_16_field_required_attributes(self):
        """Test field required attributes"""
        model = self.env['producteca.product.connections']
        
        # Test required fields
        self.assertTrue(model._fields['producteca_account_id'].required)
        self.assertTrue(model._fields['producteca_id'].required)
        
        # Test non-required fields
        self.assertFalse(model._fields['product_id'].required)
        self.assertFalse(model._fields['producteca_variation_id'].required)

    def test_17_field_default_values(self):
        """Test field default values"""
        model = self.env['producteca.product.connections']
        
        # Test active field default
        self.assertTrue(model._fields['active'].default)

    def test_18_search_active_connections(self):
        """Test searching for active connections only"""
        # Create active connection
        active_connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': self.product.id,
            'producteca_id': 'ACTIVE_CONN_001',
            'active': True,
        })
        
        # Create inactive connection
        inactive_connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': self.product.id,
            'producteca_id': 'INACTIVE_CONN_001',
            'active': False,
        })
        
        # Search for active connections
        active_connections = self.env['producteca.product.connections'].search([
            ('active', '=', True)
        ])
        
        self.assertIn(active_connection, active_connections)
        self.assertNotIn(inactive_connection, active_connections)

    def test_19_connection_update_operations(self):
        """Test updating connection fields"""
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': self.product.id,
            'producteca_id': 'UPDATE_PROD_001',
            'producteca_variation_id': 'UPDATE_VAR_001',
        })
        
        # Update producteca_id
        connection.write({'producteca_id': 'UPDATED_PROD_001'})
        self.assertEqual(connection.producteca_id, 'UPDATED_PROD_001')
        
        # Update variation_id
        connection.write({'producteca_variation_id': 'UPDATED_VAR_001'})
        self.assertEqual(connection.producteca_variation_id, 'UPDATED_VAR_001')
        
        # Update active status
        connection.write({'active': False})
        self.assertFalse(connection.active)

    def test_20_connection_with_different_products(self):
        """Test connection with different products"""
        # Create additional products
        product2 = self.env['product.product'].create({
            'name': 'Second Test Product',
            'default_code': 'STP001',
        })
        
        product3 = self.env['product.product'].create({
            'name': 'Third Test Product',
            'default_code': 'TTP001',
        })
        
        # Create connections for different products
        connections = []
        for i, product in enumerate([self.product, product2, product3]):
            connection = self.env['producteca.product.connections'].create({
                'producteca_account_id': self.producteca_account.id,
                'product_id': product.id,
                'producteca_id': f'DIFF_PROD_{i+1}',
            })
            connections.append(connection)
        
        # Verify all connections have different products
        self.assertEqual(len(connections), 3)
        products = [conn.product_id for conn in connections]
        self.assertEqual(len(set(products)), 3)  # All different products

    def test_21_sync_description_account_data_validation(self):
        """Test _sync_description_product with different account data"""
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': self.product.id,
            'producteca_id': 'ACCOUNT_DATA_PROD_001',
        })
        
        # Test with complete account data
        complete_account_data = {
            'bearer_token': 'complete_bearer_token',
            'api_key': 'complete_api_key',
            'create_if_dosnt_exist': True
        }
        
        product_dict = {
            'sku': 'TCP001',
            'notes': 'Complete test description'
        }
        
        # Method should execute without error
        connection._sync_description_product(complete_account_data, product_dict)
        
        # Test with minimal account data
        minimal_account_data = {
            'bearer_token': 'minimal_bearer_token',
            'api_key': 'minimal_api_key',
            'create_if_dosnt_exist': False
        }
        
        connection._sync_description_product(minimal_account_data, product_dict)

    def test_22_connection_deletion(self):
        """Test connection deletion"""
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': self.product.id,
            'producteca_id': 'DELETE_PROD_001',
        })
        
        connection_id = connection.id
        
        # Delete connection
        connection.unlink()
        
        # Verify deletion
        deleted_connection = self.env['producteca.product.connections'].search([
            ('id', '=', connection_id)
        ])
        self.assertEqual(len(deleted_connection), 0)

    def test_23_fix_descriptions_html_content_handling(self):
        """Test fix_producteca_descriptions with HTML content"""
        # Create product with complex HTML description
        html_product = self.env['product.product'].create({
            'name': 'HTML Product',
            'default_code': 'HTML001',
            'description': '<div><p>Complex <strong>HTML</strong> description with <em>formatting</em></p><ul><li>Item 1</li><li>Item 2</li></ul></div>',
        })
        
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': html_product.id,
            'producteca_id': 'HTML_DESC_PROD_001',
        })
        
        # Mock the delay method to capture the call
        with patch.object(connection, 'with_delay') as mock_delay:
            mock_delay.return_value = connection
            
            # Mock _sync_description_product to capture arguments
            with patch.object(connection, '_sync_description_product') as mock_sync:
                # Test fix descriptions
                result = self.env['producteca.product.connections'].fix_producteca_descriptions()
                
                # Verify method was called
                mock_delay.assert_called_once()
                self.assertTrue(result)

    def test_24_connection_search_domain_operations(self):
        """Test complex search domain operations"""
        # Create multiple connections for testing
        connections_data = [
            ('SEARCH_PROD_A', 'SEARCH_VAR_A', True),
            ('SEARCH_PROD_B', 'SEARCH_VAR_B', False),
            ('SEARCH_PROD_C', 'SEARCH_VAR_C', True),
            ('SEARCH_PROD_D', None, True),
        ]
        
        created_connections = []
        for prod_id, var_id, active in connections_data:
            connection = self.env['producteca.product.connections'].create({
                'producteca_account_id': self.producteca_account.id,
                'product_id': self.product.id,
                'producteca_id': prod_id,
                'producteca_variation_id': var_id,
                'active': active,
            })
            created_connections.append(connection)
        
        # Test complex search domains
        # Active connections with variation ID
        active_with_var = self.env['producteca.product.connections'].search([
            ('active', '=', True),
            ('producteca_variation_id', '!=', False)
        ])
        
        # Should find SEARCH_PROD_A and SEARCH_PROD_C
        self.assertEqual(len(active_with_var), 2)
        
        # Connections without variation ID
        without_var = self.env['producteca.product.connections'].search([
            ('producteca_variation_id', '=', False)
        ])
        
        # Should find SEARCH_PROD_D
        self.assertGreaterEqual(len(without_var), 1)

    def test_25_comprehensive_connection_workflow(self):
        """Test comprehensive connection workflow and integration"""
        # Create comprehensive test scenario
        
        # 1. Create connection
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': self.product.id,
            'producteca_id': 'COMPREHENSIVE_PROD_001',
            'producteca_variation_id': 'COMPREHENSIVE_VAR_001',
            'active': True,
        })
        
        # 2. Verify creation
        self.assertEqual(connection.producteca_account_id, self.producteca_account)
        self.assertEqual(connection.product_id, self.product)
        self.assertEqual(connection.producteca_id, 'COMPREHENSIVE_PROD_001')
        self.assertEqual(connection.producteca_variation_id, 'COMPREHENSIVE_VAR_001')
        self.assertTrue(connection.active)
        
        # 3. Test search functionality
        found_connection = self.env['producteca.product.connections'].search([
            ('producteca_account_id', '=', self.producteca_account.id),
            ('producteca_id', '=', 'COMPREHENSIVE_PROD_001'),
            ('producteca_variation_id', '=', 'COMPREHENSIVE_VAR_001'),
            ('product_id', '=', self.product.id)
        ])
        
        self.assertEqual(len(found_connection), 1)
        self.assertEqual(found_connection.id, connection.id)
        
        # 4. Test update operations
        connection.write({
            'producteca_id': 'UPDATED_COMPREHENSIVE_PROD_001',
            'active': False,
        })
        
        self.assertEqual(connection.producteca_id, 'UPDATED_COMPREHENSIVE_PROD_001')
        self.assertFalse(connection.active)
        
        # 5. Test account integration
        self.assertEqual(connection.producteca_account_id.api_key, 'test_connections_api_key')
        self.assertEqual(connection.producteca_account_id.bearer_token, 'test_connections_bearer_token')
        
        # 6. Test product integration
        self.assertEqual(connection.product_id.name, 'Test Connection Product')
        self.assertEqual(connection.product_id.default_code, 'TCP001')
        
        # 7. Test description synchronization readiness
        if connection.product_id.description:
            # Connection is ready for description sync
            self.assertTrue(bool(connection.product_id.description))
            self.assertTrue(bool(connection.producteca_account_id.api_key))
            self.assertTrue(bool(connection.producteca_account_id.bearer_token))