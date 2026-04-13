from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ProductSubmission(models.Model):
    """
    Designer-submitted product request.
    Flow: draft → submitted (by designer via portal) →
          approved (admin creates product) | rejected (with reason).
    This keeps product creation in admin hands while giving designers
    a self-service intake form.
    """
    _name        = 'product.submission'
    _description = 'Consignment Product Submission'
    _order       = 'create_date desc'
    _rec_name    = 'product_name'
    _inherit     = ['mail.thread', 'mail.activity.mixin']

    designer_id   = fields.Many2one('res.partner', string='Designer', required=True,
        domain=[('is_consignor', '=', True)], ondelete='restrict', tracking=True)
    product_name  = fields.Char(string='Product Name', required=True)
    description   = fields.Text(string='Description')
    suggested_price = fields.Float(string='Suggested Retail Price (₹)', digits=(16, 2))
    category      = fields.Selection([
        ('ethnic',    'Ethnic Wear'),
        ('bridal',    'Bridal & Occasion'),
        ('western',   'Western Wear'),
        ('casual',    'Casual & Street'),
        ('luxury',    'Luxury Designer'),
        ('kids',      'Kids & Teen'),
        ('accessory', 'Accessories'),
    ], string='Category', required=True)
    quantity      = fields.Integer(string='Quantity to Consign', default=1)
    image         = fields.Binary(string='Product Photo')
    image_filename = fields.Char(string='Photo Filename')
    is_eco_certified = fields.Boolean(string='Eco Certified')
    eco_certification_body = fields.Char(string='Certification Body')
    notes         = fields.Text(string='Additional Notes')

    state = fields.Selection([
        ('draft',     'Draft'),
        ('submitted', 'Submitted'),
        ('approved',  'Approved'),
        ('rejected',  'Rejected'),
    ], default='draft', required=True, tracking=True)

    rejection_reason = fields.Text(string='Rejection Reason', tracking=True)
    product_id       = fields.Many2one('product.template', string='Created Product',
        readonly=True, help='Set when admin approves and creates the product.')
    submitted_date   = fields.Datetime(string='Submitted On', readonly=True)
    reviewed_by      = fields.Many2one('res.users', string='Reviewed By', readonly=True)

    def action_submit(self):
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError('Only draft submissions can be submitted.')
            rec.write({'state': 'submitted', 'submitted_date': fields.Datetime.now()})
            rec.message_post(body='Product submission sent for admin review.')

    def action_approve(self):
        """Admin approves: auto-creates the product.template record."""
        self.ensure_one()
        if self.state != 'submitted':
            raise ValidationError('Only submitted requests can be approved.')
        product = self.env['product.template'].create({
            'name':                   self.product_name,
            'description_sale':       self.description or '',
            'list_price':             self.suggested_price,
            'is_consignment':         True,
            'designer_id':            self.designer_id.id,
            'consignment_category':   self.category,
            'is_eco_certified':       self.is_eco_certified,
            'eco_certification_body': self.eco_certification_body or '',
            'image_1920':             self.image,
            'is_storable':            True,
            'sale_ok':                True,
            'purchase_ok':            True,
            'available_in_pos':       True,
            'is_published':           True,
        })
        self.write({
            'state':       'approved',
            'product_id':  product.id,
            'reviewed_by': self.env.uid,
        })
        
        # WOW FACTOR: Automated Inventory integration
        msg_body = f'Approved. Product <b>{product.name}</b> created.'
        if self.quantity > 0:
            picking_type = self.env['stock.picking.type'].search([('code', '=', 'incoming')], limit=1)
            location_src = self.env.ref('stock.stock_location_suppliers', raise_if_not_found=False)
            if picking_type and location_src and product.product_variant_id:
                picking = self.env['stock.picking'].create({
                    'partner_id': self.designer_id.id,
                    'picking_type_id': picking_type.id,
                    'location_id': location_src.id,
                    'location_dest_id': picking_type.default_location_dest_id.id,
                    'origin': f'Consignor Submission: {self.id}',
                })
                self.env['stock.move'].create({
                    'name': product.name,
                    'product_id': product.product_variant_id.id,
                    'product_uom_qty': self.quantity,
                    'product_uom': product.uom_id.id,
                    'picking_id': picking.id,
                    'location_id': location_src.id,
                    'location_dest_id': picking_type.default_location_dest_id.id,
                })
                picking.action_confirm()
                msg_body += f'<br/>Created Inventory Receipt: <a href="#" data-oe-model="stock.picking" data-oe-id="{picking.id}">{picking.name}</a>'

        self.message_post(body=msg_body)

    def action_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Submission',
            'res_model': 'product.submission.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_submission_id': self.id},
        }
