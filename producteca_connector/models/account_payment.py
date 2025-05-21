from odoo import models, fields, api
PRODUCTECA_FIELDS = ['date', 'amount', 'journal', 'state']

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    producteca_payment_id = fields.Char(string='Producteca Payment ID')
    
    @api.model
    def create(self, vals):
        created_payments = super(AccountPayment, self).create(vals)
        queue_payments = []
        for payment in created_payments:
            for invoice in payment.reconciled_invoice_ids:
                if invoice.producteca_order_id and not payment.producteca_payment_id:
                    producteca_payment_data = {
                        'date': payment.date,
                        'amount': payment.amount,
                        'method': payment.journal_id.producteca_payment_method,
                        'status': 'Approved',
                        'producteca_sale_order_id': invoice.producteca_order_id.id,
                    }
                    producteca_payment_dict = {
                        "odoo_item_id": payment.id,
                        "model": "account.payment",
                        "producteca_method": "create",
                        "producteca_account_id": invoice.producteca_account_id.id,
                        "producteca_body": producteca_payment_data,
                    }
                    queue_payments.append(producteca_payment_dict)
        if queue_payments:
            self.env['producteca.queue'].sudo().create(queue_payments)
        return created_payments


    def write(self, vals):
        result = super(AccountPayment, self).write(vals)
        queue_payments = []
        for payment in self:
                if payment.producteca_payment_id and any(field in vals for field in PRODUCTECA_FIELDS) and not self.env.context.get("update_from_invoice"):
                    invoice = payment.reconciled_invoice_ids.filtered(lambda x: x.producteca_order_id)[0] if payment.reconciled_invoice_ids.filtered(lambda x: x.producteca_order_id) else False
                    if not invoice:
                        continue
                    producteca_payment_data = {
                        'date': payment.date,
                        'amount': payment.amount,
                        'method': payment.journal_id.producteca_payment_method,
                        'status': 'Approved',
                        'producteca_sale_order_id': invoice.producteca_order_id.id,
                    }
                    producteca_payment_dict ={
                        "odoo_item_id": payment.producteca_payment_id,
                        "model": "account.payment",
                        "producteca_method": "update",
                        "producteca_account_id": invoice.producteca_account_id.id,
                        "producteca_body": producteca_payment_data,
                    }
                    queue_payments.append(producteca_payment_dict)
        if queue_payments:
            self.env['producteca.queue'].sudo().create(queue_payments)
        return result