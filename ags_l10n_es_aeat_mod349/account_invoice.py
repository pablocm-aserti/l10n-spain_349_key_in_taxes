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

from openerp import models, fields, api, exceptions, _
from openerp.addons.l10n_es_aeat_mod349.models.account_invoice \
    import OPERATION_KEYS
from datetime import datetime, date
# from collections import defaultdict
import calendar


class account_invoice(models.Model):
    _inherit = 'account.invoice'

    @api.model
    def _get_invoices_by_type(
            self, partner, fiscalyear=None, period_id=None,
            month=None, period_selection=None):
        """
        Returns invoices ids by type (supplier/customer) for a fiscal
        year, period or month.
        """
        assert period_selection, 'There is no period selected'
        # Set type of invoice
        invoice_type = ('in_invoice', 'out_invoice', 'in_refund', 'out_refund')
        domain = [('partner_id', 'child_of', partner.id),
                  ('state', 'in', ['open', 'paid']),
                  ('type', 'in', invoice_type)]

        # Invoices by fiscalyear (Annual)
        if period_selection == '0A':
            if not fiscalyear:
                raise exceptions.Warning(
                    _('Cannot get invoices.\nThere is no fiscal year '
                      'selected'))
            domain.append(('period_id', 'in',
                           [period.id for period in fiscalyear.period_ids
                            if not period.special]))
        # Invoices by period
        elif period_selection in ['1T', '2T', '3T', '4T']:
            if not period_id:
                raise exceptions.Warning(
                    _('Cannot get invoices.\nThere is no period selected'))
            domain.append(('period_id', 'in', period_id))
        # Invoices by month
        else:
            if not month and not fiscalyear:
                raise exceptions.Warning(
                    _('Cannot get invoices.\nThere is no month and/or fiscal '
                      'year selected'))
            month = int(month)
            year = self._get_year_from_fy_month(fiscalyear, month)
            month_last_day = calendar.monthrange(year, month)[1]
            date_start = datetime(year=year, month=month, day=1)
            date_stop = datetime(year=year, month=month, day=month_last_day)
            domain.append(
                ('date_invoice', '>=', fields.Date.to_string(date_start)))
            domain.append(
                ('date_invoice', '<=', fields.Date.to_string(date_stop)))
        all_invoices = self.search(domain)
        invoices_by_key = {}
        cr = self._cr
        if all_invoices:
            for op_key in [x[0] for x in OPERATION_KEYS]:
                cr.execute("""
                    select distinct invoice_id
                    from account_invoice_line invl
                    join account_invoice_line_tax ilt on
                        ilt.invoice_line_id = invl.id
                    join account_tax tax on ilt.tax_id = tax.id
                    where invl.invoice_id in %s and tax.op_key_349 = %s
                """, (all_invoices._ids, op_key))
                inv_ids_by_key = [x[0] for x in cr.fetchall()]
                invoices_by_key[op_key] = self.browse(inv_ids_by_key)
        return invoices_by_key

    def _get_keys_349(self):
        self.ensure_one()
        inv_taxes = set()
        for l in self.invoice_line:
            inv_taxes.update(l.invoice_line_tax_id)
        return set([t.op_key_349 for t in inv_taxes])

    @api.multi
    def clean_refund_invoices(
            self, partner, op_key, fiscalyear=None, periods=None, month=None,
            period_selection=None):
        """Separate refunds from invoices"""
        invoices = self.env['account.invoice']
        refunds = self.env['account.invoice']
        for inv in self:
            if inv.type in ('in_refund', 'out_refund'):
                if not inv.origin_invoices_ids:
                    invoices += inv
                    continue
                for origin_line in inv.origin_invoices_ids:
                    if (origin_line.state in ('open', 'paid') and
                            origin_line.partner_id.commercial_partner_id ==
                            partner):
                        orig_keys = origin_line._get_keys_349()
                        if period_selection == '0A':
                            if (origin_line.period_id.id not in
                                    [period.id for period in
                                     fiscalyear.period_ids if not
                                     period.special]) and \
                                    op_key in orig_keys:
                                refunds += inv
                            else:
                                invoices += inv
                        elif period_selection in ['1T', '2T', '3T', '4T']:
                            if origin_line.period_id not in periods and \
                                    op_key in orig_keys:
                                refunds += inv
                            else:
                                invoices += inv
                        else:
                            month = int(month)
                            year = self._get_year_from_fy_month(fiscalyear,
                                                                month)
                            if (fields.Date.from_string(
                                    origin_line.date_invoice) <
                                    date(year=year, month=month, day=1)) and \
                                    op_key in orig_keys:
                                refunds += inv
                            else:
                                invoices += inv
                        break
            else:
                invoices += inv
        return invoices, refunds


#     def _get_invoices_by_type(self, cr, uid, partner_id, operation_key,
#         fiscalyear_id=None, period_id=None, month=None, period_selection=None, context=None):
#         """
#         Returns invoices ids by type (supplier/customer)
#         for a fiscalyear/period/month
#         """
#         assert period_selection, 'There is no period selected'
# 
#         ## Set type of invoice
#         type = ['in_invoice', 'out_invoice', 'in_refund', 'out_refund']
# 
#         fiscal_y_obj = self.pool.get('account.fiscalyear')
#         fiscalyear_brw = fiscal_y_obj.browse(cr, uid, fiscalyear_id, context=context)
#         search_dict = [
#             ('partner_id', '=', partner_id),
#             ('state', 'in', ['open', 'paid']),
#             ('type', 'in', type),
#             ('operation_key', '=', operation_key)]
# 
#         ##
#         ## Invoices by fiscalyear (Annual)
#         if period_selection == '0A':
#             if not fiscalyear_id:
#                 raise orm.except_orm(_('Error'),
#                                      _('Cannot get invoices.\nThere is no\
#                                      fiscalyear selected'))
# 
#             search_dict.append(('period_id', 'in', [period.id for period in
#                                                     fiscalyear_brw.period_ids
#                                                     if not period.special]))
# 
#         ##
#         ## Invoices by period
#         elif period_selection in ['1T', '2T', '3T', '4T']:
#             if not period_id:
#                 raise orm.except_orm(_('Error'),
#                                      _('Cannot get invoices.\nThere is no \
#                                      period selected'))
# 
#             search_dict.append(('period_id', 'in', period_id))
# 
#         ##
#         ## Invoices by month
#         else:
#             year = fiscalyear_brw.code[:4]
#             if not month and not fiscalyear_id:
#                 raise orm.except_orm(_('Error'),
#                                      _('Cannot get invoices.\nThere is \
#                                      no month and/or fiscalyear selected'))
# 
#             search_dict.append(('date_account',
#                                 '>=',
#                                 MONTH_DATES_MAPPING[month]['date_start'] %
#                                                                         year))
# 
#             if month == '02':
#                 #checks if year is leap to can search
#                 #by last February date in database
#                 if int(year) % 4 == 0 and \
#                 (int(year) % 100 != 0 or int(year) % 400 == 0):
#                     search_dict.append(('date_account',
#                                         '<=', "%s-02-29" % year))
#                 else:
#                     search_dict.append(('date_account',
#                                         '<=',
#                                         MONTH_DATES_MAPPING[month]['date' +
#                                                                    '_stop']
#                                                                    % year))
#             else:
#                 search_dict.append(('date_account',
#                                     '<=',
#                                     MONTH_DATES_MAPPING[month]['date_stop']
#                                     % year))
# 
#         return self.search(cr, uid, search_dict, context=context)
# 
#     def clean_refund_invoices(self, cr, uid, ids, partner_id,
#                               fiscalyear_id=None, period_id=None,
#                               month=None, period_selection=None, context=None):
#         """separates restitution invoices"""
#         invoice_lines = []
#         restitution_lines = []
#         fiscal_y_obj = self.pool.get('account.fiscalyear')
#         fiscalyear_brw = fiscal_y_obj.browse(cr, uid, fiscalyear_id, context=context)
# 
#         for refund in self.browse(cr, uid, ids, context=context):
#             if refund.type in ['in_refund', 'out_refund']:
#                 if not refund.origin_invoices_ids:
#                     invoice_lines.append(refund.id)
#                     continue
#                 for origin_line in refund.origin_invoices_ids:
#                     if origin_line.state in ['open', 'paid'] and \
#                                     origin_line.partner_id.id == partner_id:
#                         if period_selection == '0A':
#                             if origin_line.period_id.id not in \
#                                         [period.id for period in
#                                         fiscalyear_brw.period_ids if not \
#                                         period.special]:
#                                 restitution_lines.append(refund.id)
#                                 break
#                             else:
#                                 invoice_lines.append(refund.id)
#                                 break
#                         elif period_selection in ['1T', '2T', '3T', '4T']:
#                             if origin_line.period_id.id != period_id:
#                                 restitution_lines.append(refund.id)
#                                 break
#                             else:
#                                 invoice_lines.append(refund.id)
#                                 break
#                         else:
#                             if origin_line.date_account < \
#                                     MONTH_DATES_MAPPING[month]['date_start'] \
#                                     % fiscalyear_brw.code[:4]:
#                                 restitution_lines.append(refund.id)
#                                 break
#                             else:
#                                 invoice_lines.append(refund.id)
#                                 break
#             else:
#                 invoice_lines.append(refund.id)
# 
#         return invoice_lines, restitution_lines
