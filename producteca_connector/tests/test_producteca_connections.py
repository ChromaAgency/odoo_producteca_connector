# -*- coding: utf-8 -*-
"""Tests for producteca.product.connections model - Variant-based connections"""

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestProductecaConnections(TransactionCase):
    """Test producteca.product.connections with variant-based logic"""

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

    def test_01_connection_uses_product_id(self):
        """Test connections use product_id (variant) not product_tmpl_id"""
        template = self.env['product.template'].create({
            'name': 'Test Template',
            'type': 'consu',
        })
        
        variant = template.product_variant_ids[0]
        
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.account.id,
            'product_id': variant.id,
            'producteca_id': 'PROD_001',
            'producteca_variation_id': 'VAR_001',
        })
        
        self.assertEqual(connection.product_id.id, variant.id)
        self.assertEqual(connection.product_tmpl_id.id, template.id)

    def test_02_unique_variant_per_account(self):
        """Test unique constraint: one variant can't have multiple connections to same account"""
        template = self.env['product.template'].create({
            'name': 'Constraint Test',
            'type': 'consu',
        })
        
        variant = template.product_variant_ids[0]
        
        self.env['producteca.product.connections'].create({
            'producteca_account_id': self.account.id,
            'product_id': variant.id,
            'producteca_id': 'PROD_002',
            'producteca_variation_id': 'VAR_002',
        })
        
        with self.assertRaises(ValidationError):
            self.env['producteca.product.connections'].create({
                'producteca_account_id': self.account.id,
                'product_id': variant.id,
                'producteca_id': 'PROD_002',
                'producteca_variation_id': 'VAR_003',  # Different variation
            })

    def test_03_search_connections_by_producteca_variation_id(self):
        """Test searching connections by producteca_variation_id"""
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
            'product_id': variant.id,
            'producteca_id': 'PROD_SEARCH_001',
            'producteca_variation_id': 'VAR_SEARCH_001',
        })
        
        found = self.env['producteca.product.connections'].search([
            ('producteca_variation_id', '=', 'VAR_SEARCH_001'),
            ('producteca_account_id', '=', self.account.id)
        ])
        
        self.assertEqual(found, connection)

    def test_04_active_field_default_true(self):
        """Test active field defaults to True"""
        template = self.env['product.template'].create({
            'name': 'Active Test',
            'type': 'consu',
        })
        
        variant = template.product_variant_ids[0]
        
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.account.id,
            'product_id': variant.id,
            'producteca_id': 'PROD_ACTIVE',
            'producteca_variation_id': 'VAR_ACTIVE',
        })
        
        self.assertTrue(connection.active)

    def test_05_multiple_variants_same_product(self):
        """Test product can have multiple variant connections to same account"""
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
        
        conn1 = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.account.id,
            'product_id': variant1.id,
            'producteca_id': 'PROD_MULTI',
            'producteca_variation_id': 'VAR_MULTI_1',
        })
        
        conn2 = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.account.id,
            'product_id': variant2.id,
            'producteca_id': 'PROD_MULTI',
            'producteca_variation_id': 'VAR_MULTI_2',
        })
        
        self.assertEqual(variant1.producteca_connection_ids, conn1)
        self.assertEqual(variant2.producteca_connection_ids, conn2)
        
        # Ambas conexiones tienen el mismo producteca_id (producto)
        self.assertEqual(conn1.producteca_id, conn2.producteca_id)
        # Pero diferentes producteca_variation_id
        self.assertNotEqual(conn1.producteca_variation_id, conn2.producteca_variation_id)
