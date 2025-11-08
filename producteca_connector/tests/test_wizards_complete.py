# -*- coding: utf-8 -*-
"""Comprehensive test suite for wizard models.

This module contains comprehensive unit tests for wizard functionality
including import operations, cancellation confirmations, and API integrations.
"""

from unittest.mock import Mock, patch, MagicMock
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestConfirmCancelSaleOrderWizard(TransactionCase):
    """Test suite for ConfirmCancelSaleOrder wizard."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        
        self.producteca_account = self.env['producteca.account'].create({
            'name': 'Test Account',
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'is_active': True,
        })
        
        self.partner = self.env['res.partner'].create({
            'name': 'Test Customer',
        })
        
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'type': 'product',
        })
        
        self.sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'produceteca_account_id': self.producteca_account.id,
            'producteca_id': '12345',
        })

    def test_wizard_creation(self):
        """Test wizard creation and default values."""
        wizard = self.env['confirm.cancel.sale.order'].create({
            'sale_order_id': self.sale_order.id,
        })
        
        self.assertEqual(wizard.sale_order_id, self.sale_order)
        self.assertIn('Advertencia', wizard.warning_message)

    @patch('odoo.addons.producteca_connector.models.sale_order.SaleOrder.action_cancel')
    def test_confirm_cancel_success(self, mock_cancel):
        """Test successful order cancellation."""
        wizard = self.env['confirm.cancel.sale.order'].create({
            'sale_order_id': self.sale_order.id,
        })
        
        mock_client = Mock()
        mock_sales_order = Mock()
        
        with patch.object(self.producteca_account, 'SalesOrder', return_value=mock_sales_order):
            result = wizard.action_confirm_cancel()
            
            mock_sales_order.cancel.assert_called_once()
            self.assertEqual(result['type'], 'ir.actions.act_window_close')

    def test_confirm_cancel_no_order(self):
        """Test cancellation without order."""
        wizard = self.env['confirm.cancel.sale.order'].create({})
        
        with self.assertRaises(UserError):
            wizard.action_confirm_cancel()

    def test_cancel_action(self):
        """Test wizard cancellation."""
        wizard = self.env['confirm.cancel.sale.order'].create({
            'sale_order_id': self.sale_order.id,
        })
        
        result = wizard.action_cancel()
        self.assertEqual(result['type'], 'ir.actions.act_window_close')


class TestProductecaProductsWizardComplete(TransactionCase):
    """Comprehensive test suite for ProductecaProductsWizard."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        
        self.producteca_account = self.env['producteca.account'].create({
            'name': 'Test Account',
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'is_active': True,
            'is_producteca_able_to_create_products': True,
        })

    def test_wizard_fields(self):
        """Test wizard field configuration."""
        wizard = self.env['producteca.products.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '123,456,789',
        })
        
        self.assertEqual(wizard.producteca_account_id, self.producteca_account)
        self.assertEqual(wizard.search_text, '123,456,789')
        self.assertTrue(wizard.update_if_exists)

    @patch('odoo.addons.producteca_connector.models.product_product.ProductProduct.with_delay')
    def test_import_new_products(self, mock_with_delay):
        """Test importing new products."""
        wizard = self.env['producteca.products.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '123,456',
        })
        
        mock_delayed = Mock()
        mock_with_delay.return_value = mock_delayed
        
        result = wizard.action_obtain_products()
        
        self.assertEqual(result['type'], 'ir.actions.act_window_close')
        self.assertEqual(mock_delayed.get_product_from_producteca_and_create.call_count, 2)

    def test_no_permission_error(self):
        """Test import without permissions."""
        self.producteca_account.is_producteca_able_to_create_products = False
        
        wizard = self.env['producteca.products.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '123,456',
        })
        
        with self.assertRaises(UserError):
            wizard.action_obtain_products()


class TestProductecaSaleordersWizardComplete(TransactionCase):
    """Comprehensive test suite for ProductecaSaleordersWizard."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        
        self.producteca_account = self.env['producteca.account'].create({
            'name': 'Test Account',
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'is_active': True,
        })

    def test_wizard_creation(self):
        """Test wizard creation."""
        wizard = self.env['producteca.saleorders.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '123,456',
        })
        
        self.assertEqual(wizard.producteca_account_id, self.producteca_account)
        self.assertEqual(wizard.search_text, '123,456')

    @patch('odoo.addons.producteca_connector.models.sale_order.SaleOrder.with_delay')
    def test_import_sale_orders(self, mock_with_delay):
        """Test importing sale orders."""
        wizard = self.env['producteca.saleorders.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '123,456',
        })
        
        mock_client = Mock()
        mock_order = Mock()
        mock_order.to_dict.return_value = {'id': '123'}
        mock_client.SalesOrder.get.return_value = mock_order
        
        mock_delayed = Mock()
        mock_with_delay.return_value = mock_delayed
        
        with patch.object(self.producteca_account, 'get_client', return_value=mock_client):
            wizard.action_obtain_saleorders()
        
        self.assertEqual(mock_client.SalesOrder.get.call_count, 2)
        self.assertEqual(mock_delayed._upset_saleorder_from_producteca.call_count, 2)

    @patch('odoo.addons.producteca_connector.models.sale_order.SaleOrder.with_delay')
    def test_import_missing_orders(self, mock_with_delay):
        """Test import with missing orders."""
        wizard = self.env['producteca.saleorders.wizard'].create({
            'producteca_account_id': self.producteca_account.id,
            'search_text': '123,999',
        })
        
        mock_client = Mock()
        mock_order = Mock()
        mock_order.to_dict.return_value = {'id': '123'}
        mock_client.SalesOrder.get.side_effect = [mock_order, None]
        
        mock_delayed = Mock()
        mock_with_delay.return_value = mock_delayed
        
        with patch.object(self.producteca_account, 'get_client', return_value=mock_client):
            wizard.action_obtain_saleorders()
        
        # Only one job should be created for existing order
        self.assertEqual(mock_delayed._upset_saleorder_from_producteca.call_count, 1)