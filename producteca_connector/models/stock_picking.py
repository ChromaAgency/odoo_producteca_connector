from odoo import models, fields
import logging
_logger = logging.getLogger(__name__)

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
    
    def _obtain_carrier_id(self, carrier_name):
        carrier = self.env['delivery.carrier'].search([('name', '=', carrier_name)], limit=1)
        if not carrier:
            delivery_product = self.env['product.product'].create({
                'name': f'Servicio de Entrega: {carrier_name}',
                'type': 'service',
                'invoice_policy': 'order',
            })
            
            carrier = self.env['delivery.carrier'].create({
                'name': carrier_name,
                'product_id': delivery_product.id,
            })
        return carrier.id

    def _process_picking_with_shipment(self, picking_data):
        products = {product_line.get('product'): product_line.get('quantity') for product_line in picking_data.get('products')}
        status = picking_data.get('method').get('status')
        raw_date = picking_data.get('date')
        if raw_date:
            cleaned_date = raw_date.split('.')[0].replace('T', ' ')
            parsed_date = fields.Datetime.to_datetime(cleaned_date)
        else:
            parsed_date = fields.Datetime.now()
        if status == 'Done':
            for line in self.move_line_ids:
                line.qty_done = products.get(line.product_id.producteca_connection_ids.filtered(lambda x: x.producteca_account_id == self.producteca_account_id).producteca_id)
            self.date_done = parsed_date
            self.scheduled_date = parsed_date
            self.action_confirm()
        else:
            for line in self.move_line_ids:
                line.quantity = products.get(line.product_id.producteca_connection_ids.filtered(lambda x: x.producteca_account_id == self.producteca_account_id).producteca_id)
            self.scheduled_date = parsed_date
            self.carrier_tracking_ref = picking_data.get('method').get('trackingNumber')
        if picking_data.get('integration'):
            self.producteca_shipment_id = picking_data.get('integration').get('integrationId')
        if picking_data.get('method'):
            self.carrier_id = self._obtain_carrier_id(picking_data.get('method').get('courier'))

    def _create_producteca_dict_for_picking(self):
        date_value = self.date_done if self.state == 'done' else self.scheduled_date
        content_dict = {
            "date": date_value.isoformat() if date_value else None,
            "method": {
                "trackingNumber": self.carrier_tracking_ref if self.carrier_tracking_ref else '',
                "trackingUrl": '',
                "courier": self.carrier_id.name if self.carrier_id else 'Unknown',
                "status": "Done" if self.state == 'done' else "PickingPending",
            }
        }
        product_dict = [
            {
                "product": line.product_id.producteca_connection_ids.filtered(lambda x: x.producteca_account_id == self.sale_id.producteca_account_id).producteca_id,
                "variation": line.product_id.producteca_connection_ids.filtered(lambda x: x.producteca_account_id == self.sale_id.producteca_account_id).producteca_variation_id,
                "quantity": line.qty_done if self.state == 'done' else line.quantity,
            }
            for line in self.move_line_ids
        ] 
        if product_dict:
            content_dict.update({"products": product_dict})
        return content_dict

    def _update_producteca_shipment(self, producteca_body):
        self.ensure_one()
        if not self.producteca_shipment_id:
            return None
        if not producteca_body:
            return None
        client = self.producteca_account_id.get_client()
        return client.SalesOrder(id=self.sale_id.producteca_id).update_shipment(self.producteca_shipment_id, producteca_body)

    def _create_producteca_shipment(self):
        client = self.producteca_account_id.get_client()
        producteca_body = self._create_producteca_dict_for_picking()
        return client.SalesOrder(id=self.sale_id.producteca_id).add_shipment(producteca_body)

    def write(self, vals):
        res = super(StockPicking, self).write(vals)
        for picking in self:
            # TODO: Check if we can use the _create_producteca_dict_for_picking
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
                picking = picking.with_context(update_from_validate=True)
                for invoice in picking.sale_id.invoice_ids:
                    invoice.with_delay().add_invoice_to_producteca()
    
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
