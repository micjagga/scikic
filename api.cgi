#!/home/compbio-10/anaconda/bin/python

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


rawform = cgi.FieldStorage().value
print 'Content-Type: text/html\n'; #TODO Is the page text/html

try:
    form = json.loads(rawform)
except ValueError:
    print "Invalid JSON" #TODO Set error code header



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
if 'features' in form:
    features = form['features']
else:
    features = None

if (action=='question'):
    if not isinstance(data,list):
        print "Generating a question requires a list of dictionaries of previous questions."
        exit()
    for it in data:
        check_format(it)

if (action=='inference'):
    if not isinstance(data,list):
        print "Inference requires a list of dictionaries."
        exit()
    if features is None:
        print "Inference requires a list of features that need to be acquired as 'features' in the dictionary"
        exit()
    if not isinstance(features,list):
        print "Inference requires features to be a list."
    for it in data:
        check_format(it)
#data should be a single dictionary...
if (action=='questionstring'):
    check_format(data)

##Do the actions....
if action=='inference':
    output = inference.do_inference(data,features)
    print json.dumps(output)

if action=='question':
    question = inference.pick_question(data)
    print json.dumps(question)

if action=='questionstring':
    question_string = inference.get_question_string(data)
    print json.dumps(question_string)

if action=='processanswer':
    data = inference.process_answer(data)
    print json.dumps(data)

if action=='metadata':
    metadata = inference.get_meta_data(data)
    print json.dumps(metadata)
