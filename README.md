# scikic

This repo is the API part of the online inference engine and psychic.

To install
<ol>
<li>clone the repo to, for example <tt>public_html/api</tt>
<li>Alter <tt>config.py</tt> to point to somewhere the script can save its data
<li>Run <tt>python setup.py</tt> to download and create all the files that it requires. This can take a LONG LONG time.
<li>Access the API (see <tt>Examples of API usage.ipynb</tt>)
<li>You may also need to alter the environment variables of the apache webserver,
<pre>export PATH=/home/myusername/anaconda/bin:$PATH
export NLTK_DATA=/home/myusername/api_data/nltk_data</pre>
</ol>
