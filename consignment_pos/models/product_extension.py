from odoo import models, fields, api


class ProductTemplate(models.Model):

    _inherit = 'product.template'

    is_consignment       = fields.Boolean('Is Consignment Item', default=False)
    designer_id          = fields.Many2one('res.partner', string='Designer',
        domain=[('is_consignor', '=', True)],
        help='The consigning designer who owns this product.')
    consignment_date_in  = fields.Date('Date Received')
    consignment_category = fields.Selection([
        ('ethnic',    'Ethnic Wear'),
        ('bridal',    'Bridal & Occasion'),
        ('western',   'Western Wear'),
        ('casual',    'Casual & Street'),
        ('luxury',    'Luxury Designer'),
        ('kids',      'Kids & Teen'),
        ('accessory', 'Accessories'),
    ], string='Consignment Category')
    designer_tag = fields.Char(
        string='Designer Tag', compute='_compute_designer_tag', store=True)

    # Week 9: low stock threshold
    low_stock_threshold = fields.Integer(
        string='Low Stock Alert Threshold',
        default=2,
        help='Send low-stock alert email when qty_available drops to or below this value.',
    )
    low_stock_alert_sent = fields.Boolean(
        string='Low Stock Alert Sent',
        default=False,
        help='Prevents duplicate alert emails. Reset when stock is replenished.',
    )

    @api.depends('designer_id', 'is_consignment')
    def _compute_designer_tag(self):
        for p in self:
            p.designer_tag = (
                p.designer_id.name
                if p.is_consignment and p.designer_id else ''
            )

    @api.model
    def check_low_stock_and_alert(self):
        """
        Week 9: Low Stock Alert cron method.
        Searches for consignment products where:
          qty_available <= low_stock_threshold
          AND low_stock_alert_sent = False
        Sends one email to admin + one to designer, then flags alert as sent.
        Flag is reset to False when product is restocked (qty > threshold).
        """
        low_products = self.search([
            ('is_consignment',       '=', True),
            ('active',                 '=', True),
            ('low_stock_alert_sent', '=', False),
        ]).filtered(lambda p: p.qty_available <= p.low_stock_threshold)

        if not low_products:
            return

        tmpl = self.env.ref(
            'consignment_pos.email_template_low_stock', raise_if_not_found=False)

        for product in low_products:
            if tmpl:
                tmpl.send_mail(product.id, force_send=True)
            product.low_stock_alert_sent = True

        # Reset flag for restocked products
        restocked = self.search([
            ('is_consignment',       '=', True),
            ('low_stock_alert_sent', '=', True),
        ]).filtered(lambda p: p.qty_available > p.low_stock_threshold)
        restocked.write({'low_stock_alert_sent': False})

    is_eco_certified = fields.Boolean(
        string='Eco Certified',
        default=False,
        help='Mark True if this product holds eco-certification (GOTS, Oeko-Tex, Khadi Mark, etc.).',
    )
    eco_certification_body = fields.Char(
        string='Certification Body',
        help='Name of the certifying organisation. E.g. GOTS, Oeko-Tex, Khadi Mark.',
    )
