#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import urllib.request

base_url = 'https://distribution.dcc-rules.de/'

rules_dir = 'rules/'
if not os.path.exists(rules_dir):
	os.makedirs(rules_dir)
for country in sys.argv[1:]:
	with urllib.request.urlopen(base_url + rules_dir + country, timeout=10) as url:
		for rule in json.loads(url.read().decode()):
			print("Loading rule " + rule['identifier'])
			urllib.request.urlretrieve(base_url + rules_dir + country + '/' + rule['hash'], rules_dir + rule['identifier'])

bnrules_dir = 'bnrules/'
if not os.path.exists(bnrules_dir):
	os.makedirs(bnrules_dir)
with urllib.request.urlopen(base_url + bnrules_dir, timeout=10) as url:
	for bnrule in json.loads(url.read().decode()):
		print("Loading bnrule " + bnrule['identifier'])
		urllib.request.urlretrieve(base_url + bnrules_dir + bnrule['hash'], bnrules_dir + bnrule['identifier'])


valuesets_dir = 'valuesets/'
if not os.path.exists(valuesets_dir):
	os.makedirs(valuesets_dir)
with urllib.request.urlopen(base_url + valuesets_dir, timeout=10) as url:
	for valueset in json.loads(url.read().decode()):
		print("Loading valueset " + valueset['id'])
		urllib.request.urlretrieve(base_url + valuesets_dir + valueset['hash'], valuesets_dir + valueset['id'])


