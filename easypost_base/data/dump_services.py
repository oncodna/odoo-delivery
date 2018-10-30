# -*- coding: utf-8 -*-
"""Dumps data from services.htm to a dictionary in services.py"""
from lxml import etree
import pprint

res = {}

parser = etree.XMLParser(recover=True)
root = etree.parse("services.htm", parser=parser).getroot()


for div in root.iter('div'):
    carrier = None
    for classname in div.get('class').split(' '):
        if classname.startswith('carrier-'):
            carrier = "-".join(classname.split("-")[1:])
    if carrier:
        ul_node = div.find('ul')
        services = []
        for li_node in (ul_node.getchildren() if ul_node else []):
            services.append(li_node.text.strip())
        res[carrier] = services


with open("services.py", "w") as out_file:
    out_file.write(pprint.pformat(res))
