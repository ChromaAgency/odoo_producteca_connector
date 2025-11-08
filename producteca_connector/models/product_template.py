from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    """Extended Product Template for Producteca integration.
    
    This model extends the standard Odoo product template to support integration
    with Producteca marketplace. It adds functionality to track which products
    are synchronized with Producteca and manages price synchronization.
    
    Business Logic:
    - Tracks whether product template has variants that are Producteca products
    - Provides foundation for price synchronization with Producteca marketplace
    - Manages product lifecycle for marketplace integration
    - Supports batch operations for multiple product variants
    
    Key Features:
    - Automatic detection of Producteca products through variants
    - Price synchronization capabilities (currently commented out)
    - Integration with Producteca product connections
    - Support for marketplace-specific product attributes
    """
    _inherit = 'product.template'

    # Producteca Integration Fields
    is_producteca_product = fields.Boolean(
        string="Is Producteca Product", 
        compute="_compute_is_producteca_product", 
        store=True,
        help="Indicates if this product template has any variants that are synchronized with Producteca marketplace."
    )


    @api.depends('product_variant_ids.is_producteca_product')
    def _compute_is_producteca_product(self):
        """Compute whether this product template has Producteca product variants.
        
        This method checks all product variants of the template to determine if any
        of them are synchronized with Producteca marketplace. If at least one variant
        is a Producteca product, the template is marked as a Producteca product.
        
        The computation is triggered when:
        - Product variants are added or removed
        - Variant Producteca status changes
        - Template variants are modified
        
        Business Logic:
        - Template is considered a Producteca product if ANY variant is a Producteca product
        - Uses efficient any() function for performance with multiple variants
        - Automatically updates when variant status changes
        """
        for template in self:
            template.is_producteca_product = any(
                variant.is_producteca_product 
                for variant in template.product_variant_ids
            )
