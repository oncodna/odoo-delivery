import easypost
from odoo.exceptions import AccessError, MissingError
import logging

_logger = logging.getLogger(__name__)


def ep_exception(err):
    """TODO: improve this"""
    error_dic = err.json_body
    msg = error_dic["message"]
    if error_dic.get("errors"):
        msg += ":\n"
        error_list = []
        for error in error_dic['errors']:
            error_list.append('\tField "%s": %s' % (error['field'], error['message']))
        msg += "\n".join(error_list)
    return AccessError(msg)


def ep_call(env, method_name, *args, **kwargs):
    def get_method(method_name):
        res = easypost
        for attr in method_name.split('.'):
            res = getattr(res, attr)
        return res

    easypost.api_key = env.env.user.company_id.easypost_key
    try:
        method = get_method(method_name)
        return method(*args, **kwargs)
    except easypost.Error as e:
        raise ep_exception(e)


class EPRule(object):

    def __init__(self, ep_field, odoo_attr=None, convert_fun=None, required=False):
        self.ep_field = ep_field
        self.odoo_field = odoo_attr or ep_field
        self.convert_fun = convert_fun or (lambda env, x: x)
        self.required = required

    def convert(self, rset, check_missing=False):
        def get_value():
            res = rset
            for attr in self.odoo_attr.split('.'):
                res = getattr(res, attr)
            return res

        res = self.convert_fun(rset, get_value())
        if not res and check_missing:
            raise MissingError('Cannot convert to delivery address: field %s is empty' % self.odoo_field)
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
