#!/usr/bin/env python
# -*- coding: utf-8 -*-

from mechanize import Browser
import datetime

chantal_url = "http://127.0.0.1:8000/"

browser = Browser()
browser.set_handle_robots(False)

class SixChamberDeposition(object):
    def __init__(self, number, carrier, operator, timestamp=None):
        self.number = deposition_number
        self.carrier = carrier
        self.operator = operator
        self.timestamp = timestamp or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.comments = u""

class SixChamberLayer(object):
    def __init__(self, number, chamber):
        self.number, self.chamber = number, chamber
        self.

def login(name, password):
    browser.open(chantal_url+"login/")
    browser.select_form(nr=0)
    browser["username"] = name
    browser["password"] = password
    browser.submit()

def logout():
    browser.open(chantal_url+"logout/")

def add_layer(deposition):
    browser.open(chantal_url+"edit/6-chamber_deposition/%s"%deposition)
    browser.select_form(nr=0)
    browser["structural-change-add-layers"] = "1"
    browser.submit()
    browser.select_form(nr=0)
    browser["0-chamber"] = ["#4"]
    browser.submit()
    
login("bronger", "*******")
add_layer("01B410")
logout()
