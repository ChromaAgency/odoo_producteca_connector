# -*- coding: utf-8 -*-
"""Tests for producteca.product.connections model - Template Migration"""

from odoo.tests.common import TransactionCase


class TestProductecaConnections(TransactionCase):
    """Test producteca.product.connections with template-based logic"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.account = cls.env['producteca.account'].create({
            'account_name': 'Test Account',
            'api_key': 'test_key',
            'bearer_token': 'test_token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': cls.env['stock.warehouse'].search([], limit=1).id,
        })

    def test_01_connection_uses_product_tmpl_id(self):
        """Test connections use product_tmpl_id not product_id"""
        template = self.env['product.template'].create({
            'name': 'Test Template',
            'type': 'consu',
        })
        
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.account.id,
            'product_tmpl_id': template.id,
            'producteca_id': 'PROD_001',
        })
        
        self.assertEqual(connection.product_tmpl_id.id, template.id)
        self.assertFalse(hasattr(connection, 'product_id'))

    def test_02_connection_has_many2many_variants(self):
        """Test connections have Many2many product_variant_ids field"""
        template = self.env['product.template'].create({
            'name': 'Multi Variant Template',
            'type': 'consu',
        })
        
        variant1 = self.env['product.product'].create({
            'product_tmpl_id': template.id,
            'default_code': 'VAR001',
        })
        
        variant2 = self.env['product.product'].create({
            'product_tmpl_id': template.id,
            'default_code': 'VAR002',
        })
        
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.account.id,
            'product_tmpl_id': template.id,
            'producteca_id': 'PROD_002',
            'product_variant_ids': [(6, 0, [variant1.id, variant2.id])],
        })
        
        self.assertEqual(len(connection.product_variant_ids), 2)
        self.assertIn(variant1, connection.product_variant_ids)
        self.assertIn(variant2, connection.product_variant_ids)

    def test_03_search_connections_by_variant(self):
        """Test searching connections by variant ID"""
        template = self.env['product.template'].create({
            'name': 'Search Test Template',
            'type': 'consu',
        })
        
        variant = self.env['product.product'].create({
            'product_tmpl_id': template.id,
            'default_code': 'SEARCH001',
        })
        
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.account.id,
            'product_tmpl_id': template.id,
            'producteca_id': 'PROD_SEARCH_001',
            'product_variant_ids': [(6, 0, [variant.id])],
        })
        
        found = self.env['producteca.product.connections'].search([
            ('product_variant_ids', 'in', variant.id)
        ])
        
        self.assertIn(connection, found)

    def test_04_active_field_default_true(self):
        """Test active field defaults to True"""
        template = self.env['product.template'].create({
            'name': 'Active Test',
            'type': 'consu',
        })
        
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.account.id,
            'product_tmpl_id': template.id,
            'producteca_id': 'PROD_ACTIVE',
        })
        
        self.assertTrue(connection.active)

    def test_05_multiple_connections_same_template(self):
        """Test template can have multiple connections to different accounts"""
        template = self.env['product.template'].create({
            'name': 'Multi Connection Template',
            'type': 'consu',
        })
        
        account2 = self.env['producteca.account'].create({
            'account_name': 'Second Account',
            'api_key': 'key2',
            'bearer_token': 'token2',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': self.env['stock.warehouse'].search([], limit=1).id,
        })
        
        conn1 = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.account.id,
            'product_tmpl_id': template.id,
            'producteca_id': 'PROD_MULTI_1',
        })
        
        conn2 = self.env['producteca.product.connections'].create({
            'producteca_account_id': account2.id,
            'product_tmpl_id': template.id,
            'producteca_id': 'PROD_MULTI_2',
        })
        
        self.assertEqual(len(template.producteca_connection_ids), 2)
        self.assertIn(conn1, template.producteca_connection_ids)
        self.assertIn(conn2, template.producteca_connection_ids)
