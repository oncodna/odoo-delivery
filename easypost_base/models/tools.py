# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) OncoDNA <http://www.oncodna.com>
#    See LICENSE file for full copyright and licensing details.
#
##############################################################################

import easypost
from odoo import _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


def ep_convert_dimension(dimension):
    ''' Convert dimension from mm to inches '''
    return round(dimension * 0.0393701, 1)


def ep_convert_weight(weight):
    ''' Convert weight from kg to Oz '''
    res = round(weight * 35.274, 1)
    return max(res, 1) if weight else 0


def ep_exception(err):
    """TODO: improve this"""
    error_dic = err.json_body["error"]
    msg = error_dic["message"]
    if error_dic.get("errors"):
        msg += ":\n"
        error_list = []
        for error in error_dic['errors']:
            error_list.append('\tField "%s": %s' % (error['field'], error['message']))
        msg += "\n".join(error_list)
    return UserError(msg)


def ep_call(env, method_name, *args, **kwargs):
    def get_method(method_name):
        res = easypost
        for attr in method_name.split('.'):
            res = getattr(res, attr)
        return res

    easypost.api_key = env.user.company_id.easypost_key
    try:
        method = get_method(method_name)
        return method(*args, **kwargs)
    except easypost.Error as e:
        raise ep_exception(e)


def ep_exec(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except easypost.Error as e:
        raise ep_exception(e)


def ep_check_shipment_rates(shipment):
    if not shipment.rates:
        error_messages = []
        for msg in shipment.messages:
            if msg.type == "rate_error":
                error_messages.append(msg.message)
        message = _("No rates were received from the carrier.")
        if error_messages:
            message += _(" Errors include:\n\n")
            message += "\n".join(error_messages)
        else:
            message += _("\nHint: check if the package type is compatible with the kind of shipment "
                         "you try to execute")
        raise UserError(message)


class EPRule(object):

    def __init__(self, ep_field, odoo_attr=None, convert_fun=None, required=False):
        self.ep_field = ep_field
        self.odoo_attr = odoo_attr or ep_field
        self.convert_fun = convert_fun or (lambda env, x: x)
        self.required = required

    def convert(self, rset, check_missing=False):
        def get_value():
            val = rset
            for attr in self.odoo_attr.split('.'):
                if attr == "self":
                    break
                val = getattr(val, attr)
            return val

        res = self.convert_fun(rset, get_value())
        if not res and check_missing and self.required:
            field = self.odoo_attr if self.odoo_attr != 'self' else self.ep_field
            message = _('Missing value in {model_name} "{instance_name}": ' \
                        'field "{field}" is mandatory for shipping').format(model_name=rset._description,
                                                                            instance_name=rset.display_name,
                                                                            field=field)
            raise UserError(message)
        return self.ep_field, res


class EPRuleSet(object):

    def __init__(self, *rules):
        self.dict_from = dict((r.ep_field, r) for r in rules)
        self.rules = self.dict_from.values()  # remove duplicates

    def convert(self, rset, check_missing=False):
        res = {}
        for name in self.dict_from:
            field, value = self.dict_from[name].convert(rset, check_missing=check_missing)
            if value:
                res[field] = value
        return res
