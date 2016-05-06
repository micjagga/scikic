import answer as ans
import random
import logging
from timeit import default_timer as time

#import all answer_something.py classes
import os
import glob
modules = glob.glob("answer_*.py")
trimmedmods = [f[:f.find('.py')] for f in modules]
for mod in trimmedmods:
     __import__(mod)

import pymc as pm
import numpy as np
import config

logging.basicConfig(filename=config.loggingFile,level=logging.DEBUG)

logging.info('-------')

def logfacts(facts):
    logging.info('   Facts:')
    for f in facts:
        logging.info('      %s: %s' % (f,facts[f]))
 #       for fi in facts[f]:
 #           logging.info('            >   %s: %s' % (fi, facts[f][fi]))
    logging.info(' ');

def process_answers(questions_asked=[],unprocessed_questions=[],facts={}):
    # questions_asked - all the question/answer tuples that you want to add to the 'answers' list (of instantiated classes)
    # unprocessed_questions - all the question/answer tuples that you still need to incorporate into the facts dictionary
    # facts - the facts dictionary so far (altered in place)
    #
    #instantiate classes for each dataset we have
    #put these instances in the 'answers' array which is
    #returned. Also alter the facts variable in place.

    answers = []
    for it,qa in enumerate(questions_asked):
        t0 = time()        
        if 'answer' not in qa:
            continue #this question doesn't have an answer
        c = [cls for cls in ans.Answer.__subclasses__() if cls.dataset==qa['dataset']]
        if len(c)==0:
            continue #don't know this sort of data: skip it
        name = "item%d" % it
        new_answer = c[0](name,qa['dataitem'],qa['detail'],qa['answer'])
        answers.append(new_answer)
        if qa in unprocessed_questions:
            logging.info("process_answers: adding facts from %s" % new_answer.dataset)
            new_answer.append_facts(facts, answers)
        logging.info('Time (class %s) append_facts %fms' % (new_answer.dataset,(time()-t0)*1000))            
    return answers


def smooth(dist, its):
    """Smooths a distribution (if it's not categorical - i.e. more continuous).
    We do this so that we can have fewer iterations and still have a plausible looking
    distribution of ages.
    We decide if the dist is 'continous' if it's got more than 30 items - not ideal
    We also smooth more if fewer iterations have been used."""
    N = 1000/np.sqrt(its) #e.g. its = 5000 -> size = 31. its=50,000 -> size = 4
    logging.info("Smoothing kernel size %f" % N)
    if N<2: #if we don't need to smooth...
        return dist
    if len(dist)<30: #if it's not categorical don't smooth
        return dist
        
    box = np.ones(N)/N
    dist = np.convolve(dist, box, mode='same').tolist()
    return dist

def do_inference(data):
#parameters in data's dictionary:
# 'questions_asked', 'unprocessed_questions', 'facts', 'config'
#
#we need to:
#1. Add any other questions that are unprocessed (i.e don't have items added to the facts dictionary)
#2. process the unprocessed questions,
#   using:
#3. 
    t0_start = time()
    questions_asked = []
    unprocessed_questions = []
    facts = {}
    config = {}
    datasets = None
    mcmc_iterations = 1000 #default

    if 'questions_asked' in data:
        questions_asked = data['questions_asked']
    if 'unprocessed_questions' in data:
        unprocessed_questions = data['unprocessed_questions']
    if 'facts' in data: 
        facts = data['facts']
    if 'datasets' in data:
        datasets = data['datasets']
    if 'config' in data:
        if 'mcmc_iterations' in data['config']:
            mcmc_iterations = data['config']['mcmc_iterations']

    #Some datasets we won't have asked questions about as they don't need question/answer responses (such as the babynames dataset,
    #which just gets its 'name' value from the 'facts' structure).
    #We still need to add these to our 'unprocessed_questions' array so that they get used.
    c = [cls for cls in ans.Answer.__subclasses__()]
    for cl in c:
        t0 = time()
        if (datasets is not None): #allows us to only use a subset of classes if we wish
            if cl.dataset not in datasets:
                continue
        cl.init_db() #(normally should be started from an instance, but we don't really mind).
        dataitem, detail = cl.pick_question(questions_asked,facts,'')
        dataset = cl.dataset
        if (dataitem=='None'):
            item = {'dataset':dataset, 'dataitem':dataitem, 'detail':detail, 'answer':0} #no answer provided to this type of dataset
            unprocessed_questions.append(item)
            questions_asked.append(item)
        logging.info('Time (class %s) initialising %fms' % (cl.dataset,(time()-t0)*1000))

    answers = process_answers(questions_asked,unprocessed_questions,facts)
    
    features = {}
    relationships = []
    descriptions = {}
    for a in answers:
        t0 = time()    
        logging.info('   adding %s' % a.dataset)
        a.append_features(features,facts,relationships,descriptions)
        logging.info('Time (class %s) append_features %fms' % (a.dataset,(time()-t0)*1000))        

    logging.info('   features has %d items' % (len(features)))
    for f in features:
        logging.info('      %s' % (f))

    t0 = time()    
    model = pm.Model(features)
    mcmc = pm.MCMC(model)
    mcmc.sample(mcmc_iterations,mcmc_iterations/50,4,progress_bar=False)
    logging.info('Time MCMC %fms' % ((time()-t0)*1000))
    output = {}

    for feature in features:
        try:
            trc = mcmc.trace(features[feature])[:]
            count = np.zeros(max(trc)+1)
            for v in range(min(trc),max(trc)+1):            
                count[v] = np.sum(trc==v)
            count = 1.0*count/count.sum() #normalise
            output[feature] = {'distribution':count.tolist()}
        except KeyError:
            output[feature] = {'distribution':[1]}
            #pass #we silently discard features we can't get a trace on, as these are the observed features.

    answer_range = {}
        
    for o in output:
        vals = output[o]['distribution']    
        output[o]['distribution'] = smooth(output[o]['distribution'], mcmc_iterations) #smooth the output (hack to make things quicker)
        tally = 0
        mean = 0
        for i,v in enumerate(vals):
            if tally<0.25:
                lower_range = i
            if tally<0.75:
                upper_range = i
            tally += v
            mean += i*1.0*v
        output[o]['quartiles'] = {'lower':lower_range,'upper':upper_range,'mean':mean}

    insights = {}
    for a in answers:
        insights.update(a.insights(output, facts))
        
    logging.info('Time Inference Total %fms' % ((time()-t0_start)*1000))
    insights['debug_total_inference_time'] = '%fms' % ((time()-t0_start)*1000)
    return output, facts, insights, relationships, descriptions

#Some datasets need to process an answer (for example lookup where a location is, etc). It's best to do this once, when you get
#the user response, rather than repeatedly later, when you read it.
def process_answer(data):
    logging.info('process_answer (data has %d items)' % (len(data)))
    c = [cls for cls in ans.Answer.__subclasses__() if cls.dataset==data['dataset']]
    if len(c)>0:
        answer, detail = c[0].process_answer(data['dataitem'],data['detail'],data['answer'])
        data['answer'] = answer
        data['detail'] = detail
        return data
    else:
        return data  #just return what we were given. "Unable to find specified dataset"


def pick_question(data):
    #Generating a question requires a dictionary of 'questions_asked', 'facts' and 'target'. The 'questions_asked' is a list of dictionaries
    #of previous questions, that you want to avoid asking again.
    #The 'unprocessed_questions' are questions that you've asked already and that haven't been incorporated into the 'facts' dictionary.

    logging.info('pick_question')
    questions_asked = []
    unprocessed_questions = []
    facts = {}
    target = ''
    if 'questions_asked' in data:
        questions_asked = data['questions_asked']
    if 'unprocessed_questions' in data:
        unprocessed_questions = data['unprocessed_questions']
    if 'facts' in data: 
        facts = data['facts']
    if 'target' in data:
        target = data['target']

    if len(unprocessed_questions)>0: #add data from the questions asked to the facts dictionary
        process_answers(questions_asked,unprocessed_questions,facts)
    questions_only_asked = []
    
    logging.info('    facts: %s' % facts)
    for qa in questions_asked:
        #to make it easy to check through which questions we've asked, we make a string for each one.
        questionstring = "%s_%s_%s" % (qa['dataset'], qa['dataitem'], qa['detail'])
        questions_only_asked.append(questionstring) #this doesn't include the answer so we can look for if we've asked the question already.

    found = False           #have we found a question?
    for counter in range(200): #skip though everything until we find one...
#        c = [cls for cls in ans.Answer.__subclasses__() if cls.dataset not in ['personality']] 
        c = [cls for cls in ans.Answer.__subclasses__()]
        cl = random.choice(c)
  #      print cl.dataset + "<br/>"
#        if (cl.dataset=='movielens' or cl.dataset=='personality'):
#            if random.random()<0.9: #discourage movielens questions, as they're of less use
#                continue
        cl.init_db() #normally should be started from an instance?? but we don't really mind.
        dataitem, detail = cl.pick_question(questions_asked,facts,target)
        dataset = cl.dataset
        if (dataitem=='None' or dataitem=='Skip'): #not a dataset that needs questions
            continue;
        question = "%s_%s_%s" % (dataset, dataitem, detail)
        if (question in questions_only_asked): #duplicate of one we've already asked
            continue
        else:
            logging.info('    found a question: %s, %s, %s' % (dataset,dataitem,detail))
            found = True
            break

    if not found:
        logging.info('    not found a question')
        dataset = None
        dataitem = None
        detail = None
    logging.info('    returning (%s)' % dataset)
    return {'question':{'dataset':dataset, 'dataitem':dataitem, 'detail':detail},'facts':facts}

def get_question_string(data):
    c = [cls for cls in ans.Answer.__subclasses__() if cls.dataset==data['dataset']]
    if len(c)==0:
        return "Don't know this type of data";
    d = c[0]('temp',data['dataitem'],data['detail'])
    return d.question_to_text()

def get_meta_data(data):
    metaData = []
    dataset_list = []
    if 'dataset' in data:
        classes = [cls for cls in ans.Answer.__subclasses__() if cls.dataset in data['dataset']]
        if len(classes)==0:
            return "Don't know this type of data";
    else:
        classes = ans.Answer.__subclasses__()
    for c in classes:
        meta = c.metaData() #data from this one class
        meta['dataset'] = c.dataset #add the name of the dataset
        metaData.append(meta)
    return metaData
