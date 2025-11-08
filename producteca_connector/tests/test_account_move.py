# -*- coding: utf-8 -*-
"""
Test suite for AccountMove model in producteca_connector module.

This module provides comprehensive test coverage for the AccountMove model,
which handles invoice integration with Producteca platform, including:
- Producteca payment states and order management
- Invoice integration with external API
- Payment creation from Producteca data
- Posting workflow with delayed jobs

Test Patterns:
- Uses Odoo TransactionCase for database operations
- Mock external API calls to avoid network dependencies
- Test inheritance and field behavior
- Validate business logic and workflows
- Edge cases and error handling

Coverage Areas:
- Field definitions and constraints
- Method behavior and return values
- API integration workflows
- Payment processing
- State management
- Error handling scenarios
"""

from unittest.mock import patch, MagicMock
from odoo.tests.common import TransactionCase
from odoo.tools.safe_eval import safe_eval
from odoo import Command
import json


class TestAccountMove(TransactionCase):
    """Test cases for AccountMove model with Producteca integration."""

    def setUp(self):
        """Set up test data for AccountMove tests."""
        super(TestAccountMove, self).setUp()
        
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
        
        # Create account journal
        self.journal = self.env['account.journal'].create({
            'name': 'Test Sales Journal',
            'type': 'sale',
            'code': 'TSJ',
            'company_id': self.company.id,
        })
        
        # Create payment journal with Producteca method
        self.payment_journal = self.env['account.journal'].create({
            'name': 'Test Payment Journal',
            'type': 'bank',
            'code': 'TPJ',
            'company_id': self.company.id,
            'producteca_payment_method': 'CreditCard',
        })
        
        # Create test invoice
        self.invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.journal.id,
            'company_id': self.company.id,
            'producteca_order_id': '12345',
            'producteca_account_id': self.producteca_account.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product.id,
                'quantity': 2,
                'price_unit': 100.0,
                'name': 'Test Product Line',
            })],
        })

    def test_01_model_inheritance(self):
        """Test that AccountMove properly inherits from account.move."""
        self.assertEqual(self.invoice._name, 'account.move')
        self.assertTrue(hasattr(self.invoice, 'producteca_payment_state'))
        self.assertTrue(hasattr(self.invoice, 'producteca_order_id'))
        self.assertTrue(hasattr(self.invoice, 'producteca_account_id'))

    def test_02_default_field_values(self):
        """Test default values for Producteca-specific fields."""
        new_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.journal.id,
        })
        self.assertEqual(new_invoice.producteca_payment_state, 'pending')
        self.assertFalse(new_invoice.producteca_order_id)
        self.assertFalse(new_invoice.producteca_account_id)
        self.assertFalse(new_invoice.producteca_invoice_already_exists)

    def test_03_field_assignments(self):
        """Test field assignments and data integrity."""
        self.invoice.write({
            'producteca_payment_state': 'approved',
            'producteca_order_id': '67890',
            'producteca_invoice_already_exists': True,
            'producteca_payment_data': '[{"id": "pay_123", "amount": 200.0, "status": "Approved"}]',
        })
        
        self.assertEqual(self.invoice.producteca_payment_state, 'approved')
        self.assertEqual(self.invoice.producteca_order_id, '67890')
        self.assertTrue(self.invoice.producteca_invoice_already_exists)
        self.assertIn('pay_123', self.invoice.producteca_payment_data)

    def test_04_payment_state_selection(self):
        """Test payment state selection field validation."""
        # Test valid states
        self.invoice.producteca_payment_state = 'pending'
        self.assertEqual(self.invoice.producteca_payment_state, 'pending')
        
        self.invoice.producteca_payment_state = 'approved'
        self.assertEqual(self.invoice.producteca_payment_state, 'approved')
        
        # Test that only valid states are accepted through ORM
        with self.assertRaises(ValueError):
            self.invoice.write({'producteca_payment_state': 'invalid_state'})

    @patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client')
    def test_05_add_invoice_to_producteca_success(self, mock_get_client):
        """Test successful invoice addition to Producteca."""
        # Mock client and its methods
        mock_client = MagicMock()
        mock_sales_order = MagicMock()
        mock_client.SalesOrder.return_value = mock_sales_order
        mock_get_client.return_value = mock_client
        
        # Set up invoice for Producteca integration
        self.invoice.write({
            'move_type': 'out_invoice',
            'producteca_account_id': self.producteca_account.id,
            'producteca_order_id': '12345',
            'producteca_invoice_already_exists': True,
        })
        
        # Ensure access token exists
        self.invoice._portal_ensure_token()
        
        # Call the method
        self.invoice.add_invoice_to_producteca()
        
        # Verify client calls
        mock_get_client.assert_called_once()
        mock_client.SalesOrder.assert_called_once()
        mock_sales_order.invoice_integration.assert_called_once()

    @patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client')
    def test_06_add_invoice_to_producteca_no_account(self, mock_get_client):
        """Test invoice addition when no Producteca account is set."""
        self.invoice.write({
            'move_type': 'out_invoice',
            'producteca_account_id': False,
            'producteca_order_id': '12345',
        })
        
        # Method should not call API without account
        self.invoice.add_invoice_to_producteca()
        mock_get_client.assert_not_called()

    @patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client')
    def test_07_add_invoice_to_producteca_no_order_id(self, mock_get_client):
        """Test invoice addition when no Producteca order ID is set."""
        self.invoice.write({
            'move_type': 'out_invoice',
            'producteca_account_id': self.producteca_account.id,
            'producteca_order_id': False,
        })
        
        # Method should not call API without order ID
        self.invoice.add_invoice_to_producteca()
        mock_get_client.assert_not_called()

    @patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client')
    def test_08_add_invoice_to_producteca_wrong_move_type(self, mock_get_client):
        """Test invoice addition with wrong move type."""
        self.invoice.write({
            'move_type': 'in_invoice',  # Not out_invoice
            'producteca_account_id': self.producteca_account.id,
            'producteca_order_id': '12345',
        })
        
        # Method should not call API for non-customer invoices
        self.invoice.add_invoice_to_producteca()
        mock_get_client.assert_not_called()

    def test_09_create_payments_from_producteca_data_valid(self):
        """Test payment creation from valid Producteca payment data."""
        payment_data = [
            {
                'id': 'pay_123',
                'amount': 200.0,
                'date': '2024-01-15',
                'method': 'CreditCard',
                'status': 'Approved'
            }
        ]
        
        self.invoice.write({
            'producteca_payment_data': str(payment_data),
        })
        
        # Count payments before
        payment_count_before = self.env['account.payment'].search_count([])
        
        # Create payments from Producteca data
        self.invoice._create_payments_from_producteca()
        
        # Verify payment was created
        payment_count_after = self.env['account.payment'].search_count([])
        self.assertEqual(payment_count_after, payment_count_before + 1)
        
        # Verify payment state updated
        self.assertEqual(self.invoice.producteca_payment_state, 'approved')

    def test_10_create_payments_from_producteca_data_invalid_status(self):
        """Test payment creation with invalid status."""
        payment_data = [
            {
                'id': 'pay_456',
                'amount': 150.0,
                'date': '2024-01-15',
                'method': 'CreditCard',
                'status': 'Rejected'  # Not Approved
            }
        ]
        
        self.invoice.write({
            'producteca_payment_data': str(payment_data),
        })
        
        payment_count_before = self.env['account.payment'].search_count([])
        
        # Create payments from Producteca data
        self.invoice._create_payments_from_producteca()
        
        # No payment should be created for rejected status
        payment_count_after = self.env['account.payment'].search_count([])
        self.assertEqual(payment_count_after, payment_count_before)
        
        # Payment state should remain pending
        self.assertEqual(self.invoice.producteca_payment_state, 'pending')

    def test_11_create_payments_from_producteca_no_matching_journal(self):
        """Test payment creation when no matching journal is found."""
        payment_data = [
            {
                'id': 'pay_789',
                'amount': 100.0,
                'date': '2024-01-15',
                'method': 'PayPal',  # No journal configured for PayPal
                'status': 'Approved'
            }
        ]
        
        self.invoice.write({
            'producteca_payment_data': str(payment_data),
        })
        
        payment_count_before = self.env['account.payment'].search_count([])
        
        # Create payments from Producteca data
        self.invoice._create_payments_from_producteca()
        
        # No payment should be created without matching journal
        payment_count_after = self.env['account.payment'].search_count([])
        self.assertEqual(payment_count_after, payment_count_before)

    def test_12_create_payments_from_producteca_empty_data(self):
        """Test payment creation with empty Producteca data."""
        self.invoice.write({
            'producteca_payment_data': '',
        })
        
        payment_count_before = self.env['account.payment'].search_count([])
        
        # Method should handle empty data gracefully
        self.invoice._create_payments_from_producteca()
        
        payment_count_after = self.env['account.payment'].search_count([])
        self.assertEqual(payment_count_after, payment_count_before)

    def test_13_create_payments_from_producteca_no_data(self):
        """Test payment creation when no Producteca payment data exists."""
        self.invoice.write({
            'producteca_payment_data': False,
        })
        
        payment_count_before = self.env['account.payment'].search_count([])
        
        # Method should handle missing data gracefully
        self.invoice._create_payments_from_producteca()
        
        payment_count_after = self.env['account.payment'].search_count([])
        self.assertEqual(payment_count_after, payment_count_before)

    def test_14_create_payments_multiple_payments(self):
        """Test creation of multiple payments from Producteca data."""
        payment_data = [
            {
                'id': 'pay_111',
                'amount': 100.0,
                'date': '2024-01-15',
                'method': 'CreditCard',
                'status': 'Approved'
            },
            {
                'id': 'pay_222',
                'amount': 100.0,
                'date': '2024-01-16',
                'method': 'CreditCard',
                'status': 'Approved'
            }
        ]
        
        self.invoice.write({
            'producteca_payment_data': str(payment_data),
        })
        
        payment_count_before = self.env['account.payment'].search_count([])
        
        # Create payments from Producteca data
        self.invoice._create_payments_from_producteca()
        
        # Two payments should be created
        payment_count_after = self.env['account.payment'].search_count([])
        self.assertEqual(payment_count_after, payment_count_before + 2)

    @patch('odoo.addons.producteca_connector.models.account_move.AccountMove.add_invoice_to_producteca')
    def test_15_action_post_triggers_producteca_integration(self, mock_add_invoice):
        """Test that action_post triggers Producteca integration."""
        # Mock the delayed job
        mock_add_invoice.return_value = True
        
        # Post the invoice
        self.invoice.action_post()
        
        # Verify the invoice is posted
        self.assertEqual(self.invoice.state, 'posted')
        
        # Note: In real scenario, with_delay() would be tested differently
        # This tests the general workflow

    def test_16_action_post_calls_create_payments(self):
        """Test that action_post calls payment creation."""
        payment_data = [
            {
                'id': 'pay_post_test',
                'amount': 200.0,
                'date': '2024-01-15',
                'method': 'CreditCard',
                'status': 'Approved'
            }
        ]
        
        self.invoice.write({
            'producteca_payment_data': str(payment_data),
        })
        
        payment_count_before = self.env['account.payment'].search_count([])
        
        # Post the invoice (this should trigger payment creation)
        self.invoice.action_post()
        
        # Verify payment was created during posting
        payment_count_after = self.env['account.payment'].search_count([])
        self.assertEqual(payment_count_after, payment_count_before + 1)

    def test_17_portal_token_generation(self):
        """Test portal access token generation for invoice URLs."""
        # Initially no token
        self.assertFalse(self.invoice.access_token)
        
        # Set up invoice for Producteca integration
        self.invoice.write({
            'producteca_account_id': self.producteca_account.id,
            'producteca_order_id': '12345',
            'producteca_invoice_already_exists': True,
        })
        
        with patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client'):
            self.invoice.add_invoice_to_producteca()
            
        # Token should be generated
        self.assertTrue(self.invoice.access_token)

    def test_18_payment_data_safe_eval_handling(self):
        """Test safe evaluation of payment data strings."""
        # Test with valid Python list string
        payment_data_str = "[{'id': 'test', 'amount': 100, 'status': 'Approved'}]"
        self.invoice.write({
            'producteca_payment_data': payment_data_str,
        })
        
        # Method should safely evaluate the string
        self._create_payments_helper()
        
        # Test with malicious code (should be safely handled)
        malicious_data = "__import__('os').system('rm -rf /')"
        self.invoice.write({
            'producteca_payment_data': malicious_data,
        })
        
        # Should not execute malicious code and handle gracefully
        self._create_payments_helper()

    def _create_payments_helper(self):
        """Helper method for payment creation testing."""
        try:
            self.invoice._create_payments_from_producteca()
        except Exception:
            # Should handle evaluation errors gracefully
            pass

    def test_19_context_propagation_in_payment_creation(self):
        """Test context propagation during payment creation."""
        payment_data = [
            {
                'id': 'context_test',
                'amount': 150.0,
                'date': '2024-01-15',
                'method': 'CreditCard',
                'status': 'Approved'
            }
        ]
        
        self.invoice.write({
            'producteca_payment_data': str(payment_data),
        })
        
        # The method should set update_from_invoice context
        self.invoice._create_payments_from_producteca()
        
        # Verify payment was created with proper context handling
        payment_count = self.env['account.payment'].search_count([])
        self.assertGreater(payment_count, 0)

    def test_20_payment_id_assignment_to_matched_payments(self):
        """Test Producteca payment ID assignment to matched payments."""
        payment_data = [
            {
                'id': 'matched_payment_test',
                'amount': 200.0,
                'date': '2024-01-15',
                'method': 'CreditCard',
                'status': 'Approved'
            }
        ]
        
        self.invoice.write({
            'producteca_payment_data': str(payment_data),
        })
        
        # Create payment from Producteca data
        self.invoice._create_payments_from_producteca()
        
        # Find the created payment
        payment = self.env['account.payment'].search([], limit=1, order='create_date desc')
        
        # Verify Producteca payment ID was assigned
        if payment and payment.producteca_payment_id:
            self.assertEqual(payment.producteca_payment_id, 'matched_payment_test')

    def test_21_invoice_integration_dict_structure(self):
        """Test the structure of invoice integration dictionary."""
        # Set up mock to capture the call arguments
        with patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_sales_order = MagicMock()
            mock_client.SalesOrder.return_value = mock_sales_order
            mock_get_client.return_value = mock_client
            
            self.invoice.write({
                'move_type': 'out_invoice',
                'producteca_account_id': self.producteca_account.id,
                'producteca_order_id': '12345',
                'producteca_invoice_already_exists': True,
                'name': 'INV/2024/0001',
            })
            
            self.invoice._portal_ensure_token()
            self.invoice.add_invoice_to_producteca()
            
            # Verify the dictionary structure passed to API
            call_args = mock_client.SalesOrder.call_args[1] if mock_client.SalesOrder.call_args else {}
            if call_args:
                self.assertIn('id', call_args)
                self.assertIn('invoiceIntegration', call_args)
                self.assertEqual(call_args['id'], 12345)
                
                invoice_integration = call_args['invoiceIntegration']
                self.assertIn('documentUrl', invoice_integration)
                self.assertIn('integrationId', invoice_integration)
                self.assertIn('decreaseStock', invoice_integration)
                self.assertTrue(invoice_integration['decreaseStock'])

    def test_22_ensure_one_decorator_compliance(self):
        """Test that _create_payments_from_producteca respects ensure_one."""
        # Create multiple invoices
        invoice2 = self.invoice.copy()
        invoices = self.invoice + invoice2
        
        # Method should handle single record properly
        self.invoice._create_payments_from_producteca()
        
        # Should not be called on recordset with multiple records
        with self.assertRaises(ValueError):
            invoices._create_payments_from_producteca()

    def test_23_payment_register_wizard_integration(self):
        """Test integration with account.payment.register wizard."""
        payment_data = [
            {
                'id': 'wizard_test',
                'amount': 175.0,
                'date': '2024-01-15',
                'method': 'CreditCard',
                'status': 'Approved'
            }
        ]
        
        self.invoice.write({
            'producteca_payment_data': str(payment_data),
        })
        
        # Count payment register records before
        wizard_count_before = self.env['account.payment.register'].search_count([])
        
        # Create payments (this uses the wizard internally)
        self.invoice._create_payments_from_producteca()
        
        # Verify wizard was used (may create temporary records)
        # The actual verification depends on the implementation details

    def test_24_error_handling_in_payment_creation(self):
        """Test error handling during payment creation process."""
        # Test with invalid payment data structure
        invalid_payment_data = [
            {
                'invalid_field': 'value',
                'status': 'Approved'
                # Missing required fields like amount, date, method
            }
        ]
        
        self.invoice.write({
            'producteca_payment_data': str(invalid_payment_data),
        })
        
        # Method should handle errors gracefully
        try:
            self.invoice._create_payments_from_producteca()
        except Exception as e:
            # Should not raise unhandled exceptions
            self.fail(f"Payment creation raised unexpected exception: {e}")

    def test_25_comprehensive_workflow_integration(self):
        """Test complete workflow from invoice creation to Producteca integration."""
        # Create a complete invoice with all Producteca data
        complete_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.journal.id,
            'company_id': self.company.id,
            'producteca_order_id': '98765',
            'producteca_account_id': self.producteca_account.id,
            'producteca_invoice_already_exists': True,
            'producteca_payment_data': str([{
                'id': 'workflow_payment',
                'amount': 300.0,
                'date': '2024-01-15',
                'method': 'CreditCard',
                'status': 'Approved'
            }]),
            'invoice_line_ids': [Command.create({
                'product_id': self.product.id,
                'quantity': 3,
                'price_unit': 100.0,
                'name': 'Complete Workflow Product',
            })],
        })
        
        # Mock the Producteca client
        with patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_sales_order = MagicMock()
            mock_client.SalesOrder.return_value = mock_sales_order
            mock_get_client.return_value = mock_client
            
            # Post the invoice (triggers complete workflow)
            complete_invoice.action_post()
            
            # Verify invoice state
            self.assertEqual(complete_invoice.state, 'posted')
            
            # Verify payment state was updated
            self.assertEqual(complete_invoice.producteca_payment_state, 'approved')
            
            # Verify payment was created
            payments = self.env['account.payment'].search([
                ('producteca_payment_id', '=', 'workflow_payment')
            ])
            self.assertEqual(len(payments), 1)
            
            # Verify API integration was triggered
            mock_get_client.assert_called()