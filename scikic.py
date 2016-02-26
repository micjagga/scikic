import json
import inference
import config
import numpy as np

import logging
from logging import FileHandler

from psych.jsonExtractor import jsonExtractor

from flask import jsonify
from flask import request
from flask import Flask
app = Flask(__name__)

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
    features, facts, insights = inference.do_inference(data)
    facts = recursive_numpy_array_removal(facts)
    output_string = json.dumps({'features':features,'facts':facts,'insights':insights})
    return output_string
    
@app.route('/question', methods=['POST'])
def route_question():
    data = parse_json(request.data)
    question = inference.pick_question(data)    
    question_string = inference.get_question_string(question['question'])
    return json.dumps({'question':question['question'], 'facts':question['facts'], 'question_string':question_string})

@app.route('/version', methods=['GET','POST'])
def route_version():     
    return json.dumps({'version':'1.0'})
      
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
    je = jsonExtractor()
    jsonStr = je.getJsonStr(user_status, predictTypeList)
    return jsonStr
    
if __name__ == '__main__':
    app.run(debug=False,host='0.0.0.0', port=4567)
