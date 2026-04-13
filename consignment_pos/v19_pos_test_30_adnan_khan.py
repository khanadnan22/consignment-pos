print("Renaming Admin User...")
admin_user = env.ref('base.user_admin')
admin_user.write({'name': 'Adnan Khan'})
admin_user.partner_id.write({'name': 'Adnan Khan'})

print("Renaming Company...")
company = env.company
company.write({
    'name': 'Adnan Khan Consignment',
    'website': 'http://localhost:9123/consignment'
})

print("Renaming POS Config...")
pos = env['pos.config'].search([], limit=1)
if pos:
    pos.write({'name': 'Adnan Khan POS'})

env.cr.commit()
print("Everything renamed to Adnan Khan!")
