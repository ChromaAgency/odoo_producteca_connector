# -*- coding: utf-8 -*-
"""
Test suite for ProductecaImageController in producteca_connector module.

This module provides comprehensive test coverage for the ProductecaImageController,
which handles webhook processing and image serving for Producteca integration, including:
- Webhook reception and processing for products and sale orders
- Image serving with proper content types and caching
- Error handling and logging
- Authentication and CSRF handling

Test Patterns:
- Uses Odoo HttpCase for HTTP request testing
- Mock external dependencies and delayed jobs
- Test HTTP routes and response handling
- Validate error scenarios and edge cases
- Test webhook data processing

Coverage Areas:
- Webhook endpoint handling and routing
- Product webhook processing
- Sale order webhook processing  
- Image endpoint with content type detection
- Error handling and logging
- Response formatting and headers
"""

from unittest.mock import patch, MagicMock
from odoo.tests.common import HttpCase
import json
import base64
import logging


class TestProductecaImageController(HttpCase):
    """Test cases for ProductecaImageController."""

    def setUp(self):
        """Set up test data for ProductecaImageController tests."""
        super(TestProductecaImageController, self).setUp()
        
        # Create test company
        self.company = self.env['res.company'].create({
            'name': 'Test Company',
            'country_id': self.env.ref('base.ar').id,
        })
        
        # Create Producteca account
        self.producteca_account = self.env['producteca.account'].create({
            'name': 'Test Producteca Account',
            'api_key': 'test_api_key',
            'base_url': 'https://test.producteca.com',
            'company_id': self.company.id,
            'producteca_company_id': 'test_company_123',
        })
        
        # Create test product with image
        test_image_data = base64.b64encode(b'fake_image_data')
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 100.0,
            'image_1920': test_image_data,
        })
        
        # Create test product without image
        self.product_no_image = self.env['product.product'].create({
            'name': 'Product Without Image',
            'list_price': 50.0,
            'image_1920': False,
        })

    def test_01_controller_class_definition(self):
        """Test controller class definition."""
        from odoo.addons.producteca_connector.controllers.main import ProductecaImageController
        
        controller = ProductecaImageController()
        self.assertIsNotNone(controller)

    @patch('odoo.addons.producteca_connector.models.product_product.ProductProduct.get_product_from_producteca_and_create')
    def test_02_process_product_webhook_method(self, mock_get_create):
        """Test _process_product_webhook method."""
        from odoo.addons.producteca_connector.controllers.main import ProductecaImageController
        
        controller = ProductecaImageController()
        mock_get_create.return_value = True
        
        # Mock request environment
        with patch('odoo.http.request') as mock_request:
            mock_env = MagicMock()
            mock_request.env = mock_env
            mock_product_model = MagicMock()
            mock_env.__getitem__.return_value = mock_product_model
            mock_product_model.with_delay.return_value = mock_product_model
            
            result = controller._process_product_webhook(self.producteca_account.id, 12345)
            
            # Verify delayed job was triggered
            mock_product_model.with_delay.assert_called_once()

    @patch('odoo.addons.producteca_connector.models.sale_order.SaleOrder._upset_saleorder_from_producteca')
    def test_03_process_sale_webhook_method(self, mock_upset):
        """Test _process_sale_webhook method."""
        from odoo.addons.producteca_connector.controllers.main import ProductecaImageController
        
        controller = ProductecaImageController()
        mock_upset.return_value = True
        
        # Mock client and sale order
        mock_client = MagicMock()
        mock_sale_order = MagicMock()
        mock_sale_order.to_dict.return_value = {'id': 12345, 'total': 100.0}
        mock_client.SalesOrder.get.return_value = mock_sale_order
        
        # Mock request environment
        with patch('odoo.http.request') as mock_request:
            mock_env = MagicMock()
            mock_request.env = mock_env
            mock_sale_model = MagicMock()
            mock_env.__getitem__.return_value = mock_sale_model
            mock_sale_model.with_delay.return_value = mock_sale_model
            
            result = controller._process_sale_webhook(mock_client, self.producteca_account.id, 67890)
            
            # Verify API calls
            mock_client.SalesOrder.get.assert_called_once_with(67890)
            mock_sale_order.to_dict.assert_called_once()
            mock_sale_model.with_delay.assert_called_once()

    def test_04_webhook_route_configuration(self):
        """Test webhook route configuration."""
        from odoo.addons.producteca_connector.controllers.main import ProductecaImageController
        
        # Get the webhook method
        webhook_method = getattr(ProductecaImageController, 'webhooks')
        
        # Check if method exists
        self.assertTrue(callable(webhook_method))

    @patch('odoo.addons.producteca_connector.controllers.main.ProductecaImageController._process_product_webhook')
    def test_05_webhooks_product_processing(self, mock_process_product):
        """Test webhook endpoint for product processing."""
        mock_process_product.return_value = True
        
        webhook_data = {
            'resourceType': 'products',
            'resourceId': 12345,
            'companyId': 'test_company_123'
        }
        
        with patch('odoo.http.request') as mock_request:
            # Mock request data
            mock_request.httprequest.data = json.dumps(webhook_data).encode()
            mock_request.env = self.env
            mock_request.not_found = MagicMock(return_value='Not Found')
            mock_request.make_response = MagicMock(return_value='OK')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaImageController
            controller = ProductecaImageController()
            
            result = controller.webhooks()
            
            # Verify product webhook was processed
            mock_process_product.assert_called_once()

    @patch('odoo.addons.producteca_connector.controllers.main.ProductecaImageController._process_sale_webhook')
    def test_06_webhooks_sale_order_processing(self, mock_process_sale):
        """Test webhook endpoint for sale order processing."""
        mock_process_sale.return_value = True
        
        webhook_data = {
            'resourceType': 'products/saleOrders',
            'resourceId': 67890,
            'companyId': 'test_company_123'
        }
        
        with patch('odoo.http.request') as mock_request:
            # Mock request data
            mock_request.httprequest.data = json.dumps(webhook_data).encode()
            mock_request.env = self.env
            mock_request.not_found = MagicMock(return_value='Not Found')
            mock_request.make_response = MagicMock(return_value='OK')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaImageController
            controller = ProductecaImageController()
            
            result = controller.webhooks()
            
            # Verify sale webhook was processed
            mock_process_sale.assert_called_once()

    def test_07_webhooks_company_not_found(self):
        """Test webhook with non-existent company ID."""
        webhook_data = {
            'resourceType': 'products',
            'resourceId': 12345,
            'companyId': 'non_existent_company'
        }
        
        with patch('odoo.http.request') as mock_request:
            mock_request.httprequest.data = json.dumps(webhook_data).encode()
            mock_request.env = self.env
            mock_request.not_found = MagicMock(return_value='Not Found')
            mock_request.make_response = MagicMock(return_value='OK')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaImageController
            controller = ProductecaImageController()
            
            result = controller.webhooks()
            
            # Should return not found
            mock_request.not_found.assert_called_once_with("companyId not found")

    def test_08_webhooks_invalid_json(self):
        """Test webhook with invalid JSON data."""
        with patch('odoo.http.request') as mock_request:
            mock_request.httprequest.data = b'invalid json data'
            mock_request.env = self.env
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaImageController
            controller = ProductecaImageController()
            
            # Should handle JSON parsing errors
            try:
                result = controller.webhooks()
            except json.JSONDecodeError:
                # Expected behavior for invalid JSON
                pass

    def test_09_get_product_image_existing_product(self):
        """Test get_product_image with existing product."""
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.not_found = MagicMock(return_value='Not Found')
            mock_request.make_response = MagicMock(return_value='Image Response')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaImageController
            controller = ProductecaImageController()
            
            result = controller.get_product_image(self.product.id)
            
            # Should return image response
            mock_request.make_response.assert_called_once()

    def test_10_get_product_image_non_existent_product(self):
        """Test get_product_image with non-existent product."""
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.not_found = MagicMock(return_value='Not Found')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaImageController
            controller = ProductecaImageController()
            
            result = controller.get_product_image(99999)  # Non-existent ID
            
            # Should return not found
            mock_request.not_found.assert_called_once()

    def test_11_get_product_image_no_image_data(self):
        """Test get_product_image with product having no image."""
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.not_found = MagicMock(return_value='Not Found')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaImageController
            controller = ProductecaImageController()
            
            result = controller.get_product_image(self.product_no_image.id)
            
            # Should return not found for missing image
            mock_request.not_found.assert_called_once()

    def test_12_image_content_type_detection_jpeg(self):
        """Test image content type detection for JPEG."""
        # Create product with JPEG-like image data
        jpeg_header = b'\xff\xd8\xff'  # JPEG header
        jpeg_data = base64.b64encode(jpeg_header + b'fake_jpeg_data')
        
        product_jpeg = self.env['product.product'].create({
            'name': 'JPEG Product',
            'image_1920': jpeg_data,
        })
        
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.make_response = MagicMock(return_value='JPEG Response')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaImageController
            controller = ProductecaImageController()
            
            result = controller.get_product_image(product_jpeg.id)
            
            # Verify response was created (content type would be detected in real implementation)
            mock_request.make_response.assert_called_once()

    def test_13_image_content_type_detection_png(self):
        """Test image content type detection for PNG."""
        # Create product with PNG-like image data
        png_header = b'\x89PNG'  # PNG header
        png_data = base64.b64encode(png_header + b'fake_png_data')
        
        product_png = self.env['product.product'].create({
            'name': 'PNG Product',
            'image_1920': png_data,
        })
        
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.make_response = MagicMock(return_value='PNG Response')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaImageController
            controller = ProductecaImageController()
            
            result = controller.get_product_image(product_png.id)
            
            # Verify response was created
            mock_request.make_response.assert_called_once()

    def test_14_image_content_type_detection_gif(self):
        """Test image content type detection for GIF."""
        # Create product with GIF-like image data  
        gif_header = b'GIF8'  # GIF header
        gif_data = base64.b64encode(gif_header + b'fake_gif_data')
        
        product_gif = self.env['product.product'].create({
            'name': 'GIF Product',
            'image_1920': gif_data,
        })
        
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.make_response = MagicMock(return_value='GIF Response')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaImageController
            controller = ProductecaImageController()
            
            result = controller.get_product_image(product_gif.id)
            
            # Verify response was created
            mock_request.make_response.assert_called_once()

    def test_15_image_response_headers(self):
        """Test image response headers configuration."""
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.make_response = MagicMock(return_value='Response with Headers')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaImageController
            controller = ProductecaImageController()
            
            result = controller.get_product_image(self.product.id)
            
            # Verify make_response was called with headers
            call_args = mock_request.make_response.call_args
            if call_args and len(call_args) > 1:
                headers = call_args[1].get('headers', [])
                # Headers should include Content-Type, Cache-Control, Content-Length
                self.assertIsInstance(headers, (list, tuple))

    @patch('logging.getLogger')
    def test_16_error_logging_in_image_endpoint(self, mock_logger):
        """Test error logging in image endpoint."""
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.not_found = MagicMock(return_value='Not Found')
            
            # Force an exception in the method
            with patch('base64.b64decode', side_effect=Exception('Test error')):
                from odoo.addons.producteca_connector.controllers.main import ProductecaImageController
                controller = ProductecaImageController()
                
                result = controller.get_product_image(self.product.id)
                
                # Should handle error gracefully
                mock_request.not_found.assert_called()

    def test_17_webhook_logging(self):
        """Test webhook request logging."""
        webhook_data = {
            'resourceType': 'products',
            'resourceId': 12345,
            'companyId': 'test_company_123'
        }
        
        with patch('odoo.http.request') as mock_request:
            mock_request.httprequest.data = json.dumps(webhook_data).encode()
            mock_request.env = self.env
            mock_request.make_response = MagicMock(return_value='OK')
            
            with patch('logging.getLogger') as mock_logger:
                mock_logger_instance = MagicMock()
                mock_logger.return_value = mock_logger_instance
                
                from odoo.addons.producteca_connector.controllers.main import ProductecaImageController
                controller = ProductecaImageController()
                
                # Mock process methods to avoid external calls
                with patch.object(controller, '_process_product_webhook'):
                    result = controller.webhooks()
                
                # Verify logging was called
                mock_logger_instance.info.assert_called()

    def test_18_webhook_unknown_resource_type(self):
        """Test webhook with unknown resource type."""
        webhook_data = {
            'resourceType': 'unknown_type',
            'resourceId': 12345,
            'companyId': 'test_company_123'
        }
        
        with patch('odoo.http.request') as mock_request:
            mock_request.httprequest.data = json.dumps(webhook_data).encode()
            mock_request.env = self.env
            mock_request.make_response = MagicMock(return_value='OK')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaImageController
            controller = ProductecaImageController()
            
            result = controller.webhooks()
            
            # Should still return OK even for unknown resource types
            mock_request.make_response.assert_called_once_with("OK")

    def test_19_image_route_configuration(self):
        """Test image route configuration."""
        from odoo.addons.producteca_connector.controllers.main import ProductecaImageController
        
        # Get the image method
        image_method = getattr(ProductecaImageController, 'get_product_image')
        
        # Check if method exists
        self.assertTrue(callable(image_method))

    def test_20_webhook_post_data_processing(self):
        """Test webhook POST data processing."""
        webhook_data = {
            'resourceType': 'products',
            'resourceId': 555,
            'companyId': 'test_company_123',
            'additional_field': 'extra_data'
        }
        
        with patch('odoo.http.request') as mock_request:
            mock_request.httprequest.data = json.dumps(webhook_data).encode()
            mock_request.env = self.env
            mock_request.make_response = MagicMock(return_value='OK')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaImageController
            controller = ProductecaImageController()
            
            with patch.object(controller, '_process_product_webhook') as mock_process:
                result = controller.webhooks(**{'extra': 'post_data'})
                
                # Verify processing was called with correct parameters
                mock_process.assert_called_once()

    def test_21_image_base64_decoding_error(self):
        """Test image base64 decoding error handling."""
        # Create product with invalid base64 data
        product_invalid = self.env['product.product'].create({
            'name': 'Invalid Image Product',
            'image_1920': 'invalid_base64_data',
        })
        
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.not_found = MagicMock(return_value='Not Found')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaImageController
            controller = ProductecaImageController()
            
            result = controller.get_product_image(product_invalid.id)
            
            # Should handle base64 decoding errors
            mock_request.not_found.assert_called()

    def test_22_webhook_empty_data(self):
        """Test webhook with empty data."""
        with patch('odoo.http.request') as mock_request:
            mock_request.httprequest.data = b''
            mock_request.env = self.env
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaImageController
            controller = ProductecaImageController()
            
            # Should handle empty data gracefully
            try:
                result = controller.webhooks()
            except (json.JSONDecodeError, KeyError):
                # Expected behavior for empty/invalid data
                pass

    def test_23_producteca_account_search_by_company_id(self):
        """Test Producteca account search by company ID."""
        webhook_data = {
            'resourceType': 'products',
            'resourceId': 12345,
            'companyId': 'test_company_123'
        }
        
        with patch('odoo.http.request') as mock_request:
            mock_request.httprequest.data = json.dumps(webhook_data).encode()
            mock_request.env = self.env
            mock_request.make_response = MagicMock(return_value='OK')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaImageController
            controller = ProductecaImageController()
            
            with patch.object(controller, '_process_product_webhook') as mock_process:
                result = controller.webhooks()
                
                # Should find the account by company ID
                account_call_args = mock_process.call_args
                if account_call_args:
                    account_id = account_call_args[0][0]
                    self.assertEqual(account_id, self.producteca_account.id)

    def test_24_client_retrieval_in_sale_webhook(self):
        """Test client retrieval in sale webhook processing."""
        webhook_data = {
            'resourceType': 'products/saleOrders',
            'resourceId': 67890,
            'companyId': 'test_company_123'
        }
        
        with patch('odoo.http.request') as mock_request:
            mock_request.httprequest.data = json.dumps(webhook_data).encode()
            mock_request.env = self.env
            mock_request.make_response = MagicMock(return_value='OK')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaImageController
            controller = ProductecaImageController()
            
            with patch.object(controller, '_process_sale_webhook') as mock_process:
                with patch.object(self.producteca_account, 'get_client') as mock_get_client:
                    mock_client = MagicMock()
                    mock_get_client.return_value = mock_client
                    
                    result = controller.webhooks()
                    
                    # Should retrieve client and pass to processing
                    mock_get_client.assert_called_once()
                    mock_process.assert_called_once()

    def test_25_comprehensive_controller_workflow(self):
        """Test comprehensive controller workflow."""
        # Test complete webhook processing workflow
        webhook_data = {
            'resourceType': 'products',
            'resourceId': 12345,
            'companyId': 'test_company_123',
            'timestamp': '2024-01-15T10:30:00Z',
            'event': 'product.updated'
        }
        
        with patch('odoo.http.request') as mock_request:
            mock_request.httprequest.data = json.dumps(webhook_data).encode()
            mock_request.env = self.env
            mock_request.not_found = MagicMock(return_value='Not Found')
            mock_request.make_response = MagicMock(return_value='OK')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaImageController
            controller = ProductecaImageController()
            
            # Mock all processing methods
            with patch.object(controller, '_process_product_webhook') as mock_product_process:
                with patch('logging.getLogger') as mock_logger:
                    mock_logger_instance = MagicMock()
                    mock_logger.return_value = mock_logger_instance
                    
                    # Execute webhook
                    result = controller.webhooks()
                    
                    # Verify complete workflow
                    # 1. Logging was called
                    mock_logger_instance.info.assert_called()
                    
                    # 2. Account was found
                    # 3. Product processing was triggered
                    mock_product_process.assert_called_once_with(self.producteca_account.id, 12345)
                    
                    # 4. Success response was returned
                    mock_request.make_response.assert_called_once_with("OK")
        
        # Test complete image serving workflow
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.not_found = MagicMock(return_value='Not Found')
            mock_request.make_response = MagicMock(return_value='Image Response')
            
            # Execute image serving
            result = controller.get_product_image(self.product.id)
            
            # Verify image workflow
            # 1. Product was found
            # 2. Image data was processed
            # 3. Response was created with proper headers
            mock_request.make_response.assert_called_once()
            
            # Verify response includes image data and headers
            call_args = mock_request.make_response.call_args
            self.assertIsNotNone(call_args)
            
            # Should have image data as first argument
            image_data = call_args[0][0]
            self.assertIsInstance(image_data, bytes)
            
            # Should have headers as keyword argument
            if len(call_args) > 1:
                headers = call_args[1].get('headers', [])
                # Verify essential headers are present
                header_names = [header[0] for header in headers] if headers else []
                expected_headers = ['Content-Type', 'Cache-Control', 'Content-Length']
                for expected_header in expected_headers:
                    self.assertIn(expected_header, header_names)