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

    update_if_exists = fields.Boolean(string='Actualizar el producto si existe', default=True)

    def action_obtain_products(self):
        producteca_products_ids = self.search_text.split(",")
        connections = self.env['producteca.connections'].sudo().search([('producteca_account_id', '=', self.producteca_account_id.id), ('product_id', 'in', producteca_products_ids)])
        if self.producteca_account_id.is_producteca_able_to_create_products:
            products_to_create = [int(product_id) for product_id in producteca_products_ids if int(product_id) not in connections.mapped('product_id.id')]
            self.env['producteca.queue'].sudo().create_obtain_from_producteca_queue(products_to_create, self.producteca_account_id)
        else:
            raise UserError('La cuenta de producteca no tiene permiso de crear productos en Odoo')
        if connections and not self.update_if_exists:
            raise UserError('Los productos %s ya existen en Odoo con lo que no se importarán',', '.join([str(connection.product_id.name) for connection in connections]))
        if connections and self.update_if_exists:
            products_to_update = [int(product_id) for product_id in producteca_products_ids if int(product_id) in connections.mapped('product_id.id')]
            self.env['producteca.queue'].sudo().create_obtain_from_producteca_queue(products_to_update, self.producteca_account_id)
        return {'type': 'ir.actions.act_window_close'}