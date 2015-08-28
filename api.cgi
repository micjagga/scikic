#!/usr/bin/env python

#import answer_where

"""Example queries:

#An inference request
import requests
data = [{'dataset':'postcode','dataitem':'postcode','detail':'','answer':'s63af'}]
payload = {"version":1, 'data': data, 'apikey': 'YOUR_API_KEY_HERE', 'action':'inference'}
r = requests.post('http://scikic.org/api/api.cgi',json=payload)

#Getting the question string
#data = {'dataset':'postcode','dataitem':'postcode','detail':''}
#payload = {"version":1, 'data': data, 'apikey': 'YOUR_API_KEY_HERE', 'action':'questionstring'}

#
#http://scikic.org/api/api.cgi?apikey=xxxxxxxx&action=inference&version=1&json=[{"dataset":"postcode","dataitem":"postcode","detail":"","answer":"S63AF"}]
#http://scikic.org/api/api.cgi?apikey=xxxxxxxx&action=question&version=1&json=[{"dataset":"postcode","dataitem":"postcode","detail":"","answer":"S63AF"}]
#http://scikic.org/api/api.cgi?{"apikey":"xxxxxxxx","action":"questionstring","version":1,"data":[]}   "dataset":"postcode","dataitem":"postcode","detail":""]
"""

import json
import cgi
from sys import exit
import inference

import config
import logging
logging.basicConfig(filename=config.loggingFile,level=logging.DEBUG)


#checks data is a dictionary with correct fields.
def check_format(item):
    if not isinstance(item,dict):
        print "Incorrect structure for this action."
        exit()
    if 'dataset' not in item:
        print "Missing dataset"
        exit()
    if 'dataitem' not in item:
        print "Missing dataitem"
        exit()
    if 'detail' not in item:
        print "Missing detail"
        exit()
#    if 'answer' not in it: #TODO Confirm things work if answer left out
#        print "Missing answer"
#        exit()


import numpy as np
#We need to json things like the 'facts' dictionary, but json breaks on np.arrays, so this converts them to python arrays.
def recursive_numpy_array_removal(arr):
    out = None
    if isinstance(arr,list):
        out = []
        for item in arr:
            out.append(recursive_numpy_array_removal(item))
        return out
    if isinstance(arr,np.ndarray):
       # print "NP ARRAY"
        return recursive_numpy_array_removal(arr.tolist()) #convert to list, and apply fn
    if isinstance(arr,dict):
        out = {}
        for key in arr:
            out[key] = recursive_numpy_array_removal(arr[key])
        return out
    return arr
        

rawform = cgi.FieldStorage().value
print 'Content-Type: text/html\n\n'; #TODO Is the page text/html

try:
    form = json.loads(rawform)
except ValueError:
    print "Invalid JSON" #TODO Set error code header
    exit()
except TypeError:
    print "Missing API query JSON" #TODO Set error code header
    exit()


if not 'apikey' in form:
    print "Please supply a valid API key" #TODO set error code header
    exit() #400 Bad Request: The server cannot or will not process the request due to something that is perceived to be a client error (e.g., malformed request syntax, invalid request message framing, or deceptive request routing).
if not 'action' in form:
    print "Please specify the action to be taken" #TODO set error code header
    exit()
if not 'version' in form:
    print "Please specify the version of the API you want to use" #TODO set error code header
    exit()
if not 'data' in form:
    print "Please supply json data" #TODO set error code header
    exit()


apikey = form['apikey']
action = form['action']
version = form['version']
data = form['data']

datamsg = str(data)
if len(datamsg)>70:
    datamsg = datamsg[0:70]+'...';
logging.info('API Query [%s]: %s' % (action,datamsg))

if (action=='question'):
    if not isinstance(data,dict):
        print "Generating a question requires a dictionary of 'previous_questions', 'unprocessed_questions', 'facts' and 'target'. The 'previous_questions' is a list of dictionaries of previous questions, that you want to avoid asking again. The 'unprocessed_questions' are questions that you've asked already and that haven't been incorporated into the 'facts' dictionary."
        exit()
    if 'previous_questions' in data:
        for it in data['previous_questions']:
            check_format(it)
    if 'unprocessed_questions' in data:
        for it in data['unprocessed_questions']:
            check_format(it)

if (action=='inference') or (action=='getfacts'):
    if not isinstance(data,dict) or 'answers' not in data or 'facts' not in data:
        print "Inference and getfacts require a dictionary of answers and facts."
    if not isinstance(data['answers'],list) or not isinstance(data['facts'],dict):
        print "Inference and getfacts require a dictionary of answers and facts. Answers should be a list. Facts should be a dictionary"
        exit()
    for it in data['answers']:
        check_format(it)

if (action=='questionstring'):
    check_format(data)

if (action=='metadata'):
    if 'dataset' not in data:
        print "Metadata needs dataset to be specified."
        exit()

##Do the actions....
if action=='inference':
    output, facts, insights = inference.do_inference(data['answers'],data['facts'])
    facts = recursive_numpy_array_removal(facts)
    print json.dumps({'features':output,'facts':facts,'insights':insights})

if action=='getfacts':
    facts = data['facts']
    inference.process_answers(data['answers'],facts)
    facts = recursive_numpy_array_removal(facts)
    print json.dumps({'facts':facts})

if action=='question':
    question = inference.pick_question(data)
    print json.dumps(question)

if action=='questionstring':
    question_string = inference.get_question_string(data)
    print json.dumps(question_string)

if action=='metadata':
    metadata = inference.get_meta_data(data)
    print json.dumps(metadata)
