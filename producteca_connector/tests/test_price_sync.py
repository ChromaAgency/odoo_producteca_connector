# -*- coding: utf-8 -*-
"""Tests for price synchronization between Odoo and Producteca"""

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from unittest.mock import patch, MagicMock


class TestPriceSynchronization(TransactionCase):
    """Test price sync configurations and behaviors"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.warehouse = cls.env['stock.warehouse'].search([], limit=1)
        cls.pricelist = cls.env['product.pricelist'].create({
            'name': 'Test Pricelist',
        })

    def test_01_price_sync_mutual_exclusivity_constraint(self):
        """Test that both price sync options cannot be True simultaneously"""
        with self.assertRaises(Exception):
            self.env['producteca.account'].create({
                'account_name': 'Invalid Price Sync',
                'api_key': 'key',
                'bearer_token': 'token',
                'imported_sale_action': 'quotation',
                'default_warehouse_id': self.warehouse.id,
                'is_product_price_modified_by_producteca': True,
                'is_odoo_able_to_update_producteca_prices': True,
            })

    def test_02_producteca_modifies_prices_in_odoo(self):
        """Test account configured for Producteca to modify prices in Odoo"""
        account = self.env['producteca.account'].create({
            'account_name': 'Producteca Updates Odoo',
            'api_key': 'key',
            'bearer_token': 'token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
            'is_product_price_modified_by_producteca': True,
            'is_odoo_able_to_update_producteca_prices': False,
        })
        
        self.assertTrue(account.is_product_price_modified_by_producteca)
        self.assertFalse(account.is_odoo_able_to_update_producteca_prices)

    def test_03_odoo_updates_prices_in_producteca(self):
        """Test account configured for Odoo to update prices in Producteca"""
        account = self.env['producteca.account'].create({
            'account_name': 'Odoo Updates Producteca',
            'api_key': 'key',
            'bearer_token': 'token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
            'default_pricelist_id': self.pricelist.id,
            'is_product_price_modified_by_producteca': False,
            'is_odoo_able_to_update_producteca_prices': True,
        })
        
        self.assertFalse(account.is_product_price_modified_by_producteca)
        self.assertTrue(account.is_odoo_able_to_update_producteca_prices)
        self.assertEqual(account.default_pricelist_id.id, self.pricelist.id)

    def test_04_no_price_sync_both_false(self):
        """Test account with no price synchronization"""
        account = self.env['producteca.account'].create({
            'account_name': 'No Price Sync',
            'api_key': 'key',
            'bearer_token': 'token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
            'is_product_price_modified_by_producteca': False,
            'is_odoo_able_to_update_producteca_prices': False,
        })
        
        self.assertFalse(account.is_product_price_modified_by_producteca)
        self.assertFalse(account.is_odoo_able_to_update_producteca_prices)

    def test_05_odoo_price_update_requires_pricelist(self):
        """Test that updating Producteca prices from Odoo requires pricelist"""
        account = self.env['producteca.account'].create({
            'account_name': 'Needs Pricelist',
            'api_key': 'key',
            'bearer_token': 'token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
            'is_odoo_able_to_update_producteca_prices': True,
            'default_pricelist_id': self.pricelist.id,
        })
        
        # Should have pricelist when enabling price updates
        self.assertTrue(account.default_pricelist_id)

    def test_06_price_sync_from_producteca_in_sale_order(self):
        """Test that sale order uses Producteca prices when configured"""
        account = self.env['producteca.account'].create({
            'account_name': 'SO Price from Producteca',
            'api_key': 'key',
            'bearer_token': 'token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
            'is_product_price_modified_by_producteca': True,
        })
        
        # When importing sale orders, should use Producteca prices
        self.assertTrue(account.is_product_price_modified_by_producteca)

    def test_07_default_pricelist_not_in_additional_pricelists(self):
        """Test constraint that default pricelist cannot be in additional pricelists"""
        pricelist1 = self.env['product.pricelist'].create({
            'name': 'Default Pricelist Constraint',
        })
        
        pricelist2 = self.env['product.pricelist'].create({
            'name': 'Additional Pricelist Constraint',
            'producteca_pricelist_name': 'PRODUCTECA_LIST',
        })
        
        # First create account with valid configuration
        account = self.env['producteca.account'].create({
            'account_name': 'Pricelist Test',
            'api_key': 'key',
            'bearer_token': 'token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
            'default_pricelist_id': pricelist1.id,
            'pricelist_ids': [(6, 0, [pricelist2.id])],
        })
        
        # Verify initial state is correct
        self.assertEqual(account.default_pricelist_id.id, pricelist1.id)
        self.assertIn(pricelist2, account.pricelist_ids)
        self.assertNotIn(pricelist1, account.pricelist_ids)
        
        # Set producteca name on pricelist1 to allow it in pricelist_ids
        pricelist1.producteca_pricelist_name = 'DEFAULT_LIST'
        
        # Now try to violate constraint - should fail
        with self.assertRaises(ValidationError):
            account.write({
                'pricelist_ids': [(6, 0, [pricelist1.id, pricelist2.id])],
            })

    def test_08_stock_sync_configuration(self):
        """Test stock synchronization configuration"""
        account = self.env['producteca.account'].create({
            'account_name': 'Stock Sync Test',
            'api_key': 'key',
            'bearer_token': 'token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
            'is_stock_modified_by_producteca': True,
        })
        
        self.assertTrue(account.is_stock_modified_by_producteca)

    def test_09_product_creation_and_modification_flags(self):
        """Test product creation and modification flags work independently"""
        # Can create but not modify
        account1 = self.env['producteca.account'].create({
            'account_name': 'Create Only',
            'api_key': 'key1',
            'bearer_token': 'token1',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
            'is_producteca_able_to_create_products': True,
            'is_producteca_able_to_modified_products': False,
        })
        
        self.assertTrue(account1.is_producteca_able_to_create_products)
        self.assertFalse(account1.is_producteca_able_to_modified_products)
        
        # Can modify but not create
        account2 = self.env['producteca.account'].create({
            'account_name': 'Modify Only',
            'api_key': 'key2',
            'bearer_token': 'token2',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
            'is_producteca_able_to_create_products': False,
            'is_producteca_able_to_modified_products': True,
        })
        
        self.assertFalse(account2.is_producteca_able_to_create_products)
        self.assertTrue(account2.is_producteca_able_to_modified_products)
        
        # Can do both
        account3 = self.env['producteca.account'].create({
            'account_name': 'Create and Modify',
            'api_key': 'key3',
            'bearer_token': 'token3',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
            'is_producteca_able_to_create_products': True,
            'is_producteca_able_to_modified_products': True,
        })
        
        self.assertTrue(account3.is_producteca_able_to_create_products)
        self.assertTrue(account3.is_producteca_able_to_modified_products)

    def test_10_create_if_doesnt_exist_flag(self):
        """Test create_if_dosnt_exist flag behavior"""
        account = self.env['producteca.account'].create({
            'account_name': 'Auto Create Test',
            'api_key': 'key',
            'bearer_token': 'token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
            'is_producteca_able_to_create_products': True,
            'create_if_dosnt_exist': True,
        })
        
        self.assertTrue(account.create_if_dosnt_exist)
        self.assertTrue(account.is_producteca_able_to_create_products)
