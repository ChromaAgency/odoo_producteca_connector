# -*- coding: utf-8 -*-
"""
Test suite for AccountJournal model in producteca_connector module.

This module provides comprehensive test coverage for the AccountJournal model,
which handles payment method integration with Producteca platform, including:
- Producteca payment method selection
- Journal configuration for different payment types
- Integration with Producteca payment processing

Test Patterns:
- Uses Odoo TransactionCase for database operations
- Test inheritance and field behavior
- Validate selection field constraints
- Business logic validation

Coverage Areas:
- Field definitions and selection values
- Payment method mappings
- ondelete behavior
- Journal filtering and matching
"""

from unittest.mock import patch, MagicMock
from odoo.tests.common import TransactionCase


class TestAccountJournal(TransactionCase):
    """Test cases for AccountJournal model with Producteca integration."""

    def setUp(self):
        """Set up test data for AccountJournal tests."""
        super(TestAccountJournal, self).setUp()
        
        # Create test company
        self.company = self.env['res.company'].create({
            'name': 'Test Company',
            'country_id': self.env.ref('base.ar').id,
        })
        
        # Create test journal
        self.journal = self.env['account.journal'].create({
            'name': 'Test Journal',
            'type': 'bank',
            'code': 'TEST',
            'company_id': self.company.id,
        })

    def test_01_model_inheritance(self):
        """Test that AccountJournal properly inherits from account.journal."""
        self.assertEqual(self.journal._name, 'account.journal')
        self.assertTrue(hasattr(self.journal, 'producteca_payment_method'))

    def test_02_producteca_payment_method_field_exists(self):
        """Test that producteca_payment_method field is properly defined."""
        field = self.journal._fields.get('producteca_payment_method')
        self.assertIsNotNone(field)
        self.assertEqual(field.type, 'selection')

    def test_03_payment_method_selection_values(self):
        """Test all payment method selection values."""
        expected_methods = [
            'Cash', 'CreditCard', 'BankLoan', 'BankTransfer', 'Check',
            'MercadoPago', 'DebitCard', 'BankDeposit', 'DineroMail',
            'Ticket', 'Decidir', 'LoyaltyPoints', 'PayPal', 'PayPalPlus', 'Atm'
        ]
        
        field = self.journal._fields['producteca_payment_method']
        selection_values = [item[0] for item in field.selection]
        
        for method in expected_methods:
            self.assertIn(method, selection_values)

    def test_04_cash_payment_method(self):
        """Test Cash payment method assignment."""
        self.journal.producteca_payment_method = 'Cash'
        self.assertEqual(self.journal.producteca_payment_method, 'Cash')

    def test_05_credit_card_payment_method(self):
        """Test CreditCard payment method assignment."""
        self.journal.producteca_payment_method = 'CreditCard'
        self.assertEqual(self.journal.producteca_payment_method, 'CreditCard')

    def test_06_bank_loan_payment_method(self):
        """Test BankLoan payment method assignment."""
        self.journal.producteca_payment_method = 'BankLoan'
        self.assertEqual(self.journal.producteca_payment_method, 'BankLoan')

    def test_07_bank_transfer_payment_method(self):
        """Test BankTransfer payment method assignment."""
        self.journal.producteca_payment_method = 'BankTransfer'
        self.assertEqual(self.journal.producteca_payment_method, 'BankTransfer')

    def test_08_check_payment_method(self):
        """Test Check payment method assignment."""
        self.journal.producteca_payment_method = 'Check'
        self.assertEqual(self.journal.producteca_payment_method, 'Check')

    def test_09_mercado_pago_payment_method(self):
        """Test MercadoPago payment method assignment."""
        self.journal.producteca_payment_method = 'MercadoPago'
        self.assertEqual(self.journal.producteca_payment_method, 'MercadoPago')

    def test_10_debit_card_payment_method(self):
        """Test DebitCard payment method assignment."""
        self.journal.producteca_payment_method = 'DebitCard'
        self.assertEqual(self.journal.producteca_payment_method, 'DebitCard')

    def test_11_bank_deposit_payment_method(self):
        """Test BankDeposit payment method assignment."""
        self.journal.producteca_payment_method = 'BankDeposit'
        self.assertEqual(self.journal.producteca_payment_method, 'BankDeposit')

    def test_12_dinero_mail_payment_method(self):
        """Test DineroMail payment method assignment."""
        self.journal.producteca_payment_method = 'DineroMail'
        self.assertEqual(self.journal.producteca_payment_method, 'DineroMail')

    def test_13_ticket_payment_method(self):
        """Test Ticket payment method assignment."""
        self.journal.producteca_payment_method = 'Ticket'
        self.assertEqual(self.journal.producteca_payment_method, 'Ticket')

    def test_14_decidir_payment_method(self):
        """Test Decidir payment method assignment."""
        self.journal.producteca_payment_method = 'Decidir'
        self.assertEqual(self.journal.producteca_payment_method, 'Decidir')

    def test_15_loyalty_points_payment_method(self):
        """Test LoyaltyPoints payment method assignment."""
        self.journal.producteca_payment_method = 'LoyaltyPoints'
        self.assertEqual(self.journal.producteca_payment_method, 'LoyaltyPoints')

    def test_16_paypal_payment_method(self):
        """Test PayPal payment method assignment."""
        self.journal.producteca_payment_method = 'PayPal'
        self.assertEqual(self.journal.producteca_payment_method, 'PayPal')

    def test_17_paypal_plus_payment_method(self):
        """Test PayPalPlus payment method assignment."""
        self.journal.producteca_payment_method = 'PayPalPlus'
        self.assertEqual(self.journal.producteca_payment_method, 'PayPalPlus')

    def test_18_atm_payment_method(self):
        """Test Atm payment method assignment."""
        self.journal.producteca_payment_method = 'Atm'
        self.assertEqual(self.journal.producteca_payment_method, 'Atm')

    def test_19_invalid_payment_method(self):
        """Test assignment of invalid payment method."""
        with self.assertRaises(ValueError):
            self.journal.producteca_payment_method = 'InvalidMethod'

    def test_20_default_payment_method_value(self):
        """Test default value for payment method field."""
        new_journal = self.env['account.journal'].create({
            'name': 'New Test Journal',
            'type': 'bank',
            'code': 'NEW',
            'company_id': self.company.id,
        })
        
        # Should be False/None by default
        self.assertFalse(new_journal.producteca_payment_method)

    def test_21_ondelete_set_null_behavior(self):
        """Test ondelete='set null' behavior for selection field."""
        # This tests the metadata of the field
        field = self.journal._fields['producteca_payment_method']
        self.assertEqual(field.ondelete, 'set null')

    def test_22_payment_method_filtering(self):
        """Test filtering journals by payment method."""
        # Create journals with different payment methods
        journal_credit = self.env['account.journal'].create({
            'name': 'Credit Card Journal',
            'type': 'bank',
            'code': 'CC',
            'company_id': self.company.id,
            'producteca_payment_method': 'CreditCard',
        })
        
        journal_cash = self.env['account.journal'].create({
            'name': 'Cash Journal',
            'type': 'cash',
            'code': 'CASH',
            'company_id': self.company.id,
            'producteca_payment_method': 'Cash',
        })
        
        # Filter by CreditCard
        credit_journals = self.env['account.journal'].search([
            ('producteca_payment_method', '=', 'CreditCard')
        ])
        self.assertIn(journal_credit, credit_journals)
        self.assertNotIn(journal_cash, credit_journals)
        
        # Filter by Cash
        cash_journals = self.env['account.journal'].search([
            ('producteca_payment_method', '=', 'Cash')
        ])
        self.assertIn(journal_cash, cash_journals)
        self.assertNotIn(journal_credit, cash_journals)

    def test_23_payment_method_search_domain(self):
        """Test search domain functionality for payment methods."""
        # Create journals with various payment methods
        journals_data = [
            ('MP Journal', 'MercadoPago'),
            ('PP Journal', 'PayPal'),
            ('DC Journal', 'DebitCard'),
        ]
        
        created_journals = []
        for name, method in journals_data:
            journal = self.env['account.journal'].create({
                'name': name,
                'type': 'bank',
                'code': method[:3].upper(),
                'company_id': self.company.id,
                'producteca_payment_method': method,
            })
            created_journals.append(journal)
        
        # Search for digital payment methods
        digital_methods = ['MercadoPago', 'PayPal', 'PayPalPlus']
        digital_journals = self.env['account.journal'].search([
            ('producteca_payment_method', 'in', digital_methods)
        ])
        
        self.assertEqual(len(digital_journals), 2)  # MercadoPago and PayPal

    def test_24_payment_method_integration_with_invoice(self):
        """Test payment method integration in invoice payment process."""
        # Set up journal with payment method
        self.journal.producteca_payment_method = 'CreditCard'
        
        # Create partner and product for invoice
        partner = self.env['res.partner'].create({
            'name': 'Test Customer',
            'company_id': self.company.id,
        })
        
        product = self.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 100.0,
        })
        
        # Create sales journal
        sales_journal = self.env['account.journal'].create({
            'name': 'Sales Journal',
            'type': 'sale',
            'code': 'SAL',
            'company_id': self.company.id,
        })
        
        # Create invoice
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'journal_id': sales_journal.id,
            'company_id': self.company.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': product.id,
                'quantity': 1,
                'price_unit': 100.0,
                'name': 'Test Product Line',
            })],
        })
        
        # Verify journal can be found by payment method
        journals = self.env['account.journal'].search([
            ('producteca_payment_method', '=', 'CreditCard')
        ])
        self.assertIn(self.journal, journals)

    def test_25_comprehensive_payment_method_mapping(self):
        """Test comprehensive payment method mapping and validation."""
        # Test all payment methods with their Spanish labels
        payment_methods_mapping = {
            'Cash': 'Efectivo',
            'CreditCard': 'Tarjeta de Crédito',
            'BankLoan': 'Préstamo Bancario',
            'BankTransfer': 'Transferencia Bancaria',
            'Check': 'Cheque',
            'MercadoPago': 'Mercado Pago',
            'DebitCard': 'Tarjeta de Débito',
            'BankDeposit': 'Depósito Bancario',
            'DineroMail': 'DineroMail',
            'Ticket': 'Ticket',
            'Decidir': 'Decidir',
            'LoyaltyPoints': 'Puntos de Fidelidad',
            'PayPal': 'PayPal',
            'PayPalPlus': 'PayPal Plus',
            'Atm': 'ATM',
        }
        
        field = self.journal._fields['producteca_payment_method']
        selection_dict = dict(field.selection)
        
        # Verify all mappings exist and are correct
        for key, spanish_label in payment_methods_mapping.items():
            self.assertIn(key, selection_dict)
            self.assertEqual(selection_dict[key], spanish_label)
        
        # Test creating journals with all methods
        for method_key in payment_methods_mapping.keys():
            journal = self.env['account.journal'].create({
                'name': f'Test {method_key} Journal',
                'type': 'bank',
                'code': method_key[:4].upper(),
                'company_id': self.company.id,
                'producteca_payment_method': method_key,
            })
            
            self.assertEqual(journal.producteca_payment_method, method_key)
            
            # Clean up to avoid code conflicts
            journal.unlink()