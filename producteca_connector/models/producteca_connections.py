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


    def _sync_description_product(self, account_data, product_dict):
        """Synchronize product description to Producteca marketplace.
        
        This method is executed in a queue to asynchronously synchronize
        product descriptions from Odoo to the Producteca marketplace using
        the Producteca API.
        
        Args:
            account_data (dict): Account authentication data containing:
                - bearer_token (str): Bearer token for API authentication
                - api_key (str): API key for marketplace access
                - create_if_dosnt_exist (bool): Create product if not exists
            product_dict (dict): Product data to synchronize containing:
                - sku (str): Product SKU/reference
                - notes (str): Product description/notes
                
        Business Logic:
        - Builds authenticated headers for API requests
        - Formats product data according to API requirements  
        - Logs synchronization operations for debugging
        - Handles HTML content in descriptions
        
        Note: API call is currently commented out for development/testing.
        """
        headers = {
            "Authorization": f"Bearer {account_data['bearer_token']}",
            "x-api-key": account_data['api_key'],
            "Content-Type": "application/json",
            "createifitdoesntexist": str(account_data['create_if_dosnt_exist']).lower()
        }
        _logger.info(f"product dict to sync description: {product_dict}")
        
        

    def fix_producteca_descriptions(self):
        """Fix and synchronize all product descriptions to Producteca.
        
        This method performs a bulk operation to synchronize all product
        descriptions from connected Odoo templates to their corresponding
        Producteca marketplace products. It processes all active connections
        and queues description updates.
        
        Returns:
            bool: True when operation is completed successfully
            
        Business Logic:
        - Searches all active product connections (one per variant)
        - Groups by template (since description is at template level in Producteca)
        - Takes one variant with SKU per template to send the update
        - Description comes from template (notes is at product level in Producteca)
        - Converts Markup descriptions to string format
        - Preserves HTML formatting in descriptions
        - Queues each update for asynchronous processing
        - Uses delay() for background processing to avoid blocking
        
        Performance Considerations:
        - Processes all connections in single query
        - Uses queued jobs to prevent timeout issues
        - Maintains database transaction integrity
        - Supports large-scale bulk operations
        
        Usage:
        Typically called manually or via cron job to sync descriptions:
        - After bulk product imports
        - When descriptions are updated in batch
        - During marketplace reconciliation processes
        """
        connections = self.env['producteca.product.connections'].sudo().search([])
        
        templates_processed = set()
        
        for connection in connections:
            template = connection.product_tmpl_id
            
            if not template or template.id in templates_processed:
                continue
            
            if not template.description:
                templates_processed.add(template.id)
                continue
            
            variant = connection.product_id
            if not variant or not variant.default_code:
                _logger.warning(f"Connection for template {template.name} has no variant with SKU. Skipping description sync.")
                templates_processed.add(template.id)
                continue
            
            account = connection.producteca_account_id
            description_text = str(template.description)
            
            account_data = {
                'api_key': account.api_key,
                'bearer_token': account.bearer_token,
                'create_if_dosnt_exist': account.create_if_dosnt_exist
            }
            product_dict = {
                "sku": variant.default_code,
                "notes": description_text
            }

            self.with_delay()._sync_description_product(account_data, product_dict)
            templates_processed.add(template.id)
            
        return True