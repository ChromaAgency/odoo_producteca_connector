# -*- coding: utf-8 -*-
"""
Test module for wizards in producteca_connector.

This module aggregates all test cases for wizard-related models:
- ProductecaProductsWizard: Product import from Producteca
- ProductecaSaleordersWizard: Sale order import from Producteca  
- ConfirmCancelSaleOrder: Sale order cancellation confirmation
"""

from . import test_import_producteca_product
from . import test_import_producteca_saleorder
from . import test_confirm_cancel_sale_order