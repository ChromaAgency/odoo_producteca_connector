from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    # All Producteca product logic has been migrated to product.template
    # This model now only inherits product.product without adding functionality
