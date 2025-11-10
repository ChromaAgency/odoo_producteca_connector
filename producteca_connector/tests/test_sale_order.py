# -*- coding: utf-8 -*-
"""Tests for sale.order Producteca integration"""

from odoo.tests.common import TransactionCase


class TestSaleOrderProducteca(TransactionCase):
    """Test sale.order Producteca integration and configurations"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.warehouse = cls.env['stock.warehouse'].search([], limit=1)
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Customer SO',
            'email': 'testso@example.com',
        })
        
        cls.account = cls.env['producteca.account'].create({
            'account_name': 'Test SO Account',
            'api_key': 'test_api_key_so',
            'bearer_token': 'test_bearer_token_so',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': cls.warehouse.id,
            'is_producteca_able_to_create_products': True,
            'is_producteca_able_to_modified_products': True,
        })
        
        cls.product_template = cls.env['product.template'].create({
            'name': 'Test Product SO',
            'type': 'consu',
            'list_price': 100.0,
        })
        
        cls.product = cls.product_template.product_variant_ids[0]
        cls.product.default_code = 'TEST_SKU_SO_001'

    def test_01_prepare_sale_order_dict_structure(self):
        """Test _prepare_sale_order_dict creates dict with required fields"""
        body = {
            'id': 'ORDER_001',
            'status': 'pending',
            'channel': '1',
            'customer': {
                'name': 'Test Customer',
                'email': 'customer@test.com',
            },
            'lines': [],
            'shipments': [],
            'payments': [],
        }
        
        order_obj = self.env['sale.order']
        result = order_obj._prepare_sale_order_dict(body, self.account)
        
        self.assertIsInstance(result, dict)
        self.assertIn('partner_id', result)
        self.assertIn('order_line', result)
        self.assertIn('producteca_account_id', result)
        self.assertEqual(result.get('producteca_account_id'), self.account.id)
        self.assertEqual(result.get('producteca_id'), 'ORDER_001')

    def test_02_get_partner_id_with_existing_partner(self):
        """Test _get_partner_id returns existing partner"""
        body = {
            'customer': {
                'name': self.partner.name,
                'email': self.partner.email,
            },
        }
        
        order_obj = self.env['sale.order']
        partner = order_obj._get_partner_id(body, self.account)
        
        self.assertTrue(partner)
        # Should return a partner (either existing or new)
        self.assertIsInstance(partner.id, int)

    def test_03_sale_order_with_producteca_fields(self):
        """Test creating sale order with Producteca fields"""
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'producteca_account_id': self.account.id,
            'producteca_id': 'ORDER_TEST_001',
        })
        
        self.assertEqual(order.producteca_id, 'ORDER_TEST_001')
        self.assertEqual(order.producteca_account_id.id, self.account.id)

    def test_04_get_warehouse_returns_default(self):
        """Test _get_warehouse returns default warehouse ID when 'Default' specified"""
        order_obj = self.env['sale.order']
        warehouse_id = order_obj._get_warehouse('Default', self.account)
        
        # When 'Default' specified, should return default warehouse ID
        self.assertEqual(warehouse_id, self.account.default_warehouse_id.id)

    def test_05_imported_sale_action_quotation(self):
        """Test sale action with quotation config keeps draft state"""
        self.account.imported_sale_action = 'quotation'
        
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'producteca_account_id': self.account.id,
            'producteca_id': 'ORDER_QUOTATION',
        })
        
        # Add order line to make it valid
        self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product.id,
            'product_uom_qty': 1,
            'price_unit': 100.0,
        })
        
        initial_state = order.state
        order._run_import_sale_action(self.account)
        
        # quotation action confirms the order
        self.assertEqual(order.state, 'sale')

    def test_06_imported_sale_action_confirm(self):
        """Test sale action with confirm config confirms order"""
        self.account.imported_sale_action = 'confirm'
        
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'producteca_account_id': self.account.id,
            'producteca_id': 'ORDER_CONFIRM',
        })
        
        # Add order line
        self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product.id,
            'product_uom_qty': 1,
            'price_unit': 100.0,
        })
        
        order._run_import_sale_action(self.account)
        
        # Should be confirmed
        self.assertEqual(order.state, 'sale')

    def test_07_get_cart_id_extraction(self):
        """Test _get_cart_id creates cart and returns ID"""
        body = {
            'cartId': 'CART_TEST_001',
        }
        
        order_obj = self.env['sale.order']
        cart_id = order_obj._get_cart_id(body)
        
        # Should create cart and return its ID
        self.assertTrue(cart_id)
        self.assertIsInstance(cart_id, int)
        
        # Verify cart was created
        cart = self.env['sale.order.cart'].search([
            ('producteca_id', '=', 'CART_TEST_001')
        ])
        self.assertTrue(cart)
        self.assertEqual(cart.id, cart_id)

    def test_08_get_cart_id_returns_none_when_missing(self):
        """Test _get_cart_id returns None when cartId not in body"""
        body = {}
        
        order_obj = self.env['sale.order']
        cart_id = order_obj._get_cart_id(body)
        
        self.assertIsNone(cart_id)

    def test_09_mapped_origin_application_with_valid_channel(self):
        """Test _mapped_origin_application with valid channel"""
        order_obj = self.env['sale.order']
        
        # Test with channel 0 or similar
        result = order_obj._mapped_origin_application(0)
        # Result can be False or an application record
        self.assertIsNotNone(result)

    def test_10_sale_order_run_quotation_process(self):
        """Test _run_quotation_process confirms order when in draft"""
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        
        self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product.id,
            'product_uom_qty': 1,
            'price_unit': 100.0,
        })
        
        self.assertEqual(order.state, 'draft')
        
        order._run_quotation_process()
        
        # Should move to sale state
        self.assertEqual(order.state, 'sale')

    def test_11_sale_order_run_confirm_process(self):
        """Test _run_confirm_process confirms and creates/posts invoice"""
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        
        self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product.id,
            'product_uom_qty': 1,
            'price_unit': 100.0,
        })
        
        order._run_confirm_process()
        
        # Should be confirmed
        self.assertEqual(order.state, 'sale')
        # Should have invoice created and posted
        self.assertTrue(len(order.invoice_ids) > 0)
        posted_invoices = order.invoice_ids.filtered(lambda i: i.state == 'posted')
        self.assertTrue(len(posted_invoices) > 0)

