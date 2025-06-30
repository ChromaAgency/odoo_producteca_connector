from odoo import models, fields

PRODUCTECA_FIELDS = [
    "date_done",
    "scheduled_date",
    "carrier_tracking_ref",
    "state",
    "carrier_id",
]


class StockPicking(models.Model):
    _inherit = "stock.picking"

    producteca_shipment_id = fields.Char(string="Producteca Shipment ID")
    producteca_account_id = fields.Many2one('producteca.account', string='Producteca Account')

    def _update_producteca_shipment(self, producteca_body):
        self.ensure_one()
        client = self.producteca_account_id.get_client()
        return client.SaleOrder(id=self.sale_id.producte_order_id).update_shipment(self.producteca_shipment_id, producteca_body)

    def _create_producteca_shipment(self, producteca_body):
        # TODO: Check this when refactoring SO
        client = self.producteca_account_id.get_client()
        return client.SaleOrder(id=self.sale_id.producte_order_id).add_shipment(producteca_body)

    def write(self, vals):
        res = super(StockPicking, self).write(vals)
        for picking in self:
            if picking.producteca_shipment_id and any(field in vals for field in PRODUCTECA_FIELDS) and not self.env.context.get("update_from_confirm"):
                producteca_content_dict = {"id": picking.producteca_shipment_id}
                date_to_send = picking.date_done if picking.state == 'done' else picking.scheduled_date
                producteca_content_dict["date"] = date_to_send.isoformat()
                method_dict = {}
                if "carrier_tracking_ref" in vals:
                    method_dict["trackingNumber"] = picking.carrier_tracking_ref
                    method_dict["trackingUrl"] = ''
                if "carrier_id" in vals:
                    method_dict["courier"] = picking.carrier_id.name if picking.carrier_id else 'Unknown'
                if "state" in vals:
                    method_dict["status"] = "Done" if picking.state == 'done' else "PickingPending"
                if method_dict:
                    producteca_content_dict["method"] = method_dict
                self.with_delay()._update_producteca_shipment(producteca_content_dict)
        return res

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        for picking in self:
            if picking.producteca_shipment_id and picking.state == 'done' and not self.env.context.get("update_from_confirm"):
                self = self.with_context(update_from_validate=True)
                self.env['producteca.queue'].create({
                    'producteca_method': 'update',
                    'producteca_body': {"id": picking.sale_id.producteca_id, "invoiceIntegration":{"decreaseStock": True}},
                    'model': 'account.move',
                    'producteca_account_id': picking.sale_id.producteca_account_id.id,
                })
        return res


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def write(self, vals):
        res = super(StockMoveLine, self).write(vals)
        for move_line in self:
            if move_line.picking_id.sale_id.producteca_id and ("qty_done" in vals and "product_uom_qty" in vals) and \
                    not self.env.context.get("update_from_confirm") and not self.env.context.get("update_from_validate"):
                account = move_line.picking_id.sale_id.producteca_account_id
                product_dict = {"products": {
                    "product": move_line.product_id.producteca_connection_ids.filtered(lambda x: x.producteca_account_id == account).producteca_variation_id,
                    "variation": move_line.product_id.producteca_connection_ids.filtered(lambda x: x.producteca_account_id == account).producteca_variation_id,
                    "quantity": move_line.qty_done if move_line.picking.state == 'done' else move_line.product_uom_qty,
                }}
                move_line.picking_id.with_delay()._update_producteca_shipment(product_dict)
        return res
