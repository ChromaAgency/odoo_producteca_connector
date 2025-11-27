from odoo import models, fields, api
PRODUCTECA_FIELDS = ['date', 'amount', 'journal', 'state']

ODOO_TO_PRODUCTECA_STATE = {
    'in_process': 'InProcess',
    'paid': 'Approved',
    'canceled': 'Cancelled',
    'rejected': 'Rejected',
}

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    producteca_payment_id = fields.Char(string='Producteca Payment ID')
    producteca_account_id = fields.Many2one('producteca.account', string='Producteca Account')

    def _get_producteca_status(self):
        """Mapea el estado de Odoo al estado de Producteca."""
        self.ensure_one()
        return ODOO_TO_PRODUCTECA_STATE.get(self.state)

    def _prepare_producteca_payment_data(self, invoice):
        """Prepara los datos del pago para enviar a Producteca."""
        self.ensure_one()
        
        data = {
            'date': self.date.isoformat() if self.date else fields.Date.today().isoformat(),
            'amount': self.amount,
            'method': self.journal_id.producteca_payment_method,
            'producteca_sale_order_id': invoice.producteca_order_id,
        }
        
        producteca_status = self._get_producteca_status()
        data['status'] = producteca_status
        data['hasCancelableStatus'] = False if producteca_status == 'Approved' else True
        
        return data

    def _upsert_payment_in_producteca(self, account, producteca_body):
        client = account.get_client()
        sale_order_id = int(producteca_body.pop('producteca_sale_order_id'))
        producteca_sale_order = client.SalesOrder(id=sale_order_id)
        
        if self.producteca_payment_id:
            sale_order_data = producteca_sale_order.get(sale_order_id)
            existing_payment = next(
                (p for p in sale_order_data._record.payments if str(p.id) == str(self.producteca_payment_id)),
                None
            )
            
            if existing_payment and existing_payment.status == 'Approved':
                producteca_body.pop('status', None)
                producteca_body.pop('hasCancelableStatus', None)
            
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
                    
                    producteca_payment_data = payment._prepare_producteca_payment_data(invoice)
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
                
                producteca_payment_data = payment._prepare_producteca_payment_data(invoice)
                payment._upsert_payment_in_producteca(invoice.producteca_account_id, producteca_payment_data)
       
        return result
