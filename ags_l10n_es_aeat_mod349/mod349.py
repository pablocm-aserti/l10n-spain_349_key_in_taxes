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
from collections import defaultdict
from openerp import models, api
from openerp.addons.l10n_es_aeat_mod349.models.account_invoice \
    import OPERATION_KEYS
from openerp.addons.l10n_es_aeat_mod349.models.mod349 \
    import _format_partner_vat


class Mod349(models.Model):
    _inherit = "l10n.es.aeat.mod349.report"

    def _create_349_partner_records(self, invoices, partner, operation_key):
        """creates partner records in 349"""
        rec_obj = self.env['l10n.es.aeat.mod349.partner_record']
        partner_country = partner.country_id
        amounts_by_invoice = defaultdict(float)
        for inv in invoices:
            lines = inv.invoice_line.filtered(
                lambda l: any((t.op_key_349 == operation_key
                               for t in l.invoice_line_tax_id)))
            lines_amount = sum([l.price_subtotal for l in lines])
            if inv.company_id.currency_id != inv.currency_id:
                rate = inv.amount_untaxed / inv.cc_amount_untaxed 
                lines_amount = lines_amount / rate
            if inv.type in ('in_refund', 'out_refund'):
                amounts_by_invoice[inv.id] -= lines_amount
            else:
                amounts_by_invoice[inv.id] += lines_amount
        invoice_created = rec_obj.create(
            {'report_id': self.id,
             'partner_id': partner.id,
             'partner_vat': _format_partner_vat(partner_vat=partner.vat,
                                                country=partner_country),
             'operation_key': operation_key,
             'country_id': partner_country.id or False,
             'total_operation_amount': sum(amounts_by_invoice.values())
             })
        # Creation of partner detail lines
        for invoice in invoices:
            detail_obj = self.env['l10n.es.aeat.mod349.partner_record_detail']
            detail_obj.create({'partner_record_id': invoice_created.id,
                               'invoice_id': invoice.id,
                               'amount_untaxed':
                               amounts_by_invoice[invoice.id]})
        return invoice_created

    def _create_349_refund_records(self, refunds, partner, operation_key):
        """Creates restitution records in 349"""
        partner_detail_obj = self.env[
            'l10n.es.aeat.mod349.partner_record_detail']
        obj = self.env['l10n.es.aeat.mod349.partner_refund']
        obj_detail = self.env['l10n.es.aeat.mod349.partner_refund_detail']
        partner_country = partner.country_id
        record = defaultdict(list)
        for refund in refunds:
            # goes around all refunded invoices
            for origin_inv in refund.origin_invoices_ids:
                if origin_inv.state in ('open', 'paid'):
                    # searches for details of another 349s to restore
                    refund_details = partner_detail_obj.search(
                        [('invoice_id', '=', origin_inv.id),
                         ('partner_record_id.operation_key', '=',
                          operation_key)])
                    if refund_details:
                        # creates a dictionary key with partner_record id to
                        # after recover it
                        key = refund_details.partner_record_id
                        record[key].append(refund)
                        break

        # recorremos nuestro diccionario y vamos creando registros
        for partner_rec in record:
            refund_amounts = defaultdict(float)
            total_operation_amount = partner_rec.total_operation_amount
            for refund in record[partner_rec]:
                lines = refund.invoice_line.filtered(
                    lambda l: any((t.op_key_349 == operation_key
                                   for t in l.invoice_line_tax_id)))
                refund_amounts[refund] = sum([l.price_subtotal for l in lines])
                if refund.company_id.currency_id != refund.currency_id:
                    rate = refund.amount_untaxed / refund.cc_amount_untaxed
                    refund_amounts[refund] = refund_amounts[refund] / rate
                total_operation_amount -= refund_amounts[refund]
            record_created = obj.create(
                {'report_id': self.id,
                 'partner_id': partner.id,
                 'partner_vat': _format_partner_vat(
                     partner_vat=partner.vat, country=partner_country),
                 'operation_key': operation_key,
                 'country_id': partner_country.id,
                 'total_operation_amount': total_operation_amount,
                 'total_origin_amount': partner_rec.total_operation_amount,
                 'period_selection': partner_rec.report_id.period_selection,
                 'month_selection': partner_rec.report_id.month_selection,
                 'fiscalyear_id': partner_rec.report_id.fiscalyear_id.id})
            # Creation of partner detail lines
            for refund in record[partner_rec]:
                obj_detail.create(
                    {'refund_id': record_created.id,
                     'invoice_id': refund.id,
                     'amount_untaxed': refund_amounts[refund]})
        return True

    @api.multi
    def calculate(self):
        """Computes the records in report."""
        partner_obj = self.env['res.partner']
        invoice_obj = self.env['account.invoice']
        for mod349 in self:
            # Remove previous partner records and partner refunds in report
            mod349.partner_record_ids.unlink()
            mod349.partner_refund_ids.unlink()
            # Returns all commercial partners
            partners = partner_obj.with_context(active_test=False).search(
                [('parent_id', '=', False)])

            for partner in partners:
                # Invoices
                invoices_total_by_key = invoice_obj._get_invoices_by_type(
                    partner, period_selection=mod349.period_selection,
                    fiscalyear=mod349.fiscalyear_id,
                    period_id=[x.id for x in mod349.period_ids],
                    month=mod349.month_selection)
                for op_key in [x[0] for x in OPERATION_KEYS]:
                    if op_key not in invoices_total_by_key:
                        continue
                    # Separates normal invoices from restitution
                    invoices, refunds = \
                        invoices_total_by_key[op_key].clean_refund_invoices(
                            partner, op_key, fiscalyear=mod349.fiscalyear_id,
                            periods=mod349.period_ids,
                            month=mod349.month_selection,
                            period_selection=mod349.period_selection)
                    if invoices:
                        mod349._create_349_partner_records(invoices, partner,
                                                           op_key)
                    if refunds:
                        mod349._create_349_refund_records(refunds, partner,
                                                          op_key)
        return True

