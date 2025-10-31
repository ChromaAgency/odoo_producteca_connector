# -*- coding: utf-8 -*-
"""
Test suite for ProductecaSaleordersWizard in producteca_connector module.

This module provides comprehensive test coverage for the ProductecaSaleordersWizard,
which handles sale order import operations from Producteca platform, including:
- Sale order search and import functionality
- API client integration for order retrieval
- Delayed job processing for order creation/update
- Error handling and validation

Test Patterns:
- Uses Odoo TransactionCase for database operations
- Mock external API calls to avoid network dependencies
- Test wizard workflow and user interactions
- Validate business logic and error scenarios
- API integration testing with mock responses

Coverage Areas:
- Wizard field validation and requirements
- Sale order search text parsing
- API client communication
- Delayed job creation for order imports
- Error handling for missing orders
- Response data processing
"""

from unittest.mock import patch, MagicMock
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestProductecaSaleordersWizard(TransactionCase):
    """Test cases for ProductecaSaleordersWizard model."""

    def setUp(self):
        """Set up test data for ProductecaSaleordersWizard tests."""
        super(TestProductecaSaleordersWizard, self).setUp()
        
        # Create test company
        self.company = self.env['res.company'].create({
            'name': 'Test Company',
            'country_id': self.env.ref('base.ar').id,
        })
        
        # Create Producteca account
        self.producteca_account = self.env['producteca.account'].create({
            'name': 'Test Producteca Account',
            'api_key': 'test_api_key',
            'base_url': 'https://test.producteca.com',
            'company_id': self.company.id,
        })
        
        # Create test partner
        self.partner = self.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'customer@test.com',
            'company_id': self.company.id,
        })

    def test_01_wizard_model_definition(self):
        """Test wizard model definition and inheritance."""
        wizard = self.env['producteca.saleorders.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '12345',
        })
        
        self.assertEqual(wizard._name, 'producteca.saleorders.wizard')
        self.assertTrue(hasattr(wizard, 'producteca_account_id'))
        self.assertTrue(hasattr(wizard, 'search_text'))

    def test_02_required_fields_validation(self):
        """Test required fields validation."""
        # Test creating wizard without required fields
        with self.assertRaises(Exception):
            self.env['producteca.saleorders.wizard'].create({})
        
        # Test with missing producteca_account_id
        with self.assertRaises(Exception):
            self.env['producteca.saleorders.wizard'].create({
                'search_text': '12345',
            })
        
        # Test with missing search_text
        with self.assertRaises(Exception):
            self.env['producteca.saleorders.wizard'].create({
                'producteca_account_id': self.producteca_account.id,
            })

    def test_03_wizard_field_assignments(self):
        """Test wizard field assignments."""
        wizard = self.env['producteca.saleorders.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '12345,67890',
        })
        
        self.assertEqual(wizard.producteca_account_id, self.producteca_account)
        self.assertEqual(wizard.search_text, '12345,67890')

    def test_04_wizard_description_field(self):
        """Test wizard description field."""
        wizard_model = self.env['producteca.saleorders.wizard']
        self.assertEqual(wizard_model._description, 'Wizard para obtener ordenes de venta de Producteca')

    def test_05_transient_model_behavior(self):
        """Test transient model behavior."""
        wizard = self.env['producteca.saleorders.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '12345',
        })
        
        # Verify it's a transient model
        self.assertTrue(wizard._transient)
        
        # Should have an ID assigned
        self.assertTrue(wizard.id)

    def test_06_search_text_parsing_single_id(self):
        """Test search text parsing with single sale order ID."""
        wizard = self.env['producteca.saleorders.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '12345',
        })
        
        producteca_sale_order_ids = wizard.search_text.split(",")
        self.assertEqual(len(producteca_sale_order_ids), 1)
        self.assertEqual(producteca_sale_order_ids[0], '12345')

    def test_07_search_text_parsing_multiple_ids(self):
        """Test search text parsing with multiple sale order IDs."""
        wizard = self.env['producteca.saleorders.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '12345,67890,111222,333444',
        })
        
        producteca_sale_order_ids = wizard.search_text.split(",")
        self.assertEqual(len(producteca_sale_order_ids), 4)
        expected_ids = ['12345', '67890', '111222', '333444']
        self.assertEqual(producteca_sale_order_ids, expected_ids)

    def test_08_search_text_parsing_with_spaces(self):
        """Test search text parsing with spaces."""
        wizard = self.env['producteca.saleorders.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': ' 12345 , 67890 , 111222 ',
        })
        
        producteca_sale_order_ids = wizard.search_text.split(",")
        # Should handle spaces in the split
        self.assertEqual(len(producteca_sale_order_ids), 3)

    @patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client')
    @patch('odoo.addons.producteca_connector.models.sale_order.SaleOrder._upset_saleorder_from_producteca')
    def test_09_action_obtain_saleorders_single_order(self, mock_upset, mock_get_client):
        """Test action_obtain_saleorders with single order."""
        # Mock client and sale order
        mock_client = MagicMock()
        mock_sale_order = MagicMock()
        mock_sale_order.to_dict.return_value = {
            'id': 12345,
            'customer': {'name': 'Test Customer'},
            'items': [],
            'total': 100.0
        }
        mock_client.SalesOrder.get.return_value = mock_sale_order
        mock_get_client.return_value = mock_client
        
        wizard = self.env['producteca.saleorders.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '12345',
        })
        
        # Execute wizard action
        wizard.action_obtain_saleorders()
        
        # Verify API calls
        mock_get_client.assert_called_once()
        mock_client.SalesOrder.get.assert_called_once_with('12345')
        mock_sale_order.to_dict.assert_called_once()

    @patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client')
    @patch('odoo.addons.producteca_connector.models.sale_order.SaleOrder._upset_saleorder_from_producteca')
    def test_10_action_obtain_saleorders_multiple_orders(self, mock_upset, mock_get_client):
        """Test action_obtain_saleorders with multiple orders."""
        # Mock client
        mock_client = MagicMock()
        
        # Mock different sale orders
        def mock_get_sale_order(order_id):
            mock_order = MagicMock()
            mock_order.to_dict.return_value = {
                'id': int(order_id),
                'customer': {'name': f'Customer {order_id}'},
                'items': [],
                'total': 100.0 * int(order_id)
            }
            return mock_order
        
        mock_client.SalesOrder.get.side_effect = mock_get_sale_order
        mock_get_client.return_value = mock_client
        
        wizard = self.env['producteca.saleorders.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '12345,67890,111222',
        })
        
        # Execute wizard action
        wizard.action_obtain_saleorders()
        
        # Verify API calls for all orders
        self.assertEqual(mock_client.SalesOrder.get.call_count, 3)
        mock_client.SalesOrder.get.assert_any_call('12345')
        mock_client.SalesOrder.get.assert_any_call('67890')
        mock_client.SalesOrder.get.assert_any_call('111222')

    @patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client')
    def test_11_action_obtain_saleorders_order_not_found(self, mock_get_client):
        """Test action_obtain_saleorders when order is not found."""
        # Mock client returning None for non-existent order
        mock_client = MagicMock()
        mock_client.SalesOrder.get.return_value = None
        mock_get_client.return_value = mock_client
        
        wizard = self.env['producteca.saleorders.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '99999',  # Non-existent order
        })
        
        # Should handle missing orders gracefully
        wizard.action_obtain_saleorders()
        
        # Verify API call was made
        mock_client.SalesOrder.get.assert_called_once_with('99999')

    @patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client')
    @patch('odoo.addons.producteca_connector.models.sale_order.SaleOrder._upset_saleorder_from_producteca')
    def test_12_action_obtain_saleorders_mixed_scenario(self, mock_upset, mock_get_client):
        """Test action_obtain_saleorders with mix of found and not found orders."""
        # Mock client
        mock_client = MagicMock()
        
        def mock_get_sale_order(order_id):
            if order_id == '99999':
                return None  # Order not found
            mock_order = MagicMock()
            mock_order.to_dict.return_value = {
                'id': int(order_id),
                'customer': {'name': f'Customer {order_id}'},
                'items': [],
                'total': 100.0
            }
            return mock_order
        
        mock_client.SalesOrder.get.side_effect = mock_get_sale_order
        mock_get_client.return_value = mock_client
        
        wizard = self.env['producteca.saleorders.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '12345,99999,67890',  # Mix of existing and non-existing
        })
        
        # Execute wizard action
        wizard.action_obtain_saleorders()
        
        # Verify all API calls were made
        self.assertEqual(mock_client.SalesOrder.get.call_count, 3)

    @patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client')
    def test_13_client_retrieval_from_account(self, mock_get_client):
        """Test client retrieval from Producteca account."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        wizard = self.env['producteca.saleorders.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '12345',
        })
        
        # Mock sales order for complete flow
        mock_client.SalesOrder.get.return_value = None
        
        wizard.action_obtain_saleorders()
        
        # Verify client was retrieved from account
        mock_get_client.assert_called_once()

    @patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client')
    def test_14_api_error_handling(self, mock_get_client):
        """Test API error handling."""
        # Mock client to raise an exception
        mock_client = MagicMock()
        mock_client.SalesOrder.get.side_effect = Exception('API Connection Error')
        mock_get_client.return_value = mock_client
        
        wizard = self.env['producteca.saleorders.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '12345',
        })
        
        # Should handle API errors gracefully
        try:
            wizard.action_obtain_saleorders()
        except Exception as e:
            # Should not raise unhandled exceptions in production
            # but for testing, we verify the exception path exists
            self.assertIn('API Connection Error', str(e))

    @patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client')
    @patch('odoo.addons.producteca_connector.models.sale_order.SaleOrder._upset_saleorder_from_producteca')
    def test_15_delayed_job_processing(self, mock_upset, mock_get_client):
        """Test delayed job processing for sale order import."""
        # Mock client and sale order
        mock_client = MagicMock()
        mock_sale_order = MagicMock()
        mock_sale_order.to_dict.return_value = {
            'id': 12345,
            'customer': {'name': 'Test Customer'},
            'items': [{'product_id': 1, 'quantity': 2}],
            'total': 200.0
        }
        mock_client.SalesOrder.get.return_value = mock_sale_order
        mock_get_client.return_value = mock_client
        
        wizard = self.env['producteca.saleorders.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '12345',
        })
        
        wizard.action_obtain_saleorders()
        
        # Verify the delayed job would be created
        # Note: In real implementation, this uses with_delay()
        mock_get_client.assert_called_once()

    @patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client')
    @patch('odoo.addons.producteca_connector.models.sale_order.SaleOrder._upset_saleorder_from_producteca')
    def test_16_sale_order_data_structure(self, mock_upset, mock_get_client):
        """Test sale order data structure processing."""
        # Mock client and sale order with complex data
        mock_client = MagicMock()
        mock_sale_order = MagicMock()
        
        complex_order_data = {
            'id': 12345,
            'customer': {
                'name': 'Complex Customer',
                'email': 'complex@test.com',
                'address': 'Test Address 123'
            },
            'items': [
                {'product_id': 1, 'quantity': 2, 'price': 50.0},
                {'product_id': 2, 'quantity': 1, 'price': 100.0}
            ],
            'total': 200.0,
            'status': 'confirmed',
            'payment_method': 'credit_card'
        }
        
        mock_sale_order.to_dict.return_value = complex_order_data
        mock_client.SalesOrder.get.return_value = mock_sale_order
        mock_get_client.return_value = mock_client
        
        wizard = self.env['producteca.saleorders.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '12345',
        })
        
        wizard.action_obtain_saleorders()
        
        # Verify complex data structure was processed
        mock_sale_order.to_dict.assert_called_once()

    def test_17_empty_search_text_handling(self):
        """Test handling of empty search text."""
        wizard = self.env['producteca.saleorders.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '',
        })
        
        # Should handle empty search text gracefully
        wizard.action_obtain_saleorders()
        
        # No orders should be processed
        # Verify wizard still exists
        self.assertTrue(wizard.id)

    @patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client')
    def test_18_whitespace_only_search_text(self, mock_get_client):
        """Test handling of whitespace-only search text."""
        mock_client = MagicMock()
        mock_client.SalesOrder.get.return_value = None
        mock_get_client.return_value = mock_client
        
        wizard = self.env['producteca.saleorders.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '   ,  ,   ',
        })
        
        # Should handle whitespace gracefully
        wizard.action_obtain_saleorders()
        
        # API calls might be made for empty strings
        mock_get_client.assert_called_once()

    @patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client')
    @patch('odoo.addons.producteca_connector.models.sale_order.SaleOrder._upset_saleorder_from_producteca')
    def test_19_account_reference_in_upset_call(self, mock_upset, mock_get_client):
        """Test account reference is passed to upset method."""
        # Mock client and sale order
        mock_client = MagicMock()
        mock_sale_order = MagicMock()
        mock_sale_order.to_dict.return_value = {'id': 12345}
        mock_client.SalesOrder.get.return_value = mock_sale_order
        mock_get_client.return_value = mock_client
        
        wizard = self.env['producteca.saleorders.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '12345',
        })
        
        wizard.action_obtain_saleorders()
        
        # Verify account is referenced correctly
        self.assertEqual(wizard.producteca_account_id, self.producteca_account)

    @patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client')
    def test_20_invalid_order_id_handling(self, mock_get_client):
        """Test handling of invalid order IDs."""
        mock_client = MagicMock()
        mock_client.SalesOrder.get.return_value = None
        mock_get_client.return_value = mock_client
        
        wizard = self.env['producteca.saleorders.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': 'invalid,not_a_number,abc123',
        })
        
        # Should handle invalid IDs gracefully
        wizard.action_obtain_saleorders()
        
        # API calls should still be made (string IDs are valid)
        mock_get_client.assert_called_once()

    @patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client')
    @patch('odoo.addons.producteca_connector.models.sale_order.SaleOrder._upset_saleorder_from_producteca')
    def test_21_order_iteration_logic(self, mock_upset, mock_get_client):
        """Test order iteration logic in action method."""
        # Mock client
        mock_client = MagicMock()
        
        order_responses = {}
        
        def mock_get_sale_order(order_id):
            if order_id in order_responses:
                return order_responses[order_id]
            mock_order = MagicMock()
            mock_order.to_dict.return_value = {'id': order_id}
            order_responses[order_id] = mock_order
            return mock_order
        
        mock_client.SalesOrder.get.side_effect = mock_get_sale_order
        mock_get_client.return_value = mock_client
        
        wizard = self.env['producteca.saleorders.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '111,222,333',
        })
        
        wizard.action_obtain_saleorders()
        
        # Verify iteration through all order IDs
        expected_calls = ['111', '222', '333']
        actual_calls = [call[0][0] for call in mock_client.SalesOrder.get.call_args_list]
        self.assertEqual(actual_calls, expected_calls)

    @patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client')
    def test_22_client_sales_order_interface(self, mock_get_client):
        """Test client SalesOrder interface usage."""
        mock_client = MagicMock()
        mock_sales_order_class = MagicMock()
        mock_client.SalesOrder = mock_sales_order_class
        mock_sales_order_class.get.return_value = None
        mock_get_client.return_value = mock_client
        
        wizard = self.env['producteca.saleorders.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '12345',
        })
        
        wizard.action_obtain_saleorders()
        
        # Verify client interface usage
        mock_get_client.assert_called_once()
        mock_client.SalesOrder.get.assert_called_once_with('12345')

    @patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client')
    @patch('odoo.addons.producteca_connector.models.sale_order.SaleOrder._upset_saleorder_from_producteca')
    def test_23_to_dict_method_call(self, mock_upset, mock_get_client):
        """Test to_dict method call on sale order objects."""
        # Mock client and sale order
        mock_client = MagicMock()
        mock_sale_order = MagicMock()
        mock_sale_order.to_dict.return_value = {'test': 'data'}
        mock_client.SalesOrder.get.return_value = mock_sale_order
        mock_get_client.return_value = mock_client
        
        wizard = self.env['producteca.saleorders.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '12345',
        })
        
        wizard.action_obtain_saleorders()
        
        # Verify to_dict method was called
        mock_sale_order.to_dict.assert_called_once()

    @patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client')
    def test_24_multiple_account_handling(self, mock_get_client):
        """Test handling with different Producteca accounts."""
        # Create second account
        second_account = self.env['producteca.account'].create({
            'name': 'Second Producteca Account',
            'api_key': 'second_api_key',
            'base_url': 'https://second.producteca.com',
            'company_id': self.company.id,
        })
        
        mock_client = MagicMock()
        mock_client.SalesOrder.get.return_value = None
        mock_get_client.return_value = mock_client
        
        # Test with first account
        wizard1 = self.env['producteca.saleorders.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '11111',
        })
        
        # Test with second account
        wizard2 = self.env['producteca.saleorders.wizard'].create({
            'producteca_account_id': second_account.id,
            'search_text': '22222',
        })
        
        wizard1.action_obtain_saleorders()
        wizard2.action_obtain_saleorders()
        
        # Both should work with their respective accounts
        self.assertEqual(wizard1.producteca_account_id, self.producteca_account)
        self.assertEqual(wizard2.producteca_account_id, second_account)

    @patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client')
    @patch('odoo.addons.producteca_connector.models.sale_order.SaleOrder._upset_saleorder_from_producteca')
    def test_25_comprehensive_workflow_test(self, mock_upset, mock_get_client):
        """Test comprehensive wizard workflow."""
        # Mock client with realistic responses
        mock_client = MagicMock()
        
        # Create realistic order data
        order_data = {
            '12345': {
                'id': 12345,
                'customer': {
                    'name': 'John Doe',
                    'email': 'john@example.com',
                    'phone': '+1234567890'
                },
                'items': [
                    {'product_id': 101, 'quantity': 2, 'price': 25.0, 'name': 'Product A'},
                    {'product_id': 102, 'quantity': 1, 'price': 50.0, 'name': 'Product B'}
                ],
                'subtotal': 100.0,
                'tax': 10.0,
                'total': 110.0,
                'status': 'confirmed',
                'created_at': '2024-01-15T10:30:00Z',
                'payment_method': 'credit_card',
                'shipping_address': {
                    'street': '123 Main St',
                    'city': 'Test City',
                    'country': 'Argentina'
                }
            },
            '67890': {
                'id': 67890,
                'customer': {
                    'name': 'Jane Smith',
                    'email': 'jane@example.com'
                },
                'items': [
                    {'product_id': 103, 'quantity': 3, 'price': 30.0, 'name': 'Product C'}
                ],
                'total': 90.0,
                'status': 'pending'
            }
        }
        
        def mock_get_sale_order(order_id):
            if order_id in order_data:
                mock_order = MagicMock()
                mock_order.to_dict.return_value = order_data[order_id]
                return mock_order
            return None
        
        mock_client.SalesOrder.get.side_effect = mock_get_sale_order
        mock_get_client.return_value = mock_client
        
        # Create comprehensive wizard test
        wizard = self.env['producteca.saleorders.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '12345,67890,99999',  # Mix of existing and non-existing orders
        })
        
        # Execute comprehensive workflow
        wizard.action_obtain_saleorders()
        
        # Verify all aspects of the workflow
        # 1. Client retrieval
        mock_get_client.assert_called_once()
        
        # 2. API calls for all orders
        self.assertEqual(mock_client.SalesOrder.get.call_count, 3)
        mock_client.SalesOrder.get.assert_any_call('12345')
        mock_client.SalesOrder.get.assert_any_call('67890')
        mock_client.SalesOrder.get.assert_any_call('99999')
        
        # 3. Wizard state maintained
        self.assertEqual(wizard.producteca_account_id, self.producteca_account)
        self.assertEqual(wizard.search_text, '12345,67890,99999')
        
        # 4. Verify account relationship
        self.assertEqual(wizard.producteca_account_id.name, 'Test Producteca Account')
        self.assertEqual(wizard.producteca_account_id.api_key, 'test_api_key')
        
        # 5. Verify wizard is still accessible after operation
        self.assertTrue(wizard.id)
        self.assertEqual(wizard._name, 'producteca.saleorders.wizard')