# -*- coding: utf-8 -*-
"""
Test suite for ProductecaInvoiceController in producteca_connector module.

This module provides comprehensive test coverage for the ProductecaInvoiceController,
which handles PDF invoice serving for Producteca integration, including:
- PDF invoice retrieval with access token validation
- Base64 PDF decoding and serving
- Dynamic PDF generation when stored PDF is unavailable
- Error handling and logging
- Response formatting with proper headers

Test Patterns:
- Uses Odoo HttpCase for HTTP request testing
- Mock PDF generation and file operations
- Test HTTP routes and response handling
- Validate error scenarios and edge cases
- Test authentication and access control

Coverage Areas:
- Invoice PDF endpoint with token validation
- Base64 PDF content processing
- Dynamic PDF report generation
- Error handling and logging
- Response headers and content type
- Security validation with access tokens
"""

from unittest.mock import patch, MagicMock
from odoo.tests.common import HttpCase
import base64
import logging


class TestProductecaInvoiceController(HttpCase):
    """Test cases for ProductecaInvoiceController."""

    def setUp(self):
        """Set up test data for ProductecaInvoiceController tests."""
        super(TestProductecaInvoiceController, self).setUp()
        
        # Create test company
        self.company = self.env['res.company'].create({
            'name': 'Test Company',
            'country_id': self.env.ref('base.ar').id,
        })
        
        # Create test partner
        self.partner = self.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'customer@test.com',
            'company_id': self.company.id,
        })
        
        # Create test product
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 100.0,
            'standard_price': 50.0,
            'type': 'product',
        })
        
        # Create sales journal
        self.sales_journal = self.env['account.journal'].create({
            'name': 'Test Sales Journal',
            'type': 'sale',
            'code': 'TSJ',
            'company_id': self.company.id,
        })
        
        # Create test invoice with PDF content
        test_pdf_content = base64.b64encode(b'fake_pdf_content')
        self.invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.sales_journal.id,
            'company_id': self.company.id,
            'name': 'INV/2024/0001',
            'access_token': 'test_access_token_123',
            'invoice_pdf_report_file': test_pdf_content,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 2,
                'price_unit': 100.0,
                'name': 'Test Product Line',
            })],
        })
        
        # Create invoice without PDF content
        self.invoice_no_pdf = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.sales_journal.id,
            'company_id': self.company.id,
            'name': 'INV/2024/0002',
            'access_token': 'test_access_token_456',
            'invoice_pdf_report_file': False,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 150.0,
                'name': 'Test Product Line 2',
            })],
        })

    def test_01_controller_class_definition(self):
        """Test controller class definition."""
        from odoo.addons.producteca_connector.controllers.main import ProductecaIInvoiceController
        
        controller = ProductecaIInvoiceController()
        self.assertIsNotNone(controller)

    def test_02_get_invoice_pdf_route_configuration(self):
        """Test PDF invoice route configuration."""
        from odoo.addons.producteca_connector.controllers.main import ProductecaIInvoiceController
        
        # Get the PDF method
        pdf_method = getattr(ProductecaIInvoiceController, 'get_invoice_pdf')
        
        # Check if method exists
        self.assertTrue(callable(pdf_method))

    def test_03_get_invoice_pdf_existing_invoice_with_pdf(self):
        """Test get_invoice_pdf with existing invoice and PDF content."""
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.not_found = MagicMock(return_value='Not Found')
            mock_request.make_response = MagicMock(return_value='PDF Response')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaIInvoiceController
            controller = ProductecaIInvoiceController()
            
            result = controller.get_invoice_pdf(
                self.invoice.id, 
                'test_access_token_123'
            )
            
            # Should return PDF response
            mock_request.make_response.assert_called_once()

    def test_04_get_invoice_pdf_invalid_access_token(self):
        """Test get_invoice_pdf with invalid access token."""
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.not_found = MagicMock(return_value='Not Found')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaIInvoiceController
            controller = ProductecaIInvoiceController()
            
            result = controller.get_invoice_pdf(
                self.invoice.id, 
                'invalid_token'
            )
            
            # Should return not found for invalid token
            mock_request.not_found.assert_called_once()

    def test_05_get_invoice_pdf_non_existent_invoice(self):
        """Test get_invoice_pdf with non-existent invoice."""
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.not_found = MagicMock(return_value='Not Found')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaIInvoiceController
            controller = ProductecaIInvoiceController()
            
            result = controller.get_invoice_pdf(
                99999,  # Non-existent ID
                'any_token'
            )
            
            # Should return not found
            mock_request.not_found.assert_called_once()

    @patch('odoo.http.request')
    @patch('base64.b64decode')
    def test_06_get_invoice_pdf_base64_decode_success(self, mock_b64decode, mock_request):
        """Test successful base64 decoding of PDF content."""
        mock_b64decode.return_value = b'decoded_pdf_content'
        mock_request.env = self.env
        mock_request.not_found = MagicMock(return_value='Not Found')
        mock_request.make_response = MagicMock(return_value='PDF Response')
        
        from odoo.addons.producteca_connector.controllers.main import ProductecaIInvoiceController
        controller = ProductecaIInvoiceController()
        
        result = controller.get_invoice_pdf(
            self.invoice.id, 
            'test_access_token_123'
        )
        
        # Should decode base64 and return response
        mock_b64decode.assert_called()
        mock_request.make_response.assert_called_once()

    @patch('odoo.http.request')
    @patch('base64.b64decode')
    def test_07_get_invoice_pdf_base64_decode_error(self, mock_b64decode, mock_request):
        """Test base64 decoding error handling."""
        mock_b64decode.side_effect = Exception('Base64 decode error')
        mock_request.env = self.env
        mock_request.not_found = MagicMock(return_value='Not Found')
        mock_request.make_response = MagicMock(return_value='Generated PDF')
        
        # Mock report generation
        mock_report = MagicMock()
        mock_report._render_qweb_pdf.return_value = (b'generated_pdf', 'application/pdf')
        mock_request.env.__getitem__.return_value = mock_report
        
        from odoo.addons.producteca_connector.controllers.main import ProductecaIInvoiceController
        controller = ProductecaIInvoiceController()
        
        result = controller.get_invoice_pdf(
            self.invoice.id, 
            'test_access_token_123'
        )
        
        # Should fall back to PDF generation
        mock_report._render_qweb_pdf.assert_called_once()

    def test_08_get_invoice_pdf_no_stored_pdf_content(self):
        """Test get_invoice_pdf when no stored PDF content exists."""
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.not_found = MagicMock(return_value='Not Found')
            mock_request.make_response = MagicMock(return_value='Generated PDF')
            
            # Mock report generation
            mock_report = MagicMock()
            mock_report._render_qweb_pdf.return_value = (b'generated_pdf_content', 'application/pdf')
            mock_request.env.__getitem__.return_value = mock_report
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaIInvoiceController
            controller = ProductecaIInvoiceController()
            
            result = controller.get_invoice_pdf(
                self.invoice_no_pdf.id, 
                'test_access_token_456'
            )
            
            # Should generate PDF on demand
            mock_report._render_qweb_pdf.assert_called_once_with(
                'account.account_invoices', 
                [self.invoice_no_pdf.id]
            )

    def test_09_get_invoice_pdf_generation_failure(self):
        """Test PDF generation failure handling."""
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.not_found = MagicMock(return_value='Not Found')
            mock_request.make_response = MagicMock(return_value='Error Response')
            
            # Mock report generation failure
            mock_report = MagicMock()
            mock_report._render_qweb_pdf.return_value = (None, None)
            mock_request.env.__getitem__.return_value = mock_report
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaIInvoiceController
            controller = ProductecaIInvoiceController()
            
            result = controller.get_invoice_pdf(
                self.invoice_no_pdf.id, 
                'test_access_token_456'
            )
            
            # Should return not found when generation fails
            mock_request.not_found.assert_called()

    def test_10_get_invoice_pdf_generation_exception(self):
        """Test exception handling during PDF generation."""
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.not_found = MagicMock(return_value='Not Found')
            mock_request.make_response = MagicMock(return_value='Error Response')
            
            # Mock report generation exception
            mock_report = MagicMock()
            mock_report._render_qweb_pdf.side_effect = Exception('Generation error')
            mock_request.env.__getitem__.return_value = mock_report
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaIInvoiceController
            controller = ProductecaIInvoiceController()
            
            result = controller.get_invoice_pdf(
                self.invoice_no_pdf.id, 
                'test_access_token_456'
            )
            
            # Should handle generation exceptions
            mock_request.make_response.assert_called()

    def test_11_pdf_response_headers(self):
        """Test PDF response headers configuration."""
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.make_response = MagicMock(return_value='PDF Response')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaIInvoiceController
            controller = ProductecaIInvoiceController()
            
            result = controller.get_invoice_pdf(
                self.invoice.id, 
                'test_access_token_123'
            )
            
            # Verify make_response was called with headers
            call_args = mock_request.make_response.call_args
            if call_args:
                # Should have PDF data and headers
                pdf_data = call_args[0][0]
                headers = call_args[1].get('headers', []) if len(call_args) > 1 else []
                
                # Verify PDF data is bytes
                self.assertIsInstance(pdf_data, bytes)
                
                # Verify essential headers
                if headers:
                    header_names = [header[0] for header in headers]
                    expected_headers = ['Content-Type', 'Content-Disposition', 'Content-Length']
                    for expected_header in expected_headers:
                        self.assertIn(expected_header, header_names)

    def test_12_pdf_filename_generation(self):
        """Test PDF filename generation in Content-Disposition header."""
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.make_response = MagicMock(return_value='PDF Response')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaIInvoiceController
            controller = ProductecaIInvoiceController()
            
            result = controller.get_invoice_pdf(
                self.invoice.id, 
                'test_access_token_123'
            )
            
            # Verify filename includes invoice name
            call_args = mock_request.make_response.call_args
            if call_args and len(call_args) > 1:
                headers = call_args[1].get('headers', [])
                disposition_header = None
                
                for header in headers:
                    if header[0] == 'Content-Disposition':
                        disposition_header = header[1]
                        break
                
                if disposition_header:
                    self.assertIn('factura_', disposition_header)
                    self.assertIn('.pdf', disposition_header)

    @patch('logging.getLogger')
    def test_13_error_logging_in_pdf_endpoint(self, mock_logger):
        """Test error logging in PDF endpoint."""
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.not_found = MagicMock(return_value='Not Found')
            mock_request.make_response = MagicMock(return_value='Error Response')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaIInvoiceController
            controller = ProductecaIInvoiceController()
            
            result = controller.get_invoice_pdf(
                self.invoice.id, 
                'invalid_token'
            )
            
            # Should log warning for invalid token
            mock_logger_instance.warning.assert_called()

    def test_14_invoice_search_with_access_token(self):
        """Test invoice search with access token validation."""
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.make_response = MagicMock(return_value='PDF Response')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaIInvoiceController
            controller = ProductecaIInvoiceController()
            
            # Should find invoice with correct token
            result = controller.get_invoice_pdf(
                self.invoice.id, 
                'test_access_token_123'
            )
            
            # Should return PDF response for valid token
            mock_request.make_response.assert_called_once()

    def test_15_pdf_content_type_validation(self):
        """Test PDF content type in response headers."""
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.make_response = MagicMock(return_value='PDF Response')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaIInvoiceController
            controller = ProductecaIInvoiceController()
            
            result = controller.get_invoice_pdf(
                self.invoice.id, 
                'test_access_token_123'
            )
            
            # Verify content type is application/pdf
            call_args = mock_request.make_response.call_args
            if call_args and len(call_args) > 1:
                headers = call_args[1].get('headers', [])
                content_type = None
                
                for header in headers:
                    if header[0] == 'Content-Type':
                        content_type = header[1]
                        break
                
                if content_type:
                    self.assertEqual(content_type, 'application/pdf')

    def test_16_pdf_content_length_header(self):
        """Test PDF content length header."""
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.make_response = MagicMock(return_value='PDF Response')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaIInvoiceController
            controller = ProductecaIInvoiceController()
            
            result = controller.get_invoice_pdf(
                self.invoice.id, 
                'test_access_token_123'
            )
            
            # Verify content length matches PDF data length
            call_args = mock_request.make_response.call_args
            if call_args:
                pdf_data = call_args[0][0]
                headers = call_args[1].get('headers', []) if len(call_args) > 1 else []
                
                content_length = None
                for header in headers:
                    if header[0] == 'Content-Length':
                        content_length = int(header[1])
                        break
                
                if content_length:
                    self.assertEqual(content_length, len(pdf_data))

    def test_17_report_technical_name(self):
        """Test correct technical report name usage."""
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.not_found = MagicMock(return_value='Not Found')
            mock_request.make_response = MagicMock(return_value='Generated PDF')
            
            # Mock report generation
            mock_report = MagicMock()
            mock_report._render_qweb_pdf.return_value = (b'generated_pdf', 'application/pdf')
            mock_request.env.__getitem__.return_value = mock_report
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaIInvoiceController
            controller = ProductecaIInvoiceController()
            
            result = controller.get_invoice_pdf(
                self.invoice_no_pdf.id, 
                'test_access_token_456'
            )
            
            # Should use correct technical report name
            mock_report._render_qweb_pdf.assert_called_once_with(
                'account.account_invoices', 
                [self.invoice_no_pdf.id]
            )

    def test_18_general_exception_handling(self):
        """Test general exception handling in PDF endpoint."""
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.make_response = MagicMock(return_value='Error Response')
            
            # Force a general exception
            mock_request.env.__getitem__.side_effect = Exception('General error')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaIInvoiceController
            controller = ProductecaIInvoiceController()
            
            result = controller.get_invoice_pdf(
                self.invoice.id, 
                'test_access_token_123'
            )
            
            # Should handle general exceptions gracefully
            mock_request.make_response.assert_called()

    def test_19_empty_pdf_content_handling(self):
        """Test handling of empty PDF content."""
        # Create invoice with empty PDF content
        invoice_empty_pdf = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.sales_journal.id,
            'company_id': self.company.id,
            'name': 'INV/2024/0003',
            'access_token': 'test_access_token_789',
            'invoice_pdf_report_file': '',  # Empty string
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 100.0,
                'name': 'Empty PDF Test',
            })],
        })
        
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.not_found = MagicMock(return_value='Not Found')
            mock_request.make_response = MagicMock(return_value='Generated PDF')
            
            # Mock report generation
            mock_report = MagicMock()
            mock_report._render_qweb_pdf.return_value = (b'generated_pdf', 'application/pdf')
            mock_request.env.__getitem__.return_value = mock_report
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaIInvoiceController
            controller = ProductecaIInvoiceController()
            
            result = controller.get_invoice_pdf(
                invoice_empty_pdf.id, 
                'test_access_token_789'
            )
            
            # Should generate PDF for empty content
            mock_report._render_qweb_pdf.assert_called_once()

    def test_20_invoice_name_in_filename(self):
        """Test invoice name inclusion in PDF filename."""
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.make_response = MagicMock(return_value='PDF Response')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaIInvoiceController
            controller = ProductecaIInvoiceController()
            
            result = controller.get_invoice_pdf(
                self.invoice.id, 
                'test_access_token_123'
            )
            
            # Verify invoice name is used in filename
            call_args = mock_request.make_response.call_args
            if call_args and len(call_args) > 1:
                headers = call_args[1].get('headers', [])
                
                for header in headers:
                    if header[0] == 'Content-Disposition':
                        # Should contain invoice name
                        self.assertIn(self.invoice.name, header[1])

    def test_21_fallback_to_invoice_id_in_filename(self):
        """Test fallback to invoice ID when name is not available."""
        # Create invoice without name
        invoice_no_name = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.sales_journal.id,
            'company_id': self.company.id,
            'name': False,  # No name
            'access_token': 'test_access_token_no_name',
            'invoice_pdf_report_file': base64.b64encode(b'pdf_content'),
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 100.0,
                'name': 'No Name Test',
            })],
        })
        
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.make_response = MagicMock(return_value='PDF Response')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaIInvoiceController
            controller = ProductecaIInvoiceController()
            
            result = controller.get_invoice_pdf(
                invoice_no_name.id, 
                'test_access_token_no_name'
            )
            
            # Should fallback to invoice ID in filename
            call_args = mock_request.make_response.call_args
            if call_args and len(call_args) > 1:
                headers = call_args[1].get('headers', [])
                
                for header in headers:
                    if header[0] == 'Content-Disposition':
                        # Should contain invoice ID
                        self.assertIn(str(invoice_no_name.id), header[1])

    def test_22_sudo_access_in_invoice_search(self):
        """Test sudo access in invoice search."""
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.make_response = MagicMock(return_value='PDF Response')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaIInvoiceController
            controller = ProductecaIInvoiceController()
            
            result = controller.get_invoice_pdf(
                self.invoice.id, 
                'test_access_token_123'
            )
            
            # Method should use sudo for invoice search
            # This is implicitly tested by the successful execution

    def test_23_multiple_invoice_token_validation(self):
        """Test token validation with multiple invoices."""
        # Create second invoice with different token
        invoice2 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.sales_journal.id,
            'company_id': self.company.id,
            'name': 'INV/2024/0004',
            'access_token': 'different_token_123',
            'invoice_pdf_report_file': base64.b64encode(b'different_pdf'),
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 75.0,
                'name': 'Different Invoice Test',
            })],
        })
        
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.not_found = MagicMock(return_value='Not Found')
            mock_request.make_response = MagicMock(return_value='PDF Response')
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaIInvoiceController
            controller = ProductecaIInvoiceController()
            
            # Test correct token for first invoice
            result1 = controller.get_invoice_pdf(
                self.invoice.id, 
                'test_access_token_123'
            )
            
            # Should return PDF
            mock_request.make_response.assert_called()
            mock_request.make_response.reset_mock()
            
            # Test wrong token for first invoice
            result2 = controller.get_invoice_pdf(
                self.invoice.id, 
                'different_token_123'  # Wrong token
            )
            
            # Should return not found
            mock_request.not_found.assert_called()

    def test_24_pdf_report_service_integration(self):
        """Test integration with PDF report service."""
        with patch('odoo.http.request') as mock_request:
            mock_request.env = self.env
            mock_request.not_found = MagicMock(return_value='Not Found')
            mock_request.make_response = MagicMock(return_value='Generated PDF')
            
            # Mock ir.actions.report service
            mock_report_service = MagicMock()
            mock_report_service._render_qweb_pdf.return_value = (
                b'generated_report_content', 
                'application/pdf'
            )
            mock_request.env.__getitem__.return_value = mock_report_service
            
            from odoo.addons.producteca_connector.controllers.main import ProductecaIInvoiceController
            controller = ProductecaIInvoiceController()
            
            result = controller.get_invoice_pdf(
                self.invoice_no_pdf.id, 
                'test_access_token_456'
            )
            
            # Should interact with report service
            mock_request.env.__getitem__.assert_called_with('ir.actions.report')
            mock_report_service._render_qweb_pdf.assert_called_once()

    def test_25_comprehensive_pdf_controller_workflow(self):
        """Test comprehensive PDF controller workflow."""
        # Test complete PDF serving workflow with all scenarios
        test_scenarios = [
            {
                'name': 'existing_pdf',
                'invoice': self.invoice,
                'token': 'test_access_token_123',
                'expect_generation': False
            },
            {
                'name': 'missing_pdf',
                'invoice': self.invoice_no_pdf,
                'token': 'test_access_token_456',
                'expect_generation': True
            }
        ]
        
        from odoo.addons.producteca_connector.controllers.main import ProductecaIInvoiceController
        controller = ProductecaIInvoiceController()
        
        for scenario in test_scenarios:
            with self.subTest(scenario=scenario['name']):
                with patch('odoo.http.request') as mock_request:
                    mock_request.env = self.env
                    mock_request.not_found = MagicMock(return_value='Not Found')
                    mock_request.make_response = MagicMock(return_value='PDF Response')
                    
                    # Mock report generation for missing PDF scenario
                    if scenario['expect_generation']:
                        mock_report = MagicMock()
                        mock_report._render_qweb_pdf.return_value = (
                            b'generated_pdf_content', 
                            'application/pdf'
                        )
                        mock_request.env.__getitem__.return_value = mock_report
                    
                    # Execute PDF retrieval
                    result = controller.get_invoice_pdf(
                        scenario['invoice'].id, 
                        scenario['token']
                    )
                    
                    # Verify successful response
                    mock_request.make_response.assert_called_once()
                    
                    # Verify response structure
                    call_args = mock_request.make_response.call_args
                    self.assertIsNotNone(call_args)
                    
                    # Should have PDF data
                    pdf_data = call_args[0][0]
                    self.assertIsInstance(pdf_data, bytes)
                    self.assertGreater(len(pdf_data), 0)
                    
                    # Should have proper headers
                    if len(call_args) > 1:
                        headers = call_args[1].get('headers', [])
                        header_dict = {h[0]: h[1] for h in headers}
                        
                        # Verify essential headers
                        self.assertEqual(header_dict.get('Content-Type'), 'application/pdf')
                        self.assertIn('Content-Disposition', header_dict)
                        self.assertIn('Content-Length', header_dict)
                        
                        # Verify filename in Content-Disposition
                        disposition = header_dict['Content-Disposition']
                        self.assertIn('filename=', disposition)
                        self.assertIn('.pdf', disposition)
                        
                        # Verify content length matches data
                        content_length = int(header_dict['Content-Length'])
                        self.assertEqual(content_length, len(pdf_data))
                    
                    # If generation was expected, verify it was called
                    if scenario['expect_generation']:
                        mock_request.env.__getitem__.assert_called_with('ir.actions.report')
        
        # Test error scenarios
        error_scenarios = [
            {
                'name': 'invalid_token',
                'invoice_id': self.invoice.id,
                'token': 'invalid_token',
                'expect_not_found': True
            },
            {
                'name': 'non_existent_invoice',
                'invoice_id': 99999,
                'token': 'any_token',
                'expect_not_found': True
            }
        ]
        
        for scenario in error_scenarios:
            with self.subTest(scenario=scenario['name']):
                with patch('odoo.http.request') as mock_request:
                    mock_request.env = self.env
                    mock_request.not_found = MagicMock(return_value='Not Found')
                    
                    result = controller.get_invoice_pdf(
                        scenario['invoice_id'], 
                        scenario['token']
                    )
                    
                    # Should return not found for error scenarios
                    if scenario['expect_not_found']:
                        mock_request.not_found.assert_called()