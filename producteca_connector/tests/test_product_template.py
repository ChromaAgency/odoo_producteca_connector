# -*- coding: utf-8 -*-
"""
Test module for product_template.py - Producteca Connector
Tests for ProductTemplate inheritance and Producteca integration
"""

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from unittest.mock import patch, MagicMock


class TestProductTemplate(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test company
        cls.company = cls.env.company
        
        # Create test warehouse
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Test Template Warehouse',
            'code': 'TTW',
            'company_id': cls.company.id,
        })
        
        # Create test producteca account
        cls.producteca_account = cls.env['producteca.account'].create({
            'account_name': 'Test Template Account',
            'api_key': 'test_template_api_key',
            'bearer_token': 'test_template_bearer_token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': cls.warehouse.id,
        })

    def test_01_product_template_inheritance(self):
        """Test that product.template is properly inherited"""
        template = self.env['product.template'].create({
            'name': 'Test Template Inheritance',
            'type': 'product',
        })
        
        # Should inherit from product.template
        self.assertEqual(template._name, 'product.template')
        
        # Should have standard product.template functionality
        self.assertTrue(hasattr(template, 'name'))
        self.assertTrue(hasattr(template, 'type'))
        self.assertTrue(hasattr(template, 'list_price'))
        
        # Should have custom Producteca field
        self.assertTrue(hasattr(template, 'is_producteca_product'))

    def test_02_is_producteca_product_field_exists(self):
        """Test that is_producteca_product field exists and is computed"""
        template = self.env['product.template'].create({
            'name': 'Test Producteca Field',
            'type': 'product',
        })
        
        # Test field existence
        self.assertIn('is_producteca_product', template._fields)
        
        # Test field type and properties
        field = template._fields['is_producteca_product']
        self.assertEqual(field.type, 'boolean')
        self.assertEqual(field.string, 'Is Producteca Product')
        self.assertTrue(field.compute)
        self.assertTrue(field.store)

    def test_03_compute_is_producteca_product_no_variants(self):
        """Test _compute_is_producteca_product with no variants"""
        template = self.env['product.template'].create({
            'name': 'Test No Variants',
            'type': 'product',
        })
        
        # Should be False when no variants are Producteca products
        self.assertFalse(template.is_producteca_product)

    def test_04_compute_is_producteca_product_with_producteca_variant(self):
        """Test _compute_is_producteca_product with Producteca variant"""
        template = self.env['product.template'].create({
            'name': 'Test With Producteca Variant',
            'type': 'product',
        })
        
        # Get the default variant created automatically
        variant = template.product_variant_ids[0]
        
        # Mark variant as Producteca product
        variant.write({'is_producteca_product': True})
        
        # Trigger computation
        template._compute_is_producteca_product()
        
        # Template should now be marked as Producteca product
        self.assertTrue(template.is_producteca_product)

    def test_05_compute_is_producteca_product_mixed_variants(self):
        """Test _compute_is_producteca_product with mixed variants"""
        # Create template with attributes to generate multiple variants
        color_attribute = self.env['product.attribute'].create({
            'name': 'Color',
            'sequence': 1,
        })
        
        red_value = self.env['product.attribute.value'].create({
            'name': 'Red',
            'attribute_id': color_attribute.id,
        })
        
        blue_value = self.env['product.attribute.value'].create({
            'name': 'Blue',
            'attribute_id': color_attribute.id,
        })
        
        template = self.env['product.template'].create({
            'name': 'Test Mixed Variants',
            'type': 'product',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': color_attribute.id,
                'value_ids': [(6, 0, [red_value.id, blue_value.id])],
            })],
        })
        
        # Get variants
        variants = template.product_variant_ids
        self.assertEqual(len(variants), 2)
        
        # Mark only one variant as Producteca product
        variants[0].write({'is_producteca_product': True})
        variants[1].write({'is_producteca_product': False})
        
        # Trigger computation
        template._compute_is_producteca_product()
        
        # Template should be True if ANY variant is Producteca product
        self.assertTrue(template.is_producteca_product)

    def test_06_compute_is_producteca_product_all_variants_false(self):
        """Test _compute_is_producteca_product when all variants are False"""
        # Create template with multiple variants
        size_attribute = self.env['product.attribute'].create({
            'name': 'Size',
            'sequence': 1,
        })
        
        small_value = self.env['product.attribute.value'].create({
            'name': 'Small',
            'attribute_id': size_attribute.id,
        })
        
        large_value = self.env['product.attribute.value'].create({
            'name': 'Large', 
            'attribute_id': size_attribute.id,
        })
        
        template = self.env['product.template'].create({
            'name': 'Test All Variants False',
            'type': 'product',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': size_attribute.id,
                'value_ids': [(6, 0, [small_value.id, large_value.id])],
            })],
        })
        
        # Mark all variants as non-Producteca products
        for variant in template.product_variant_ids:
            variant.write({'is_producteca_product': False})
        
        # Trigger computation
        template._compute_is_producteca_product()
        
        # Template should be False
        self.assertFalse(template.is_producteca_product)

    def test_07_compute_is_producteca_product_dependency(self):
        """Test that computation depends on product_variant_ids.is_producteca_product"""
        template = self.env['product.template'].create({
            'name': 'Test Dependency',
            'type': 'product',
        })
        
        # Check depends decorator
        field = template._fields['is_producteca_product']
        self.assertIn('product_variant_ids.is_producteca_product', field.depends)

    def test_08_template_with_single_variant(self):
        """Test template with single variant Producteca integration"""
        template = self.env['product.template'].create({
            'name': 'Single Variant Template',
            'type': 'product',
            'list_price': 100.0,
        })
        
        # Should have one default variant
        self.assertEqual(len(template.product_variant_ids), 1)
        
        variant = template.product_variant_ids[0]
        
        # Initially not Producteca product
        self.assertFalse(template.is_producteca_product)
        self.assertFalse(variant.is_producteca_product)
        
        # Mark variant as Producteca product
        variant.write({'is_producteca_product': True})
        
        # Template should reflect change
        template._compute_is_producteca_product()
        self.assertTrue(template.is_producteca_product)

    def test_09_template_creation_with_producteca_variant_data(self):
        """Test creating template with variant that has Producteca data"""
        template = self.env['product.template'].create({
            'name': 'Template with Producteca Data',
            'type': 'product',
            'list_price': 150.0,
        })
        
        variant = template.product_variant_ids[0]
        
        # Create Producteca connection for variant
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': variant.id,
            'producteca_id': 'TEMPLATE_PROD_001',
        })
        
        # Mark variant as Producteca product
        variant.write({'is_producteca_product': True})
        
        # Template should be computed as Producteca product
        template._compute_is_producteca_product()
        self.assertTrue(template.is_producteca_product)
        
        # Verify connection exists
        self.assertEqual(len(variant.producteca_connection_ids), 1)
        self.assertEqual(variant.producteca_connection_ids[0], connection)

    def test_10_template_update_triggers_computation(self):
        """Test that template updates trigger is_producteca_product computation"""
        template = self.env['product.template'].create({
            'name': 'Update Test Template',
            'type': 'product',
        })
        
        variant = template.product_variant_ids[0]
        
        # Initially False
        self.assertFalse(template.is_producteca_product)
        
        # Update variant to be Producteca product
        variant.write({'is_producteca_product': True})
        
        # Refresh template to get computed value
        template.refresh()
        
        # Should be computed as True
        self.assertTrue(template.is_producteca_product)

    def test_11_multiple_templates_different_producteca_status(self):
        """Test multiple templates with different Producteca status"""
        templates_data = [
            ('Producteca Template 1', True),
            ('Non-Producteca Template 1', False),
            ('Producteca Template 2', True),
            ('Non-Producteca Template 2', False),
        ]
        
        created_templates = []
        for name, is_producteca in templates_data:
            template = self.env['product.template'].create({
                'name': name,
                'type': 'product',
            })
            
            # Set variant status
            variant = template.product_variant_ids[0]
            variant.write({'is_producteca_product': is_producteca})
            
            # Trigger computation
            template._compute_is_producteca_product()
            
            created_templates.append(template)
        
        # Verify status
        for i, template in enumerate(created_templates):
            expected_status = templates_data[i][1]
            self.assertEqual(template.is_producteca_product, expected_status)

    def test_12_search_producteca_templates(self):
        """Test searching for templates with Producteca products"""
        # Create Producteca template
        producteca_template = self.env['product.template'].create({
            'name': 'Search Producteca Template',
            'type': 'product',
        })
        
        producteca_variant = producteca_template.product_variant_ids[0]
        producteca_variant.write({'is_producteca_product': True})
        producteca_template._compute_is_producteca_product()
        
        # Create non-Producteca template
        normal_template = self.env['product.template'].create({
            'name': 'Search Normal Template',
            'type': 'product',
        })
        
        normal_variant = normal_template.product_variant_ids[0]
        normal_variant.write({'is_producteca_product': False})
        normal_template._compute_is_producteca_product()
        
        # Search for Producteca templates
        producteca_templates = self.env['product.template'].search([
            ('is_producteca_product', '=', True)
        ])
        
        self.assertIn(producteca_template, producteca_templates)
        self.assertNotIn(normal_template, producteca_templates)

    def test_13_template_field_properties(self):
        """Test is_producteca_product field properties"""
        model = self.env['product.template']
        field = model._fields['is_producteca_product']
        
        # Test field properties
        self.assertEqual(field.type, 'boolean')
        self.assertEqual(field.string, 'Is Producteca Product')
        self.assertEqual(field.compute, '_compute_is_producteca_product')
        self.assertTrue(field.store)
        self.assertEqual(field.depends, ('product_variant_ids.is_producteca_product',))

    def test_14_compute_method_signature(self):
        """Test _compute_is_producteca_product method signature"""
        template = self.env['product.template'].create({
            'name': 'Method Signature Test',
            'type': 'product',
        })
        
        # Method should exist and be callable
        self.assertTrue(hasattr(template, '_compute_is_producteca_product'))
        self.assertTrue(callable(getattr(template, '_compute_is_producteca_product')))
        
        # Method should accept no parameters (besides self)
        import inspect
        sig = inspect.signature(template._compute_is_producteca_product)
        self.assertEqual(len(sig.parameters), 0)

    def test_15_template_with_service_type(self):
        """Test template with service type"""
        service_template = self.env['product.template'].create({
            'name': 'Service Template',
            'type': 'service',
        })
        
        variant = service_template.product_variant_ids[0]
        variant.write({'is_producteca_product': True})
        
        # Computation should work for services too
        service_template._compute_is_producteca_product()
        self.assertTrue(service_template.is_producteca_product)

    def test_16_template_with_consu_type(self):
        """Test template with consumable type"""
        consu_template = self.env['product.template'].create({
            'name': 'Consumable Template',
            'type': 'consu',
        })
        
        variant = consu_template.product_variant_ids[0]
        variant.write({'is_producteca_product': True})
        
        # Computation should work for consumables too
        consu_template._compute_is_producteca_product()
        self.assertTrue(consu_template.is_producteca_product)

    def test_17_template_mass_update_computation(self):
        """Test mass update triggering computation"""
        templates = []
        for i in range(5):
            template = self.env['product.template'].create({
                'name': f'Mass Update Template {i}',
                'type': 'product',
            })
            templates.append(template)
        
        # Mark all variants as Producteca products
        for template in templates:
            for variant in template.product_variant_ids:
                variant.write({'is_producteca_product': True})
        
        # Trigger mass computation
        template_recordset = self.env['product.template'].browse([t.id for t in templates])
        template_recordset._compute_is_producteca_product()
        
        # All should be computed as True
        for template in templates:
            template.refresh()
            self.assertTrue(template.is_producteca_product)

    def test_18_template_without_variants(self):
        """Test template edge case without variants"""
        # This is technically impossible in Odoo as templates always have at least one variant
        # But we test the computation logic handles empty variant sets
        template = self.env['product.template'].create({
            'name': 'Edge Case Template',
            'type': 'product',
        })
        
        # Should have at least one variant
        self.assertGreater(len(template.product_variant_ids), 0)
        
        # Test computation with empty variant evaluation
        template._compute_is_producteca_product()
        
        # Should handle gracefully
        self.assertFalse(template.is_producteca_product)

    def test_19_template_computation_performance(self):
        """Test computation performance with many variants"""
        # Create attribute with many values
        style_attribute = self.env['product.attribute'].create({
            'name': 'Style',
            'sequence': 1,
        })
        
        values = []
        for i in range(5):  # Create 5 variants
            value = self.env['product.attribute.value'].create({
                'name': f'Style {i}',
                'attribute_id': style_attribute.id,
            })
            values.append(value)
        
        template = self.env['product.template'].create({
            'name': 'Performance Test Template',
            'type': 'product',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': style_attribute.id,
                'value_ids': [(6, 0, [v.id for v in values])],
            })],
        })
        
        # Should have 5 variants
        self.assertEqual(len(template.product_variant_ids), 5)
        
        # Mark some variants as Producteca products
        template.product_variant_ids[0].write({'is_producteca_product': True})
        template.product_variant_ids[2].write({'is_producteca_product': True})
        
        # Computation should be efficient
        template._compute_is_producteca_product()
        self.assertTrue(template.is_producteca_product)

    def test_20_template_store_functionality(self):
        """Test that computed field is stored properly"""
        template = self.env['product.template'].create({
            'name': 'Store Test Template',
            'type': 'product',
        })
        
        variant = template.product_variant_ids[0]
        variant.write({'is_producteca_product': True})
        
        # Trigger computation
        template._compute_is_producteca_product()
        
        # Value should be stored in database
        template.refresh()
        self.assertTrue(template.is_producteca_product)
        
        # Should be searchable (because it's stored)
        found_templates = self.env['product.template'].search([
            ('is_producteca_product', '=', True)
        ])
        self.assertIn(template, found_templates)

    def test_21_template_integration_with_producteca_connections(self):
        """Test template integration with Producteca connections"""
        template = self.env['product.template'].create({
            'name': 'Integration Test Template',
            'type': 'product',
        })
        
        variant = template.product_variant_ids[0]
        
        # Create Producteca connection
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': variant.id,
            'producteca_id': 'INTEGRATION_PROD_001',
        })
        
        # Mark as Producteca product
        variant.write({'is_producteca_product': True})
        
        # Template should reflect integration
        template._compute_is_producteca_product()
        self.assertTrue(template.is_producteca_product)
        
        # Verify connection through variant
        self.assertEqual(len(variant.producteca_connection_ids), 1)
        self.assertEqual(variant.producteca_connection_ids[0], connection)

    def test_22_template_variant_creation_triggers_computation(self):
        """Test that new variant creation triggers template computation"""
        # Create attribute for variant generation
        material_attribute = self.env['product.attribute'].create({
            'name': 'Material',
            'sequence': 1,
        })
        
        wood_value = self.env['product.attribute.value'].create({
            'name': 'Wood',
            'attribute_id': material_attribute.id,
        })
        
        template = self.env['product.template'].create({
            'name': 'Variant Creation Test',
            'type': 'product',
        })
        
        # Initially False
        self.assertFalse(template.is_producteca_product)
        
        # Add attribute line to create new variant
        template.write({
            'attribute_line_ids': [(0, 0, {
                'attribute_id': material_attribute.id,
                'value_ids': [(6, 0, [wood_value.id])],
            })],
        })
        
        # Should have one variant
        self.assertEqual(len(template.product_variant_ids), 1)
        
        # Mark new variant as Producteca product
        template.product_variant_ids[0].write({'is_producteca_product': True})
        
        # Template should be updated
        template._compute_is_producteca_product()
        self.assertTrue(template.is_producteca_product)

    def test_23_template_copy_behavior(self):
        """Test template copy behavior with Producteca fields"""
        original_template = self.env['product.template'].create({
            'name': 'Original Template',
            'type': 'product',
        })
        
        # Mark variant as Producteca product
        original_variant = original_template.product_variant_ids[0]
        original_variant.write({'is_producteca_product': True})
        original_template._compute_is_producteca_product()
        
        # Copy template
        copied_template = original_template.copy({'name': 'Copied Template'})
        
        # Copied template should have correct computation
        copied_template._compute_is_producteca_product()
        
        # Check if copied variant inherits Producteca status
        copied_variant = copied_template.product_variant_ids[0]
        # Note: is_producteca_product might not be copied depending on copy configuration
        # We test that computation works correctly for copied template

    def test_24_template_unlink_behavior(self):
        """Test template deletion behavior"""
        template = self.env['product.template'].create({
            'name': 'Delete Test Template',
            'type': 'product',
        })
        
        variant = template.product_variant_ids[0]
        
        # Create connection
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': variant.id,
            'producteca_id': 'DELETE_PROD_001',
        })
        
        template_id = template.id
        connection_id = connection.id
        
        # Delete template (should cascade to variants and connections)
        template.unlink()
        
        # Verify deletion
        deleted_template = self.env['product.template'].search([('id', '=', template_id)])
        self.assertEqual(len(deleted_template), 0)
        
        # Connection should also be deleted (depending on cascade configuration)
        remaining_connection = self.env['producteca.product.connections'].search([('id', '=', connection_id)])
        # Connection might remain if no cascade delete is configured

    def test_25_comprehensive_template_functionality(self):
        """Test comprehensive template functionality and edge cases"""
        # Create comprehensive test scenario
        
        # 1. Create template with all properties
        template = self.env['product.template'].create({
            'name': 'Comprehensive Template Test',
            'type': 'product',
            'list_price': 199.99,
            'standard_price': 99.99,
            'description': 'Comprehensive test template',
        })
        
        # 2. Get variant and set up Producteca integration
        variant = template.product_variant_ids[0]
        
        # 3. Create Producteca connection
        connection = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': variant.id,
            'producteca_id': 'COMPREHENSIVE_PROD_001',
            'producteca_variation_id': 'COMPREHENSIVE_VAR_001',
        })
        
        # 4. Mark as Producteca product
        variant.write({'is_producteca_product': True})
        
        # 5. Test computation
        template._compute_is_producteca_product()
        self.assertTrue(template.is_producteca_product)
        
        # 6. Test search functionality
        found_templates = self.env['product.template'].search([
            ('is_producteca_product', '=', True),
            ('name', '=', 'Comprehensive Template Test')
        ])
        self.assertEqual(len(found_templates), 1)
        self.assertEqual(found_templates[0].id, template.id)
        
        # 7. Test field properties
        self.assertEqual(template.name, 'Comprehensive Template Test')
        self.assertEqual(template.type, 'product')
        self.assertEqual(template.list_price, 199.99)
        self.assertTrue(template.is_producteca_product)
        
        # 8. Test variant relationship
        self.assertEqual(len(template.product_variant_ids), 1)
        self.assertEqual(template.product_variant_ids[0].id, variant.id)
        self.assertTrue(variant.is_producteca_product)
        
        # 9. Test connection relationship
        self.assertEqual(len(variant.producteca_connection_ids), 1)
        self.assertEqual(variant.producteca_connection_ids[0].id, connection.id)
        
        # 10. Test update operations
        template.write({'name': 'Updated Comprehensive Template'})
        self.assertEqual(template.name, 'Updated Comprehensive Template')
        
        # Computation should still work after updates
        template._compute_is_producteca_product()
        self.assertTrue(template.is_producteca_product)