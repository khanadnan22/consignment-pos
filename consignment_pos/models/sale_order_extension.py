from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):

    _inherit = 'sale.order.line'

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

    @api.depends('product_id', 'price_subtotal')
    def _compute_consignment_fields(self):
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
            today    = fields.Date.today()

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


class SaleOrder(models.Model):
    """
    Week 9: Track consignment-related sale orders for easy filtering.
    has_consignment is a stored computed flag so we can search
    efficiently: ('has_consignment', '=', True)
    """
    _inherit = 'sale.order'

    has_consignment = fields.Boolean(
        string='Has Consignment Items',
        compute='_compute_has_consignment',
        store=True,
    )

    @api.depends('order_line.is_consignment_line')
    def _compute_has_consignment(self):
        for order in self:
            order.has_consignment = any(
                l.is_consignment_line for l in order.order_line
            )
