from odoo import models, fields, api
PRODUCTECA_FIELDS = ['date', 'amount', 'journal', 'state']

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    producteca_payment_id = fields.Char(string='Producteca Payment ID')
    producteca_account_id = fields.Many2one('producteca.account', string='Producteca Account')

    def _upsert_payment_in_producteca(self, account, producteca_body):
        client = account.get_client()
        sale_order_id = int(producteca_body.pop('producteca_sale_order_id'))
        producteca_sale_order = client.SalesOrder(id=sale_order_id)
        
        if self.producteca_payment_id:
            result = producteca_sale_order.update_payment(self.producteca_payment_id, producteca_body)
        else:
            result = producteca_sale_order.add_payment(producteca_body)
            if result and hasattr(result, 'id'):
                self.producteca_payment_id = str(result.id)
        
        return result

    @api.model
    def create(self, vals):
        created_payments = super(AccountPayment, self).create(vals)
        for payment in created_payments:
            for invoice in payment.reconciled_invoice_ids:
                if invoice.producteca_order_id and not payment.producteca_payment_id:
                    if not payment.journal_id.producteca_payment_method:
                        continue
                    
                    producteca_payment_data = {
                        'date': payment.date.isoformat() if payment.date else fields.Date.today().isoformat(),
                        'amount': payment.amount,
                        'method': payment.journal_id.producteca_payment_method,
                        'status': 'Approved',
                        'hasCancelableStatus': False,
                        'producteca_sale_order_id': invoice.producteca_order_id,
                    }
                    payment._upsert_payment_in_producteca(invoice.producteca_account_id, producteca_payment_data)
        return created_payments

    def write(self, vals):
        result = super(AccountPayment, self).write(vals)
        for payment in self:
            if payment.producteca_payment_id and any(field in vals for field in PRODUCTECA_FIELDS) and not self.env.context.get("update_from_invoice"):
                invoices_with_producteca = payment.reconciled_invoice_ids.filtered(lambda x: x.producteca_order_id)
                if not invoices_with_producteca:
                    continue
                
                invoice = invoices_with_producteca[0]
                
                if not payment.journal_id.producteca_payment_method:
                    continue
                
                producteca_payment_data = {
                    'date': payment.date.isoformat() if payment.date else fields.Date.today().isoformat(),
                    'amount': payment.amount,
                    'method': payment.journal_id.producteca_payment_method,
                    'status': 'Approved',
                    'hasCancelableStatus': False,
                    'producteca_sale_order_id': invoice.producteca_order_id,
                }
                payment._upsert_payment_in_producteca(invoice.producteca_account_id, producteca_payment_data)
       
        return result
