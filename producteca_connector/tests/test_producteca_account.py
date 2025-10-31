# -*- coding: utf-8 -*-
"""
Test module for producteca_account.py - Producteca Connector
Tests for ProductecaAccountConfig functionality and API integration
"""

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from unittest.mock import patch, MagicMock
import psycopg2


class TestProductecaAccountConfig(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test company
        cls.company = cls.env.company
        
        # Create test warehouse
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Test Producteca Warehouse',
            'code': 'TPW',
            'company_id': cls.company.id,
        })
        
        # Create test pricelist
        cls.pricelist = cls.env['product.pricelist'].create({
            'name': 'Test Producteca Pricelist',
            'company_id': cls.company.id,
        })

    def test_01_producteca_account_fields_exist(self):
        """Test that all required fields exist and are properly defined"""
        account = self.env['producteca.account'].create({
            'account_name': 'Test Account',
            'api_key': 'test_api_key',
            'bearer_token': 'test_bearer_token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
        })
        
        # Test field existence and types
        self.assertIn('active', account._fields)
        self.assertIn('account_name', account._fields)
        self.assertIn('api_key', account._fields)
        self.assertIn('bearer_token', account._fields)
        self.assertIn('producteca_company_id', account._fields)
        self.assertIn('company_id', account._fields)
        self.assertIn('imported_sale_action', account._fields)
        self.assertIn('warehouse_ids', account._fields)
        self.assertIn('default_warehouse_id', account._fields)
        self.assertIn('pricelist_to_sync', account._fields)
        
        # Test boolean configuration fields
        self.assertIn('is_stock_modified_by_producteca', account._fields)
        self.assertIn('is_product_price_modified_by_producteca', account._fields)
        self.assertIn('is_producteca_able_to_create_products', account._fields)
        self.assertIn('is_producteca_able_to_modified_products', account._fields)
        self.assertIn('create_if_dosnt_exist', account._fields)
        self.assertIn('is_odoo_able_to_update_producteca_prices', account._fields)

    def test_02_create_basic_producteca_account(self):
        """Test creating basic producteca account"""
        account = self.env['producteca.account'].create({
            'account_name': 'Basic Test Account',
            'api_key': 'basic_api_key_123',
            'bearer_token': 'basic_bearer_token_123',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
        })
        
        self.assertEqual(account.account_name, 'Basic Test Account')
        self.assertEqual(account.api_key, 'basic_api_key_123')
        self.assertEqual(account.bearer_token, 'basic_bearer_token_123')
        self.assertEqual(account.imported_sale_action, 'quotation')
        self.assertEqual(account.default_warehouse_id, self.warehouse)
        self.assertTrue(account.active)  # Default should be True

    def test_03_required_fields_validation(self):
        """Test that required fields are enforced"""
        # Test missing account_name
        with self.assertRaises(Exception):
            self.env['producteca.account'].create({
                'api_key': 'test_api_key',
                'bearer_token': 'test_bearer_token',
                'imported_sale_action': 'quotation',
                'default_warehouse_id': self.warehouse.id,
            })
        
        # Test missing api_key
        with self.assertRaises(Exception):
            self.env['producteca.account'].create({
                'account_name': 'Test Account',
                'bearer_token': 'test_bearer_token',
                'imported_sale_action': 'quotation',
                'default_warehouse_id': self.warehouse.id,
            })
        
        # Test missing bearer_token
        with self.assertRaises(Exception):
            self.env['producteca.account'].create({
                'account_name': 'Test Account',
                'api_key': 'test_api_key',
                'imported_sale_action': 'quotation',
                'default_warehouse_id': self.warehouse.id,
            })
        
        # Test missing imported_sale_action
        with self.assertRaises(Exception):
            self.env['producteca.account'].create({
                'account_name': 'Test Account',
                'api_key': 'test_api_key',
                'bearer_token': 'test_bearer_token',
                'default_warehouse_id': self.warehouse.id,
            })

    def test_04_imported_sale_action_selection(self):
        """Test imported_sale_action selection field values"""
        # Test quotation
        account1 = self.env['producteca.account'].create({
            'account_name': 'Quotation Account',
            'api_key': 'test_api_key',
            'bearer_token': 'test_bearer_token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
        })
        self.assertEqual(account1.imported_sale_action, 'quotation')
        
        # Test draft_invoice
        account2 = self.env['producteca.account'].create({
            'account_name': 'Draft Invoice Account',
            'api_key': 'test_api_key',
            'bearer_token': 'test_bearer_token',
            'imported_sale_action': 'draft_invoice',
            'default_warehouse_id': self.warehouse.id,
        })
        self.assertEqual(account2.imported_sale_action, 'draft_invoice')
        
        # Test confirm
        account3 = self.env['producteca.account'].create({
            'account_name': 'Confirm Account',
            'api_key': 'test_api_key',
            'bearer_token': 'test_bearer_token',
            'imported_sale_action': 'confirm',
            'default_warehouse_id': self.warehouse.id,
        })
        self.assertEqual(account3.imported_sale_action, 'confirm')

    def test_05_warehouse_configuration(self):
        """Test warehouse configuration fields"""
        # Create additional warehouses
        warehouse2 = self.env['stock.warehouse'].create({
            'name': 'Secondary Warehouse',
            'code': 'SEC',
            'company_id': self.company.id,
        })
        
        account = self.env['producteca.account'].create({
            'account_name': 'Warehouse Test Account',
            'api_key': 'test_api_key',
            'bearer_token': 'test_bearer_token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
            'warehouse_ids': [(6, 0, [self.warehouse.id, warehouse2.id])],
        })
        
        self.assertEqual(account.default_warehouse_id, self.warehouse)
        self.assertEqual(len(account.warehouse_ids), 2)
        self.assertIn(self.warehouse, account.warehouse_ids)
        self.assertIn(warehouse2, account.warehouse_ids)

    def test_06_pricelist_configuration(self):
        """Test pricelist configuration"""
        account = self.env['producteca.account'].create({
            'account_name': 'Pricelist Test Account',
            'api_key': 'test_api_key',
            'bearer_token': 'test_bearer_token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
            'pricelist_to_sync': self.pricelist.id,
        })
        
        self.assertEqual(account.pricelist_to_sync, self.pricelist)

    def test_07_boolean_configuration_fields(self):
        """Test boolean configuration fields"""
        account = self.env['producteca.account'].create({
            'account_name': 'Boolean Config Account',
            'api_key': 'test_api_key',
            'bearer_token': 'test_bearer_token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
            'is_stock_modified_by_producteca': True,
            'is_product_price_modified_by_producteca': True,
            'is_producteca_able_to_create_products': True,
            'is_producteca_able_to_modified_products': True,
            'create_if_dosnt_exist': True,
            'is_odoo_able_to_update_producteca_prices': False,  # Should be False due to constraint
        })
        
        self.assertTrue(account.is_stock_modified_by_producteca)
        self.assertTrue(account.is_product_price_modified_by_producteca)
        self.assertTrue(account.is_producteca_able_to_create_products)
        self.assertTrue(account.is_producteca_able_to_modified_products)
        self.assertTrue(account.create_if_dosnt_exist)
        self.assertFalse(account.is_odoo_able_to_update_producteca_prices)

    def test_08_get_orders_from_last_days_default(self):
        """Test get_orders_from_last_days field default value"""
        account = self.env['producteca.account'].create({
            'account_name': 'Days Config Account',
            'api_key': 'test_api_key',
            'bearer_token': 'test_bearer_token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
        })
        
        self.assertEqual(account.get_orders_from_last_days, 7)  # Default value

    def test_09_update_get_orders_from_last_days(self):
        """Test updating get_orders_from_last_days field"""
        account = self.env['producteca.account'].create({
            'account_name': 'Days Update Account',
            'api_key': 'test_api_key',
            'bearer_token': 'test_bearer_token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
            'get_orders_from_last_days': 15,
        })
        
        self.assertEqual(account.get_orders_from_last_days, 15)
        
        # Update value
        account.write({'get_orders_from_last_days': 30})
        self.assertEqual(account.get_orders_from_last_days, 30)

    def test_10_price_sync_exclusivity_constraint_violation(self):
        """Test price synchronization exclusivity constraint violation"""
        with self.assertRaises(psycopg2.IntegrityError):
            with self.env.cr.savepoint():
                self.env['producteca.account'].create({
                    'account_name': 'Invalid Price Sync Account',
                    'api_key': 'test_api_key',
                    'bearer_token': 'test_bearer_token',
                    'imported_sale_action': 'quotation',
                    'default_warehouse_id': self.warehouse.id,
                    'is_product_price_modified_by_producteca': True,
                    'is_odoo_able_to_update_producteca_prices': True,  # Both True should fail
                })

    def test_11_price_sync_exclusivity_constraint_valid_combinations(self):
        """Test valid price synchronization constraint combinations"""
        # Both False - should work
        account1 = self.env['producteca.account'].create({
            'account_name': 'Valid Price Sync 1',
            'api_key': 'test_api_key',
            'bearer_token': 'test_bearer_token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
            'is_product_price_modified_by_producteca': False,
            'is_odoo_able_to_update_producteca_prices': False,
        })
        
        self.assertFalse(account1.is_product_price_modified_by_producteca)
        self.assertFalse(account1.is_odoo_able_to_update_producteca_prices)
        
        # Producteca True, Odoo False - should work
        account2 = self.env['producteca.account'].create({
            'account_name': 'Valid Price Sync 2',
            'api_key': 'test_api_key_2',
            'bearer_token': 'test_bearer_token_2',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
            'is_product_price_modified_by_producteca': True,
            'is_odoo_able_to_update_producteca_prices': False,
        })
        
        self.assertTrue(account2.is_product_price_modified_by_producteca)
        self.assertFalse(account2.is_odoo_able_to_update_producteca_prices)
        
        # Producteca False, Odoo True - should work
        account3 = self.env['producteca.account'].create({
            'account_name': 'Valid Price Sync 3',
            'api_key': 'test_api_key_3',
            'bearer_token': 'test_bearer_token_3',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
            'is_product_price_modified_by_producteca': False,
            'is_odoo_able_to_update_producteca_prices': True,
        })
        
        self.assertFalse(account3.is_product_price_modified_by_producteca)
        self.assertTrue(account3.is_odoo_able_to_update_producteca_prices)

    def test_12_update_existing_account_price_sync_constraint(self):
        """Test updating existing account triggers price sync constraint"""
        account = self.env['producteca.account'].create({
            'account_name': 'Update Constraint Account',
            'api_key': 'test_api_key',
            'bearer_token': 'test_bearer_token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
            'is_product_price_modified_by_producteca': False,
            'is_odoo_able_to_update_producteca_prices': False,
        })
        
        # Update to valid state
        account.write({'is_product_price_modified_by_producteca': True})
        self.assertTrue(account.is_product_price_modified_by_producteca)
        
        # Try to update to invalid state
        with self.assertRaises(psycopg2.IntegrityError):
            with self.env.cr.savepoint():
                account.write({'is_odoo_able_to_update_producteca_prices': True})

    @patch('producteca.ProductecaClient')
    def test_13_get_client_method(self, mock_producteca_client):
        """Test get_client method returns ProductecaClient instance"""
        account = self.env['producteca.account'].create({
            'account_name': 'Client Test Account',
            'api_key': 'test_api_key_client',
            'bearer_token': 'test_bearer_token_client',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
        })
        
        # Mock ProductecaClient
        mock_client_instance = MagicMock()
        mock_producteca_client.return_value = mock_client_instance
        
        # Test get_client
        client = account.get_client()
        
        # Verify client creation
        mock_producteca_client.assert_called_once_with(
            api_key='test_api_key_client',
            token='test_bearer_token_client'
        )
        self.assertEqual(client, mock_client_instance)

    def test_14_rec_name_functionality(self):
        """Test _rec_name functionality using account_name"""
        account = self.env['producteca.account'].create({
            'account_name': 'RecName Test Account',
            'api_key': 'test_api_key',
            'bearer_token': 'test_bearer_token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
        })
        
        # Test display name
        self.assertEqual(account.display_name, 'RecName Test Account')
        self.assertEqual(str(account), 'RecName Test Account')

    def test_15_company_id_field(self):
        """Test company_id field functionality"""
        # Create second company
        company2 = self.env['res.company'].create({
            'name': 'Second Test Company',
        })
        
        account = self.env['producteca.account'].create({
            'account_name': 'Company Test Account',
            'api_key': 'test_api_key',
            'bearer_token': 'test_bearer_token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
            'company_id': company2.id,
        })
        
        self.assertEqual(account.company_id, company2)

    def test_16_producteca_company_id_field(self):
        """Test producteca_company_id field"""
        account = self.env['producteca.account'].create({
            'account_name': 'Producteca ID Test Account',
            'api_key': 'test_api_key',
            'bearer_token': 'test_bearer_token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
            'producteca_company_id': 'PROD_COMP_123',
        })
        
        self.assertEqual(account.producteca_company_id, 'PROD_COMP_123')

    def test_17_active_field_functionality(self):
        """Test active field functionality"""
        account = self.env['producteca.account'].create({
            'account_name': 'Active Test Account',
            'api_key': 'test_api_key',
            'bearer_token': 'test_bearer_token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
            'active': False,
        })
        
        self.assertFalse(account.active)
        
        # Update to active
        account.write({'active': True})
        self.assertTrue(account.active)

    def test_18_search_active_accounts(self):
        """Test searching for active accounts"""
        # Create active account
        active_account = self.env['producteca.account'].create({
            'account_name': 'Active Search Account',
            'api_key': 'test_api_key_active',
            'bearer_token': 'test_bearer_token_active',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
            'active': True,
        })
        
        # Create inactive account
        inactive_account = self.env['producteca.account'].create({
            'account_name': 'Inactive Search Account',
            'api_key': 'test_api_key_inactive',
            'bearer_token': 'test_bearer_token_inactive',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
            'active': False,
        })
        
        # Search for active accounts
        active_accounts = self.env['producteca.account'].search([
            ('active', '=', True)
        ])
        
        self.assertIn(active_account, active_accounts)
        self.assertNotIn(inactive_account, active_accounts)

    @patch('producteca_connector.models.product_product.ProductProduct.sync_all_products_from_producteca')
    def test_19_sync_all_products_from_producteca_method(self, mock_sync):
        """Test sync_all_products_from_producteca method"""
        account = self.env['producteca.account'].create({
            'account_name': 'Sync Test Account',
            'api_key': 'test_api_key',
            'bearer_token': 'test_bearer_token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
        })
        
        # Mock the sync method
        mock_sync.return_value = True
        
        # Test sync method
        result = account.sync_all_products_from_producteca()
        
        # Verify method was called
        mock_sync.assert_called_once()
        self.assertTrue(result)

    def test_20_multiple_accounts_different_configurations(self):
        """Test creating multiple accounts with different configurations"""
        configs = [
            {
                'account_name': 'Config 1',
                'api_key': 'api_key_1',
                'bearer_token': 'bearer_1',
                'imported_sale_action': 'quotation',
                'is_stock_modified_by_producteca': True,
                'is_producteca_able_to_create_products': True,
            },
            {
                'account_name': 'Config 2',
                'api_key': 'api_key_2',
                'bearer_token': 'bearer_2',
                'imported_sale_action': 'draft_invoice',
                'is_product_price_modified_by_producteca': True,
                'is_producteca_able_to_modified_products': True,
            },
            {
                'account_name': 'Config 3',
                'api_key': 'api_key_3',
                'bearer_token': 'bearer_3',
                'imported_sale_action': 'confirm',
                'is_odoo_able_to_update_producteca_prices': True,
                'create_if_dosnt_exist': True,
            }
        ]
        
        created_accounts = []
        for config in configs:
            config['default_warehouse_id'] = self.warehouse.id
            account = self.env['producteca.account'].create(config)
            created_accounts.append(account)
        
        # Verify all accounts created with correct configurations
        self.assertEqual(len(created_accounts), 3)
        
        for i, account in enumerate(created_accounts):
            expected_config = configs[i]
            self.assertEqual(account.account_name, expected_config['account_name'])
            self.assertEqual(account.api_key, expected_config['api_key'])
            self.assertEqual(account.imported_sale_action, expected_config['imported_sale_action'])

    def test_21_constraint_error_message(self):
        """Test constraint error message content"""
        try:
            with self.env.cr.savepoint():
                self.env['producteca.account'].create({
                    'account_name': 'Constraint Message Test',
                    'api_key': 'test_api_key',
                    'bearer_token': 'test_bearer_token',
                    'imported_sale_action': 'quotation',
                    'default_warehouse_id': self.warehouse.id,
                    'is_product_price_modified_by_producteca': True,
                    'is_odoo_able_to_update_producteca_prices': True,
                })
        except psycopg2.IntegrityError as e:
            # Check that constraint name appears in error
            self.assertIn('check_price_sync_exclusivity', str(e))

    def test_22_field_attributes_validation(self):
        """Test field attributes and properties"""
        model = self.env['producteca.account']
        
        # Test string attributes
        self.assertEqual(model._fields['account_name'].string, 'Account Name')
        self.assertEqual(model._fields['api_key'].string, 'API Key')
        self.assertEqual(model._fields['bearer_token'].string, 'Bearer Token')
        self.assertEqual(model._fields['imported_sale_action'].string, 'Imported Sale Action')
        
        # Test required fields
        self.assertTrue(model._fields['account_name'].required)
        self.assertTrue(model._fields['api_key'].required)
        self.assertTrue(model._fields['bearer_token'].required)
        self.assertTrue(model._fields['imported_sale_action'].required)
        self.assertTrue(model._fields['default_warehouse_id'].required)
        
        # Test default values
        self.assertTrue(model._fields['active'].default)
        self.assertEqual(model._fields['get_orders_from_last_days'].default, 7)

    def test_23_sql_constraint_definition(self):
        """Test SQL constraint definition"""
        model = self.env['producteca.account']
        constraints = model._sql_constraints
        
        # Find price sync constraint
        price_constraint = None
        for constraint in constraints:
            if constraint[0] == 'check_price_sync_exclusivity':
                price_constraint = constraint
                break
        
        self.assertIsNotNone(price_constraint)
        self.assertEqual(price_constraint[0], 'check_price_sync_exclusivity')
        self.assertIn('NOT(is_product_price_modified_by_producteca = true AND is_odoo_able_to_update_producteca_prices = true)', price_constraint[1])
        self.assertIn('Only one price synchronization option can be active', price_constraint[2])

    def test_24_model_inheritance_and_properties(self):
        """Test model inheritance and basic properties"""
        model = self.env['producteca.account']
        
        # Test model name and description
        self.assertEqual(model._name, 'producteca.account')
        self.assertEqual(model._description, 'Producteca Account')
        self.assertEqual(model._rec_name, 'account_name')

    def test_25_comprehensive_field_coverage(self):
        """Test comprehensive field coverage and edge cases"""
        account = self.env['producteca.account'].create({
            'account_name': 'Comprehensive Test Account',
            'api_key': 'comprehensive_api_key',
            'bearer_token': 'comprehensive_bearer_token',
            'producteca_company_id': 'COMP_COMPREHENSIVE_001',
            'imported_sale_action': 'confirm',
            'default_warehouse_id': self.warehouse.id,
            'warehouse_ids': [(6, 0, [self.warehouse.id])],
            'pricelist_to_sync': self.pricelist.id,
            'is_stock_modified_by_producteca': True,
            'is_product_price_modified_by_producteca': False,
            'is_producteca_able_to_create_products': True,
            'is_producteca_able_to_modified_products': True,
            'create_if_dosnt_exist': True,
            'get_orders_from_last_days': 14,
            'is_odoo_able_to_update_producteca_prices': True,
            'company_id': self.company.id,
            'active': True,
        })
        
        # Verify all fields are set correctly
        self.assertEqual(account.account_name, 'Comprehensive Test Account')
        self.assertEqual(account.api_key, 'comprehensive_api_key')
        self.assertEqual(account.bearer_token, 'comprehensive_bearer_token')
        self.assertEqual(account.producteca_company_id, 'COMP_COMPREHENSIVE_001')
        self.assertEqual(account.imported_sale_action, 'confirm')
        self.assertEqual(account.default_warehouse_id, self.warehouse)
        self.assertIn(self.warehouse, account.warehouse_ids)
        self.assertEqual(account.pricelist_to_sync, self.pricelist)
        self.assertTrue(account.is_stock_modified_by_producteca)
        self.assertFalse(account.is_product_price_modified_by_producteca)
        self.assertTrue(account.is_producteca_able_to_create_products)
        self.assertTrue(account.is_producteca_able_to_modified_products)
        self.assertTrue(account.create_if_dosnt_exist)
        self.assertEqual(account.get_orders_from_last_days, 14)
        self.assertTrue(account.is_odoo_able_to_update_producteca_prices)
        self.assertEqual(account.company_id, self.company)
        self.assertTrue(account.active)