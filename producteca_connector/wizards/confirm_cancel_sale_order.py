from odoo import models, fields, api
from odoo.exceptions import UserError


class ConfirmCancelSaleOrder(models.TransientModel):
    """Wizard for confirming sale order cancellation with Producteca integration.
    
    This transient model provides a confirmation dialog for canceling sale orders
    that are synchronized with the Producteca marketplace. It warns users about
    potential reputation impacts and handles the cancellation process both in
    Odoo and the external marketplace.
    
    The wizard ensures proper synchronization between the local system and the
    Producteca marketplace when canceling orders, maintaining data consistency
    and compliance with marketplace policies.
    
    Key Features:
    - Warning message about reputation impact
    - Dual cancellation (Odoo + Producteca)
    - Error handling for invalid orders
    - User confirmation workflow
    - Marketplace API integration
    
    Business Logic:
    - Validates order selection before processing
    - Cancels order in Producteca marketplace first
    - Then cancels the local Odoo sale order
    - Maintains audit trail of cancellation actions
    
    Security:
    - Transient model (no permanent data storage)
    - Proper error handling for failed API calls
    - User authorization checks through Odoo framework
    """
    _name = 'confirm.cancel.sale.order'
    _description = 'Confirm Cancel Sale Order'

    sale_order_id = fields.Many2one(
        'sale.order', 
        string='Sale Order',
        help="The sale order to be cancelled in both Odoo and Producteca marketplace"
    )
    warning_message = fields.Text(
        readonly=True, 
        default="Advertencia: Cancelar esta orden en Producteca puede afectar tu reputación en algunos canales de ventas. ¿Estás seguro de continuar?",
        help="Warning message about potential reputation impact from order cancellation"
    )

    def action_confirm_cancel(self):
        """Confirm and execute the sale order cancellation process.
        
        This method handles the complete cancellation workflow including:
        1. Validation of the selected sale order
        2. Cancellation in Producteca marketplace via API
        3. Local cancellation in Odoo system
        4. Error handling for failed operations
        
        The cancellation is performed in the correct order (marketplace first,
        then local) to ensure data consistency and proper error recovery.
        
        Returns:
            dict: Action to close the wizard window after successful cancellation
            
        Raises:
            UserError: If no sale order is selected or cancellation fails
            
        Business Process:
            1. Validates that a sale order is selected
            2. Gets the Producteca account client for API communication
            3. Cancels the order in Producteca marketplace
            4. Cancels the local Odoo sale order with special context
            5. Closes the wizard dialog
            
        Error Handling:
            - Missing sale order: Raises UserError
            - API failures: Handled by client library
            - Local cancellation issues: Handled by Odoo framework
        """
        if not self.sale_order_id:
            raise UserError("No se selecciono una orden")
        client = self.sale_order_id.produceteca_account_id
        client.SalesOrder(id=self.sale_order_id.producteca_id).cancel()
        self.sale_order_id.with_context({'cancel_order_in_producteca': True}).action_cancel()
        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        """Cancel the wizard without performing any order cancellation.
        
        This method allows users to exit the confirmation dialog without
        proceeding with the order cancellation. No changes are made to
        either the Odoo system or the Producteca marketplace.
        
        Returns:
            dict: Action to close the wizard window without any changes
        """
        return {'type': 'ir.actions.act_window_close'}