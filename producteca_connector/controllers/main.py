from odoo.addons.web.controllers.binary import Binary
from odoo.http import request
from odoo import http
import base64

class ProductecaImageController(Binary):
    @http.route(['/producteca/image/<int:product_id>'], type='http', auth="none", csrf=False)
    def get_product_image(self, product_id, **kw):
        try:
            product = request.env['product.product'].sudo().browse(product_id).exists()
            if not product:
                return request.not_found()
                
            if not product.image_1920:
                return request.not_found()
                
            image_data = base64.b64decode(product.image_1920)
            
            content_type = 'image/jpeg'
            if product.image_1920.startswith(b'\x89PNG'):
                content_type = 'image/png'
            if product.image_1920.startswith(b'GIF8'):
                content_type = 'image/gif'
            
            return request.make_response(
                image_data,
                headers=[
                    ('Content-Type', content_type),
                    ('Cache-Control', 'max-age=31536000'),
                    ('Content-Length', str(len(image_data))),
                ]
            )
        except Exception as e:
            return request.not_found()