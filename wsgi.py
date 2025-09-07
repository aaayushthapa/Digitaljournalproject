import sys
# add your project directory to the sys.path
project_home = '/home/aayushthapa123/DigitalJournalproject'
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# import flask app but need to call it "application" for WSGI to work
from app import app as application  # noqa