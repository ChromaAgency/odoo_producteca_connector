from odoo import models, fields, api
from ..utils.sales_orders.sales_orders import SaleOrder
from ..utils.config.config import ConfigProducteca
from odoo.exceptions import UserError
from ..models.producteca_queue import ACCEPTATION_CODES
import logging
_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    producteca_id = fields.Char(string="Producteca ID")
    cart_id = fields.Many2one("sale.order.cart", string="Cart")
    origin_platform = fields.Char(string="Origin Platform")
    invoice_integration_producteca_id = fields.Char(string="Invoice Integration Producteca ID")
    producteca_app_id = fields.Integer(string="Producteca App ID")
    producteca_shipment_data = fields.Text(string="Información del envío")

    def action_close_order(self):
        connection = self.env['producteca.connections'].sudo().search([('producteca_id', '=', self.producteca_id)])
        if not connection:
            raise UserError("No se encontro la conexion con Producteca para cerrar la orden")
        config = ConfigProducteca(
            token=connection.producteca_account_id.bearer_token,
            api_key=connection.producteca_account_id.api_key
        )
        response_status, _ = SaleOrder.close(config, int(self.producteca_id))
        if response_status not in ACCEPTATION_CODES:
            raise UserError("No se pudo cerrar la orden en Producteca")

    def action_cancel(self):
        if self.producteca_id and not self.env.context.get('cancel_order_in_producteca', False):
            return {
            'name': 'Confirm Cancel Order',
            'type': 'ir.actions.act_window',
            'res_model': 'confirm.cancel.sale.order',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id
            }
        }
        else:
            return super().action_cancel()

    def _create_invoices(self, grouped=False, final=False, date=None):
        moves = super()._create_invoices(grouped=grouped, final=final, date=date)
        invoices_to_queue = []
        for order in self:
            if order.producteca_id:
                for invoice in order.invoice_ids:
                    invoice_dict = {
                        "odoo_item_id":order.id,
                        "model": "account.move",
                        "producteca_method": "update",
                        "producteca_body":{
                            "id": int(order.producteca_id),
                            "invoiceIntegration": {
                                "documentUrl": f"{self.env['ir.config_parameter'].sudo().get_param('web.base.url')}/facturas/{invoice.id}/{invoice.access_token}/factura_producteca.pdf",
                                "integrationId": order.invoice_integration_producteca_id,
                                "app": order.producteca_app_id,
                            }
                        }
                    }
                    invoices_to_queue.append(invoice_dict)
        if invoices_to_queue:
            self.env['producteca.queue'].sudo().create(invoices_to_queue)
        return moves
    
    def write(self, vals):
        _ = super().write(vals)
        for rec in self:
            if rec.producteca_id and ('note' in vals or 'tag_ids' in vals) and not self.env.context.get('creation_from_queue', False):
                connection = self.env['producteca.connections'].sudo().search([('producteca_id', '=', rec.producteca_id)])
                if not connection:
                    raise UserError("No se encontro la conexion con Producteca para cerrar la orden")
                config = ConfigProducteca(
                    token=connection.producteca_account_id.bearer_token,
                    api_key=connection.producteca_account_id.api_key
                )
                update_dict = {
                    "id": int(rec.producteca_id),
                    "note": rec.note if 'note' in vals else None,
                    "tags": [tag.name for tag in rec.tag_ids] if 'tag_ids' in vals else None
                }
                sale_order = SaleOrder(config=config, **update_dict)
                response_status, _ = sale_order.synchronize(config, sale_order)
                if response_status not in ACCEPTATION_CODES:
                    raise UserError("No se pudo actualizar la orden en Producteca")
        return _

class SaleOrderCart(models.Model):
    _name = "sale.order.cart"
    _description = "Sale Order Cart"
    _rec_name = "producteca_id"

    producteca_id = fields.Char(string="Producteca ID")
    order_ids = fields.One2many("sale.order", "cart_id", string="Orders")
    