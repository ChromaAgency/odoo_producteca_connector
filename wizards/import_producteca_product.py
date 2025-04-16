from odoo import models, fields
from odoo.exceptions import UserError

class ProductecaProductsWizard(models.TransientModel):
    _name = 'producteca.products.wizard'
    _description = 'Wizard para obtener productos de Producteca'

    producteca_account_id = fields.Many2one(
        'producteca.account',
        string='Cuenta de Producteca',
        required=True
    )
    search_text = fields.Char(
        string='Texto de búsqueda',
        required=True
    )

    def action_obtain_products(self):
        self.env['producteca.queue'].sudo().create_obtain_from_producteca_queue(self.search_text, self.producteca_account_id)
        if self.producteca_account_id.is_producteca_able_to_create_products:        
            return {'type': 'ir.actions.act_window_close'}
        raise UserError('La cuenta de producteca no tiene permiso de crear productos en Odoo')