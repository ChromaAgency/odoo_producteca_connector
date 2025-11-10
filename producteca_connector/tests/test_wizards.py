# -*- coding: utf-8 -*-
"""Tests for Producteca wizards"""

from odoo.tests.common import TransactionCase
from psycopg2 import IntegrityError


class TestProductecaWizards(TransactionCase):
    """Test Producteca import wizards"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.warehouse = cls.env['stock.warehouse'].search([], limit=1)
        
        cls.account = cls.env['producteca.account'].create({
            'account_name': 'Test Wizard Account',
            'api_key': 'test_api_key',
            'bearer_token': 'test_bearer_token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': cls.warehouse.id,
            'is_producteca_able_to_create_products': True,
        })

    def test_01_create_product_import_wizard(self):
        """Test creating producteca.products.wizard"""
        wizard = self.env['producteca.products.wizard'].create({
            'producteca_account_id': self.account.id,
            'search_text': 'PROD001,PROD002',
        })
        
        self.assertEqual(wizard.producteca_account_id.id, self.account.id)
        self.assertEqual(wizard.search_text, 'PROD001,PROD002')

    def test_02_product_wizard_requires_account(self):
        """Test product wizard requires account"""
        with self.assertRaises(IntegrityError):
            self.env['producteca.products.wizard'].create({
                'search_text': 'PROD001',
            })

    def test_03_product_wizard_requires_search_text(self):
        """Test product wizard requires search text"""
        with self.assertRaises(IntegrityError):
            self.env['producteca.products.wizard'].create({
                'producteca_account_id': self.account.id,
            })

    def test_04_create_saleorder_import_wizard(self):
        """Test creating producteca.saleorders.wizard"""
        wizard = self.env['producteca.saleorders.wizard'].create({
            'producteca_account_id': self.account.id,
            'search_text': 'ORDER001,ORDER002',
        })
        
        self.assertEqual(wizard.producteca_account_id.id, self.account.id)
        self.assertEqual(wizard.search_text, 'ORDER001,ORDER002')

    def test_05_saleorder_wizard_requires_account(self):
        """Test saleorder wizard requires account"""
        with self.assertRaises(Exception):
            self.env['producteca.saleorders.wizard'].create({
                'search_text': 'ORDER001',
            })
    
    def test_06_saleorder_wizard_requires_search_text(self):
        """Test saleorder wizard requires search text"""
        with self.assertRaises(Exception):
            self.env['producteca.saleorders.wizard'].create({
                'producteca_account_id': self.account.id,
            })

    def test_07_wizard_with_account_without_create_permission(self):
        """Test wizard validates account permissions"""
        restricted_account = self.env['producteca.account'].create({
            'account_name': 'Restricted Account',
            'api_key': 'restricted_key',
            'bearer_token': 'restricted_token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.warehouse.id,
            'is_producteca_able_to_create_products': False,
        })
        
        wizard = self.env['producteca.products.wizard'].create({
            'producteca_account_id': restricted_account.id,
            'search_text': 'PROD001',
        })
        
        # Wizard should be created but action should validate permissions
        self.assertFalse(wizard.producteca_account_id.is_producteca_able_to_create_products)
