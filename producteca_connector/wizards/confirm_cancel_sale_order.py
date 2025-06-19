from odoo import models, fields, api
from odoo.exceptions import UserError
from ..utils.sales_orders.sales_orders import SaleOrder
from ..utils.config.config import ConfigProducteca
from ..models.producteca_queue import ACCEPTATION_CODES

class ConfirmCancelSaleOrder(models.TransientModel):
    _name = 'confirm.cancel.sale.order'
    _description = 'Confirm Cancel Sale Order'

    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    warning_message = fields.Text(readonly=True, default="Advertencia: Cancelar esta orden en Producteca puede afectar tu reputación en algunos canales de ventas. ¿Estás seguro de continuar?")

    def action_confirm_cancel(self):
        if not self.sale_order_id:
            raise UserError("No se selecciono una orden")
        connection = self.env['producteca.connections'].sudo().search([('producteca_id', '=', self.sale_order_id.producteca_id)])
        if not connection:
            raise UserError("No se encontro la conexion con Producteca para cancelar la orden")
        config = ConfigProducteca(
            token=connection.producteca_account_id.bearer_token,
            api_key=connection.producteca_account_id.api_key
        )
        response_status, _ = SaleOrder.cancel(config, int(self.sale_order_id.producteca_id))
        if response_status not in ACCEPTATION_CODES:
            raise UserError("No se pudo cancelar la orden en Producteca")
        self.sale_order_id.with_context({'cancel_order_in_producteca': True}).action_cancel()
        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}