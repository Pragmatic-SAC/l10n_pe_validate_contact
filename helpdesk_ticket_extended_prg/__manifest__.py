# -*- coding: utf-8 -*-
{
    'name': "helpdesk_ticket_extended_prg",

    'summary': """
        Ticket required and not allowing adding hours in presale """,

    'description': """
        Ticket required and not allowing adding hours in presale
    """,

    'author': "PRAGMATIC S.A.C.",
    'website': "https://pragmatic.com.pe/",

    # Categories can be used to filter modules in modules listing
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    "depends": [
        "project",
        "helpdesk_timesheet",
    ],

    # always loaded
    'data': [
        'views/views.xml',

    ],


}
