# -*- coding: utf-8 -*-
"""
Test module for accounting models in producteca_connector.

This module aggregates all test cases for accounting-related models:
- AccountMove: Invoice integration with Producteca
- AccountJournal: Payment method configuration
- AccountPayment: Payment synchronization
"""

from . import test_account_move
from . import test_account_journal  
from . import test_account_payment