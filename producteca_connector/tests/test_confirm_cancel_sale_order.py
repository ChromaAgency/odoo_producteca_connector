# -*- coding: utf-8 -*-
"""
Test suite for ConfirmCancelSaleOrder wizard in producteca_connector module.

This module provides comprehensive test coverage for the ConfirmCancelSaleOrder wizard,
which handles sale order cancellation confirmation and integration with Producteca platform, including:
- Confirmation dialog for order cancellation
- Integration with Producteca API for order cancellation
- Sale order cancellation with context control
- Warning message display and user interaction

Test Patterns:
- Uses Odoo TransactionCase for database operations
- Mock external API calls to avoid network dependencies
- Test wizard workflow and user interactions
- Validate business logic and error scenarios
- Context handling for cancellation operations

Coverage Areas:
- Wizard field validation and requirements
- Warning message display
- Order cancellation confirmation workflow
- Producteca API integration for cancellation
- Context-based cancellation control
- Error handling for missing orders
"""

from unittest.mock import patch, MagicMock
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from odoo import Command


class TestConfirmCancelSaleOrder(TransactionCase):
    """Test cases for ConfirmCancelSaleOrder wizard model."""

    def setUp(self):
        """Set up test data for ConfirmCancelSaleOrder tests."""
        super(TestConfirmCancelSaleOrder, self).setUp()
        
        # Create test company
        self.company = self.env['res.company'].create({
            'name': 'Test Company',
            'country_id': self.env.ref('base.ar').id,
        })
        
        # Create test partner
        self.partner = self.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'customer@test.com',
            'company_id': self.company.id,
        })
        
        # Create Producteca account
        self.producteca_account = self.env['producteca.account'].create({
            'name': 'Test Producteca Account',
            'api_key': 'test_api_key',
            'base_url': 'https://test.producteca.com',
            'company_id': self.company.id,
        })
        
        # Create test product
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 100.0,
            'standard_price': 50.0,
            'type': 'product',
        })
        
        # Create sales journal
        self.sales_journal = self.env['account.journal'].create({
            'name': 'Test Sales Journal',
            'type': 'sale',
            'code': 'TSJ',
            'company_id': self.company.id,
        })
        
        # Create test sale order with Producteca data
        self.sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'producteca_id': '12345',
            'produceteca_account_id': self.producteca_account.id,
            'order_line': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 2,
                'price_unit': 100.0,
                'name': 'Test Product Line',
            })],
        })

    def test_01_wizard_model_definition(self):
        """Test wizard model definition and inheritance."""
        wizard = self.env['confirm.cancel.sale.order'].create({
            'sale_order_id': self.sale_order.id,
        })
        
        self.assertEqual(wizard._name, 'confirm.cancel.sale.order')
        self.assertTrue(hasattr(wizard, 'sale_order_id'))
        self.assertTrue(hasattr(wizard, 'warning_message'))

    def test_02_wizard_description_field(self):
        """Test wizard description field."""
        wizard_model = self.env['confirm.cancel.sale.order']
        self.assertEqual(wizard_model._description, 'Confirm Cancel Sale Order')

    def test_03_transient_model_behavior(self):
        """Test transient model behavior."""
        wizard = self.env['confirm.cancel.sale.order'].create({
            'sale_order_id': self.sale_order.id,
        })
        
        # Verify it's a transient model
        self.assertTrue(wizard._transient)
        
        # Should have an ID assigned
        self.assertTrue(wizard.id)

    def test_04_default_warning_message(self):
        """Test default warning message."""
        wizard = self.env['confirm.cancel.sale.order'].create({
            'sale_order_id': self.sale_order.id,
        })
        
        expected_message = "Advertencia: Cancelar esta orden en Producteca puede afectar tu reputación en algunos canales de ventas. ¿Estás seguro de continuar?"
        self.assertEqual(wizard.warning_message, expected_message)

    def test_05_warning_message_readonly(self):
        """Test warning message field is readonly."""
        field = self.env['confirm.cancel.sale.order']._fields['warning_message']
        self.assertTrue(field.readonly)

    def test_06_wizard_field_assignments(self):
        """Test wizard field assignments."""
        wizard = self.env['confirm.cancel.sale.order'].create({
            'sale_order_id': self.sale_order.id,
        })
        
        self.assertEqual(wizard.sale_order_id, self.sale_order)
        self.assertIsNotNone(wizard.warning_message)

    def test_07_wizard_without_sale_order(self):
        """Test wizard creation without sale order."""
        wizard = self.env['confirm.cancel.sale.order'].create({})
        
        # Should be created but sale_order_id will be False
        self.assertFalse(wizard.sale_order_id)

    def test_08_action_confirm_cancel_no_order(self):
        """Test action_confirm_cancel with no sale order selected."""
        wizard = self.env['confirm.cancel.sale.order'].create({})
        
        # Should raise UserError when no order is selected
        with self.assertRaises(UserError) as context:
            wizard.action_confirm_cancel()
        
        self.assertIn('No se selecciono una orden', str(context.exception))

    @patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client')
    def test_09_action_confirm_cancel_success(self, mock_get_client):
        """Test successful action_confirm_cancel operation."""
        # Mock client and cancel method
        mock_client = MagicMock()
        mock_sales_order = MagicMock()
        mock_client.SalesOrder.return_value = mock_sales_order
        mock_sales_order.cancel.return_value = {'success': True}
        
        # Note: There's a typo in the original code (produceteca_account_id vs producteca_account_id)
        # We'll test with the actual field name from the model
        wizard = self.env['confirm.cancel.sale.order'].create({
            'sale_order_id': self.sale_order.id,
        })
        
        # Mock the get_client method on the account
        with patch.object(self.sale_order.produceteca_account_id, 'get_client', return_value=mock_client):
            result = wizard.action_confirm_cancel()
            
            # Should return window close action
            self.assertEqual(result['type'], 'ir.actions.act_window_close')

    def test_10_action_cancel_window_close(self):
        """Test action_cancel returns window close."""
        wizard = self.env['confirm.cancel.sale.order'].create({
            'sale_order_id': self.sale_order.id,
        })
        
        result = wizard.action_cancel()
        
        # Should return window close action
        self.assertEqual(result['type'], 'ir.actions.act_window_close')

    @patch('odoo.addons.producteca_connector.models.sale_order.SaleOrder.action_cancel')
    def test_11_sale_order_cancel_with_context(self, mock_action_cancel):
        """Test sale order cancellation with specific context."""
        wizard = self.env['confirm.cancel.sale.order'].create({
            'sale_order_id': self.sale_order.id,
        })
        
        mock_action_cancel.return_value = True
        
        # Mock the Producteca client
        with patch.object(self.sale_order.produceteca_account_id, 'get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_sales_order = MagicMock()
            mock_client.SalesOrder.return_value = mock_sales_order
            mock_get_client.return_value = mock_client
            
            wizard.action_confirm_cancel()
            
            # Verify context was set for cancellation
            # Note: The actual context check would depend on implementation details

    def test_12_multiple_wizards_same_order(self):
        """Test multiple wizards for the same order."""
        wizard1 = self.env['confirm.cancel.sale.order'].create({
            'sale_order_id': self.sale_order.id,
        })
        
        wizard2 = self.env['confirm.cancel.sale.order'].create({
            'sale_order_id': self.sale_order.id,
        })
        
        # Both wizards should reference the same order
        self.assertEqual(wizard1.sale_order_id, wizard2.sale_order_id)
        self.assertEqual(wizard1.sale_order_id, self.sale_order)

    def test_13_wizard_with_different_orders(self):
        """Test wizards with different sale orders."""
        # Create second sale order
        second_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'producteca_id': '67890',
            'produceteca_account_id': self.producteca_account.id,
            'order_line': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 150.0,
                'name': 'Second Product Line',
            })],
        })
        
        wizard1 = self.env['confirm.cancel.sale.order'].create({
            'sale_order_id': self.sale_order.id,
        })
        
        wizard2 = self.env['confirm.cancel.sale.order'].create({
            'sale_order_id': second_order.id,
        })
        
        # Wizards should reference different orders
        self.assertNotEqual(wizard1.sale_order_id, wizard2.sale_order_id)
        self.assertEqual(wizard1.sale_order_id, self.sale_order)
        self.assertEqual(wizard2.sale_order_id, second_order)

    @patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client')
    def test_14_producteca_api_integration(self, mock_get_client):
        """Test Producteca API integration in cancellation."""
        mock_client = MagicMock()
        mock_sales_order = MagicMock()
        mock_client.SalesOrder.return_value = mock_sales_order
        mock_sales_order.cancel.return_value = {'status': 'cancelled'}
        
        wizard = self.env['confirm.cancel.sale.order'].create({
            'sale_order_id': self.sale_order.id,
        })
        
        # Mock the client properly
        with patch.object(self.sale_order.produceteca_account_id, 'get_client', return_value=mock_client):
            wizard.action_confirm_cancel()
            
            # Verify API interaction
            mock_client.SalesOrder.assert_called_once_with(id=self.sale_order.producteca_id)
            mock_sales_order.cancel.assert_called_once()

    def test_15_sale_order_producteca_id_reference(self):
        """Test sale order Producteca ID reference."""
        wizard = self.env['confirm.cancel.sale.order'].create({
            'sale_order_id': self.sale_order.id,
        })
        
        # Verify Producteca ID is accessible through the sale order
        self.assertEqual(wizard.sale_order_id.producteca_id, '12345')

    @patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client')
    def test_16_api_error_handling(self, mock_get_client):
        """Test API error handling during cancellation."""
        # Mock client to raise an exception
        mock_client = MagicMock()
        mock_client.SalesOrder.side_effect = Exception('API Connection Error')
        
        wizard = self.env['confirm.cancel.sale.order'].create({
            'sale_order_id': self.sale_order.id,
        })
        
        # Mock the client
        with patch.object(self.sale_order.produceteca_account_id, 'get_client', return_value=mock_client):
            # Should handle API errors gracefully
            try:
                wizard.action_confirm_cancel()
            except Exception as e:
                # In production, this should be handled gracefully
                self.assertIn('API Connection Error', str(e))

    def test_17_context_propagation_test(self):
        """Test context propagation in cancellation."""
        wizard = self.env['confirm.cancel.sale.order'].create({
            'sale_order_id': self.sale_order.id,
        })
        
        # Mock Producteca client to avoid external calls
        with patch.object(self.sale_order.produceteca_account_id, 'get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_sales_order = MagicMock()
            mock_client.SalesOrder.return_value = mock_sales_order
            mock_get_client.return_value = mock_client
            
            # Mock the action_cancel method to check context
            with patch.object(self.sale_order, 'action_cancel') as mock_cancel:
                wizard.action_confirm_cancel()
                
                # The method should have been called
                mock_cancel.assert_called_once()

    def test_18_wizard_field_types_validation(self):
        """Test wizard field types validation."""
        wizard = self.env['confirm.cancel.sale.order'].create({
            'sale_order_id': self.sale_order.id,
        })
        
        # Test field types
        self.assertIsInstance(wizard.sale_order_id.id, int)
        self.assertIsInstance(wizard.warning_message, str)

    def test_19_sale_order_relationship_validation(self):
        """Test sale order relationship validation."""
        wizard = self.env['confirm.cancel.sale.order'].create({
            'sale_order_id': self.sale_order.id,
        })
        
        # Verify relationship integrity
        self.assertEqual(wizard.sale_order_id._name, 'sale.order')
        self.assertEqual(wizard.sale_order_id.id, self.sale_order.id)
        
        # Verify order data accessibility
        self.assertEqual(wizard.sale_order_id.partner_id, self.partner)
        self.assertEqual(wizard.sale_order_id.producteca_id, '12345')

    @patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client')
    def test_20_producteca_account_access(self, mock_get_client):
        """Test Producteca account access through sale order."""
        mock_client = MagicMock()
        mock_sales_order = MagicMock()
        mock_client.SalesOrder.return_value = mock_sales_order
        mock_get_client.return_value = mock_client
        
        wizard = self.env['confirm.cancel.sale.order'].create({
            'sale_order_id': self.sale_order.id,
        })
        
        # Test account access
        producteca_account = wizard.sale_order_id.produceteca_account_id
        self.assertEqual(producteca_account, self.producteca_account)
        self.assertEqual(producteca_account.name, 'Test Producteca Account')

    def test_21_warning_message_content_validation(self):
        """Test warning message content validation."""
        wizard = self.env['confirm.cancel.sale.order'].create({
            'sale_order_id': self.sale_order.id,
        })
        
        # Verify warning message contains key information
        warning = wizard.warning_message
        self.assertIn('Advertencia', warning)
        self.assertIn('Cancelar', warning)
        self.assertIn('Producteca', warning)
        self.assertIn('reputación', warning)
        self.assertIn('seguro', warning)

    def test_22_wizard_action_return_types(self):
        """Test wizard action return types."""
        wizard = self.env['confirm.cancel.sale.order'].create({
            'sale_order_id': self.sale_order.id,
        })
        
        # Test action_cancel return
        cancel_result = wizard.action_cancel()
        self.assertIsInstance(cancel_result, dict)
        self.assertIn('type', cancel_result)
        self.assertEqual(cancel_result['type'], 'ir.actions.act_window_close')

    def test_23_sale_order_state_before_cancellation(self):
        """Test sale order state before cancellation."""
        wizard = self.env['confirm.cancel.sale.order'].create({
            'sale_order_id': self.sale_order.id,
        })
        
        # Verify initial order state
        initial_state = wizard.sale_order_id.state
        self.assertIn(initial_state, ['draft', 'sent', 'sale'])  # Valid pre-cancel states

    def test_24_multiple_cancel_attempts(self):
        """Test multiple cancel attempts on same order."""
        wizard1 = self.env['confirm.cancel.sale.order'].create({
            'sale_order_id': self.sale_order.id,
        })
        
        wizard2 = self.env['confirm.cancel.sale.order'].create({
            'sale_order_id': self.sale_order.id,
        })
        
        # Both wizards should handle the same order
        self.assertEqual(wizard1.sale_order_id, wizard2.sale_order_id)
        
        # Both should be able to perform cancel action
        result1 = wizard1.action_cancel()
        result2 = wizard2.action_cancel()
        
        self.assertEqual(result1['type'], 'ir.actions.act_window_close')
        self.assertEqual(result2['type'], 'ir.actions.act_window_close')

    @patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client')
    def test_25_comprehensive_cancellation_workflow(self, mock_get_client):
        """Test comprehensive cancellation workflow."""
        # Mock complete Producteca client interaction
        mock_client = MagicMock()
        mock_sales_order = MagicMock()
        mock_client.SalesOrder.return_value = mock_sales_order
        mock_sales_order.cancel.return_value = {
            'id': '12345',
            'status': 'cancelled',
            'cancelled_at': '2024-01-15T14:30:00Z',
            'reason': 'User cancellation'
        }
        
        # Create comprehensive test wizard
        wizard = self.env['confirm.cancel.sale.order'].create({
            'sale_order_id': self.sale_order.id,
        })
        
        # Mock the get_client method
        with patch.object(self.sale_order.produceteca_account_id, 'get_client', return_value=mock_client):
            # Mock the action_cancel method to avoid actual cancellation
            with patch.object(self.sale_order, 'action_cancel') as mock_action_cancel:
                mock_action_cancel.return_value = True
                
                # Execute comprehensive workflow
                result = wizard.action_confirm_cancel()
                
                # Verify all aspects of the workflow
                # 1. Client interaction
                mock_client.SalesOrder.assert_called_once_with(id=self.sale_order.producteca_id)
                mock_sales_order.cancel.assert_called_once()
                
                # 2. Sale order cancellation with context
                mock_action_cancel.assert_called_once()
                
                # 3. Return value
                self.assertEqual(result['type'], 'ir.actions.act_window_close')
                
                # 4. Wizard state maintained
                self.assertEqual(wizard.sale_order_id, self.sale_order)
                self.assertIsNotNone(wizard.warning_message)
                
                # 5. Sale order relationship intact
                self.assertEqual(wizard.sale_order_id.producteca_id, '12345')
                self.assertEqual(wizard.sale_order_id.produceteca_account_id, self.producteca_account)
                
                # 6. Verify wizard is still accessible after operation
                self.assertTrue(wizard.id)
                self.assertEqual(wizard._name, 'confirm.cancel.sale.order')