from odoo import models, fields, api
from odoo.exceptions import UserError


class ConfirmCancelSaleOrder(models.TransientModel):
    _name = 'confirm.cancel.sale.order'
    _description = 'Confirm Cancel Sale Order'

    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    warning_message = fields.Text(readonly=True, default="Advertencia: Cancelar esta orden en Producteca puede afectar tu reputación en algunos canales de ventas. ¿Estás seguro de continuar?")

    def action_confirm_cancel(self):
        if not self.sale_order_id:
            raise UserError("No se selecciono una orden")
        client = self.sale_order_id.produceteca_account_id
        client.SalesOrder(id=self.sale_order_id.producteca_id).cancel()
        self.sale_order_id.with_context({'cancel_order_in_producteca': True}).action_cancel()
        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}