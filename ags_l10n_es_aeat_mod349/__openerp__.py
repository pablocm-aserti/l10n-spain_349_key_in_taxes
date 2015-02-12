# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Aserti Global Solutions (http://www.aserti.es/).
#
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################

{
    "name": "ASERTI: AEAT Model 349",
    "version": "1.0",
    "author": "Aserti Global Solutions",
    "license": "AGPL-3",
    "category": 'Localisation/Accounting',
    "description": """
Añade a los impuestos la clave operacional del modelo 349 y hace que la declaración tenga
granularidad a nivel de línea de factura en lugar de factura. Una misma factura puede contener
líneas de distinta naturaleza (calve de operación 349) y generará los registros correspondientes para
cada clave en el modelo 349.

TODO:
Hacemos que el módulo tenga en cuenta la fecha de contabilización (añadida en ags_account) en lugar de la de factura
    """,
    "depends": [
        "l10n_es_aeat_mod349",
#         "ags_account",
    ],
    'data': [
        "account_view.xml",
        "account_invoice_view.xml"
    ],
    'installable': True,

}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
