from odoo import models, fields, api
from odoo.tools.translate import html_translate


class ResPartner(models.Model):
    """
    Week 1-2: Extended res.partner with consignor fields.
    Week 8: Added website_published, website_description, website_slug
    for designer public profile pages on the Odoo Website frontend.
    """
    _inherit = 'res.partner'

    # ── Core consignor fields (Week 1) ────────────────────────────────────────
    is_consignor     = fields.Boolean(string='Is Consignor / Designer', default=False)
    commission_rate  = fields.Float(string='Default Commission Rate (%)', digits=(5, 2))
    consignment_date = fields.Date(string='Consignment Start Date')

    # ── Week 8: Website fields ────────────────────────────────────────────────
    website_published = fields.Boolean(
        string='Published on Website',
        default=False,
        help='When True, this designer has a public profile page on the website.',
    )
    website_description = fields.Html(
        string='Designer Bio (Website)',
        sanitize=True,
        translate=html_translate,
        help='Rich text bio displayed on the designer public profile page.',
    )
    designer_specialty = fields.Char(
        string='Specialty / Style',
        help='Short descriptor shown on designer cards. E.g. "Ethnic Wear", "Bridal Couture".',
    )
    website_product_count = fields.Integer(
        string='Active Products on Website',
        compute='_compute_website_product_count',
        help='Number of published consignment products for this designer.',
    )

    @api.depends('is_consignor')
    def _compute_website_product_count(self):
        for partner in self:
            if partner.is_consignor:
                partner.website_product_count = self.env['product.template'].search_count([
                    ('designer_id',    '=', partner.id),
                    ('is_consignment', '=', True),
                    ('is_published', '=', True),
                ])
            else:
                partner.website_product_count = 0

    designer_type = fields.Selection([
        ('individual',  'Individual Designer'),
        ('shg',         'Self-Help Group (SHG)'),
        ('ngo',         'NGO / Trust'),
        ('cooperative', 'Cooperative'),
    ], string='Designer Type', default='individual',
       help='Classification for commission tier resolution. SHG and NGO types qualify for social equity rates.')

    craft_region_id = fields.Many2one(
        'craft.region', string='Craft Origin Region',
        help='Geographic origin of the designer for the regional craft map.',
    )

    settlement_count = fields.Integer(
        string='Settlement Count',
        compute='_compute_settlements',
    )
    unpaid_commission = fields.Float(
        string='Unpaid Commissions',
        compute='_compute_settlements',
    )

    def _compute_settlements(self):
        for partner in self:
            if partner.is_consignor:
                settlements = self.env['settlement.record'].search([('designer_id', '=', partner.id)])
                partner.settlement_count = len(settlements)
                partner.unpaid_commission = sum(s.payout_amount for s in settlements if s.state in ['draft', 'posted'])
            else:
                partner.settlement_count = 0
                partner.unpaid_commission = 0.0

    def action_view_settlements(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Settlements',
            'res_model': 'settlement.record',
            'view_mode': 'list,form',
            'domain': [('designer_id', '=', self.id)],
            'context': {'default_designer_id': self.id},
        }
