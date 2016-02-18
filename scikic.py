import json
import inference
import config
import numpy as np

import logging
from logging import FileHandler


from flask import request
from flask import Flask
app = Flask(__name__)

# TO DO, add error handlers http://flask.pocoo.org/docs/0.10/patterns/apierrors/
# TO DO, stop errors showing up on client

file_handler = FileHandler('/var/log/scikic/error.log')
file_handler.setLevel(logging.WARNING)
app.logger.addHandler(file_handler)

def parse_json(data):
    try:
        out = json.loads(data)
    except ValueError:
        print "Invalid JSON"
        exit()
    except TypeError:
        print "Missing API query JSON"
        exit()
        
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
  
@app.route('/metadata', methods=['POST'])
def route_metadata(): 
    data = parse_json(request.data)  
    metadata = inference.get_meta_data(data)
    return json.dumps(metadata)

#if __name__ == '__main__':
#    app.run(host='127.0.0.1', port=4000)
