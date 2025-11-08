# -*- coding: utf-8 -*-
"""
Test module for controllers in producteca_connector.

This module aggregates all test cases for controller-related classes:
- ProductecaImageController: Webhook processing and image serving
- ProductecaIInvoiceController: PDF invoice serving with authentication
"""

from . import test_producteca_image_controller
from . import test_producteca_invoice_controller