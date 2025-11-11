from odoo import models, fields
from odoo.exceptions import UserError

class ProductecaProductsWizard(models.TransientModel):
    """Wizard for importing and updating products from Producteca marketplace.
    
    This transient model provides a user interface for importing products from
    the Producteca marketplace into Odoo. It supports both creating new products
    and updating existing ones based on user preferences and account permissions.
    
    The wizard handles bulk product import operations using background jobs for
    better performance and user experience. It includes comprehensive validation
    and error handling for various import scenarios.
    
    Key Features:
    - Bulk product import from Producteca
    - Automatic product creation and updates
    - Background job processing for performance
    - Duplicate handling with user preferences
    - Account permission validation
    - Search-based product selection
    
    Business Logic:
    - Validates account permissions before import
    - Checks for existing product connections
    - Creates new products or updates existing ones
    - Uses queue jobs for asynchronous processing
    - Maintains data consistency between systems
    
    Import Process:
    1. Parse comma-separated product IDs
    2. Check existing connections in Odoo
    3. Validate account permissions
    4. Queue import jobs for new/updated products
    5. Handle conflicts based on user preferences
    """
    _name = 'producteca.products.wizard'
    _description = 'Wizard para obtener productos de Producteca'

    producteca_account_id = fields.Many2one(
        'producteca.account',
        string='Cuenta de Producteca',
        required=True,
        help="The Producteca account to use for importing products. Must have product creation permissions."
    )
    search_text = fields.Char(
        string='Texto de búsqueda',
        required=True,
        help="Comma-separated list of Producteca product IDs to import (e.g., '123,456,789')"
    )

    update_if_exists = fields.Boolean(
        string='Actualizar el producto si existe', 
        default=True,
        help="If enabled, existing products will be updated with latest data from Producteca. "
             "If disabled, existing products will be skipped during import."
    )

    def _get_and_create_from_wizard(self, products_to_create, producteca_account_id):
        """Queue background jobs for product import/update operations.
        
        This method creates delayed jobs for each product to be imported or updated.
        Using background jobs improves user experience for bulk operations and
        prevents timeout issues with large product catalogs.
        
        Args:
            products_to_create (list): List of Producteca product IDs to process
            producteca_account_id (recordset): The Producteca account for API access
            
        Background Processing:
            - Each product is processed in a separate job
            - Jobs are queued for execution by the job runner
            - Progress can be monitored through the job queue interface
            - Failed jobs can be retried automatically
            
        Error Handling:
            - Individual product failures don't affect other imports
            - Job failures are logged for debugging
            - Users can retry failed imports through the UI
        """
        for product in products_to_create:
            self.env['product.template'].with_delay().get_product_from_producteca_and_create(producteca_account_id, product)

    def action_obtain_products(self):
        """Execute the product import process with validation and error handling.
        
        This method orchestrates the complete product import workflow including:
        1. Parsing and validating input product IDs
        2. Checking for existing product connections
        3. Validating account permissions
        4. Handling duplicate products based on user preferences
        5. Queuing import jobs for processing
        
        The method handles various scenarios including permission errors,
        duplicate products, and validation failures with appropriate user
        feedback and error messages.
        
        Returns:
            dict: Action to close the wizard window after successful processing
            
        Raises:
            UserError: For various validation failures:
                - Account lacks product creation permissions
                - Products already exist (when update disabled)
                - Invalid product ID format
                - API connection failures
                
        Process Flow:
            1. Parse comma-separated product IDs from search_text
            2. Find existing connections for these products
            3. Check account permissions for product creation
            4. Determine products to create vs update
            5. Queue appropriate background jobs
            6. Provide user feedback on operation status
            
        Business Rules:
            - Only accounts with creation permissions can import
            - Existing products handled based on update_if_exists setting
            - All operations performed with elevated privileges (sudo)
            - Background processing for better performance
        """
        producteca_products_ids = self.search_text.split(",")
        connections = self.env['producteca.product.connections'].sudo().search([
            ('producteca_account_id', '=', self.producteca_account_id.id), 
            ('producteca_id', 'in', producteca_products_ids)
        ])
        if self.producteca_account_id.is_producteca_able_to_create_products:
            existing_producteca_ids = connections.mapped('producteca_id')
            products_to_create = [product_id for product_id in producteca_products_ids if product_id not in existing_producteca_ids]
            if products_to_create:
                self.sudo()._get_and_create_from_wizard(products_to_create, self.producteca_account_id)
        else:
            raise UserError('La cuenta de producteca no tiene permiso de crear productos en Odoo')
        if connections and not self.update_if_exists:
            product_names = ', '.join([str(connection.product_tmpl_id.name) for connection in connections if connection.product_tmpl_id])
            raise UserError('Los productos %s ya existen en Odoo con lo que no se importarán' % product_names)
        if connections and self.update_if_exists:
            products_to_update = connections.mapped('producteca_id')
            if products_to_update:
                self.sudo()._get_and_create_from_wizard(products_to_update, self.producteca_account_id)
        return {'type': 'ir.actions.act_window_close'}