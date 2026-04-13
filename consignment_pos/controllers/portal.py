from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class ConsignmentPortal(CustomerPortal):


    def _prepare_home_portal_values(self, counters):
        """Add settlement count badge to portal home page."""
        values = super()._prepare_home_portal_values(counters)
        if 'settlement_count' in counters:
            partner = request.env.user.partner_id
            values['settlement_count'] = request.env['settlement.record'].search_count([
                ('designer_id',   '=', partner.id),
                ('state',         'in', ['posted', 'paid']),
                ('portal_published', '=', True),
            ])
        return values

    @http.route('/my/settlements', type='http', auth='user', website=True)
    def portal_my_settlements(self, page=1, **kw):
        """List view of the designer's settlements."""
        partner  = request.env.user.partner_id
        domain   = [
            ('designer_id',      '=', partner.id),
            ('state',            'in', ['posted', 'paid']),
            ('portal_published',  '=', True),
        ]
        Settlement = request.env['settlement.record']
        settlement_count = Settlement.search_count(domain)

        pager_vals = portal_pager(
            url='/my/settlements',
            total=settlement_count,
            page=page,
            step=10,
        )
        settlements = Settlement.search(
            domain, limit=10,
            offset=pager_vals['offset'],
            order='period_start desc',
        )
        return request.render('consignment_pos.portal_my_settlements', {
            'settlements':      settlements,
            'page_name':        'settlement',
            'pager':            pager_vals,
            'default_url':      '/my/settlements',
        })

    @http.route('/my/settlements/<int:settlement_id>', type='http', auth='user', website=True)
    def portal_settlement_detail(self, settlement_id, **kw):
        """Detail view of a single settlement."""
        partner    = request.env.user.partner_id
        settlement = request.env['settlement.record'].search([
            ('id',               '=', settlement_id),
            ('designer_id',      '=', partner.id),
            ('portal_published',  '=', True),
        ], limit=1)
        if not settlement:
            return request.not_found()
        return request.render('consignment_pos.portal_settlement_detail', {
            'settlement': settlement,
            'page_name':  'settlement',
        })

    # ── Designer Bio Edit ──────────────────────────────────────────────────────

    @http.route('/my/designer-profile', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def portal_designer_profile(self, **kw):
        """
        GET  — renders the bio edit form pre-filled with the designer's current data.
        POST — validates and saves website_description, designer_specialty,
               and website_published. Only the logged-in partner's own record
               is written; no privilege escalation is possible.
        """
        partner = request.env.user.partner_id

        # Only consignors have a profile to edit
        if not partner.is_consignor:
            return request.redirect('/my')

        error = None
        success = False

        if request.httprequest.method == 'POST':
            specialty    = kw.get('designer_specialty', '').strip()
            bio          = kw.get('website_description', '').strip()
            published    = bool(kw.get('website_published'))

            # Basic length guard — bio is HTML so check stripped plain length
            import re as _re
            plain_bio = _re.sub(r'<[^>]+>', '', bio)
            if len(plain_bio) > 2000:
                error = 'Bio is too long (max 2000 characters).'
            else:
                # sudo() is safe here — we are writing ONLY to the authenticated
                # user's own partner record and ONLY the three allowed fields.
                partner.sudo().write({
                    'designer_specialty':  specialty,
                    'website_description': bio,
                    'website_published':   published,
                })
                success = True

        return request.render('consignment_pos.portal_designer_profile', {
            'partner':   partner,
            'page_name': 'designer_profile',
            'error':     error,
            'success':   success,
        })
