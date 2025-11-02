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

    # Price Synchronization Methods (Currently Disabled)
    # The following methods provide price synchronization with Producteca marketplace.
    # They are currently commented out but can be enabled when needed.
    
    # def _update_product_price(self):
    #     """Update product price in Producteca marketplace.
    #     
    #     This method synchronizes the product price from Odoo to Producteca marketplace
    #     using the Producteca API. It handles currency conversion and price list mapping.
    #     
    #     Business Logic:
    #     - Retrieves product connection to Producteca
    #     - Creates authenticated client for API calls
    #     - Formats price data according to Producteca API requirements
    #     - Handles currency and price list mapping
    #     - Respects account configuration for product creation
    #     
    #     Note: Currently commented out due to potential queue duplication issues.
    #     TODO: Investigate and fix the queue generation issue before enabling.
    #     """
    #     # TODO: Check why 3 queues are getting generated
    #     producteca_connection = self.env['producteca.product.connections'].sudo().search([('product_id', '=', self.id)])
    #     client = producteca_connection.producteca_account_id.get_client()
    #     body_dict = {
    #         "code": str(producteca_connection.product_id.id),
    #         "prices": [{"amount": self.list_price, "currency": producteca_connection.product_id.currency_id.name, "priceList": "Default"}]
    #     }
    #     product_service = client.Product
    #     product_service.create_if_it_doesnt_exist = producteca_connection.producteca_account_id.create_if_dosnt_exist
    #     product_service.synchronize(body_dict)

    # def write(self, vals):
    #     """Override write method to trigger price synchronization.
    #     
    #     This method extends the standard write functionality to automatically
    #     synchronize price changes with Producteca marketplace when the list_price
    #     field is modified for Producteca products.
    #     
    #     Args:
    #         vals (dict): Dictionary of field values to update
    #         
    #     Returns:
    #         bool: Result of the parent write operation
    #         
    #     Business Logic:
    #     - Calls parent write method first
    #     - Checks if product is a Producteca product
    #     - Triggers asynchronous price update if list_price changed
    #     - Uses with_delay() for background processing
    #     
    #     Note: Currently commented out to prevent automatic price synchronization.
    #     Enable when price sync requirements are finalized.
    #     """
    #     _ = super().write(vals)
    #     for rec in self:
    #         if rec.is_producteca_product and 'list_price' in vals:
    #             rec.with_delay()._update_product_price()
    #     return _

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