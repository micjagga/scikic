import answer as ans
import random
import logging

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

def process_answers(data,facts={}):
    #instantiate classes for each dataset we have
    #put these instances in the 'answers' array which is
    #returned. Also alter the facts variable inplace.
    logging.info('process_answers (data has %d items, facts has %d items)' % (len(data),len(facts)))
    answers = []
    for it,qa in enumerate(data):
        if 'answer' not in qa:
            continue #this question doesn't have an answer
        c = [cls for cls in ans.Answer.__subclasses__() if cls.dataset==qa['dataset']]
        if len(c)==0:
            continue #don't know this sort of data: skip it
        name = "item%d" % it

        tempans = str(qa['answer'])
        if len(tempans)>15:
            tempans=tempans[0:15]+'...'
        logging.info('  adding %s [%15s] (%s,%s->%s)' % (name,qa['dataset'],qa['dataitem'],qa['detail'],tempans))
        answers.append(c[0](name,qa['dataitem'],qa['detail'],qa['answer']))

    for a in answers:
        a.append_facts(facts, answers)

    logging.info('  facts has now %d items' % (len(facts)))
    logfacts(facts)
    return answers

def do_inference(data=[],facts={}):
#data = data we have about the user stored in an array of dictionaries:
#each dictionary has four fields: dataset, dataitem, detail and answer
#
#facts = dictionary of processed
#data about the user.
#
#Note: There are two dictionaries, facts and features.
# - Facts are detailed statements about a person from a very large dimensional space (e.g. precise address, name, date of birth, etc)
#which we know with some considerable certainty
#
# - Features are those things we know less about, or that we need to perform inference over. For example age, location,
#etc...
#
#TODO: Add some facts that we've not done (e.g. output area)?? (not sure we'll know that precisely, in the long-run).
#
#The facts are used by the append_features method to help generate a probability distribution. For example, if the person's
#name is in the facts dictionary as 'Robert', then if the NamesAnswer class is instantiated, it can then use that to produce
#a feature over a person's gender.
    logging.info('do_inference (data has %d items, facts has %d items)' % (len(data),len(facts)))
     
    #Some datasets we won't have asked questions about as they don't need question/answer responses (such as the babynames dataset,
    #which just gets its 'name' value from the 'facts' structure).
    #We still need to add these to our 'data' array so that they get used.
    c = [cls for cls in ans.Answer.__subclasses__()]
    for cl in c:
        cl.init_db() #normally should be started from an instance?? but we don't really mind.
        dataitem, detail = cl.pick_question(data,{},'')
        dataset = cl.dataset
        if (dataitem=='None'):
            item = {'dataset':dataset, 'dataitem':dataitem, 'detail':detail, 'answer':0} #no answer provided to this type of dataset
            data.append(item)

    answers = process_answers(data,facts)

    
    features = {}
    for a in answers:
        logging.info('   adding %s' % a.dataset)
        a.append_features(features,facts)


    logging.info('   features has %d items' % (len(features)))
    for f in features:
        logging.info('      %s' % (f))

    model = pm.Model(features)
    mcmc = pm.MCMC(model)
    mcmc.sample(10000,1000,4,progress_bar=False)
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
            pass #we silently discard features we can't get a trace on, as these are the observed features.

    answer_range = {}
    for o in output:
        vals = output[o]['distribution']
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

    insights = []
    for a in answers:
        insights.extend(a.insights(output, facts))

    import sys
    print >>sys.stderr, output
    print >>sys.stderr, insights

    return output, facts, insights

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
    #Generating a question requires a dictionary of 'previous_questions', 'facts' and 'target'. The 'previous_questions' is a list of dictionaries of previous questions.
    logging.info('pick_question (data has %d items)' % (len(data)))
    questions_asked = []
    facts = {}
    target = ''
    if 'previous_questions' in data:
        questions_asked = data['previous_questions']
    if 'facts' in data: 
        facts = data['facts']
    if 'target' in data:
        target = data['target']

    #if len(facts)==0: #TODO: This is going to be really slow but I've put it here for now...
    if len(questions_asked)>0:
        process_answers(questions_asked, facts)
    questions_only_asked = []
    
    
    for qa in questions_asked:
        #to make it easy to check through which questions we've asked, we make a string for each one.
        questionstring = "%s_%s_%s" % (qa['dataset'], qa['dataitem'], qa['detail'])
        questions_only_asked.append(questionstring) #this doesn't include the answer so we can look for if we've asked the question already.

    found = False           #have we found a question?
    for counter in range(20):
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
            found = True
            break
    if not found:
        dataset = None
        dataitem = None
        detail = None
    return {'question':{'dataset':dataset, 'dataitem':dataitem, 'detail':detail},'facts':facts}

def get_question_string(data):
    c = [cls for cls in ans.Answer.__subclasses__() if cls.dataset==data['dataset']]
    if len(c)==0:
        return "Don't know this type of data";
    d = c[0]('temp',data['dataitem'],data['detail'])
    return d.question_to_text()

def get_meta_data(data):
    c = [cls for cls in ans.Answer.__subclasses__() if cls.dataset==data['dataset']]
    if len(c)==0:
        return "Don't know this type of data";
    return c[0].metaData()
