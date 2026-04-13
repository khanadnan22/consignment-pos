from odoo import http
from odoo.http import request


class ConsignmentWebsite(http.Controller):
  

    # ── Landing Page ──────────────────────────────────────────────────────────

    @http.route('/consignment', type='http', auth='public', website=True, sitemap=True)
    def consignment_home(self, **kw):
        """
        Public landing page. Shows featured designers and newest products.
        No login required.
        """
        Product  = request.env['product.template'].sudo()
        Partner  = request.env['res.partner'].sudo()

        featured_designers = Partner.search([
            ('is_consignor',     '=', True),
            ('website_published', '=', True)
        ], limit=6, order='id desc')

        # new_arrivals = Product.search([
        #     ('is_consignment',  '=', True),
        #     ('website_published', '=', True),
        # ], limit=8, order='id desc')

        new_arrivals = Product.search([
            ('is_consignment',  '=', True),
            ('is_published',      '=', True),   # Odoo 19 uses is_published not website_published
        ], limit=8, order='id desc')

        return request.render('consignment_pos.website_consignment_home', {
            'featured_designers': featured_designers,
            'new_arrivals':       new_arrivals,
            
        })

    # ── Consignment Shop ──────────────────────────────────────────────────────

    @http.route('/consignment/shop', type='http', auth='public', website=True, sitemap=True)
    def consignment_shop(self, designer_id=None, category=None, search='', page=1, **kw):
        """
        Full product listing page.
        Supports filtering by designer (designer_id param) and
        category (consignment_category param).
        Public access — no login required.
        """
        Product = request.env['product.template'].sudo()
        Partner = request.env['res.partner'].sudo()

        domain = [
            ('is_consignment',  '=', True),
            ('is_published', '=', True),
        ]

        # Filter by designer
        selected_designer = None
        if designer_id:
            try:
                did = int(designer_id)
                domain.append(('designer_id', '=', did))
                selected_designer = Partner.browse(did)
            except (ValueError, TypeError):
                pass

        # Filter by category
        if category:
            domain.append(('consignment_category', '=', category))

        # Search by name
        if search:
            domain.append(('name', 'ilike', search))

        # Pagination
        PPP     = 12   # products per page
        try:
            page = int(page)
        except (ValueError, TypeError):
            page = 1
        offset = (page - 1) * PPP
        total = Product.search_count(domain)

        products = Product.search(domain, limit=PPP, offset=offset, order='id desc')

        # Sidebar data
        all_designers = Partner.search([
            ('is_consignor',     '=', True),
            ('website_published','=', True),
        ], order='name asc')

        categories = [
            ('ethnic',    'Ethnic Wear'),
            ('bridal',    'Bridal & Occasion'),
            ('western',   'Western Wear'),
            ('casual',    'Casual & Street'),
            ('luxury',    'Luxury Designer'),
            ('kids',      'Kids & Teen'),
            ('accessory', 'Accessories'),
        ]

        # Pager info
        shop_pager = {
            'page_count': max(1, -(-total // PPP)),   # ceiling division
            'page':       int(page),
            'total':      total,
        }

        return request.render('consignment_pos.website_consignment_shop', {
            'products':          products,
            'all_designers':     all_designers,
            'categories':        categories,
            'selected_designer': selected_designer,
            'selected_category': category,
            'search':            search,
            'shop_pager':             shop_pager,
        })

    # ── Designers List ────────────────────────────────────────────────────────

    @http.route('/designers', type='http', auth='public', website=True, sitemap=True)
    def designers_list(self, **kw):
        """
        Public page listing all published designer profiles.
        Shows designer name, specialty, bio excerpt, and product count.
        """
        designers = request.env['res.partner'].sudo().search([
            ('is_consignor',     '=', True),
            ('website_published','=', True),
        ], order='name asc')

        return request.render('consignment_pos.website_designers_list', {
            'designers': designers,
        })

    # ── Individual Designer Profile ───────────────────────────────────────────

    @http.route('/designers/<int:designer_id>', type='http', auth='public', website=True, sitemap=False)
    def designer_profile(self, designer_id, category=None, **kw):
        """
        Individual designer public profile page.
        Shows bio, specialty, and all their published consignment products.
        Optional category filter within the designer's products.
        """
        designer = request.env['res.partner'].sudo().browse(designer_id)

        # Security: only show published consignors
        if not designer.exists() or not designer.is_consignor or not designer.website_published:
            return request.not_found()

        product_domain = [
            ('designer_id',    '=', designer.id),
            ('is_consignment', '=', True),
            ('is_published','=', True),
        ]
        if category:
            product_domain.append(('consignment_category', '=', category))

        products = request.env['product.template'].sudo().search(
            product_domain, order='id desc'
        )

        categories = [
            ('ethnic',    'Ethnic Wear'),
            ('bridal',    'Bridal & Occasion'),
            ('western',   'Western Wear'),
            ('casual',    'Casual & Street'),
            ('luxury',    'Luxury Designer'),
            ('kids',      'Kids & Teen'),
            ('accessory', 'Accessories'),
        ]

        return request.render('consignment_pos.website_designer_profile', {
            'designer':          designer,
            'products':          products,
            'categories':        categories,
            'selected_category': category,
        })

    # ── Craft Map & Apply as Designer ─────────────────────────────────────────

    @http.route('/craft-map', type='http', auth='public', website=True, sitemap=True)
    def craft_map(self, **kw):
        """ Render the interactive Indian Craft Region map """
        # We need to provide the 'regions' variable if the XML expects it!
        # The XML expects 'regions' object which has id, name, state, craft_tradition, latitude, longitude, designer_count
        regions = request.env['craft.region'].sudo().search([]) if 'craft.region' in request.env else []
        return request.render('consignment_pos.website_craft_map', {'regions': regions})

    @http.route('/designer/apply', type='http', auth='public', website=True, sitemap=True)
    def designer_apply(self, **kw):
        """ Render the designer application form """
        return request.render('consignment_pos.designer_apply_form', {})

    @http.route('/designer/apply/submit', type='http', auth='public', website=True, csrf=True)
    def designer_apply_submit(self, **kw):
        """ Handle the submission of the application form """
        name = kw.get('name')
        email = kw.get('email')
        phone = kw.get('phone')
        specialty = kw.get('designer_specialty')
        description = kw.get('website_description')
        
        if name and email:
            # Create a prospective partner
            request.env['res.partner'].sudo().create({
                'name': name,
                'email': email,
                'phone': phone,
                'is_consignor': False,  # Pending approval
                'comment': f"Application from {name}.\nType: {kw.get('designer_type')}\nSpecialty: {specialty}\nBio: {description}"
            })
        
        return request.render('consignment_pos.designer_apply_success', {})

from odoo.addons.website.controllers.main import Website

class ConsignmentWebsiteMain(Website):
    @http.route('/', type='http', auth="public", website=True, sitemap=True)
    def index(self, **kw):
        """ Redirect the default Odoo homepage to our custom Consignment landing page """
        return request.redirect('/consignment')
