from odoo import models, fields, api


class PosOrderLine(models.Model):

    _inherit = 'pos.order.line'

    is_consignment_line = fields.Boolean(
        string='Consignment Line',
        compute='_compute_consignment_fields',
        store=True,
    )
    designer_id = fields.Many2one(
        'res.partner',
        string='Designer (Consignment)',
        compute='_compute_consignment_fields',
        store=True,
    )
    payout_line_amount = fields.Float(
        string='Designer Payout (Line)',
        compute='_compute_consignment_fields',
        store=True,
        digits=(16, 2),
    )

    @api.depends('price_subtotal', 'product_id')
    def _compute_consignment_fields(self):
        today = fields.Date.today()
        for line in self:
            tmpl = line.product_id.product_tmpl_id
            if not tmpl.is_consignment or not tmpl.designer_id:
                line.is_consignment_line = False
                line.designer_id         = False
                line.payout_line_amount  = 0.0
                continue
                
            line.is_consignment_line = True
            line.designer_id         = tmpl.designer_id

            designer = tmpl.designer_id

            # Priority 1: date-filtered commission.config override
            config = self.env['commission.config'].search([
                ('designer_id', '=', designer.id),
                '|', ('date_from', '=', False), ('date_from', '<=', today),
                '|', ('date_to',   '=', False), ('date_to',   '>=', today),
            ], limit=1)

            if config:
                rate = config.commission_percentage
            elif designer.designer_type in ('shg', 'ngo', 'cooperative'):
                # Priority 2: SHG / social-equity tier — 10 % commission → 90 % payout
                rate = 10.0
            else:
                # Priority 3: designer-level default rate
                rate = designer.commission_rate

            line.payout_line_amount = line.price_subtotal * (1 - rate / 100.0)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    has_consignment = fields.Boolean(
        string='Has Consignment Items',
        compute='_compute_has_consignment',
        store=True,
    )

    @api.depends('lines.is_consignment_line')
    def _compute_has_consignment(self):
        for order in self:
            order.has_consignment = any(l.is_consignment_line for l in order.lines)
