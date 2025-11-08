# -*- coding: utf-8 -*-
"""
Test module for stock_picking.py - Producteca Connector
Tests for StockPicking inheritance and Producteca integration
"""

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from unittest.mock import patch, MagicMock
import json
from datetime import datetime


class TestStockPicking(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test company
        cls.company = cls.env.company
        
        # Create test warehouse
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Test Stock Warehouse',
            'code': 'TSKW',
            'company_id': cls.company.id,
            'producteca_warehouse_name': 'TestWarehouse',
        })
        
        # Create test producteca account
        cls.producteca_account = cls.env['producteca.account'].create({
            'account_name': 'Test Stock Account',
            'api_key': 'test_stock_api_key',
            'bearer_token': 'test_stock_bearer_token',
            'imported_sale_action': 'quotation',
            'default_warehouse_id': cls.warehouse.id,
            'warehouse_ids': [(4, cls.warehouse.id)],
        })
        
        # Create test partner
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Stock Customer',
            'email': 'stock@customer.com',
        })
        
        # Create test product
        cls.product = cls.env['product.product'].create({
            'name': 'Test Stock Product',
            'type': 'product',
            'list_price': 100.0,
            'standard_price': 60.0,
        })
        
        # Create product connection
        cls.connection = cls.env['producteca.product.connections'].create({
            'producteca_account_id': cls.producteca_account.id,
            'product_id': cls.product.id,
            'producteca_id': 'STOCK_PROD_001',
            'producteca_variation_id': 'STOCK_VAR_001',
        })
        
        # Create test sale order
        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'producteca_id': 'STOCK_ORDER_001',
            'producteca_account_id': cls.producteca_account.id,
            'order_line': [(0, 0, {
                'product_id': cls.product.id,
                'product_uom_qty': 2,
                'price_unit': 100.0,
            })],
        })

    def test_01_stock_picking_inheritance(self):
        """Test that stock.picking is properly inherited"""
        picking = self.env['stock.picking'].create({
            'partner_id': self.partner.id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
        
        # Should inherit from stock.picking
        self.assertEqual(picking._name, 'stock.picking')
        
        # Should have standard stock.picking functionality
        self.assertTrue(hasattr(picking, 'name'))
        self.assertTrue(hasattr(picking, 'partner_id'))
        self.assertTrue(hasattr(picking, 'state'))
        
        # Should have custom Producteca fields
        self.assertTrue(hasattr(picking, 'producteca_shipment_id'))
        self.assertTrue(hasattr(picking, 'producteca_account_id'))

    def test_02_producteca_fields_properties(self):
        """Test Producteca-specific field properties"""
        picking = self.env['stock.picking'].create({
            'partner_id': self.partner.id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
        
        # Test field existence and types
        fields = picking._fields
        
        self.assertIn('producteca_shipment_id', fields)
        self.assertEqual(fields['producteca_shipment_id'].type, 'char')
        self.assertEqual(fields['producteca_shipment_id'].string, 'Producteca Shipment ID')
        
        self.assertIn('producteca_account_id', fields)
        self.assertEqual(fields['producteca_account_id'].type, 'many2one')
        self.assertEqual(fields['producteca_account_id'].comodel_name, 'producteca.account')

    def test_03_create_picking_with_producteca_data(self):
        """Test creating picking with Producteca data"""
        picking = self.env['stock.picking'].create({
            'partner_id': self.partner.id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'producteca_shipment_id': 'SHIP_001',
            'producteca_account_id': self.producteca_account.id,
        })
        
        # Test Producteca fields
        self.assertEqual(picking.producteca_shipment_id, 'SHIP_001')
        self.assertEqual(picking.producteca_account_id.id, self.producteca_account.id)

    def test_04_obtain_carrier_id_existing_carrier(self):
        """Test _obtain_carrier_id with existing carrier"""
        # Create existing carrier
        existing_carrier = self.env['delivery.carrier'].create({
            'name': 'Existing Carrier',
            'product_id': self.env['product.product'].create({
                'name': 'Existing Delivery Service',
                'type': 'service',
            }).id,
        })
        
        picking = self.env['stock.picking'].create({
            'partner_id': self.partner.id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
        
        result = picking._obtain_carrier_id('Existing Carrier')
        
        self.assertEqual(result, existing_carrier.id)

    def test_05_obtain_carrier_id_new_carrier(self):
        """Test _obtain_carrier_id creating new carrier"""
        picking = self.env['stock.picking'].create({
            'partner_id': self.partner.id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
        
        result = picking._obtain_carrier_id('New DHL Carrier')
        
        # Should create new carrier
        new_carrier = self.env['delivery.carrier'].browse(result)
        self.assertEqual(new_carrier.name, 'New DHL Carrier')
        
        # Should create delivery product
        delivery_product = new_carrier.product_id
        self.assertEqual(delivery_product.name, 'Servicio de Entrega: New DHL Carrier')
        self.assertEqual(delivery_product.type, 'service')
        self.assertEqual(delivery_product.invoice_policy, 'order')

    def test_06_process_picking_with_shipment_done_status(self):
        """Test _process_picking_with_shipment with Done status"""
        # Create picking with move lines
        picking = self.env['stock.picking'].create({
            'partner_id': self.partner.id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'producteca_account_id': self.producteca_account.id,
            'sale_id': self.sale_order.id,
        })
        
        # Add move line
        move_line = self.env['stock.move.line'].create({
            'picking_id': picking.id,
            'product_id': self.product.id,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
            'quantity': 2.0,
        })
        
        # Mock shipment data
        picking_data = {
            'products': [{'product': 'STOCK_PROD_001', 'quantity': 2}],
            'method': {'status': 'Done', 'trackingNumber': 'TRACK123', 'courier': 'FedEx'},
            'date': '2023-10-15T10:30:00.000Z',
            'integration': {'integrationId': 'INTEGRATION_001'},
        }
        
        # Process picking
        picking._process_picking_with_shipment(picking_data)
        
        # Should set qty_done
        self.assertEqual(move_line.qty_done, 2)
        
        # Should set dates
        self.assertIsNotNone(picking.date_done)
        self.assertIsNotNone(picking.scheduled_date)
        
        # Should set shipment ID and carrier
        self.assertEqual(picking.producteca_shipment_id, 'INTEGRATION_001')
        self.assertIsNotNone(picking.carrier_id)
        self.assertEqual(picking.carrier_id.name, 'FedEx')

    def test_07_process_picking_with_shipment_pending_status(self):
        """Test _process_picking_with_shipment with pending status"""
        # Create picking with move lines
        picking = self.env['stock.picking'].create({
            'partner_id': self.partner.id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'producteca_account_id': self.producteca_account.id,
            'sale_id': self.sale_order.id,
        })
        
        # Add move line
        move_line = self.env['stock.move.line'].create({
            'picking_id': picking.id,
            'product_id': self.product.id,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
            'quantity': 1.0,
        })
        
        # Mock shipment data
        picking_data = {
            'products': [{'product': 'STOCK_PROD_001', 'quantity': 1}],
            'method': {'status': 'Pending', 'trackingNumber': 'TRACK456', 'courier': 'UPS'},
            'date': '2023-10-16T14:45:00.000Z',
        }
        
        # Process picking
        picking._process_picking_with_shipment(picking_data)
        
        # Should set quantity but not qty_done
        self.assertEqual(move_line.quantity, 1)
        self.assertEqual(move_line.qty_done, 0)  # Default value
        
        # Should set scheduled date and tracking
        self.assertIsNotNone(picking.scheduled_date)
        self.assertEqual(picking.carrier_tracking_ref, 'TRACK456')
        self.assertEqual(picking.carrier_id.name, 'UPS')

    def test_08_process_picking_with_shipment_date_parsing(self):
        """Test _process_picking_with_shipment date parsing"""
        picking = self.env['stock.picking'].create({
            'partner_id': self.partner.id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'producteca_account_id': self.producteca_account.id,
            'sale_id': self.sale_order.id,
        })
        
        # Test with date
        picking_data_with_date = {
            'products': [],
            'method': {'status': 'Pending', 'courier': 'TestCarrier'},
            'date': '2023-10-15T10:30:45.123Z',
        }
        
        picking._process_picking_with_shipment(picking_data_with_date)
        self.assertIsNotNone(picking.scheduled_date)
        
        # Test without date
        picking_data_no_date = {
            'products': [],
            'method': {'status': 'Pending', 'courier': 'TestCarrier2'},
            'date': None,
        }
        
        picking._process_picking_with_shipment(picking_data_no_date)
        self.assertIsNotNone(picking.scheduled_date)  # Should set current time

    def test_09_create_producteca_dict_for_picking_done_state(self):
        """Test _create_producteca_dict_for_picking with done state"""
        # Create and confirm picking
        picking = self.env['stock.picking'].create({
            'partner_id': self.partner.id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'producteca_account_id': self.producteca_account.id,
            'sale_id': self.sale_order.id,
            'carrier_tracking_ref': 'TRACK789',
            'state': 'done',
            'date_done': datetime.now(),
        })
        
        # Add carrier
        carrier = self.env['delivery.carrier'].create({
            'name': 'Test Carrier Dict',
            'product_id': self.env['product.product'].create({
                'name': 'Test Carrier Product',
                'type': 'service',
            }).id,
        })
        picking.carrier_id = carrier.id
        
        # Add move line
        move_line = self.env['stock.move.line'].create({
            'picking_id': picking.id,
            'product_id': self.product.id,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
            'qty_done': 3.0,
        })
        
        result = picking._create_producteca_dict_for_picking()
        
        # Test result structure
        self.assertIn('date', result)
        self.assertIn('method', result)
        self.assertIn('products', result)
        
        # Test method data
        method = result['method']
        self.assertEqual(method['trackingNumber'], 'TRACK789')
        self.assertEqual(method['courier'], 'Test Carrier Dict')
        self.assertEqual(method['status'], 'Done')
        
        # Test products data
        products = result['products']
        self.assertEqual(len(products), 1)
        product_data = products[0]
        self.assertEqual(product_data['product'], 'STOCK_PROD_001')
        self.assertEqual(product_data['variation'], 'STOCK_VAR_001')
        self.assertEqual(product_data['quantity'], 3.0)

    def test_10_create_producteca_dict_for_picking_pending_state(self):
        """Test _create_producteca_dict_for_picking with pending state"""
        picking = self.env['stock.picking'].create({
            'partner_id': self.partner.id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'producteca_account_id': self.producteca_account.id,
            'sale_id': self.sale_order.id,
            'carrier_tracking_ref': 'PENDING_TRACK',
            'state': 'assigned',
            'scheduled_date': datetime.now(),
        })
        
        # Add move line
        move_line = self.env['stock.move.line'].create({
            'picking_id': picking.id,
            'product_id': self.product.id,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
            'quantity': 2.0,
        })
        
        result = picking._create_producteca_dict_for_picking()
        
        # Test method status for non-done state
        method = result['method']
        self.assertEqual(method['status'], 'PickingPending')
        self.assertEqual(method['trackingNumber'], 'PENDING_TRACK')
        
        # Test quantity from quantity field (not qty_done)
        products = result['products']
        product_data = products[0]
        self.assertEqual(product_data['quantity'], 2.0)

    def test_11_create_producteca_dict_for_picking_no_carrier(self):
        """Test _create_producteca_dict_for_picking without carrier"""
        picking = self.env['stock.picking'].create({
            'partner_id': self.partner.id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'producteca_account_id': self.producteca_account.id,
            'sale_id': self.sale_order.id,
        })
        
        result = picking._create_producteca_dict_for_picking()
        
        # Should handle missing carrier
        method = result['method']
        self.assertEqual(method['courier'], 'Unknown')
        self.assertEqual(method['trackingNumber'], '')

    @patch('odoo.addons.producteca_connector.models.stock_picking.StockPicking.env')
    def test_12_update_producteca_shipment(self, mock_env):
        """Test _update_producteca_shipment method"""
        # Mock client
        mock_client = MagicMock()
        mock_sales_order = MagicMock()
        mock_client.SalesOrder.return_value = mock_sales_order
        self.producteca_account.get_client = MagicMock(return_value=mock_client)
        
        picking = self.env['stock.picking'].create({
            'partner_id': self.partner.id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'producteca_account_id': self.producteca_account.id,
            'producteca_shipment_id': 'SHIPMENT_001',
            'sale_id': self.sale_order.id,
        })
        
        producteca_body = {'id': 'SHIPMENT_001', 'status': 'updated'}
        
        result = picking._update_producteca_shipment(producteca_body)
        
        # Should call API
        mock_client.SalesOrder.assert_called_once_with(id='STOCK_ORDER_001')
        mock_sales_order.update_shipment.assert_called_once_with('SHIPMENT_001', producteca_body)

    def test_13_update_producteca_shipment_no_shipment_id(self):
        """Test _update_producteca_shipment without shipment ID"""
        picking = self.env['stock.picking'].create({
            'partner_id': self.partner.id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'producteca_account_id': self.producteca_account.id,
            'sale_id': self.sale_order.id,
        })
        
        result = picking._update_producteca_shipment({'test': 'data'})
        
        # Should return None if no shipment ID
        self.assertIsNone(result)

    def test_14_update_producteca_shipment_no_body(self):
        """Test _update_producteca_shipment without body"""
        picking = self.env['stock.picking'].create({
            'partner_id': self.partner.id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'producteca_account_id': self.producteca_account.id,
            'producteca_shipment_id': 'SHIPMENT_002',
            'sale_id': self.sale_order.id,
        })
        
        result = picking._update_producteca_shipment(None)
        
        # Should return None if no body
        self.assertIsNone(result)

    @patch('odoo.addons.producteca_connector.models.stock_picking.StockPicking.env')
    def test_15_create_producteca_shipment(self, mock_env):
        """Test _create_producteca_shipment method"""
        # Mock client
        mock_client = MagicMock()
        mock_sales_order = MagicMock()
        mock_client.SalesOrder.return_value = mock_sales_order
        self.producteca_account.get_client = MagicMock(return_value=mock_client)
        
        picking = self.env['stock.picking'].create({
            'partner_id': self.partner.id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'producteca_account_id': self.producteca_account.id,
            'sale_id': self.sale_order.id,
        })
        
        # Mock _create_producteca_dict_for_picking
        with patch.object(picking, '_create_producteca_dict_for_picking') as mock_dict:
            mock_dict.return_value = {'test': 'shipment_data'}
            
            result = picking._create_producteca_shipment()
            
            # Should call API with created dict
            mock_client.SalesOrder.assert_called_once_with(id='STOCK_ORDER_001')
            mock_sales_order.add_shipment.assert_called_once_with({'test': 'shipment_data'})

    def test_16_write_method_tracking_update(self):
        """Test write method updating tracking info"""
        # Mock delayed update
        with patch.object(self.env['stock.picking'], 'with_delay') as mock_delay:
            mock_delayed = MagicMock()
            mock_delay.return_value = mock_delayed
            
            picking = self.env['stock.picking'].create({
                'partner_id': self.partner.id,
                'picking_type_id': self.warehouse.out_type_id.id,
                'location_id': self.warehouse.lot_stock_id.id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                'producteca_account_id': self.producteca_account.id,
                'producteca_shipment_id': 'WRITE_SHIPMENT_001',
            })
            
            # Update tracking reference
            picking.write({'carrier_tracking_ref': 'NEW_TRACK_123'})
            
            # Should call delayed update
            mock_delayed._update_producteca_shipment.assert_called_once()

    def test_17_write_method_state_update(self):
        """Test write method updating state"""
        with patch.object(self.env['stock.picking'], 'with_delay') as mock_delay:
            mock_delayed = MagicMock()
            mock_delay.return_value = mock_delayed
            
            picking = self.env['stock.picking'].create({
                'partner_id': self.partner.id,
                'picking_type_id': self.warehouse.out_type_id.id,
                'location_id': self.warehouse.lot_stock_id.id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                'producteca_account_id': self.producteca_account.id,
                'producteca_shipment_id': 'WRITE_SHIPMENT_002',
            })
            
            # Update state
            picking.write({'state': 'done'})
            
            # Should call delayed update
            mock_delayed._update_producteca_shipment.assert_called_once()

    def test_18_write_method_no_shipment_id(self):
        """Test write method without shipment ID"""
        with patch.object(self.env['stock.picking'], 'with_delay') as mock_delay:
            picking = self.env['stock.picking'].create({
                'partner_id': self.partner.id,
                'picking_type_id': self.warehouse.out_type_id.id,
                'location_id': self.warehouse.lot_stock_id.id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                'producteca_account_id': self.producteca_account.id,
                # No producteca_shipment_id
            })
            
            # Update tracking reference
            picking.write({'carrier_tracking_ref': 'SHOULD_NOT_SYNC'})
            
            # Should not call delayed update
            mock_delay.assert_not_called()

    def test_19_write_method_context_check(self):
        """Test write method with update_from_confirm context"""
        with patch.object(self.env['stock.picking'], 'with_delay') as mock_delay:
            picking = self.env['stock.picking'].create({
                'partner_id': self.partner.id,
                'picking_type_id': self.warehouse.out_type_id.id,
                'location_id': self.warehouse.lot_stock_id.id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                'producteca_account_id': self.producteca_account.id,
                'producteca_shipment_id': 'CONTEXT_SHIPMENT_001',
            })
            
            # Update with context to skip sync
            picking.with_context(update_from_confirm=True).write({
                'carrier_tracking_ref': 'CONTEXT_TRACK_123'
            })
            
            # Should not call delayed update due to context
            mock_delay.assert_not_called()

    def test_20_button_validate_with_producteca_shipment(self):
        """Test button_validate with Producteca shipment"""
        with patch.object(self.env['stock.picking'], 'with_delay') as mock_delay:
            mock_delayed = MagicMock()
            mock_delay.return_value = mock_delayed
            
            # Create picking with proper setup for validation
            picking = self.env['stock.picking'].create({
                'partner_id': self.partner.id,
                'picking_type_id': self.warehouse.out_type_id.id,
                'location_id': self.warehouse.lot_stock_id.id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                'producteca_account_id': self.producteca_account.id,
                'producteca_shipment_id': 'VALIDATE_SHIPMENT_001',
                'sale_id': self.sale_order.id,
            })
            
            # Add stock move
            move = self.env['stock.move'].create({
                'name': 'Test Move',
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'product_uom': self.product.uom_id.id,
                'picking_id': picking.id,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
            })
            
            # Confirm picking to make it ready for validation
            picking.action_confirm()
            picking.action_assign()
            
            # Set qty_done
            for move_line in picking.move_line_ids:
                move_line.qty_done = move_line.quantity
            
            # Mock parent button_validate to simulate done state
            with patch('odoo.addons.stock.models.stock_picking.StockPicking.button_validate') as mock_parent:
                mock_parent.return_value = True
                
                # Simulate done state after validation
                picking.state = 'done'
                
                result = picking.button_validate()
                
                # Should call decrease stock method
                mock_delayed._send_decreasestock_to_producteca.assert_called_once()

    def test_21_button_validate_without_producteca_shipment(self):
        """Test button_validate without Producteca shipment"""
        with patch.object(self.env['stock.picking'], 'with_delay') as mock_delay:
            picking = self.env['stock.picking'].create({
                'partner_id': self.partner.id,
                'picking_type_id': self.warehouse.out_type_id.id,
                'location_id': self.warehouse.lot_stock_id.id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                # No producteca_shipment_id
            })
            
            # Mock parent validation
            with patch('odoo.addons.stock.models.stock_picking.StockPicking.button_validate') as mock_parent:
                mock_parent.return_value = True
                
                result = picking.button_validate()
                
                # Should not call decrease stock
                mock_delay.assert_not_called()

    @patch('odoo.addons.producteca_connector.models.stock_picking.StockPicking.env')
    def test_22_send_decreasestock_to_producteca(self, mock_env):
        """Test _send_decreasestock_to_producteca method"""
        # Mock client
        mock_client = MagicMock()
        mock_sales_order = MagicMock()
        mock_client.SalesOrder.return_value = mock_sales_order
        self.producteca_account.get_client = MagicMock(return_value=mock_client)
        
        picking = self.env['stock.picking'].create({
            'partner_id': self.partner.id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'producteca_account_id': self.producteca_account.id,
            'sale_id': self.sale_order.id,
            'name': 'PICK/00001',
        })
        
        # Mock producteca_order_id on sale order
        self.sale_order.producteca_order_id = 'ORDER_123'
        
        picking._send_decreasestock_to_producteca()
        
        # Should call API with correct data
        expected_body = {
            "id": 123,  # int conversion of ORDER_123
            "invoiceIntegration": {
                "documentUrl": "",
                "integrationId": "PICK/00001",
                "decreaseStock": True
            }
        }
        
        mock_client.SalesOrder.assert_called_once_with(**expected_body)
        mock_sales_order.invoice_integration.assert_called_once()

    def test_23_producteca_fields_constant(self):
        """Test PRODUCTECA_FIELDS constant"""
        from odoo.addons.producteca_connector.models.stock_picking import PRODUCTECA_FIELDS
        
        expected_fields = [
            "date_done",
            "scheduled_date", 
            "carrier_tracking_ref",
            "state",
            "carrier_id",
        ]
        
        self.assertEqual(PRODUCTECA_FIELDS, expected_fields)

    def test_24_picking_with_multiple_move_lines(self):
        """Test picking with multiple move lines"""
        picking = self.env['stock.picking'].create({
            'partner_id': self.partner.id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'producteca_account_id': self.producteca_account.id,
            'sale_id': self.sale_order.id,
        })
        
        # Create second product and connection
        product2 = self.env['product.product'].create({
            'name': 'Test Stock Product 2',
            'type': 'product',
        })
        
        connection2 = self.env['producteca.product.connections'].create({
            'producteca_account_id': self.producteca_account.id,
            'product_id': product2.id,
            'producteca_id': 'STOCK_PROD_002',
            'producteca_variation_id': 'STOCK_VAR_002',
        })
        
        # Add multiple move lines
        move_line1 = self.env['stock.move.line'].create({
            'picking_id': picking.id,
            'product_id': self.product.id,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
            'qty_done': 2.0,
        })
        
        move_line2 = self.env['stock.move.line'].create({
            'picking_id': picking.id,
            'product_id': product2.id,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
            'qty_done': 3.0,
        })
        
        result = picking._create_producteca_dict_for_picking()
        
        # Should include both products
        products = result['products']
        self.assertEqual(len(products), 2)
        
        product_ids = [p['product'] for p in products]
        self.assertIn('STOCK_PROD_001', product_ids)
        self.assertIn('STOCK_PROD_002', product_ids)

    def test_25_comprehensive_picking_functionality(self):
        """Test comprehensive picking functionality"""
        # Create comprehensive test scenario
        
        # 1. Create picking with full Producteca data
        picking = self.env['stock.picking'].create({
            'partner_id': self.partner.id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'producteca_account_id': self.producteca_account.id,
            'producteca_shipment_id': 'COMPREHENSIVE_SHIP_001',
            'sale_id': self.sale_order.id,
            'carrier_tracking_ref': 'COMP_TRACK_123',
        })
        
        # 2. Create carrier
        carrier = self.env['delivery.carrier'].create({
            'name': 'Comprehensive Carrier',
            'product_id': self.env['product.product'].create({
                'name': 'Comprehensive Delivery Service',
                'type': 'service',
            }).id,
        })
        picking.carrier_id = carrier.id
        
        # 3. Add move lines with different products
        move_line1 = self.env['stock.move.line'].create({
            'picking_id': picking.id,
            'product_id': self.product.id,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
            'quantity': 5.0,
            'qty_done': 5.0,
        })
        
        # 4. Test comprehensive shipment data processing
        comprehensive_shipment_data = {
            'products': [
                {'product': 'STOCK_PROD_001', 'quantity': 5}
            ],
            'method': {
                'status': 'Done',
                'trackingNumber': 'COMP_TRACK_UPDATED',
                'courier': 'Updated Comprehensive Carrier',
            },
            'date': '2023-10-15T16:30:45.123Z',
            'integration': {
                'integrationId': 'COMP_INTEGRATION_001'
            }
        }
        
        # Process comprehensive shipment
        picking._process_picking_with_shipment(comprehensive_shipment_data)
        
        # 5. Test all results
        
        # Basic picking properties
        self.assertEqual(picking.producteca_shipment_id, 'COMP_INTEGRATION_001')
        self.assertEqual(picking.producteca_account_id.id, self.producteca_account.id)
        self.assertEqual(picking.sale_id.id, self.sale_order.id)
        
        # Carrier and tracking
        self.assertEqual(picking.carrier_id.name, 'Updated Comprehensive Carrier')
        self.assertIsNotNone(picking.date_done)
        self.assertIsNotNone(picking.scheduled_date)
        
        # Move line quantities
        self.assertEqual(move_line1.qty_done, 5.0)
        
        # 6. Test dict creation
        result_dict = picking._create_producteca_dict_for_picking()
        
        # Dict structure validation
        self.assertIn('date', result_dict)
        self.assertIn('method', result_dict)
        self.assertIn('products', result_dict)
        
        # Method data validation
        method = result_dict['method']
        self.assertEqual(method['courier'], 'Updated Comprehensive Carrier')
        self.assertEqual(method['status'], 'Done')  # Should be Done since state would be done
        
        # Products data validation
        products = result_dict['products']
        self.assertEqual(len(products), 1)
        product_data = products[0]
        self.assertEqual(product_data['product'], 'STOCK_PROD_001')
        self.assertEqual(product_data['variation'], 'STOCK_VAR_001')
        self.assertEqual(product_data['quantity'], 5.0)
        
        # 7. Test update operations
        with patch.object(self.env['stock.picking'], 'with_delay') as mock_delay:
            mock_delayed = MagicMock()
            mock_delay.return_value = mock_delayed
            
            # Update tracking
            picking.write({'carrier_tracking_ref': 'FINAL_TRACK_999'})
            
            # Should sync update
            mock_delayed._update_producteca_shipment.assert_called_once()
        
        # 8. Test validation workflow
        with patch.object(self.env['stock.picking'], 'with_delay') as mock_delay:
            mock_delayed = MagicMock()
            mock_delay.return_value = mock_delayed
            
            # Mock parent validation and set done state
            with patch('odoo.addons.stock.models.stock_picking.StockPicking.button_validate') as mock_parent:
                mock_parent.return_value = True
                picking.state = 'done'
                
                # Mock producteca_order_id for decrease stock
                self.sale_order.producteca_order_id = 'ORDER_999'
                
                result = picking.button_validate()
                
                # Should call decrease stock
                mock_delayed._send_decreasestock_to_producteca.assert_called_once()
        
        # 9. Test search and filtering
        found_pickings = self.env['stock.picking'].search([
            ('producteca_shipment_id', '=', 'COMP_INTEGRATION_001')
        ])
        self.assertEqual(len(found_pickings), 1)
        self.assertEqual(found_pickings[0].id, picking.id)
        
        # 10. Final validation
        self.assertTrue(picking.exists())
        self.assertEqual(picking.producteca_shipment_id, 'COMP_INTEGRATION_001')
        self.assertEqual(picking.carrier_tracking_ref, 'FINAL_TRACK_999')
        self.assertEqual(len(picking.move_line_ids), 1)
        self.assertEqual(picking.move_line_ids[0].qty_done, 5.0)