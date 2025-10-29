# -*- coding: utf-8 -*-
{
    'name': "account_extended_prg",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "PRAGMATIC S.A.C.",
    'website': "https://pragmatic.com.pe/",


    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    "version": "14.0.1.0.0",

    "depends": ["account", "l10n_latam_base"],  # l10n_latam_base opcional pero ayuda con tipos de doc
    "data": [
        "views/res_config_settings_view.xml",
    ],
    "installable": True,
}
