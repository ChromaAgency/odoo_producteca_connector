# -*- coding: utf-8 -*-
"""Tests for producteca.account model"""

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestProductecaAccount(TransactionCase):
    """Test producteca.account configuration"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env['stock.warehouse'].search([], limit=1)
        cls.pricelist = cls.env['product.pricelist'].search([], limit=1)

    def test_01_create_account_with_required_fields(self):
        """Test creating account with all required fields"""
        account = self.env['producteca.account'].create({
            'account_name': 'Test Account',
            'api_key': 'test_api_key_123',
            'bearer_token': 'test_bearer_token_456',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
        })
        
        self.assertTrue(account.id)
        self.assertEqual(account.account_name, 'Test Account')
        self.assertTrue(account.active)

    def test_02_required_fields_validation(self):
        """Test required fields raise validation errors"""
        warehouse = self.env['stock.warehouse'].search([], limit=1)
        
        # Missing api_key should fail
        with self.assertRaises(Exception):
            self.env['producteca.account'].create({
                'account_name': 'Missing API Key',
                'default_warehouse_id': warehouse.id,
                'imported_sale_action': 'quotation',
            })

    def test_03_get_client_method(self):
        """Test get_client returns ProductecaClient"""
        account = self.env['producteca.account'].create({
            'account_name': 'Client Test',
            'api_key': 'api_key',
            'bearer_token': 'bearer_token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
        })
        
        client = account.get_client()
        self.assertIsNotNone(client)

    def test_04_default_values(self):
        """Test default field values"""
        account = self.env['producteca.account'].create({
            'account_name': 'Defaults Test',
            'api_key': 'key',
            'bearer_token': 'token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
        })
        
        self.assertTrue(account.active)
        self.assertEqual(account.get_orders_from_last_days, 7)
        self.assertFalse(account.is_producteca_able_to_create_products)
        self.assertFalse(account.is_producteca_able_to_modified_products)

    def test_05_price_sync_constraint(self):
        """Test mutual exclusivity of price sync fields"""
        warehouse = self.env['stock.warehouse'].search([], limit=1)
        
        # Both price sync fields True should raise constraint violation
        with self.assertRaises(Exception):
            self.env['producteca.account'].create({
                'account_name': 'Price Sync Test',
                'api_key': 'key',
                'bearer_token': 'token',
                'imported_sale_action': 'quotation',
                'default_warehouse_id': warehouse.id,
                'is_odoo_able_to_update_producteca_prices': True,
                'is_product_price_modified_by_producteca': True,
            })

    def test_06_rec_name_is_account_name(self):
        """Test that display name uses account_name"""
        account = self.env['producteca.account'].create({
            'account_name': 'Display Name Test',
            'api_key': 'key',
            'bearer_token': 'token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
        })
        
        self.assertEqual(account.display_name, 'Display Name Test')
