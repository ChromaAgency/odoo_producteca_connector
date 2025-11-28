from odoo import models, fields, api
from odoo.tools.translate import _
import logging
_logger = logging.getLogger(__name__)
import requests

class ProductecaConnections(models.Model):
    """Product connection management for Producteca marketplace integration.
    
    This model manages the relationships between Odoo product variants and their
    corresponding variations in the Producteca marketplace. Each connection
    represents one Odoo variant linked to one Producteca variation.
    
    Business Logic:
    - Links Odoo product variants to Producteca marketplace variations
    - Maintains 1:1 relationship between variant and Producteca variation
    - Handles product description synchronization
    - Provides queued operations for marketplace sync
    - Maintains connection status and metadata
    
    Key Features:
    - Variant-to-variation mapping (1:1)
    - Variation ID management
    - Asynchronous description synchronization
    - Unique constraint per variant per account
    - Connection status tracking
    """
    _name = 'producteca.product.connections'
    _description = 'Producteca Product Connections'
    
    producteca_account_id = fields.Many2one(
        'producteca.account', 
        string='Producteca Account', 
        required=True,
        help="Producteca account this connection belongs to. Defines authentication and sync settings."
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product Variant',
        required=True,
        ondelete='cascade',
        help="Odoo product variant linked to this Producteca marketplace variation."
    )
    product_tmpl_id = fields.Many2one(
        'product.template', 
        string='Product Template',
        related='product_id.product_tmpl_id',
        store=True,
        readonly=True,
        help="Product template of the variant (computed field)."
    )
    producteca_id = fields.Char(
        string='Producteca Product ID', 
        required=True,
        help="Unique identifier for the product in Producteca marketplace (shared across variations)."
    )
    producteca_variation_id = fields.Char(
        string='Producteca Variation ID',
        required=True,
        help="Unique identifier for the specific variation in Producteca marketplace."
    )
    active = fields.Boolean(
        string='Active', 
        default=True,
        help="Indicates if this connection is active and should be used for synchronization."
    )

    _sql_constraints = [
        ('unique_variant_per_account', 
         'UNIQUE(product_id, producteca_account_id)',
         'A product variant can only have one connection per Producteca account')
    ]