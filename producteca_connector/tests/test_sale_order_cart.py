# -*- coding: utf-8 -*-
"""
Test module for sale_order_cart.py - Producteca Connector
Tests for SaleOrderCart model and functionality
"""

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestSaleOrderCart(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test company
        cls.company = cls.env.company
        
        # Create test partner
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Cart Customer',
            'email': 'cart@customer.com',
        })
        
        # Create test product
        cls.product = cls.env['product.product'].create({
            'name': 'Test Cart Product',
            'type': 'product',
            'list_price': 50.0,
        })

    def test_01_sale_order_cart_model_exists(self):
        """Test that sale.order.cart model exists"""
        cart = self.env['sale.order.cart'].create({
            'producteca_id': 'TEST_CART_001',
        })
        
        # Should exist and have correct model name
        self.assertEqual(cart._name, 'sale.order.cart')
        self.assertEqual(cart._description, 'Sale Order Cart')

    def test_02_cart_field_properties(self):
        """Test cart field properties"""
        cart = self.env['sale.order.cart'].create({
            'producteca_id': 'TEST_CART_002',
        })
        
        # Test field existence and properties
        fields = cart._fields
        
        self.assertIn('producteca_id', fields)
        self.assertEqual(fields['producteca_id'].type, 'char')
        self.assertEqual(fields['producteca_id'].string, 'Producteca ID')
        
        self.assertIn('order_ids', fields)
        self.assertEqual(fields['order_ids'].type, 'one2many')
        self.assertEqual(fields['order_ids'].comodel_name, 'sale.order')
        self.assertEqual(fields['order_ids'].inverse_name, 'cart_id')
        self.assertEqual(fields['order_ids'].string, 'Orders')

    def test_03_cart_rec_name_functionality(self):
        """Test cart _rec_name functionality"""
        cart = self.env['sale.order.cart'].create({
            'producteca_id': 'DISPLAY_CART_001',
        })
        
        # Display name should be producteca_id
        self.assertEqual(cart.display_name, 'DISPLAY_CART_001')
        self.assertEqual(cart.name_get()[0][1], 'DISPLAY_CART_001')

    def test_04_create_cart_with_producteca_id(self):
        """Test creating cart with Producteca ID"""
        cart = self.env['sale.order.cart'].create({
            'producteca_id': 'CREATE_CART_001',
        })
        
        # Test basic properties
        self.assertEqual(cart.producteca_id, 'CREATE_CART_001')
        self.assertEqual(len(cart.order_ids), 0)  # No orders initially

    def test_05_cart_without_producteca_id(self):
        """Test creating cart without Producteca ID"""
        cart = self.env['sale.order.cart'].create({})
        
        # Should create successfully
        self.assertTrue(cart.exists())
        self.assertFalse(cart.producteca_id)
        self.assertEqual(len(cart.order_ids), 0)

    def test_06_cart_with_single_order(self):
        """Test cart with single sale order"""
        cart = self.env['sale.order.cart'].create({
            'producteca_id': 'SINGLE_ORDER_CART',
        })
        
        # Create sale order linked to cart
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'cart_id': cart.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 50.0,
            })],
        })
        
        # Test relationship
        self.assertEqual(len(cart.order_ids), 1)
        self.assertEqual(cart.order_ids[0].id, sale_order.id)
        self.assertEqual(sale_order.cart_id.id, cart.id)

    def test_07_cart_with_multiple_orders(self):
        """Test cart with multiple sale orders"""
        cart = self.env['sale.order.cart'].create({
            'producteca_id': 'MULTI_ORDER_CART',
        })
        
        # Create multiple sale orders linked to cart
        orders = []
        for i in range(3):
            order = self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'cart_id': cart.id,
                'order_line': [(0, 0, {
                    'product_id': self.product.id,
                    'product_uom_qty': i + 1,
                    'price_unit': 50.0,
                })],
            })
            orders.append(order)
        
        # Test relationships
        self.assertEqual(len(cart.order_ids), 3)
        
        for order in orders:
            self.assertIn(order.id, cart.order_ids.ids)
            self.assertEqual(order.cart_id.id, cart.id)

    def test_08_cart_order_relationship_integrity(self):
        """Test cart-order relationship integrity"""
        cart = self.env['sale.order.cart'].create({
            'producteca_id': 'INTEGRITY_CART',
        })
        
        # Create order with cart
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'cart_id': cart.id,
        })
        
        # Test forward relationship
        self.assertEqual(len(cart.order_ids), 1)
        self.assertEqual(cart.order_ids[0].id, order.id)
        
        # Test reverse relationship
        self.assertEqual(order.cart_id.id, cart.id)
        
        # Remove cart from order
        order.write({'cart_id': False})
        
        # Cart should no longer have the order
        cart.refresh()
        self.assertEqual(len(cart.order_ids), 0)

    def test_09_cart_search_by_producteca_id(self):
        """Test searching carts by Producteca ID"""
        # Create multiple carts
        cart1 = self.env['sale.order.cart'].create({
            'producteca_id': 'SEARCH_CART_001',
        })
        
        cart2 = self.env['sale.order.cart'].create({
            'producteca_id': 'SEARCH_CART_002',
        })
        
        cart3 = self.env['sale.order.cart'].create({
            'producteca_id': 'SEARCH_CART_003',
        })
        
        # Search for specific cart
        found_cart = self.env['sale.order.cart'].search([
            ('producteca_id', '=', 'SEARCH_CART_002')
        ])
        
        self.assertEqual(len(found_cart), 1)
        self.assertEqual(found_cart.id, cart2.id)
        
        # Search for multiple carts
        found_carts = self.env['sale.order.cart'].search([
            ('producteca_id', 'in', ['SEARCH_CART_001', 'SEARCH_CART_003'])
        ])
        
        self.assertEqual(len(found_carts), 2)
        self.assertIn(cart1.id, found_carts.ids)
        self.assertIn(cart3.id, found_carts.ids)

    def test_10_cart_producteca_id_uniqueness(self):
        """Test Producteca ID uniqueness (if constraint exists)"""
        # Create first cart
        cart1 = self.env['sale.order.cart'].create({
            'producteca_id': 'UNIQUE_CART_001',
        })
        
        # Try to create second cart with same producteca_id
        try:
            cart2 = self.env['sale.order.cart'].create({
                'producteca_id': 'UNIQUE_CART_001',
            })
            # If no constraint, both should exist
            self.assertNotEqual(cart1.id, cart2.id)
        except ValidationError:
            # If constraint exists, should raise error
            pass

    def test_11_cart_order_deletion_behavior(self):
        """Test behavior when deleting orders from cart"""
        cart = self.env['sale.order.cart'].create({
            'producteca_id': 'DELETE_ORDER_CART',
        })
        
        # Create orders
        order1 = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'cart_id': cart.id,
        })
        
        order2 = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'cart_id': cart.id,
        })
        
        # Verify both orders in cart
        self.assertEqual(len(cart.order_ids), 2)
        
        # Delete one order
        order1.unlink()
        
        # Cart should have one order remaining
        cart.refresh()
        self.assertEqual(len(cart.order_ids), 1)
        self.assertEqual(cart.order_ids[0].id, order2.id)

    def test_12_cart_deletion_behavior(self):
        """Test behavior when deleting cart with orders"""
        cart = self.env['sale.order.cart'].create({
            'producteca_id': 'DELETE_CART_001',
        })
        
        # Create order linked to cart
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'cart_id': cart.id,
        })
        
        cart_id = cart.id
        order_id = order.id
        
        # Delete cart
        cart.unlink()
        
        # Order should still exist but cart_id should be cleared
        remaining_order = self.env['sale.order'].search([('id', '=', order_id)])
        self.assertEqual(len(remaining_order), 1)
        self.assertFalse(remaining_order.cart_id)
        
        # Cart should be deleted
        remaining_cart = self.env['sale.order.cart'].search([('id', '=', cart_id)])
        self.assertEqual(len(remaining_cart), 0)

    def test_13_cart_name_search_functionality(self):
        """Test cart name_search functionality"""
        # Create carts with different producteca_ids
        cart1 = self.env['sale.order.cart'].create({
            'producteca_id': 'NAME_SEARCH_CART_001',
        })
        
        cart2 = self.env['sale.order.cart'].create({
            'producteca_id': 'NAME_SEARCH_CART_002',
        })
        
        cart3 = self.env['sale.order.cart'].create({
            'producteca_id': 'DIFFERENT_PATTERN_001',
        })
        
        # Test name_search
        result = self.env['sale.order.cart'].name_search('NAME_SEARCH')
        
        # Should find carts with matching producteca_id
        result_ids = [r[0] for r in result]
        self.assertIn(cart1.id, result_ids)
        self.assertIn(cart2.id, result_ids)
        self.assertNotIn(cart3.id, result_ids)

    def test_14_cart_copy_behavior(self):
        """Test cart copy behavior"""
        original_cart = self.env['sale.order.cart'].create({
            'producteca_id': 'ORIGINAL_CART_001',
        })
        
        # Create order linked to original cart
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'cart_id': original_cart.id,
        })
        
        # Copy cart
        copied_cart = original_cart.copy({
            'producteca_id': 'COPIED_CART_001',
        })
        
        # Test copied cart
        self.assertEqual(copied_cart.producteca_id, 'COPIED_CART_001')
        self.assertNotEqual(copied_cart.id, original_cart.id)
        
        # Orders should not be copied (one2many fields typically don't copy)
        self.assertEqual(len(copied_cart.order_ids), 0)
        
        # Original cart should still have its order
        self.assertEqual(len(original_cart.order_ids), 1)

    def test_15_cart_write_operations(self):
        """Test cart write operations"""
        cart = self.env['sale.order.cart'].create({
            'producteca_id': 'WRITE_CART_001',
        })
        
        # Update producteca_id
        cart.write({'producteca_id': 'UPDATED_CART_001'})
        
        self.assertEqual(cart.producteca_id, 'UPDATED_CART_001')
        
        # Clear producteca_id
        cart.write({'producteca_id': False})
        
        self.assertFalse(cart.producteca_id)

    def test_16_cart_with_confirmed_orders(self):
        """Test cart with confirmed sale orders"""
        cart = self.env['sale.order.cart'].create({
            'producteca_id': 'CONFIRMED_ORDERS_CART',
        })
        
        # Create and confirm order
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'cart_id': cart.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 50.0,
            })],
        })
        
        # Confirm order
        order.action_confirm()
        
        # Cart should still contain confirmed order
        self.assertEqual(len(cart.order_ids), 1)
        self.assertEqual(cart.order_ids[0].state, 'sale')
        self.assertEqual(cart.order_ids[0].cart_id.id, cart.id)

    def test_17_cart_order_states_summary(self):
        """Test cart with orders in different states"""
        cart = self.env['sale.order.cart'].create({
            'producteca_id': 'STATES_CART_001',
        })
        
        # Create orders in different states
        draft_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'cart_id': cart.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 50.0,
            })],
        })
        
        confirmed_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'cart_id': cart.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 2,
                'price_unit': 50.0,
            })],
        })
        
        # Confirm one order
        confirmed_order.action_confirm()
        
        # Cart should contain both orders
        self.assertEqual(len(cart.order_ids), 2)
        
        # Check order states
        states = cart.order_ids.mapped('state')
        self.assertIn('draft', states)
        self.assertIn('sale', states)

    def test_18_cart_mass_operations(self):
        """Test mass operations on carts"""
        # Create multiple carts
        carts = []
        for i in range(5):
            cart = self.env['sale.order.cart'].create({
                'producteca_id': f'MASS_CART_{i:03d}',
            })
            carts.append(cart)
        
        # Test mass search
        all_mass_carts = self.env['sale.order.cart'].search([
            ('producteca_id', 'like', 'MASS_CART_%')
        ])
        
        self.assertEqual(len(all_mass_carts), 5)
        
        for cart in carts:
            self.assertIn(cart.id, all_mass_carts.ids)
        
        # Test mass update
        cart_recordset = self.env['sale.order.cart'].browse([c.id for c in carts])
        
        # Mass update is limited since there's only producteca_id field
        # But we can test that the recordset operations work
        self.assertEqual(len(cart_recordset), 5)

    def test_19_cart_integration_with_producteca_orders(self):
        """Test cart integration with Producteca orders"""
        cart = self.env['sale.order.cart'].create({
            'producteca_id': 'PRODUCTECA_INTEGRATION_CART',
        })
        
        # Create order with Producteca data
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'cart_id': cart.id,
            'producteca_id': 'PRODUCTECA_ORDER_001',
            'origin_platform': 'Mercado Libre',
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 50.0,
            })],
        })
        
        # Test integration
        self.assertEqual(cart.order_ids[0].producteca_id, 'PRODUCTECA_ORDER_001')
        self.assertEqual(cart.order_ids[0].origin_platform, 'Mercado Libre')
        self.assertEqual(cart.order_ids[0].cart_id.producteca_id, 'PRODUCTECA_INTEGRATION_CART')

    def test_20_cart_performance_with_many_orders(self):
        """Test cart performance with many orders"""
        cart = self.env['sale.order.cart'].create({
            'producteca_id': 'PERFORMANCE_CART',
        })
        
        # Create many orders
        orders = []
        for i in range(10):  # Reasonable number for testing
            order = self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'cart_id': cart.id,
                'order_line': [(0, 0, {
                    'product_id': self.product.id,
                    'product_uom_qty': 1,
                    'price_unit': 50.0,
                })],
            })
            orders.append(order)
        
        # Test that cart can handle many orders
        self.assertEqual(len(cart.order_ids), 10)
        
        # Test order access performance
        for order in orders:
            self.assertIn(order.id, cart.order_ids.ids)
        
        # Test cart access from orders
        for order in orders:
            self.assertEqual(order.cart_id.id, cart.id)

    def test_21_cart_field_constraints(self):
        """Test cart field constraints and validations"""
        # Test creating cart with various producteca_id values
        
        # Normal string
        cart1 = self.env['sale.order.cart'].create({
            'producteca_id': 'NORMAL_CART_001',
        })
        self.assertEqual(cart1.producteca_id, 'NORMAL_CART_001')
        
        # String with special characters
        cart2 = self.env['sale.order.cart'].create({
            'producteca_id': 'SPECIAL-CART_001@TEST',
        })
        self.assertEqual(cart2.producteca_id, 'SPECIAL-CART_001@TEST')
        
        # Numeric string
        cart3 = self.env['sale.order.cart'].create({
            'producteca_id': '123456789',
        })
        self.assertEqual(cart3.producteca_id, '123456789')
        
        # Empty string (should be allowed)
        cart4 = self.env['sale.order.cart'].create({
            'producteca_id': '',
        })
        self.assertEqual(cart4.producteca_id, '')

    def test_22_cart_access_rights(self):
        """Test cart access rights and security"""
        # Create cart
        cart = self.env['sale.order.cart'].create({
            'producteca_id': 'ACCESS_RIGHTS_CART',
        })
        
        # Test basic CRUD operations work
        # (More detailed access rights testing would require specific user contexts)
        
        # Read
        read_cart = self.env['sale.order.cart'].browse(cart.id)
        self.assertEqual(read_cart.producteca_id, 'ACCESS_RIGHTS_CART')
        
        # Update
        cart.write({'producteca_id': 'UPDATED_ACCESS_CART'})
        self.assertEqual(cart.producteca_id, 'UPDATED_ACCESS_CART')
        
        # Create
        new_cart = self.env['sale.order.cart'].create({
            'producteca_id': 'NEW_ACCESS_CART',
        })
        self.assertTrue(new_cart.exists())
        
        # Delete
        cart_id = new_cart.id
        new_cart.unlink()
        deleted_cart = self.env['sale.order.cart'].search([('id', '=', cart_id)])
        self.assertEqual(len(deleted_cart), 0)

    def test_23_cart_domain_filtering(self):
        """Test cart domain filtering capabilities"""
        # Create carts for filtering tests
        cart1 = self.env['sale.order.cart'].create({
            'producteca_id': 'FILTER_CART_001',
        })
        
        cart2 = self.env['sale.order.cart'].create({
            'producteca_id': 'FILTER_CART_002',
        })
        
        cart3 = self.env['sale.order.cart'].create({
            'producteca_id': 'DIFFERENT_PATTERN',
        })
        
        # Add orders to some carts
        self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'cart_id': cart1.id,
        })
        
        self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'cart_id': cart1.id,
        })
        
        # Test filtering by producteca_id pattern
        filtered_carts = self.env['sale.order.cart'].search([
            ('producteca_id', 'like', 'FILTER_CART_%')
        ])
        
        self.assertEqual(len(filtered_carts), 2)
        self.assertIn(cart1.id, filtered_carts.ids)
        self.assertIn(cart2.id, filtered_carts.ids)
        self.assertNotIn(cart3.id, filtered_carts.ids)
        
        # Test filtering by order count (if supported)
        # This would require a computed field or custom domain

    def test_24_cart_export_import_functionality(self):
        """Test cart export/import functionality"""
        # Create cart with data
        original_cart = self.env['sale.order.cart'].create({
            'producteca_id': 'EXPORT_CART_001',
        })
        
        # Add order to cart
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'cart_id': original_cart.id,
        })
        
        # Test data export (read)
        cart_data = original_cart.read(['producteca_id'])
        self.assertEqual(len(cart_data), 1)
        self.assertEqual(cart_data[0]['producteca_id'], 'EXPORT_CART_001')
        
        # Test data import (create from data)
        import_data = {
            'producteca_id': 'IMPORTED_CART_001',
        }
        
        imported_cart = self.env['sale.order.cart'].create(import_data)
        self.assertEqual(imported_cart.producteca_id, 'IMPORTED_CART_001')

    def test_25_comprehensive_cart_functionality(self):
        """Test comprehensive cart functionality and edge cases"""
        # Create comprehensive test scenario
        
        # 1. Create cart with full data
        cart = self.env['sale.order.cart'].create({
            'producteca_id': 'COMPREHENSIVE_CART_001',
        })
        
        # 2. Create multiple orders with different characteristics
        
        # Draft order
        draft_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'cart_id': cart.id,
            'producteca_id': 'DRAFT_ORDER_001',
            'origin_platform': 'Amazon',
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 50.0,
            })],
        })
        
        # Confirmed order
        confirmed_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'cart_id': cart.id,
            'producteca_id': 'CONFIRMED_ORDER_001',
            'origin_platform': 'Mercado Libre',
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 2,
                'price_unit': 50.0,
            })],
        })
        confirmed_order.action_confirm()
        
        # Order with invoice
        invoice_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'cart_id': cart.id,
            'producteca_id': 'INVOICE_ORDER_001',
            'origin_platform': 'Shopify',
            'has_existing_producteca_invoice': True,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 3,
                'price_unit': 50.0,
            })],
        })
        invoice_order.action_confirm()
        invoices = invoice_order._create_invoices()
        
        # 3. Test comprehensive functionality
        
        # Basic cart properties
        self.assertEqual(cart.producteca_id, 'COMPREHENSIVE_CART_001')
        self.assertEqual(cart.display_name, 'COMPREHENSIVE_CART_001')
        
        # Order relationships
        self.assertEqual(len(cart.order_ids), 3)
        
        # Test all orders are properly linked
        for order in [draft_order, confirmed_order, invoice_order]:
            self.assertIn(order.id, cart.order_ids.ids)
            self.assertEqual(order.cart_id.id, cart.id)
        
        # Test order states
        states = cart.order_ids.mapped('state')
        self.assertIn('draft', states)
        self.assertIn('sale', states)
        
        # Test order platforms  
        platforms = cart.order_ids.mapped('origin_platform')
        self.assertIn('Amazon', platforms)
        self.assertIn('Mercado Libre', platforms)
        self.assertIn('Shopify', platforms)
        
        # Test order totals
        total_amount = sum(cart.order_ids.mapped('amount_total'))
        expected_total = 50.0 + 100.0 + 150.0  # 1*50 + 2*50 + 3*50
        self.assertEqual(total_amount, expected_total)
        
        # 4. Test search and filtering
        
        # Search by cart producteca_id
        found_cart = self.env['sale.order.cart'].search([
            ('producteca_id', '=', 'COMPREHENSIVE_CART_001')
        ])
        self.assertEqual(len(found_cart), 1)
        self.assertEqual(found_cart.id, cart.id)
        
        # Search by order relationship (if domain supports it)
        carts_with_confirmed_orders = self.env['sale.order.cart'].search([
            ('order_ids.state', '=', 'sale')
        ])
        self.assertIn(cart.id, carts_with_confirmed_orders.ids)
        
        # 5. Test update operations
        
        # Update cart producteca_id
        cart.write({'producteca_id': 'UPDATED_COMPREHENSIVE_CART'})
        self.assertEqual(cart.producteca_id, 'UPDATED_COMPREHENSIVE_CART')
        
        # All order relationships should remain intact
        self.assertEqual(len(cart.order_ids), 3)
        
        for order in [draft_order, confirmed_order, invoice_order]:
            order.refresh()
            self.assertEqual(order.cart_id.id, cart.id)
        
        # 6. Test deletion scenarios
        
        # Remove one order from cart
        draft_order.write({'cart_id': False})
        cart.refresh()
        self.assertEqual(len(cart.order_ids), 2)
        self.assertNotIn(draft_order.id, cart.order_ids.ids)
        
        # Add order back
        draft_order.write({'cart_id': cart.id})
        cart.refresh()
        self.assertEqual(len(cart.order_ids), 3)
        
        # 7. Test copy behavior
        
        copied_cart = cart.copy({
            'producteca_id': 'COPIED_COMPREHENSIVE_CART',
        })
        
        # Copied cart should have different ID and producteca_id
        self.assertNotEqual(copied_cart.id, cart.id)
        self.assertEqual(copied_cart.producteca_id, 'COPIED_COMPREHENSIVE_CART')
        
        # Orders should not be copied (one2many behavior)
        self.assertEqual(len(copied_cart.order_ids), 0)
        
        # Original cart should keep all orders
        self.assertEqual(len(cart.order_ids), 3)
        
        # 8. Test name_get and display functionality
        
        name_result = cart.name_get()
        self.assertEqual(len(name_result), 1)
        self.assertEqual(name_result[0][0], cart.id)
        self.assertEqual(name_result[0][1], 'UPDATED_COMPREHENSIVE_CART')
        
        # 9. Test field access and properties
        
        # Test field access works correctly
        self.assertEqual(cart._rec_name, 'producteca_id')
        self.assertEqual(cart._description, 'Sale Order Cart')
        
        # Test all orders still accessible through relationship
        for order in cart.order_ids:
            self.assertTrue(order.exists())
            self.assertIsNotNone(order.producteca_id)
            self.assertIsNotNone(order.origin_platform)
        
        # 10. Final validation
        
        # Cart should be fully functional after all operations
        self.assertTrue(cart.exists())
        self.assertEqual(cart.producteca_id, 'UPDATED_COMPREHENSIVE_CART')
        self.assertEqual(len(cart.order_ids), 3)
        
        # All orders should maintain their relationships and data
        for order in cart.order_ids:
            self.assertEqual(order.cart_id.id, cart.id)
            self.assertTrue(order.exists())
            self.assertGreater(len(order.order_line), 0)