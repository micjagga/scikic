import multiprocessing

#reproducing this:
# /home/ubuntu/anaconda/bin/gunicorn -w 4 -b 127.0.0.1:4000 scikic:app

reload = True
bind = "127.0.0.1:4000"
workers = multiprocessing.cpu_count() * 2 + 1
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"


