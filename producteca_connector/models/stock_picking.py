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
    
    producteca_id = fields.Char(string="Producteca ID")
    producteca_integration_id = fields.Char(string="Producteca Integration ID")


    def write(self, vals):
        res = super(StockPicking, self).write(vals)
        for picking in self:
            if picking.producteca_id and not self.env.context.get("update_from_confirm", False) and any(field in vals for field in PRODUCTECA_FIELDS):
                producteca_dict = {}                
                if "date_done" in vals or "scheduled_date" in vals:
                    producteca_dict["date"] = picking.date_done if picking.state == 'done' else picking.scheduled_date                
                method_dict = {}                
                if "carrier_tracking_ref" in vals:
                    method_dict["trackingNumber"] = picking.carrier_tracking_ref
                    method_dict["trackingUrl"] = ''                
                if "carrier_id" in vals:
                    method_dict["courier"] = picking.carrier_id.name if picking.carrier_id else 'Unknown'                
                if "state" in vals:
                    method_dict["status"] = "Done" if picking.state == 'done' else "PickingPending"                
                if method_dict:
                    producteca_dict["method"] = method_dict
                
                #TODO va  al aqueue
                # Aquí puedes agregar la lógica para enviar este diccionario a Producteca
                # Por ejemplo:
                # self.env['producteca.queue'].create({
                #     'producteca_method': 'update',
                #     'producteca_body': producteca_dict,
                #     'model': 'stock.picking',
                #     'odoo_item_id': picking.id,
                # })

        return res


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"


    def write(self, vals):
        res = super(StockMoveLine, self).write(vals)
        for move_line in self:
            if move_line.picking_id.producteca_id and not self.env.context.get("update_from_confirm", False) and ["qty_done", "product_uom_qty"] in vals:
                producteca_dict = {"products":{
                    "product": move_line.product_id.producteca_connection_ids.producteca_variation_id,
                    "variation": move_line.product_id.producteca_connection_ids.producteca_variation_id,
                    "quantity": move_line.qty_done if move_line.picking.state == 'done' else move_line.product_uom_qty,
                }}
                #TODO ir a la queue

        return res
            # Aquí puedes agregar la lógica para enviar este diccionario a Producteca
                # Por ejemplo:
                # self.env['producteca.queue'].create({
                #     'producteca_method': 'update',
                #     'producteca_body': producteca_dict,
                #     'model': 'stock.picking',
                #     'odoo_item_id': picking.id,
                # })