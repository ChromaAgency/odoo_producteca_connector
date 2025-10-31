# -*- coding: utf-8 -*-
"""
Test module for product_product.py - Producteca Connector
Tests for ProductProduct inheritance and Producteca integration
"""

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from unittest.mock import patch, MagicMock
import json


class TestProductProduct(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test company
        cls.company = cls.env.company
        
        # Create test warehouse
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Test Product Warehouse',
            'code': 'TPW',
            'company_id': cls.company.id,
        })
        
        # Create test producteca account
        cls.producteca_account = cls.env['producteca.account'].create({
            'account_name': 'Test Product Account',
            'api_key': 'test_product_api_key',
            'bearer_token': 'test_product_bearer_token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': cls.warehouse.id,
        })
        
        # Create test brand
        cls.brand = cls.env['product.brand'].create({
            'name': 'Test Brand',
        })

    def test_01_product_product_inheritance(self):
        """Test that product.product is properly inherited"""
        product = self.env['product.product'].create({
            'name': 'Test Product Inheritance',
            'type': 'product',
        })
        
        # Should inherit from product.product
        self.assertEqual(product._name, 'product.product')
        
        # Should have standard product.product functionality
        self.assertTrue(hasattr(product, 'name'))
        self.assertTrue(hasattr(product, 'type'))
        self.assertTrue(hasattr(product, 'list_price'))
        
        # Should have custom Producteca fields
        self.assertTrue(hasattr(product, 'is_producteca_product'))
        self.assertTrue(hasattr(product, 'producteca_connection_ids'))

    def test_02_is_producteca_product_field_properties(self):
        """Test is_producteca_product field properties"""
        product = self.env['product.product'].create({
            'name': 'Test Field Properties',
            'type': 'product',
        })
        
        # Test field existence and properties
        self.assertIn('is_producteca_product', product._fields)
        field = product._fields['is_producteca_product']
        
        self.assertEqual(field.type, 'boolean')
        self.assertEqual(field.string, 'Is Producteca Product')
        self.assertFalse(field.default)  # Should default to False

    def test_03_producteca_connection_ids_field_properties(self):
        """Test producteca_connection_ids field properties"""
        product = self.env['product.product'].create({
            'name': 'Test Connection Field',
            'type': 'product',
        })
        
        # Test field existence and properties
        self.assertIn('producteca_connection_ids', product._fields)
        field = product._fields['producteca_connection_ids']
        
        self.assertEqual(field.type, 'one2many')
        self.assertEqual(field.comodel_name, 'producteca.product.connections')
        self.assertEqual(field.inverse_name, 'product_id')
        self.assertEqual(field.string, 'Producteca Connections')

    def test_04_create_producteca_connection(self):
        """Test creating Producteca connection for product"""
        product = self.env['product.product'].create({
            'name': 'Test Connection Creation',
            'type': 'product',
        })
        
        # Create connection
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': product.id,
            'producteca_id': 'CONN_PROD_001',
            'producteca_variation_id': 'CONN_VAR_001',
        })
        
        # Test relationship
        self.assertEqual(len(product.producteca_connection_ids), 1)
        self.assertEqual(product.producteca_connection_ids[0].id, connection.id)
        self.assertEqual(connection.product_id.id, product.id)

    def test_05_multiple_producteca_connections(self):
        """Test product with multiple Producteca connections"""
        product = self.env['product.product'].create({
            'name': 'Test Multiple Connections',
            'type': 'product',
        })
        
        # Create multiple connections
        connections = []
        for i in range(3):
            connection = self.env['producteca.product.connections'].create({
                'producteca_account_id': self.producteca_account.id,
                'product_id': product.id,
                'producteca_id': f'MULTI_PROD_{i:03d}',
                'producteca_variation_id': f'MULTI_VAR_{i:03d}',
            })
            connections.append(connection)
        
        # Test relationships
        self.assertEqual(len(product.producteca_connection_ids), 3)
        
        for i, connection in enumerate(connections):
            self.assertIn(connection.id, product.producteca_connection_ids.ids)
            self.assertEqual(connection.producteca_id, f'MULTI_PROD_{i:03d}')

    def test_06_is_producteca_product_flag(self):
        """Test is_producteca_product flag functionality"""
        product = self.env['product.product'].create({
            'name': 'Test Producteca Flag',
            'type': 'product',
        })
        
        # Initially should be False
        self.assertFalse(product.is_producteca_product)
        
        # Set to True
        product.write({'is_producteca_product': True})
        self.assertTrue(product.is_producteca_product)
        
        # Set back to False
        product.write({'is_producteca_product': False})
        self.assertFalse(product.is_producteca_product)

    def test_07_search_producteca_products(self):
        """Test searching for Producteca products"""
        # Create Producteca product
        producteca_product = self.env['product.product'].create({
            'name': 'Producteca Product',
            'type': 'product',
            'is_producteca_product': True,
        })
        
        # Create normal product
        normal_product = self.env['product.product'].create({
            'name': 'Normal Product',
            'type': 'product',
            'is_producteca_product': False,
        })
        
        # Search for Producteca products
        producteca_products = self.env['product.product'].search([
            ('is_producteca_product', '=', True)
        ])
        
        self.assertIn(producteca_product, producteca_products)
        self.assertNotIn(normal_product, producteca_products)

    def test_08_product_with_brand_integration(self):
        """Test product with brand integration for Producteca"""
        product = self.env['product.product'].create({
            'name': 'Test Brand Product',
            'type': 'product',
            'product_brand_id': self.brand.id,
            'is_producteca_product': True,
        })
        
        # Test brand relationship
        self.assertEqual(product.product_brand_id.id, self.brand.id)
        self.assertEqual(product.product_brand_id.name, 'Test Brand')
        
        # Create connection with brand context
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': product.id,
            'producteca_id': 'BRAND_PROD_001',
        })
        
        self.assertEqual(len(product.producteca_connection_ids), 1)

    def test_09_product_synchronization_fields(self):
        """Test product fields relevant for Producteca synchronization"""
        product = self.env['product.product'].create({
            'name': 'Sync Test Product',
            'type': 'product',
            'list_price': 150.0,
            'standard_price': 100.0,
            'weight': 2.5,
            'volume': 0.5,
            'barcode': '1234567890123',
            'default_code': 'SYNC001',
            'is_producteca_product': True,
        })
        
        # Test all sync-relevant fields
        self.assertEqual(product.name, 'Sync Test Product')
        self.assertEqual(product.list_price, 150.0)
        self.assertEqual(product.standard_price, 100.0)
        self.assertEqual(product.weight, 2.5)
        self.assertEqual(product.volume, 0.5)
        self.assertEqual(product.barcode, '1234567890123')
        self.assertEqual(product.default_code, 'SYNC001')
        self.assertTrue(product.is_producteca_product)

    def test_10_product_with_attributes(self):
        """Test product with attributes for Producteca variants"""
        # Create color attribute
        color_attribute = self.env['product.attribute'].create({
            'name': 'Color',
            'sequence': 1,
        })
        
        red_value = self.env['product.attribute.value'].create({
            'name': 'Red',
            'attribute_id': color_attribute.id,
        })
        
        # Create template with attribute
        template = self.env['product.template'].create({
            'name': 'Attribute Test Template',
            'type': 'product',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': color_attribute.id,
                'value_ids': [(6, 0, [red_value.id])],
            })],
        })
        
        # Get the variant
        product = template.product_variant_ids[0]
        
        # Mark as Producteca product
        product.write({'is_producteca_product': True})
        
        # Test attribute values
        self.assertEqual(len(product.product_template_attribute_value_ids), 1)
        attribute_value = product.product_template_attribute_value_ids[0]
        self.assertEqual(attribute_value.attribute_id.name, 'Color')
        self.assertEqual(attribute_value.product_attribute_value_id.name, 'Red')

    def test_11_product_connection_deletion(self):
        """Test product connection deletion behavior"""
        product = self.env['product.product'].create({
            'name': 'Connection Delete Test',
            'type': 'product',
            'is_producteca_product': True,
        })
        
        # Create connection
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': product.id,
            'producteca_id': 'DELETE_PROD_001',
        })
        
        connection_id = connection.id
        
        # Verify connection exists
        self.assertEqual(len(product.producteca_connection_ids), 1)
        
        # Delete connection
        connection.unlink()
        
        # Refresh product
        product.refresh()
        
        # Connection should be removed
        self.assertEqual(len(product.producteca_connection_ids), 0)
        
        # Verify connection is deleted
        remaining_connections = self.env['producteca.product.connections'].search([
            ('id', '=', connection_id)
        ])
        self.assertEqual(len(remaining_connections), 0)

    def test_12_product_stock_integration(self):
        """Test product stock integration for Producteca"""
        product = self.env['product.product'].create({
            'name': 'Stock Test Product',
            'type': 'product',
            'is_producteca_product': True,
        })
        
        # Test stock-related fields
        self.assertEqual(product.type, 'product')  # Stockable product
        
        # Check if product can have stock moves (basic integration test)
        self.assertTrue(hasattr(product, 'stock_move_ids'))
        
        # Create connection for stock sync
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': product.id,
            'producteca_id': 'STOCK_PROD_001',
        })
        
        # Test connection for stock product
        self.assertEqual(product.producteca_connection_ids[0].producteca_id, 'STOCK_PROD_001')

    def test_13_product_price_calculations(self):
        """Test product price calculations for Producteca sync"""
        product = self.env['product.product'].create({
            'name': 'Price Test Product',
            'type': 'product',
            'list_price': 200.0,
            'standard_price': 120.0,
            'is_producteca_product': True,
        })
        
        # Test price fields
        self.assertEqual(product.list_price, 200.0)
        self.assertEqual(product.standard_price, 120.0)
        
        # Test price calculations (margin, etc.)
        margin = product.list_price - product.standard_price
        self.assertEqual(margin, 80.0)
        
        # Create connection for price sync
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': product.id,
            'producteca_id': 'PRICE_PROD_001',
        })
        
        self.assertEqual(len(product.producteca_connection_ids), 1)

    def test_14_product_description_handling(self):
        """Test product description handling for Producteca"""
        product = self.env['product.product'].create({
            'name': 'Description Test Product',
            'type': 'product',
            'description': 'Short description',
            'description_sale': 'Detailed sales description',
            'is_producteca_product': True,
        })
        
        # Test description fields
        self.assertEqual(product.description, 'Short description')
        self.assertEqual(product.description_sale, 'Detailed sales description')
        
        # Create connection for description sync
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': product.id,
            'producteca_id': 'DESC_PROD_001',
        })
        
        self.assertEqual(len(product.producteca_connection_ids), 1)

    def test_15_product_category_integration(self):
        """Test product category integration for Producteca"""
        # Create category
        category = self.env['product.category'].create({
            'name': 'Test Category',
        })
        
        product = self.env['product.product'].create({
            'name': 'Category Test Product',
            'type': 'product',
            'categ_id': category.id,
            'is_producteca_product': True,
        })
        
        # Test category relationship
        self.assertEqual(product.categ_id.id, category.id)
        self.assertEqual(product.categ_id.name, 'Test Category')
        
        # Create connection for category sync
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': product.id,
            'producteca_id': 'CAT_PROD_001',
        })
        
        self.assertEqual(len(product.producteca_connection_ids), 1)

    def test_16_product_image_handling(self):
        """Test product image handling for Producteca"""
        # Create a simple base64 image string for testing
        test_image = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=='
        
        product = self.env['product.product'].create({
            'name': 'Image Test Product',
            'type': 'product',
            'image_1920': test_image,
            'is_producteca_product': True,
        })
        
        # Test image field
        self.assertEqual(product.image_1920, test_image)
        
        # Create connection for image sync
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': product.id,
            'producteca_id': 'IMAGE_PROD_001',
        })
        
        self.assertEqual(len(product.producteca_connection_ids), 1)

    def test_17_product_variant_attributes(self):
        """Test product variant attributes for Producteca"""
        # Create size attribute
        size_attribute = self.env['product.attribute'].create({
            'name': 'Size',
            'sequence': 1,
        })
        
        medium_value = self.env['product.attribute.value'].create({
            'name': 'Medium',
            'attribute_id': size_attribute.id,
        })
        
        large_value = self.env['product.attribute.value'].create({
            'name': 'Large',
            'attribute_id': size_attribute.id,
        })
        
        # Create template with attributes
        template = self.env['product.template'].create({
            'name': 'Variant Attribute Test',
            'type': 'product',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': size_attribute.id,
                'value_ids': [(6, 0, [medium_value.id, large_value.id])],
            })],
        })
        
        # Get variants
        variants = template.product_variant_ids
        self.assertEqual(len(variants), 2)
        
        # Mark variants as Producteca products
        for variant in variants:
            variant.write({'is_producteca_product': True})
        
        # Create connections for each variant
        for i, variant in enumerate(variants):
            connection = self.env['producteca.product.connections'].create({
                'producteca_account_id': self.producteca_account.id,
                'product_id': variant.id,
                'producteca_id': f'VAR_PROD_{i:03d}',
                'producteca_variation_id': f'VAR_VAR_{i:03d}',
            })
            
            self.assertEqual(len(variant.producteca_connection_ids), 1)

    def test_18_product_uom_integration(self):
        """Test product UoM integration for Producteca"""
        # Create custom UoM
        uom_category = self.env['uom.category'].create({
            'name': 'Test Category',
        })
        
        custom_uom = self.env['uom.uom'].create({
            'name': 'Dozen',
            'category_id': uom_category.id,
            'factor': 12.0,
            'uom_type': 'bigger',
        })
        
        product = self.env['product.product'].create({
            'name': 'UoM Test Product',
            'type': 'product',
            'uom_id': custom_uom.id,
            'uom_po_id': custom_uom.id,
            'is_producteca_product': True,
        })
        
        # Test UoM fields
        self.assertEqual(product.uom_id.id, custom_uom.id)
        self.assertEqual(product.uom_po_id.id, custom_uom.id)
        self.assertEqual(product.uom_id.name, 'Dozen')
        
        # Create connection for UoM sync
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': product.id,
            'producteca_id': 'UOM_PROD_001',
        })
        
        self.assertEqual(len(product.producteca_connection_ids), 1)

    def test_19_product_tax_integration(self):
        """Test product tax integration for Producteca"""
        # Create tax
        tax = self.env['account.tax'].create({
            'name': 'Test Tax 21%',
            'amount': 21.0,
            'type_tax_use': 'sale',
        })
        
        product = self.env['product.product'].create({
            'name': 'Tax Test Product',
            'type': 'product',
            'taxes_id': [(6, 0, [tax.id])],
            'is_producteca_product': True,
        })
        
        # Test tax relationship
        self.assertEqual(len(product.taxes_id), 1)
        self.assertEqual(product.taxes_id[0].id, tax.id)
        self.assertEqual(product.taxes_id[0].amount, 21.0)
        
        # Create connection for tax sync
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': product.id,
            'producteca_id': 'TAX_PROD_001',
        })
        
        self.assertEqual(len(product.producteca_connection_ids), 1)

    def test_20_product_supplier_integration(self):
        """Test product supplier integration for Producteca"""
        # Create supplier
        supplier = self.env['res.partner'].create({
            'name': 'Test Supplier',
            'is_company': True,
            'supplier_rank': 1,
        })
        
        product = self.env['product.product'].create({
            'name': 'Supplier Test Product',
            'type': 'product',
            'is_producteca_product': True,
        })
        
        # Create supplier info
        supplier_info = self.env['product.supplierinfo'].create({
            'partner_id': supplier.id,
            'product_tmpl_id': product.product_tmpl_id.id,
            'min_qty': 1,
            'price': 80.0,
        })
        
        # Test supplier relationship
        self.assertEqual(len(product.seller_ids), 1)
        self.assertEqual(product.seller_ids[0].partner_id.id, supplier.id)
        self.assertEqual(product.seller_ids[0].price, 80.0)
        
        # Create connection for supplier sync
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': product.id,
            'producteca_id': 'SUPP_PROD_001',
        })
        
        self.assertEqual(len(product.producteca_connection_ids), 1)

    def test_21_product_active_inactive_handling(self):
        """Test product active/inactive handling for Producteca"""
        product = self.env['product.product'].create({
            'name': 'Active Test Product',
            'type': 'product',
            'active': True,
            'is_producteca_product': True,
        })
        
        # Initially active
        self.assertTrue(product.active)
        
        # Create connection
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': product.id,
            'producteca_id': 'ACTIVE_PROD_001',
        })
        
        # Deactivate product
        product.write({'active': False})
        self.assertFalse(product.active)
        
        # Connection should still exist
        self.assertEqual(len(product.producteca_connection_ids), 1)
        
        # Reactivate product
        product.write({'active': True})
        self.assertTrue(product.active)

    def test_22_product_connection_unique_constraints(self):
        """Test unique constraints for product connections"""
        product = self.env['product.product'].create({
            'name': 'Constraint Test Product',
            'type': 'product',
            'is_producteca_product': True,
        })
        
        # Create first connection
        connection1 = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': product.id,
            'producteca_id': 'CONSTRAINT_PROD_001',
        })
        
        # Try to create duplicate connection (should work if no unique constraint)
        # or raise error if constraint exists
        try:
            connection2 = self.env['producteca.product.connections'].create({
                'producteca_account_id': self.producteca_account.id,
                'product_id': product.id,
                'producteca_id': 'CONSTRAINT_PROD_001',  # Same producteca_id
            })
            # If no error, both connections exist
            self.assertEqual(len(product.producteca_connection_ids), 2)
        except ValidationError:
            # If error, constraint is working
            self.assertEqual(len(product.producteca_connection_ids), 1)

    def test_23_product_mass_operations(self):
        """Test mass operations on Producteca products"""
        products = []
        
        # Create multiple products
        for i in range(5):
            product = self.env['product.product'].create({
                'name': f'Mass Op Product {i}',
                'type': 'product',
                'list_price': 100.0 + (i * 10),
                'is_producteca_product': True,
            })
            products.append(product)
        
        # Create connections for all products
        for i, product in enumerate(products):
            connection = self.env['producteca.product.connections'].create({
                'producteca_account_id': self.producteca_account.id,
                'product_id': product.id,
                'producteca_id': f'MASS_PROD_{i:03d}',
            })
        
        # Test mass search
        all_producteca_products = self.env['product.product'].search([
            ('is_producteca_product', '=', True)
        ])
        
        for product in products:
            self.assertIn(product, all_producteca_products)
        
        # Test mass update (price change)
        product_recordset = self.env['product.product'].browse([p.id for p in products])
        product_recordset.write({'standard_price': 50.0})
        
        for product in products:
            product.refresh()
            self.assertEqual(product.standard_price, 50.0)

    def test_24_product_copy_with_connections(self):
        """Test product copy behavior with connections"""
        original_product = self.env['product.product'].create({
            'name': 'Original Product',
            'type': 'product',
            'list_price': 100.0,
            'is_producteca_product': True,
        })
        
        # Create connection
        original_connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': original_product.id,
            'producteca_id': 'ORIGINAL_PROD_001',
        })
        
        # Copy product
        copied_product = original_product.copy({'name': 'Copied Product'})
        
        # Test copied product
        self.assertEqual(copied_product.name, 'Copied Product')
        self.assertEqual(copied_product.list_price, 100.0)
        self.assertEqual(copied_product.type, 'product')
        
        # Check if connections are copied (depends on copy configuration)
        # This behavior might vary based on field configuration

    def test_25_comprehensive_product_functionality(self):
        """Test comprehensive product functionality and integration"""
        # Create comprehensive test scenario
        
        # 1. Create category and brand
        category = self.env['product.category'].create({
            'name': 'Comprehensive Category',
        })
        
        # 2. Create tax
        tax = self.env['account.tax'].create({
            'name': 'Comprehensive Tax 18%',
            'amount': 18.0,
            'type_tax_use': 'sale',
        })
        
        # 3. Create supplier
        supplier = self.env['res.partner'].create({
            'name': 'Comprehensive Supplier',
            'is_company': True,
            'supplier_rank': 1,
        })
        
        # 4. Create attribute for variants
        material_attribute = self.env['product.attribute'].create({
            'name': 'Material',
            'sequence': 1,
        })
        
        steel_value = self.env['product.attribute.value'].create({
            'name': 'Steel',
            'attribute_id': material_attribute.id,
        })
        
        # 5. Create comprehensive product
        template = self.env['product.template'].create({
            'name': 'Comprehensive Product Template',
            'type': 'product',
            'categ_id': category.id,
            'product_brand_id': self.brand.id,
            'list_price': 299.99,
            'standard_price': 199.99,
            'weight': 5.0,
            'volume': 1.0,
            'barcode': '9876543210987',
            'default_code': 'COMP001',
            'description': 'Comprehensive test product',
            'description_sale': 'Detailed comprehensive product description',
            'taxes_id': [(6, 0, [tax.id])],
            'attribute_line_ids': [(0, 0, {
                'attribute_id': material_attribute.id,
                'value_ids': [(6, 0, [steel_value.id])],
            })],
        })
        
        # 6. Get the product variant
        product = template.product_variant_ids[0]
        
        # 7. Mark as Producteca product
        product.write({'is_producteca_product': True})
        
        # 8. Create supplier info
        supplier_info = self.env['product.supplierinfo'].create({
            'partner_id': supplier.id,
            'product_tmpl_id': template.id,
            'min_qty': 5,
            'price': 180.0,
        })
        
        # 9. Create Producteca connection
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': product.id,
            'producteca_id': 'COMPREHENSIVE_PROD_001',
            'producteca_variation_id': 'COMPREHENSIVE_VAR_001',
        })
        
        # 10. Test all integrations
        
        # Basic product properties
        self.assertEqual(product.name, 'Comprehensive Product Template')
        self.assertEqual(product.type, 'product')
        self.assertEqual(product.list_price, 299.99)
        self.assertEqual(product.standard_price, 199.99)
        self.assertEqual(product.weight, 5.0)
        self.assertEqual(product.volume, 1.0)
        self.assertEqual(product.barcode, '9876543210987')
        self.assertEqual(product.default_code, 'COMP001')
        self.assertTrue(product.is_producteca_product)
        
        # Category and brand
        self.assertEqual(product.categ_id.name, 'Comprehensive Category')
        self.assertEqual(product.product_brand_id.name, 'Test Brand')
        
        # Tax
        self.assertEqual(len(product.taxes_id), 1)
        self.assertEqual(product.taxes_id[0].amount, 18.0)
        
        # Supplier
        self.assertEqual(len(product.seller_ids), 1)
        self.assertEqual(product.seller_ids[0].partner_id.name, 'Comprehensive Supplier')
        self.assertEqual(product.seller_ids[0].price, 180.0)
        
        # Attributes
        self.assertEqual(len(product.product_template_attribute_value_ids), 1)
        attr_value = product.product_template_attribute_value_ids[0]
        self.assertEqual(attr_value.attribute_id.name, 'Material')
        self.assertEqual(attr_value.product_attribute_value_id.name, 'Steel')
        
        # Producteca connection
        self.assertEqual(len(product.producteca_connection_ids), 1)
        self.assertEqual(product.producteca_connection_ids[0].producteca_id, 'COMPREHENSIVE_PROD_001')
        self.assertEqual(product.producteca_connection_ids[0].producteca_variation_id, 'COMPREHENSIVE_VAR_001')
        
        # Template computation
        template._compute_is_producteca_product()
        self.assertTrue(template.is_producteca_product)
        
        # Search functionality
        found_products = self.env['product.product'].search([
            ('is_producteca_product', '=', True),
            ('name', '=', 'Comprehensive Product Template')
        ])
        self.assertEqual(len(found_products), 1)
        self.assertEqual(found_products[0].id, product.id)
        
        # Update operations
        product.write({'list_price': 349.99})
        self.assertEqual(product.list_price, 349.99)
        
        # Connection should still be valid after updates
        self.assertEqual(len(product.producteca_connection_ids), 1)
        self.assertEqual(product.producteca_connection_ids[0].product_id.id, product.id)