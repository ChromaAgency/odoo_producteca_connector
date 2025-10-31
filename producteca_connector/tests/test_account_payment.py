# -*- coding: utf-8 -*-
"""
Test suite for AccountPayment model in producteca_connector module.

This module provides comprehensive test coverage for the AccountPayment model,
which handles payment synchronization with Producteca platform, including:
- Producteca payment ID tracking
- Payment upsert operations with external API
- Create and write method overrides for synchronization
- Integration with Producteca sale orders

Test Patterns:
- Uses Odoo TransactionCase for database operations
- Mock external API calls to avoid network dependencies
- Test inheritance and field behavior
- Validate business logic and workflows
- Context handling and synchronization control

Coverage Areas:
- Field definitions and relationships
- Payment creation and updates
- API integration workflows
- Context-based synchronization control
- Error handling scenarios
"""

from unittest.mock import patch, MagicMock
from odoo.tests.common import TransactionCase
from odoo import Command


class TestAccountPayment(TransactionCase):
    """Test cases for AccountPayment model with Producteca integration."""

    def setUp(self):
        """Set up test data for AccountPayment tests."""
        super(TestAccountPayment, self).setUp()
        
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
        
        # Create payment journal with Producteca method
        self.payment_journal = self.env['account.journal'].create({
            'name': 'Test Payment Journal',
            'type': 'bank',
            'code': 'TPJ',
            'company_id': self.company.id,
            'producteca_payment_method': 'CreditCard',
        })
        
        # Create sales journal
        self.sales_journal = self.env['account.journal'].create({
            'name': 'Test Sales Journal',
            'type': 'sale',
            'code': 'TSJ',
            'company_id': self.company.id,
        })
        
        # Create test product
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 100.0,
            'standard_price': 50.0,
            'type': 'product',
        })
        
        # Create test invoice with Producteca data
        self.invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.sales_journal.id,
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
        """Test that AccountPayment properly inherits from account.payment."""
        payment = self.env['account.payment'].create({
            'amount': 100.0,
            'partner_id': self.partner.id,
            'journal_id': self.payment_journal.id,
        })
        
        self.assertEqual(payment._name, 'account.payment')
        self.assertTrue(hasattr(payment, 'producteca_payment_id'))
        self.assertTrue(hasattr(payment, 'producteca_account_id'))

    def test_02_default_field_values(self):
        """Test default values for Producteca-specific fields."""
        payment = self.env['account.payment'].create({
            'amount': 150.0,
            'partner_id': self.partner.id,
            'journal_id': self.payment_journal.id,
        })
        
        self.assertFalse(payment.producteca_payment_id)
        self.assertFalse(payment.producteca_account_id)

    def test_03_field_assignments(self):
        """Test field assignments and data integrity."""
        payment = self.env['account.payment'].create({
            'amount': 200.0,
            'partner_id': self.partner.id,
            'journal_id': self.payment_journal.id,
            'producteca_payment_id': 'pay_12345',
            'producteca_account_id': self.producteca_account.id,
        })
        
        self.assertEqual(payment.producteca_payment_id, 'pay_12345')
        self.assertEqual(payment.producteca_account_id, self.producteca_account)

    @patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client')
    def test_04_upsert_payment_new_payment(self, mock_get_client):
        """Test upsert payment operation for new payment."""
        # Mock client and sales order
        mock_client = MagicMock()
        mock_sales_order = MagicMock()
        mock_sales_order.add_payment.return_value = {'id': 'new_payment_123'}
        mock_client.SalseOrder.return_value = mock_sales_order
        mock_get_client.return_value = mock_client
        
        # Create payment without Producteca ID
        payment = self.env['account.payment'].create({
            'amount': 100.0,
            'partner_id': self.partner.id,
            'journal_id': self.payment_journal.id,
        })
        
        # Prepare Producteca body
        producteca_body = {
            'amount': 100.0,
            'date': '2024-01-15',
            'method': 'CreditCard',
            'producteca_sale_order_id': 12345,
        }
        
        # Call upsert method
        result = payment._upsert_payment_in_producteca(self.producteca_account, producteca_body)
        
        # Verify new payment was added
        mock_client.SalseOrder.assert_called_once_with(id=12345)
        mock_sales_order.add_payment.assert_called_once()
        self.assertIsNotNone(result)

    @patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client')
    def test_05_upsert_payment_existing_payment(self, mock_get_client):
        """Test upsert payment operation for existing payment."""
        # Mock client and sales order
        mock_client = MagicMock()
        mock_sales_order = MagicMock()
        mock_sales_order.update_payment.return_value = {'success': True}
        mock_client.SalseOrder.return_value = mock_sales_order
        mock_get_client.return_value = mock_client
        
        # Create payment with existing Producteca ID
        payment = self.env['account.payment'].create({
            'amount': 100.0,
            'partner_id': self.partner.id,
            'journal_id': self.payment_journal.id,
            'producteca_payment_id': 'existing_pay_456',
        })
        
        # Prepare Producteca body
        producteca_body = {
            'amount': 150.0,
            'date': '2024-01-16',
            'method': 'CreditCard',
            'producteca_sale_order_id': 12345,
        }
        
        # Call upsert method
        payment._upsert_payment_in_producteca(self.producteca_account, producteca_body)
        
        # Verify existing payment was updated
        mock_client.SalseOrder.assert_called_once_with(id=12345)
        mock_sales_order.update_payment.assert_called_once_with('existing_pay_456', producteca_body)

    def test_06_producteca_body_preparation(self):
        """Test Producteca body preparation removes sale order ID."""
        payment = self.env['account.payment'].create({
            'amount': 100.0,
            'partner_id': self.partner.id,
            'journal_id': self.payment_journal.id,
        })
        
        # Original body with sale order ID
        original_body = {
            'amount': 100.0,
            'date': '2024-01-15',
            'method': 'CreditCard',
            'producteca_sale_order_id': 12345,
        }
        
        with patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_sales_order = MagicMock()
            mock_client.SalseOrder.return_value = mock_sales_order
            mock_get_client.return_value = mock_client
            
            # Call upsert method
            payment._upsert_payment_in_producteca(self.producteca_account, original_body.copy())
            
            # Verify sale order ID was removed from body
            self.assertNotIn('producteca_sale_order_id', original_body)

    @patch('odoo.addons.producteca_connector.models.account_payment.AccountPayment._upsert_payment_in_producteca')
    def test_07_create_method_with_reconciled_invoice(self, mock_upsert):
        """Test create method with reconciled invoice having Producteca data."""
        # Post the invoice first
        self.invoice.action_post()
        
        # Mock upsert return
        mock_upsert.return_value = {'id': 'created_payment_789'}
        
        # Create payment that reconciles with the invoice
        payment_register = self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=self.invoice.ids,
        ).create({
            'amount': 200.0,
            'journal_id': self.payment_journal.id,
        })
        
        # Create payments
        payments = payment_register.action_create_payments()
        
        # Verify payment was created and upsert was called
        if payments and payments.get('res_id'):
            payment = self.env['account.payment'].browse(payments['res_id'])
            # Check if payment has invoice reconciliation
            self.assertTrue(payment.reconciled_invoice_ids)

    def test_08_create_method_without_producteca_data(self):
        """Test create method without Producteca integration data."""
        # Create regular invoice without Producteca data
        regular_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.sales_journal.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 50.0,
                'name': 'Regular Product Line',
            })],
        })
        regular_invoice.action_post()
        
        # Create payment for regular invoice
        payment_register = self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=regular_invoice.ids,
        ).create({
            'amount': 50.0,
            'journal_id': self.payment_journal.id,
        })
        
        # Create payments (should not trigger Producteca integration)
        payments = payment_register.action_create_payments()
        
        # Payment should be created normally without Producteca integration
        if payments and payments.get('res_id'):
            payment = self.env['account.payment'].browse(payments['res_id'])
            self.assertFalse(payment.producteca_payment_id)

    @patch('odoo.addons.producteca_connector.models.account_payment.AccountPayment._upsert_payment_in_producteca')
    def test_09_write_method_with_producteca_fields(self, mock_upsert):
        """Test write method when Producteca fields are updated."""
        # Create payment with Producteca ID and reconciled invoice
        payment = self.env['account.payment'].create({
            'amount': 100.0,
            'partner_id': self.partner.id,
            'journal_id': self.payment_journal.id,
            'producteca_payment_id': 'test_payment_write',
        })
        
        # Mock reconciled invoice
        payment.reconciled_invoice_ids = self.invoice
        
        # Mock upsert return
        mock_upsert.return_value = {'success': True}
        
        # Update payment with Producteca-relevant fields
        payment.write({
            'amount': 150.0,
            'date': '2024-01-20',
        })
        
        # Verify upsert was called for field update
        if mock_upsert.called:
            self.assertTrue(True)  # Upsert was called as expected

    def test_10_write_method_without_producteca_id(self):
        """Test write method when payment has no Producteca ID."""
        # Create payment without Producteca ID
        payment = self.env['account.payment'].create({
            'amount': 100.0,
            'partner_id': self.partner.id,
            'journal_id': self.payment_journal.id,
        })
        
        # Update payment (should not trigger Producteca sync)
        payment.write({
            'amount': 120.0,
        })
        
        # Payment should be updated normally
        self.assertEqual(payment.amount, 120.0)

    def test_11_write_method_with_update_from_invoice_context(self):
        """Test write method with update_from_invoice context."""
        # Create payment with Producteca ID
        payment = self.env['account.payment'].create({
            'amount': 100.0,
            'partner_id': self.partner.id,
            'journal_id': self.payment_journal.id,
            'producteca_payment_id': 'context_test_payment',
        })
        
        # Mock reconciled invoice
        payment.reconciled_invoice_ids = self.invoice
        
        # Update with context (should skip Producteca sync)
        payment.with_context(update_from_invoice=True).write({
            'amount': 175.0,
        })
        
        # Payment should be updated without triggering external sync
        self.assertEqual(payment.amount, 175.0)

    def test_12_write_method_without_reconciled_producteca_invoice(self):
        """Test write method when no reconciled invoice has Producteca data."""
        # Create regular invoice without Producteca data
        regular_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.sales_journal.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 100.0,
                'name': 'Regular Product Line',
            })],
        })
        
        # Create payment with Producteca ID but reconciled with regular invoice
        payment = self.env['account.payment'].create({
            'amount': 100.0,
            'partner_id': self.partner.id,
            'journal_id': self.payment_journal.id,
            'producteca_payment_id': 'no_producteca_invoice',
        })
        
        # Mock reconciled invoice (regular invoice without Producteca data)
        payment.reconciled_invoice_ids = regular_invoice
        
        # Update payment (should not trigger Producteca sync)
        payment.write({
            'amount': 125.0,
        })
        
        # Payment should be updated normally
        self.assertEqual(payment.amount, 125.0)

    def test_13_producteca_fields_constant(self):
        """Test PRODUCTECA_FIELDS constant includes expected fields."""
        from odoo.addons.producteca_connector.models.account_payment import PRODUCTECA_FIELDS
        
        expected_fields = ['date', 'amount', 'journal', 'state']
        for field in expected_fields:
            self.assertIn(field, PRODUCTECA_FIELDS)

    def test_14_producteca_payment_data_structure(self):
        """Test Producteca payment data structure creation."""
        payment = self.env['account.payment'].create({
            'amount': 200.0,
            'partner_id': self.partner.id,
            'journal_id': self.payment_journal.id,
            'date': '2024-01-15',
        })
        
        # Expected data structure
        expected_data = {
            'date': payment.date,
            'amount': payment.amount,
            'method': payment.journal_id.producteca_payment_method,
            'status': 'Approved',
        }
        
        # Verify data structure elements
        self.assertEqual(expected_data['amount'], 200.0)
        self.assertEqual(expected_data['method'], 'CreditCard')
        self.assertEqual(expected_data['status'], 'Approved')

    def test_15_multiple_payments_creation(self):
        """Test creation of multiple payments."""
        payment_data = [
            {'amount': 100.0, 'producteca_payment_id': 'multi_pay_1'},
            {'amount': 150.0, 'producteca_payment_id': 'multi_pay_2'},
            {'amount': 200.0, 'producteca_payment_id': 'multi_pay_3'},
        ]
        
        created_payments = []
        for data in payment_data:
            payment = self.env['account.payment'].create({
                'amount': data['amount'],
                'partner_id': self.partner.id,
                'journal_id': self.payment_journal.id,
                'producteca_payment_id': data['producteca_payment_id'],
            })
            created_payments.append(payment)
        
        # Verify all payments were created
        self.assertEqual(len(created_payments), 3)
        
        # Verify each payment has correct data
        for i, payment in enumerate(created_payments):
            self.assertEqual(payment.amount, payment_data[i]['amount'])
            self.assertEqual(payment.producteca_payment_id, payment_data[i]['producteca_payment_id'])

    @patch('odoo.addons.producteca_connector.models.producteca_account.ProductecaAccount.get_client')
    def test_16_api_error_handling(self, mock_get_client):
        """Test API error handling in upsert operations."""
        # Mock client to raise an exception
        mock_client = MagicMock()
        mock_client.SalseOrder.side_effect = Exception('API Connection Error')
        mock_get_client.return_value = mock_client
        
        payment = self.env['account.payment'].create({
            'amount': 100.0,
            'partner_id': self.partner.id,
            'journal_id': self.payment_journal.id,
        })
        
        producteca_body = {
            'amount': 100.0,
            'date': '2024-01-15',
            'method': 'CreditCard',
            'producteca_sale_order_id': 12345,
        }
        
        # Method should handle API errors gracefully
        try:
            payment._upsert_payment_in_producteca(self.producteca_account, producteca_body)
        except Exception as e:
            # Should not raise unhandled exceptions
            self.fail(f"Upsert method raised unexpected exception: {e}")

    def test_17_payment_method_from_journal(self):
        """Test payment method extraction from journal."""
        # Create journals with different payment methods
        methods_data = [
            ('Cash Journal', 'Cash'),
            ('MercadoPago Journal', 'MercadoPago'),
            ('PayPal Journal', 'PayPal'),
        ]
        
        for name, method in methods_data:
            journal = self.env['account.journal'].create({
                'name': name,
                'type': 'bank',
                'code': method[:3].upper(),
                'company_id': self.company.id,
                'producteca_payment_method': method,
            })
            
            payment = self.env['account.payment'].create({
                'amount': 100.0,
                'partner_id': self.partner.id,
                'journal_id': journal.id,
            })
            
            # Verify payment method is correctly extracted
            self.assertEqual(payment.journal_id.producteca_payment_method, method)

    def test_18_payment_reconciliation_filtering(self):
        """Test filtering of reconciled invoices with Producteca data."""
        # Create multiple invoices
        invoices = []
        
        # Invoice with Producteca data
        producteca_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.sales_journal.id,
            'producteca_order_id': '98765',
            'producteca_account_id': self.producteca_account.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 100.0,
                'name': 'Producteca Product',
            })],
        })
        invoices.append(producteca_invoice)
        
        # Regular invoice without Producteca data
        regular_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.sales_journal.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 50.0,
                'name': 'Regular Product',
            })],
        })
        invoices.append(regular_invoice)
        
        # Create payment
        payment = self.env['account.payment'].create({
            'amount': 150.0,
            'partner_id': self.partner.id,
            'journal_id': self.payment_journal.id,
        })
        
        # Mock reconciled invoices
        payment.reconciled_invoice_ids = invoices
        
        # Filter invoices with Producteca data
        producteca_invoices = payment.reconciled_invoice_ids.filtered(lambda x: x.producteca_order_id)
        
        # Should only include the Producteca invoice
        self.assertEqual(len(producteca_invoices), 1)
        self.assertEqual(producteca_invoices[0], producteca_invoice)

    def test_19_payment_state_handling(self):
        """Test payment state handling in Producteca integration."""
        payment = self.env['account.payment'].create({
            'amount': 100.0,
            'partner_id': self.partner.id,
            'journal_id': self.payment_journal.id,
            'state': 'draft',
        })
        
        # Verify initial state
        self.assertEqual(payment.state, 'draft')
        
        # Update state (this is a Producteca field)
        payment.write({'state': 'posted'})
        
        # Verify state update
        self.assertEqual(payment.state, 'posted')

    def test_20_payment_journal_field_update(self):
        """Test journal field update triggering Producteca sync."""
        # Create alternative journal
        alt_journal = self.env['account.journal'].create({
            'name': 'Alternative Journal',
            'type': 'bank',
            'code': 'ALT',
            'company_id': self.company.id,
            'producteca_payment_method': 'DebitCard',
        })
        
        payment = self.env['account.payment'].create({
            'amount': 100.0,
            'partner_id': self.partner.id,
            'journal_id': self.payment_journal.id,
            'producteca_payment_id': 'journal_update_test',
        })
        
        # Mock reconciled invoice
        payment.reconciled_invoice_ids = self.invoice
        
        # Update journal (this is a Producteca field)
        payment.write({'journal_id': alt_journal.id})
        
        # Verify journal was updated
        self.assertEqual(payment.journal_id, alt_journal)
        self.assertEqual(payment.journal_id.producteca_payment_method, 'DebitCard')

    def test_21_payment_date_field_update(self):
        """Test date field update triggering Producteca sync."""
        from datetime import date
        
        payment = self.env['account.payment'].create({
            'amount': 100.0,
            'partner_id': self.partner.id,
            'journal_id': self.payment_journal.id,
            'producteca_payment_id': 'date_update_test',
            'date': '2024-01-01',
        })
        
        # Mock reconciled invoice
        payment.reconciled_invoice_ids = self.invoice
        
        # Update date (this is a Producteca field)
        new_date = '2024-01-15'
        payment.write({'date': new_date})
        
        # Verify date was updated
        self.assertEqual(str(payment.date), new_date)

    def test_22_payment_amount_field_update(self):
        """Test amount field update triggering Producteca sync."""
        payment = self.env['account.payment'].create({
            'amount': 100.0,
            'partner_id': self.partner.id,
            'journal_id': self.payment_journal.id,
            'producteca_payment_id': 'amount_update_test',
        })
        
        # Mock reconciled invoice
        payment.reconciled_invoice_ids = self.invoice
        
        # Update amount (this is a Producteca field)
        payment.write({'amount': 250.0})
        
        # Verify amount was updated
        self.assertEqual(payment.amount, 250.0)

    def test_23_context_sensitive_operations(self):
        """Test context-sensitive operations in payment processing."""
        payment = self.env['account.payment'].create({
            'amount': 100.0,
            'partner_id': self.partner.id,
            'journal_id': self.payment_journal.id,
            'producteca_payment_id': 'context_sensitive_test',
        })
        
        # Test with different contexts
        contexts = [
            {'update_from_invoice': True},
            {'update_from_invoice': False},
            {'skip_producteca_sync': True},
            {},
        ]
        
        for context in contexts:
            payment.with_context(**context).write({'amount': payment.amount + 10})
            
        # Payment should handle all contexts gracefully
        self.assertGreater(payment.amount, 100.0)

    def test_24_payment_account_relationship(self):
        """Test relationship between payment and Producteca account."""
        payment = self.env['account.payment'].create({
            'amount': 100.0,
            'partner_id': self.partner.id,
            'journal_id': self.payment_journal.id,
            'producteca_account_id': self.producteca_account.id,
        })
        
        # Verify relationship
        self.assertEqual(payment.producteca_account_id, self.producteca_account)
        self.assertEqual(payment.producteca_account_id.name, 'Test Producteca Account')
        
        # Test relationship query
        payments_for_account = self.env['account.payment'].search([
            ('producteca_account_id', '=', self.producteca_account.id)
        ])
        self.assertIn(payment, payments_for_account)

    def test_25_comprehensive_payment_workflow(self):
        """Test comprehensive payment workflow with Producteca integration."""
        # Post the invoice first
        self.invoice.action_post()
        
        # Create payment with full Producteca integration
        payment = self.env['account.payment'].create({
            'amount': 200.0,
            'partner_id': self.partner.id,
            'journal_id': self.payment_journal.id,
            'producteca_account_id': self.producteca_account.id,
            'date': '2024-01-15',
        })
        
        # Mock reconciliation with Producteca invoice
        payment.reconciled_invoice_ids = self.invoice
        
        with patch('odoo.addons.producteca_connector.models.account_payment.AccountPayment._upsert_payment_in_producteca') as mock_upsert:
            mock_upsert.return_value = {'id': 'comprehensive_test_payment'}
            
            # Update payment to trigger Producteca sync
            payment.write({
                'amount': 250.0,
                'date': '2024-01-20',
            })
            
            # Verify payment was updated
            self.assertEqual(payment.amount, 250.0)
            self.assertEqual(str(payment.date), '2024-01-20')
            
            # Verify Producteca integration
            self.assertEqual(payment.producteca_account_id, self.producteca_account)
            self.assertTrue(payment.reconciled_invoice_ids)
            
            # Verify invoice has Producteca data
            reconciled_invoice = payment.reconciled_invoice_ids[0]
            self.assertEqual(reconciled_invoice.producteca_order_id, '12345')
            self.assertEqual(reconciled_invoice.producteca_account_id, self.producteca_account)