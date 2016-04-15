import json
import inference
import config
import numpy as np

import logging
from logging import FileHandler

from psych.Extractor import Extractor

from flask import jsonify
from flask import request
from flask import Flask
app = Flask(__name__)

#these three lines are for vasily's change
from datetime import timedelta
from flask import make_response, request, current_app
from functools import update_wrapper


# TO DO, add error handlers http://flask.pocoo.org/docs/0.10/patterns/apierrors/
# TO DO, stop errors showing up on client

file_handler = FileHandler(config.pathToData+'error.log')
file_handler.setLevel(logging.WARNING)
app.logger.addHandler(file_handler)


def parse_json(data):
    try:
        out = json.loads(data)
    except ValueError:
        raise InvalidAPIUsage('Invalid json')
    except TypeError:
        raise InvalidAPIUsage('Invalid json')
        
    if ('apikey' not in out):
        raise InvalidAPIUsage('Missing apikey json parameter')
        
    if ('version' not in out):
        raise InvalidAPIUsage('Missing version json parameter')
        
    if ('data' not in out):
        raise InvalidAPIUsage('Missing data json parameter')
        
    apikey = out['apikey']
    version = out['version']
    data = out['data']
    return data
    
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


class InvalidAPIUsage(Exception):
    status_code = 400
    def __init__(self, message, status_code=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


    def to_dict(self):
        rv = dict()
        rv['message'] = self.message
        return rv

@app.errorhandler(InvalidAPIUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

@app.route('/', methods=['GET', 'POST'])
def root():
    return "Root node"
    
@app.route('/inference', methods=['POST'])
def route_inference():
    data = parse_json(request.data)
    features, facts, insights, relationships = inference.do_inference(data)
    facts = recursive_numpy_array_removal(facts)
    output_string = json.dumps({'features':features,'facts':facts,'insights':insights,'relationships':relationships})
    return output_string
    


#code from http://flask.pocoo.org/snippets/56/ to allow response to go to a different server
#necessary as Vasily's code doesn't specify an origin, so we end up with FLASK not trusting it.
def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']




    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator
    
@app.route('/question', methods=['POST'])
@crossdomain(origin='*')
def route_question():
    data = parse_json(request.data)
    question = inference.pick_question(data)    
    question_string = inference.get_question_string(question['question'])
    return json.dumps({'question':question['question'], 'facts':question['facts'], 'question_string':question_string})

@app.route('/version', methods=['GET','POST'])
def route_version():     
    return json.dumps({'version':'3.0'})
      
@app.route('/metadata', methods=['POST'])
def route_metadata(): 
    data = parse_json(request.data)  
    metadata = inference.get_meta_data(data)
    return json.dumps(metadata)

@app.route('/psych', methods=['POST'])
def route_psych(): 
    data = parse_json(request.data)
    if 'typelist' in data:
        predictTypeList = data['typelist']
    else:
        predictTypeList = ['ope','con','ext','agr','neu'] 
    
    if 'userstatus' not in data:
        raise InvalidAPIUsage('psychometrics requires a "userstatus" parameter.')
        
    user_status = data['userstatus']
    
    ##Change to reflect update in Xingjie's code:
    ext = Extractor()
    lan = ext.isEnglish(user_status)
    if lan == True:
        score = ext.getScore(user_status, predictTypeList)
        perc = ext.getPercentile(score)
        return json.dumps({'scores':score, 'percentiles':perc})    
    else:
        raise InvalidAPIUsage('Language not English. Other languages not yet supported.')
    
if __name__ == '__main__':
    app.run(debug=False,host='0.0.0.0', port=4567)
