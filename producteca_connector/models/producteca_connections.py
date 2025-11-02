from odoo import models, fields, api
from odoo.tools.translate import _
import logging
_logger = logging.getLogger(__name__)
import requests


class ProductecaConnections(models.Model):
    """Product connection management for Producteca marketplace integration.
    
    This model manages the relationships between Odoo products and their
    corresponding entities in the Producteca marketplace. It handles the
    mapping between local products and external marketplace products,
    including variations and synchronization.
    
    Business Logic:
    - Links Odoo products to Producteca marketplace products
    - Manages product variations and their IDs
    - Handles product description synchronization
    - Provides queued operations for marketplace sync
    - Maintains connection status and metadata
    
    Key Features:
    - Product-to-marketplace mapping
    - Variation ID management
    - Asynchronous description synchronization
    - Bulk operation support
    - Connection status tracking
    """
    _name = 'producteca.product.connections'
    _description = 'Producteca Product Connections'
    
    # Connection Configuration Fields
    producteca_account_id = fields.Many2one(
        'producteca.account', 
        string='Producteca Account', 
        required=True,
        help="Producteca account this connection belongs to. Defines authentication and sync settings."
    )
    product_id = fields.Many2one(
        'product.product', 
        string='Product',
        help="Odoo product linked to this Producteca marketplace product."
    )
    producteca_variation_id = fields.Char(
        string='Producteca Variation ID',
        help="Unique identifier for the product variation in Producteca marketplace."
    )
    producteca_id = fields.Char(
        string='Producteca ID', 
        required=True,
        help="Unique identifier for the product in Producteca marketplace."
    )
    active = fields.Boolean(
        string='Active', 
        default=True,
        help="Indicates if this connection is active and should be used for synchronization."
    )


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
        # API call commented out for development
        #result = requests.post("https://api-external.producteca.com/products/synchronize", headers=headers, json=product_dict)
        #_logger.info(f"Sync description result: {result}")

    def fix_producteca_descriptions(self):
        """Fix and synchronize all product descriptions to Producteca.
        
        This method performs a bulk operation to synchronize all product
        descriptions from connected Odoo products to their corresponding
        Producteca marketplace entries. It processes all active connections
        and queues description updates.
        
        Returns:
            bool: True when operation is completed successfully
            
        Business Logic:
        - Searches all active product connections
        - Filters products that have descriptions
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
        for connection in connections:
            product = connection.product_id
            account = connection.producteca_account_id
            if not product.description:
                continue
            
            # Convert Markup to string while preserving HTML formatting
            description_text = str(product.description)
            
            account_data = {
                'api_key': account.api_key,
                'bearer_token': account.bearer_token,
                'create_if_dosnt_exist': account.create_if_dosnt_exist
            }
            product_dict = {
                "sku": product.default_code,
                "notes": description_text
            }

            self.with_delay()._sync_description_product(account_data, product_dict)
        return True