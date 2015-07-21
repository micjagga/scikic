import answer as ans

#import all answer_something.py classes
import os
import glob
modules = glob.glob("answer_*.py")
trimmedmods = [f[:f.find('.py')] for f in modules]
for mod in trimmedmods:
     __import__(mod)

import config

print "Configuring individual classes..."
c = [cls for cls in ans.Answer.__subclasses__()]
for cl in c:
    print "Class %s:" % cl.dataset
    cl.setup(config.pathToData)
