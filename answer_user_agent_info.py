import numpy as np
import answer as ans
import config
import json

import logging
logging.basicConfig(filename=config.loggingFile,level=logging.DEBUG)

class UserAgentInfoAnswer(ans.Answer):
    """User Agent Info: Parses and uses the user_agent_info structure provided by the server (has info about the client's os etc)
        current adds the ip address into facts, under facts['where']['ipaddr']"""
    
    dataset = 'user_agent_info';
 
    def __init__(self,name,dataitem,itemdetails,answer=None): 
    #    logging.info('Initialising User Agent Info class')     
        self.dataitem = dataitem
        self.itemdetails = itemdetails
        self.featurename = name
        self.answer = answer

    @classmethod
    def pick_question(self,questions_asked,facts,target):
        return 'None', 'None'

    def append_facts(self,facts,all_answers):
        try:
       #     logging.info('Parsing User Agent Info: %s' % self.answer)
            userinfo = json.loads(self.answer)
            ip = userinfo['REMOTE_ADDR']
            if 'where' not in facts:
                facts['where'] = {}
            facts['where']['ipaddr'] = ip
        except ValueError:
            logging.info('Unable to a parse user agent info')
        except TypeError:
            logging.info('Unable to a parse user agent info')
            
