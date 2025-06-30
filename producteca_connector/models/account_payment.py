from odoo import models, fields, api
PRODUCTECA_FIELDS = ['date', 'amount', 'journal', 'state']

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    producteca_payment_id = fields.Char(string='Producteca Payment ID')
    producteca_account_id = fields.Many2one('producteca.account', string='Producteca Account')

    def _upsert_payment_in_producteca(self, account, producteca_body):
        client = account.get_client()
        sale_order_id = int(producteca_body.pop('producteca_sale_order_id'))
        producteca_sale_order = client.SalseOrder(id=sale_order_id)
        if self.producteca_payment_id:
            producteca_sale_order.update_payment(self.producteca_payment_id, producteca_body)
        return producteca_sale_order.add_payment(producteca_body)

    @api.model
    def create(self, vals):
        created_payments = super(AccountPayment, self).create(vals)
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
                    payment._upsert_payment_in_producteca(invoice.producteca_account_id, producteca_payment_data)
        return created_payments

    def write(self, vals):
        result = super(AccountPayment, self).write(vals)
        for payment in self:
            # ! Check this
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
                payment._upsert_payment_in_producteca(invoice.producteca_account_id, producteca_payment_data)
       
        return result
