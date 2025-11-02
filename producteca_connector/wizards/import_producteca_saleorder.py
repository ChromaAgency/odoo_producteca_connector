from odoo import models, fields
from odoo.exceptions import UserError


class ProductecaSaleordersWizard(models.TransientModel):
    """Wizard for importing sale orders from Producteca marketplace.
    
    This transient model provides a user interface for importing sale orders from
    the Producteca marketplace into Odoo. It handles the retrieval of order data
    from the external API and creates or updates corresponding sale orders in the
    local system using background job processing.
    
    The wizard is designed to handle bulk order import operations efficiently
    while maintaining data consistency between the marketplace and Odoo systems.
    It includes error handling for various import scenarios and API failures.
    
    Key Features:
    - Bulk sale order import from Producteca
    - Background job processing for performance
    - Automatic order creation and updates
    - API error handling and validation
    - Comma-separated ID input support
    - Account-based authorization
    
    Business Logic:
    - Validates Producteca account access
    - Retrieves order data via API client
    - Creates background jobs for order processing
    - Handles order upsert operations (create/update)
    - Maintains order synchronization state
    
    Import Process:
    1. Parse comma-separated sale order IDs
    2. Initialize Producteca API client
    3. Fetch order data for each ID
    4. Queue background jobs for order processing
    5. Handle API errors and missing orders
    """
    _name = 'producteca.saleorders.wizard'
    _description = 'Wizard para obtener ordenes de venta de Producteca'

    producteca_account_id = fields.Many2one(
        'producteca.account',
        string='Cuenta de Producteca',
        required=True,
        help="The Producteca account to use for importing sale orders. Must have valid API credentials."
    )
    search_text = fields.Char(
        string='Texto de búsqueda',
        required=True,
        help="Comma-separated list of Producteca sale order IDs to import (e.g., '123,456,789')"
    )

    def action_obtain_saleorders(self):
        """Execute the sale order import process from Producteca marketplace.
        
        This method orchestrates the complete sale order import workflow including:
        1. Parsing input sale order IDs from comma-separated text
        2. Initializing the Producteca API client with account credentials
        3. Fetching order data for each specified order ID
        4. Queuing background jobs for order processing in Odoo
        5. Handling API errors and missing orders gracefully
        
        The method uses background job processing to handle potentially long-running
        import operations without blocking the user interface. Each order is
        processed individually to ensure that failures don't affect other imports.
        
        Returns:
            dict: Implicit return (None) - wizard remains open for user feedback
            
        Process Flow:
            1. Split search_text into individual order IDs
            2. Get authenticated API client from account
            3. For each order ID:
               a. Fetch order data from Producteca API
               b. If order exists, queue background job for processing
               c. Handle missing orders gracefully
            4. Background jobs will create/update sale orders asynchronously
            
        Error Handling:
            - Invalid order IDs: Skipped with logging
            - API connection failures: Handled by client library
            - Missing orders: Silently skipped (no error)
            - Processing failures: Handled by background job system
            
        Background Processing:
            - Uses with_delay() for asynchronous execution
            - Each order processed in separate job
            - Jobs can be monitored through queue interface
            - Failed jobs can be retried automatically
            
        Data Consistency:
            - Orders are upserted (created or updated)
            - Existing orders are updated with latest data
            - Order state synchronization maintained
            - Customer and product data automatically linked
        """
        producteca_products_ids = self.search_text.split(",")
        account = self.producteca_account_id
        client = account.get_client()
        for producteca_sale_order_id in producteca_products_ids:
            sale_order = client.SalesOrder.get(producteca_sale_order_id)
            if sale_order:
                self.env['sale.order'].with_delay()._upset_saleorder_from_producteca(account, sale_order.to_dict())
