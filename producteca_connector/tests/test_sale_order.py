# -*- coding: utf-8 -*-
"""
Test module for sale_order.py - Producteca Connector
Tests for SaleOrder inheritance and Producteca integration
"""

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from unittest.mock import patch, MagicMock
import json
from datetime import datetime, timedelta


class TestSaleOrder(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test company
        cls.company = cls.env.company
        
        # Create test warehouse
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Test Sale Warehouse',
            'code': 'TSW',
            'company_id': cls.company.id,
        })
        
        # Create test producteca account
        cls.producteca_account = cls.env['producteca.account'].create({
            'account_name': 'Test Sale Account',
            'api_key': 'test_sale_api_key',
            'bearer_token': 'test_sale_bearer_token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': cls.warehouse.id,
            'get_orders_from_last_days': 7,
        })
        
        # Create test partner
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Sale Customer',
            'email': 'test@customer.com',
        })
        
        # Create test product
        cls.product = cls.env['product.product'].create({
            'name': 'Test Sale Product',
            'type': 'product',
            'list_price': 100.0,
            'standard_price': 60.0,
        })
        
        # Create test cart
        cls.cart = cls.env['sale.order.cart'].create({
            'producteca_id': 'CART_001',
        })

    def test_01_sale_order_inheritance(self):
        """Test that sale.order is properly inherited"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 2,
                'price_unit': 100.0,
            })],
        })
        
        # Should inherit from sale.order
        self.assertEqual(sale_order._name, 'sale.order')
        
        # Should have standard sale.order functionality
        self.assertTrue(hasattr(sale_order, 'name'))
        self.assertTrue(hasattr(sale_order, 'partner_id'))
        self.assertTrue(hasattr(sale_order, 'order_line'))
        
        # Should have custom Producteca fields
        self.assertTrue(hasattr(sale_order, 'producteca_id'))
        self.assertTrue(hasattr(sale_order, 'cart_id'))
        self.assertTrue(hasattr(sale_order, 'origin_platform'))
        self.assertTrue(hasattr(sale_order, 'producteca_shipment_data'))
        self.assertTrue(hasattr(sale_order, 'producteca_payments_data'))
        self.assertTrue(hasattr(sale_order, 'producteca_account_id'))
        self.assertTrue(hasattr(sale_order, 'has_existing_producteca_invoice'))

    def test_02_producteca_fields_properties(self):
        """Test Producteca-specific field properties"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        
        # Test field existence and types
        fields = sale_order._fields
        
        self.assertIn('producteca_id', fields)
        self.assertEqual(fields['producteca_id'].type, 'char')
        self.assertEqual(fields['producteca_id'].string, 'Producteca ID')
        
        self.assertIn('cart_id', fields)
        self.assertEqual(fields['cart_id'].type, 'many2one')
        self.assertEqual(fields['cart_id'].comodel_name, 'sale.order.cart')
        
        self.assertIn('origin_platform', fields)
        self.assertEqual(fields['origin_platform'].type, 'char')
        
        self.assertIn('producteca_shipment_data', fields)
        self.assertEqual(fields['producteca_shipment_data'].type, 'text')
        
        self.assertIn('producteca_payments_data', fields)
        self.assertEqual(fields['producteca_payments_data'].type, 'text')
        
        self.assertIn('producteca_account_id', fields)
        self.assertEqual(fields['producteca_account_id'].type, 'many2one')
        self.assertEqual(fields['producteca_account_id'].comodel_name, 'producteca.account')
        
        self.assertIn('has_existing_producteca_invoice', fields)
        self.assertEqual(fields['has_existing_producteca_invoice'].type, 'boolean')

    def test_03_create_sale_order_with_producteca_data(self):
        """Test creating sale order with Producteca data"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'producteca_id': 'PROD_ORDER_001',
            'cart_id': self.cart.id,
            'origin_platform': 'Mercado Libre',
            'producteca_account_id': self.producteca_account.id,
            'has_existing_producteca_invoice': True,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
            })],
        })
        
        # Test Producteca fields
        self.assertEqual(sale_order.producteca_id, 'PROD_ORDER_001')
        self.assertEqual(sale_order.cart_id.id, self.cart.id)
        self.assertEqual(sale_order.origin_platform, 'Mercado Libre')
        self.assertEqual(sale_order.producteca_account_id.id, self.producteca_account.id)
        self.assertTrue(sale_order.has_existing_producteca_invoice)

    def test_04_cart_relationship(self):
        """Test cart relationship functionality"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'cart_id': self.cart.id,
        })
        
        # Test relationship
        self.assertEqual(sale_order.cart_id.id, self.cart.id)
        self.assertEqual(sale_order.cart_id.producteca_id, 'CART_001')
        
        # Test reverse relationship
        self.assertIn(sale_order.id, self.cart.order_ids.ids)

    def test_05_action_confirm_without_producteca_data(self):
        """Test action_confirm without Producteca data"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
            })],
        })
        
        # Should work normally without Producteca data
        sale_order.action_confirm()
        self.assertEqual(sale_order.state, 'sale')

    @patch('odoo.addons.producteca_connector.models.sale_order.SaleOrder._process_producteca_shipments')
    def test_06_action_confirm_with_producteca_data(self, mock_process_shipments):
        """Test action_confirm with Producteca data"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'producteca_id': 'PROD_ORDER_002',
            'producteca_account_id': self.producteca_account.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
            })],
        })
        
        # Confirm order
        sale_order.action_confirm()
        
        # Should call process shipments if has pickings
        if sale_order.picking_ids:
            mock_process_shipments.assert_called_once()
        else:
            mock_process_shipments.assert_not_called()

    def test_07_should_skip_shipment_update(self):
        """Test _should_skip_shipment_update method"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        
        # Test with empty shipment data
        self.assertFalse(sale_order._should_skip_shipment_update(None))
        self.assertFalse(sale_order._should_skip_shipment_update([]))
        
        # Test with shipment data but no Done status
        shipment_data = [{'method': {'status': 'Pending'}}]
        self.assertFalse(sale_order._should_skip_shipment_update(shipment_data))
        
        # Test with Done status
        shipment_data = [{'method': {'status': 'Done'}}]
        self.assertTrue(sale_order._should_skip_shipment_update(shipment_data))

    def test_08_mapped_origin_application(self):
        """Test _mapped_origin_application method"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        
        # Test known mappings
        self.assertEqual(sale_order._mapped_origin_application(2), 'Mercado Libre')
        self.assertEqual(sale_order._mapped_origin_application(90), 'Amazon')
        self.assertEqual(sale_order._mapped_origin_application(60), 'Shopify')
        
        # Test unknown mapping
        self.assertEqual(sale_order._mapped_origin_application(99999), 'Unknown')

    def test_09_get_warehouse_default(self):
        """Test _get_warehouse method with default warehouse"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        
        warehouse_id = sale_order._get_warehouse('Default', self.producteca_account)
        self.assertEqual(warehouse_id, self.producteca_account.default_warehouse_id.id)

    def test_10_get_warehouse_specific(self):
        """Test _get_warehouse method with specific warehouse"""
        # Create specific warehouse
        specific_warehouse = self.env['stock.warehouse'].create({
            'name': 'Specific Warehouse',
            'code': 'SPEC',
            'company_id': self.company.id,
            'producteca_warehouse_name': 'SpecificName',
        })
        
        # Add to account warehouses
        self.producteca_account.warehouse_ids = [(4, specific_warehouse.id)]
        
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        
        warehouse_id = sale_order._get_warehouse('SpecificName', self.producteca_account)
        self.assertEqual(warehouse_id, specific_warehouse.id)

    def test_11_handle_missing_product_by_sku(self):
        """Test _handle_missing_product method with existing SKU"""
        # Create product with SKU
        existing_product = self.env['product.product'].create({
            'name': 'Existing SKU Product',
            'default_code': 'SKU001',
            'type': 'product',
        })
        
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        
        line_data = {
            'variation': {'id': 123, 'sku': 'SKU001'},
            'product': {'id': 456},
            'price': 100.0,
            'quantity': 1,
        }
        
        with patch.object(existing_product, '_update_product_from_producteca'):
            result = sale_order._handle_missing_product(line_data, self.producteca_account)
        
        # Should return the existing product
        self.assertEqual(result.id, existing_product.id)

    @patch('odoo.addons.producteca_connector.models.product_product.ProductProduct._create_product_from_producteca')
    def test_12_handle_missing_product_create_new(self, mock_create_product):
        """Test _handle_missing_product method creating new product"""
        # Mock product creation
        new_product = self.env['product.product'].create({
            'name': 'New Created Product',
            'type': 'product',
        })
        mock_create_product.return_value = new_product
        
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        
        line_data = {
            'variation': {'id': 123, 'sku': 'NEWSKU001'},
            'product': {'id': 456},
            'price': 100.0,
            'quantity': 1,
        }
        
        result = sale_order._handle_missing_product(line_data, self.producteca_account)
        
        # Should call create method and return new product
        mock_create_product.assert_called_once()
        self.assertEqual(result.id, new_product.id)

    def test_13_process_sale_order_lines_with_existing_connection(self):
        """Test _process_sale_order_lines with existing product connection"""
        # Create product connection
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': self.product.id,
            'producteca_id': '456',
            'producteca_variation_id': '123',
        })
        
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        
        lines_data = [{
            'product': {'id': 456},
            'variation': {'id': 123},
            'quantity': 2,
            'price': 200.0,
        }]
        
        result = sale_order._process_sale_order_lines(
            lines_data, self.warehouse.id, {}, self.producteca_account
        )
        
        # Should create sale order line
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], 0)  # Command.create
        line_data = result[0][2]
        self.assertEqual(line_data['product_id'], self.product.id)
        self.assertEqual(line_data['product_uom_qty'], 2)
        self.assertEqual(line_data['price_unit'], 200.0)

    def test_14_handle_delivery_line_new_product(self):
        """Test _handle_delivery_line creating new delivery product"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        
        body_data = {
            'shipments': [{'method': {'courier': 'DHL'}}],
            'totalShippingCost': 50.0,
        }
        
        result = sale_order._handle_delivery_line(body_data, {})
        
        # Should create delivery line
        self.assertEqual(result[0], 0)  # Command.create
        line_data = result[2]
        self.assertEqual(line_data['product_uom_qty'], 1)
        self.assertEqual(line_data['price_unit'], 50.0)
        
        # Should create delivery product
        delivery_product = self.env['product.product'].search([
            ('name', '=', 'Servicio de Entrega: DHL')
        ])
        self.assertEqual(len(delivery_product), 1)
        self.assertEqual(delivery_product.type, 'service')

    def test_15_get_partner_id_existing_partner(self):
        """Test _get_partner_id with existing partner"""
        # Create partner with producteca_id
        producteca_partner = self.env['res.partner'].create({
            'name': 'Producteca Customer',
            'producteca_id': 'PROD_CONTACT_001',
            'parent_id': self.partner.id,  # Child contact
        })
        
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        
        body_data = {'contact': 'PROD_CONTACT_001'}
        
        result = sale_order._get_partner_id(body_data, self.producteca_account)
        
        self.assertEqual(result.id, producteca_partner.id)

    def test_16_get_partner_id_no_contact(self):
        """Test _get_partner_id with no contact data"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        
        body_data = {}  # No contact
        
        result = sale_order._get_partner_id(body_data, self.producteca_account)
        
        # Should return default producteca contact
        default_contact = self.env.ref('producteca_connector.producteca_contact', raise_if_not_found=False)
        if default_contact:
            self.assertEqual(result.id, default_contact.id)

    def test_17_get_cart_id_existing_cart(self):
        """Test _get_cart_id with existing cart"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        
        body_data = {'cartId': 'CART_001'}
        
        result = sale_order._get_cart_id(body_data)
        
        self.assertEqual(result, self.cart.id)

    def test_18_get_cart_id_new_cart(self):
        """Test _get_cart_id creating new cart"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        
        body_data = {'cartId': 'NEW_CART_001'}
        
        result = sale_order._get_cart_id(body_data)
        
        # Should create new cart
        new_cart = self.env['sale.order.cart'].search([
            ('producteca_id', '=', 'NEW_CART_001')
        ])
        self.assertEqual(len(new_cart), 1)
        self.assertEqual(result, new_cart.id)

    def test_19_prepare_sale_order_dict(self):
        """Test _prepare_sale_order_dict method"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        
        body_data = {
            'id': 'ORDER_001',
            'lines': [{
                'product': {'id': 456},
                'variation': {'id': 123},
                'quantity': 1,
                'price': 100.0,
            }],
            'warehouse': 'Default',
            'hasAnyShipments': False,
            'channel': 2,  # Mercado Libre
            'contact': None,
            'cartId': 'CART_002',
            'payments': [{'method': 'credit_card'}],
            'invoiceIntegration': True,
        }
        
        # Create product connection
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': self.product.id,
            'producteca_id': '456',
            'producteca_variation_id': '123',
        })
        
        result = sale_order._prepare_sale_order_dict(body_data, self.producteca_account)
        
        # Test result
        self.assertEqual(result['producteca_id'], 'ORDER_001')
        self.assertEqual(result['origin_platform'], 'Mercado Libre')
        self.assertEqual(result['company_id'], self.producteca_account.company_id.id)
        self.assertEqual(result['producteca_account_id'], self.producteca_account.id)
        self.assertTrue(result['has_existing_producteca_invoice'])
        self.assertIsNotNone(result['cart_id'])
        self.assertEqual(len(result['order_line']), 1)

    def test_20_run_quotation_process(self):
        """Test _run_quotation_process method"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
            })],
        })
        
        # Should be in draft state
        self.assertEqual(sale_order.state, 'draft')
        
        # Run quotation process
        result = sale_order._run_quotation_process()
        
        # Should confirm order
        self.assertEqual(result.state, 'sale')

    def test_21_run_draft_invoice_process(self):
        """Test _run_draft_invoice_process method"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
            })],
        })
        
        # Run draft invoice process
        result = sale_order._run_draft_invoice_process()
        
        # Should confirm order and create invoices
        self.assertEqual(result.state, 'sale')
        self.assertGreater(len(result.invoice_ids), 0)

    def test_22_run_confirm_process(self):
        """Test _run_confirm_process method"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
            })],
        })
        
        # Run confirm process
        result = sale_order._run_confirm_process()
        
        # Should confirm order and post invoices
        self.assertEqual(result.state, 'sale')
        self.assertGreater(len(result.invoice_ids), 0)
        for invoice in result.invoice_ids:
            self.assertEqual(invoice.state, 'posted')

    def test_23_run_import_sale_action(self):
        """Test _run_import_sale_action method with different actions"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
            })],
        })
        
        # Test quotation action
        self.producteca_account.imported_sale_action = 'quotation'
        result = sale_order._run_import_sale_action(self.producteca_account)
        self.assertEqual(result.state, 'sale')
        
        # Reset order state
        sale_order.write({'state': 'draft'})
        
        # Test draft_invoice action
        self.producteca_account.imported_sale_action = 'draft_invoice'
        result = sale_order._run_import_sale_action(self.producteca_account)
        self.assertEqual(result.state, 'sale')
        self.assertGreater(len(result.invoice_ids), 0)

    def test_24_create_invoices_with_producteca_data(self):
        """Test _create_invoices with Producteca data"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'producteca_id': 'ORDER_INVOICE_001',
            'producteca_account_id': self.producteca_account.id,
            'producteca_payments_data': '[{"method": "credit_card"}]',
            'has_existing_producteca_invoice': True,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
            })],
        })
        
        # Confirm order first
        sale_order.action_confirm()
        
        # Create invoices
        invoices = sale_order._create_invoices()
        
        # Test invoice has Producteca data
        for invoice in invoices:
            self.assertEqual(invoice.producteca_order_id, 'ORDER_INVOICE_001')
            self.assertEqual(invoice.producteca_account_id.id, self.producteca_account.id)
            self.assertTrue(invoice.producteca_invoice_already_exists)
            self.assertEqual(invoice.producteca_payment_data, '[{"method": "credit_card"}]')
        
        # Payment data should be cleared from order
        self.assertFalse(sale_order.producteca_payments_data)

    @patch('odoo.addons.producteca_connector.models.sale_order.SaleOrder.env')
    def test_25_write_method_with_producteca_sync(self, mock_env):
        """Test write method syncing with Producteca"""
        # Mock client
        mock_client = MagicMock()
        mock_sale_order_obj = MagicMock()
        mock_client.SalesOrder.return_value = mock_sale_order_obj
        self.producteca_account.get_client = MagicMock(return_value=mock_client)
        
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'producteca_id': 'SYNC_ORDER_001',
            'producteca_account_id': self.producteca_account.id,
        })
        
        # Update note and tags
        tag = self.env['crm.tag'].create({'name': 'Test Tag'})
        sale_order.write({
            'note': 'Updated note',
            'tag_ids': [(4, tag.id)],
        })
        
        # Should sync with Producteca
        mock_client.SalesOrder.assert_called_once_with(
            id=int('SYNC_ORDER_001'),
            note='Updated note',
            tags=['Test Tag']
        )
        mock_sale_order_obj.synchronize.assert_called_once()

    def test_26_action_cancel_with_producteca_order(self):
        """Test action_cancel with Producteca order"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'producteca_id': 'CANCEL_ORDER_001',
            'producteca_account_id': self.producteca_account.id,
        })
        
        # Should return wizard action
        result = sale_order.action_cancel()
        
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.assertEqual(result['res_model'], 'confirm.cancel.sale.order')
        self.assertEqual(result['target'], 'new')

    def test_27_action_cancel_without_producteca_order(self):
        """Test action_cancel without Producteca order"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        
        # Should call parent cancel method directly
        result = sale_order.action_cancel()
        # The exact result depends on parent implementation

    @patch('odoo.addons.producteca_connector.models.sale_order.SaleOrder.env')
    def test_28_action_close_order(self, mock_env):
        """Test action_close_order method"""
        # Mock client
        mock_client = MagicMock()
        mock_sale_order_obj = MagicMock()
        mock_client.SalesOrder.return_value = mock_sale_order_obj
        self.producteca_account.get_client = MagicMock(return_value=mock_client)
        
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'producteca_id': 'CLOSE_ORDER_001',
            'producteca_account_id': self.producteca_account.id,
        })
        
        # Close order
        sale_order.action_close_order()
        
        # Should call Producteca API
        mock_client.SalesOrder.assert_called_once_with(id='CLOSE_ORDER_001')
        mock_sale_order_obj.close.assert_called_once()

    @patch('odoo.addons.producteca_connector.models.sale_order.SaleOrder.env')
    def test_29_action_close_order_error(self, mock_env):
        """Test action_close_order with API error"""
        # Mock client with error
        mock_client = MagicMock()
        mock_sale_order_obj = MagicMock()
        mock_sale_order_obj.close.side_effect = Exception('API Error')
        mock_client.SalesOrder.return_value = mock_sale_order_obj
        self.producteca_account.get_client = MagicMock(return_value=mock_client)
        
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'producteca_id': 'ERROR_ORDER_001',
            'producteca_account_id': self.producteca_account.id,
        })
        
        # Should raise UserError
        with self.assertRaises(UserError):
            sale_order.action_close_order()

    def test_30_upset_saleorder_from_producteca_new_order(self):
        """Test _upset_saleorder_from_producteca creating new order"""
        sale_order = self.env['sale.order']
        
        body_data = {
            'id': 'NEW_UPSET_ORDER_001',
            'lines': [{
                'product': {'id': 456},
                'variation': {'id': 123},
                'quantity': 1,
                'price': 100.0,
            }],
            'warehouse': 'Default',
            'hasAnyShipments': False,
            'channel': 2,  # Mercado Libre
            'contact': None,
            'cartId': None,
            'payments': None,
            'invoiceIntegration': False,
        }
        
        # Create product connection
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': self.product.id,
            'producteca_id': '456',
            'producteca_variation_id': '123',
        })
        
        # Create order from Producteca
        result = sale_order._upset_saleorder_from_producteca(self.producteca_account, body_data)
        
        # Should create new order
        self.assertTrue(result.exists())
        self.assertEqual(result.producteca_id, 'NEW_UPSET_ORDER_001')
        self.assertEqual(result.origin_platform, 'Mercado Libre')

    def test_31_upset_saleorder_from_producteca_update_existing(self):
        """Test _upset_saleorder_from_producteca updating existing order"""
        # Create existing order
        existing_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'producteca_id': 'EXISTING_UPSET_ORDER',
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 80.0,
            })],
        })
        
        body_data = {
            'id': 'EXISTING_UPSET_ORDER',
            'lines': [{
                'product': {'id': 456},
                'variation': {'id': 123},
                'quantity': 2,  # Changed quantity
                'price': 200.0,  # Changed price
            }],
            'warehouse': 'Default',
            'hasAnyShipments': False,
            'channel': 90,  # Amazon (changed platform)
            'contact': None,
            'cartId': None,
            'payments': None,
            'invoiceIntegration': False,
        }
        
        # Create product connection
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': self.product.id,
            'producteca_id': '456',
            'producteca_variation_id': '123',
        })
        
        # Update order from Producteca
        result = existing_order._upset_saleorder_from_producteca(self.producteca_account, body_data)
        
        # Should update existing order
        self.assertEqual(result.id, existing_order.id)
        self.assertEqual(result.origin_platform, 'Amazon')
        
        # Order line should be updated
        self.assertEqual(len(result.order_line), 1)
        self.assertEqual(result.order_line[0].product_uom_qty, 2)
        self.assertEqual(result.order_line[0].price_unit, 200.0)

    @patch('producteca.sales_orders.search_sale_orders.SearchSalesOrderParams')
    @patch('odoo.addons.producteca_connector.models.sale_order.SaleOrder.with_delay')
    def test_32_enqueue_last_x_days_orders_from_producteca(self, mock_with_delay, mock_search_params):
        """Test enqueue_last_x_days_orders_from_producteca method"""
        # Mock client and response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.results = [
            MagicMock(order_id='ORDER_1'),
            MagicMock(order_id='ORDER_2'),
        ]
        mock_client.SalesOrder.search.return_value = mock_response
        
        # Mock individual order retrieval
        mock_order_obj = MagicMock()
        mock_order_obj.to_dict.return_value = {'id': 'ORDER_1', 'test': 'data'}
        mock_client.SalesOrder.get.return_value = mock_order_obj
        
        self.producteca_account.get_client = MagicMock(return_value=mock_client)
        
        # Mock delayed execution
        mock_delayed = MagicMock()
        mock_with_delay.return_value = mock_delayed
        
        sale_order = self.env['sale.order']
        
        # Run method
        result = sale_order.enqueue_last_x_days_orders_from_producteca()
        
        # Should return True
        self.assertTrue(result)
        
        # Should call search with correct params
        mock_client.SalesOrder.search.assert_called()
        
        # Should enqueue jobs for each order
        self.assertEqual(mock_delayed._upset_saleorder_from_producteca.call_count, 2)

    def test_33_comprehensive_sale_order_functionality(self):
        """Test comprehensive sale order functionality"""
        # Create comprehensive test scenario
        
        # 1. Create tax
        tax = self.env['account.tax'].create({
            'name': 'Sales Tax 21%',
            'amount': 21.0,
            'type_tax_use': 'sale',
        })
        
        # 2. Create product with tax
        taxed_product = self.env['product.product'].create({
            'name': 'Taxed Product',
            'type': 'product',
            'list_price': 121.0,  # Price with tax
            'taxes_id': [(4, tax.id)],
        })
        
        # 3. Create product connection
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': taxed_product.id,
            'producteca_id': 'COMP_PROD_001',
            'producteca_variation_id': 'COMP_VAR_001',
        })
        
        # 4. Create delivery product
        delivery_product = self.env['product.product'].create({
            'name': 'Servicio de Entrega: FedEx',
            'type': 'service',
            'taxes_id': [(4, tax.id)],
        })
        
        # 5. Create comprehensive order data
        body_data = {
            'id': 'COMPREHENSIVE_ORDER_001',
            'lines': [{
                'product': {'id': 'COMP_PROD_001'},
                'variation': {'id': 'COMP_VAR_001'},
                'quantity': 3,
                'price': 363.0,  # 121 * 3 with tax
            }],
            'warehouse': 'Default',
            'hasAnyShipments': True,
            'shipments': [{'method': {'courier': 'FedEx'}}],
            'totalShippingCost': 60.5,  # With tax
            'channel': 272,  # Mercado Libre
            'contact': None,
            'cartId': 'COMPREHENSIVE_CART',
            'payments': [
                {'method': 'credit_card', 'amount': 400.0},
                {'method': 'bank_transfer', 'amount': 23.5}
            ],
            'invoiceIntegration': True,
        }
        
        # 6. Create sale order from Producteca data
        sale_order = self.env['sale.order']
        result = sale_order._upset_saleorder_from_producteca(self.producteca_account, body_data)
        
        # 7. Test comprehensive functionality
        
        # Basic order properties
        self.assertEqual(result.producteca_id, 'COMPREHENSIVE_ORDER_001')
        self.assertEqual(result.origin_platform, 'Mercado Libre')
        self.assertEqual(result.producteca_account_id.id, self.producteca_account.id)
        self.assertTrue(result.has_existing_producteca_invoice)
        
        # Cart relationship
        self.assertIsNotNone(result.cart_id)
        self.assertEqual(result.cart_id.producteca_id, 'COMPREHENSIVE_CART')
        
        # Order lines
        self.assertEqual(len(result.order_line), 2)  # Product + delivery
        
        # Product line
        product_line = result.order_line.filtered(lambda l: l.product_id == taxed_product)
        self.assertEqual(len(product_line), 1)
        self.assertEqual(product_line.product_uom_qty, 3)
        self.assertEqual(product_line.price_unit, 300.0)  # Price without tax
        
        # Delivery line
        delivery_line = result.order_line.filtered(lambda l: l.product_id.name.startswith('Servicio de Entrega'))
        self.assertEqual(len(delivery_line), 1)
        self.assertEqual(delivery_line.product_uom_qty, 1)
        self.assertEqual(delivery_line.price_unit, 50.0)  # Price without tax
        
        # Payment data
        self.assertIsNotNone(result.producteca_payments_data)
        
        # 8. Test order confirmation and invoice creation
        confirmed_result = result._run_confirm_process()
        
        # Should be confirmed
        self.assertEqual(confirmed_result.state, 'sale')
        
        # Should have invoices
        self.assertGreater(len(confirmed_result.invoice_ids), 0)
        
        # Invoice should have Producteca data
        invoice = confirmed_result.invoice_ids[0]
        self.assertEqual(invoice.producteca_order_id, 'COMPREHENSIVE_ORDER_001')
        self.assertEqual(invoice.producteca_account_id.id, self.producteca_account.id)
        self.assertTrue(invoice.producteca_invoice_already_exists)
        
        # Payment data should be transferred to invoice
        self.assertIsNotNone(invoice.producteca_payment_data)
        
        # Payment data should be cleared from order
        self.assertFalse(confirmed_result.producteca_payments_data)
        
        # 9. Test pickings if generated
        if confirmed_result.picking_ids:
            for picking in confirmed_result.picking_ids:
                self.assertEqual(picking.producteca_account_id.id, self.producteca_account.id)
        
        # 10. Test search functionality
        found_orders = self.env['sale.order'].search([
            ('producteca_id', '=', 'COMPREHENSIVE_ORDER_001')
        ])
        self.assertEqual(len(found_orders), 1)
        self.assertEqual(found_orders[0].id, result.id)
        
        # 11. Test update operations
        result.write({'note': 'Updated comprehensive note'})
        self.assertEqual(result.note, 'Updated comprehensive note')
        
        # All relationships should remain intact
        self.assertEqual(len(result.order_line), 2)
        self.assertEqual(result.cart_id.producteca_id, 'COMPREHENSIVE_CART')
        self.assertEqual(result.producteca_account_id.id, self.producteca_account.id)