from odoo import models, fields, api
from ..utils.sales_orders.sales_orders import SaleOrder
from ..utils.config.config import ConfigProducteca
from odoo.exceptions import UserError
from ..models.producteca_queue import ACCEPTATION_CODES
import logging
from odoo.tools.safe_eval import safe_eval
_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    producteca_id = fields.Char(string="Producteca ID")
    cart_id = fields.Many2one("sale.order.cart", string="Cart")
    origin_platform = fields.Char(string="Origin Platform")
    invoice_integration_producteca_id = fields.Char(string="Invoice Integration Producteca ID")
    producteca_app_id = fields.Integer(string="Producteca App ID")
    producteca_shipment_data = fields.Text(string="Información del envío")
    producteca_account_id = fields.Many2one('producteca.account', string='Producteca Account')



    def _obtain_carrier_id(self, carrier_name):
        carrier = self.env['delivery.carrier'].search([('name', '=', carrier_name)]).id
        if not carrier:
            carrier = self.env['delivery.carrier'].create({
                'name': carrier_name,
                'product_id': self.env.ref('delivery.product_delivery_standard').id,
            }).id
        return carrier

    def action_confirm(self):
        _ = super().action_confirm()
        for rec in self:
            if rec.producteca_id and rec.picking_ids and rec.producteca_shipment_data:
                self = self.with_context(update_from_confirm=True)
                shipment_data = safe_eval(rec.producteca_shipment_data)
                shipment_per_picking = {shipment.get('method').get('trackingNumber'): shipment for shipment in shipment_data.get('shipments')}
                vals_to_send_to_producteca = []
                for picking in rec.picking_ids:
                    picking.producteca_id = rec.producteca_id
                    picking_data = shipment_per_picking.get(picking.carrier_tracking_ref)
                    if picking_data:
                        products = {picking.product: picking.quantity for picking in picking_data.get('products')}
                        status = picking_data.get('method').get('status')
                        if status == 'Done':
                            for line in picking.move_line_ids:
                                line.qty_done = products.get(line.product_id.producteca_connection_ids.filtered(lambda x: x.producteca_account_id == rec.producteca_account_id).producteca_id)
                            picking._action_confirm()
                            picking.date_done = picking_data.get('method').get('date')
                        else:
                            for line in picking.move_line_ids:
                                line.product_uom_qty = products.get(line.product_id.producteca_connection_ids.filtered(lambda x: x.producteca_account_id == rec.producteca_account_id).producteca_id)
                            picking.scheduled_date = picking_data.get('method').get('date')
                            picking.carrier_tracking_ref = picking_data.get('method').get('trackingNumber')
                        picking.producteca_integration_id = picking_data.get('integration').get('integrationId')
                        picking.carrier_id = self._obtain_carrier_id(picking_data.get('method').get('courier'))
                    else:
                        producteca_dict = {
                            "date": picking.date_done if picking.state == 'done' else picking.scheduled_date,
                            "method": {
                                "trackingNumber": picking.carrier_tracking_ref,
                                "trackingUrl": '',
                                "courier": picking.carrier_id.name if picking.carrier_id else 'Unknown',
                                "status": "Done" if picking.state == 'done' else "PickingPending",
                            }
                            }
                        product_dict = [
                                {
                                "product": product.producteca_connection_ids.filtered(lambda x: x.producteca_account_id == rec.producteca_account_id).product_id.producteca_id,
                                "variation": product.producteca_connection_ids.filtered(lambda x: x.producteca_account_id == rec.producteca_account_id).variation_id.producteca_id,
                                "quantity": product.qty_done if picking.state == 'done' else product.product_uom_qty,
                                }
                            for product in picking.move_line_ids] 
                        if product_dict:
                            producteca_dict.update({"products": product_dict})
                        vals_to_send_to_producteca.append({
                            "producteca_method": "update",
                            "producteca_body": producteca_dict,
                            "model": "stock.picking",
                            "odoo_item_id": picking.id,
                        })
                if vals_to_send_to_producteca: #TODO process this in the queue, somehow
                    self.env['producteca.queue'].sudo().create(vals_to_send_to_producteca)
        return _
                    
                        
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
    