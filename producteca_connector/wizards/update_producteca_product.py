# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class UpdateProductecaProduct(models.TransientModel):
    """Wizard to update product information in Producteca marketplace.
    
    This wizard allows users to manually trigger an update of product data
    from Odoo to Producteca. It handles multiple account selection and 
    provides warnings about data overwriting.
    """
    _name = 'update.producteca.product'
    _description = 'Update Product in Producteca'

    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product Template',
        required=True,
        readonly=True,
        help="Product template to update in Producteca."
    )
    account_ids = fields.Many2many(
        'producteca.account',
        string='Producteca Accounts',
        required=True,
        help="Select one or more Producteca accounts where this product will be updated."
    )
    warning_message = fields.Html(
        string='Warning',
        readonly=True,
        default=lambda self: """
            <div style="padding: 10px; background-color: #fff3cd; border: 1px solid #ffc107; border-radius: 4px;">
                <p style="margin: 0; color: #856404; font-weight: bold;">⚠️ CUIDADO!</p>
                <p style="margin: 10px 0 0 0; color: #856404;">
                    Esta acción sobreescribirá la información existente en Producteca 
                    sobre este producto y sus variantes. ¿Desea continuar?
                </p>
            </div>
        """
    )

    def action_update_product(self):
        """Execute the product update in selected Producteca accounts.
        
        This method queues update jobs for each selected account.
        """
        self.ensure_one()
        
        if not self.account_ids:
            raise UserError("Debe seleccionar al menos una cuenta de Producteca.")
        
        template = self.product_tmpl_id
        
        if not template.producteca_connection_ids:
            raise UserError(
                "Este producto no tiene conexiones con Producteca. "
                "Use el proceso de creación en su lugar."
            )
        
        for account in self.account_ids:
            template._update_product_in_producteca(account)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Actualización en Cola',
                'message': f'Se ha encolado la actualización del producto en {len(self.account_ids)} cuenta(s).',
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
