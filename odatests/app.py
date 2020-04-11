from flask import Flask
from flask import render_template,make_response,request,jsonify

import peewee
import datetime
from collections import defaultdict
from dqueue import TaskEntry, db
import yaml
import io


try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse


from playhouse.db_url import connect
from playhouse.shortcuts import model_to_dict, dict_to_model

app = Flask(__name__)

decoded_entries={}


class ReverseProxied(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_FORWARDED_PREFIX', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        scheme = environ.get('HTTP_X_SCHEME', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        return self.app(environ, start_response)

app.wsgi_app = ReverseProxied(app.wsgi_app)

@app.route('/tests')
def tests_get(methods=["GET"]):
    try:
        db.connect()
    except peewee.OperationalError as e:
        pass

    decode = bool(request.args.get('raw'))

    print("searching for entries")
    date_N_days_ago = datetime.datetime.now() - datetime.timedelta(days=float(request.args.get('since',1)))

    entries=[entry for entry in TaskEntry.select().where(TaskEntry.modified >= date_N_days_ago).order_by(TaskEntry.modified.desc()).execute()]

    bystate = defaultdict(int)
    #bystate = defaultdict(list)

    for entry in entries:
        print("found state", entry.state)
        bystate[entry.state] += 1
        #bystate[entry.state].append(entry)

    db.close()

    if request.args.get('json') is not None:
        return jsonify({k:v for k,v in bystate.items()})
    else:
        return render_template('task_stats.html', bystate=bystate)
    #return jsonify({k:len(v) for k,v in bystate.items()})

@app.route('/tests')
def tests_put(methods=["PUT"]):
    try:
        db.connect()
    except peewee.OperationalError as e:
        pass

    decode = bool(request.args.get('raw'))

    print("searching for entries")
    date_N_days_ago = datetime.datetime.now() - datetime.timedelta(days=float(request.args.get('since',1)))

    entries=[entry for entry in TaskEntry.select().where(TaskEntry.modified >= date_N_days_ago).order_by(TaskEntry.modified.desc()).execute()]

    bystate = defaultdict(int)
    #bystate = defaultdict(list)

    for entry in entries:
        print("found state", entry.state)
        bystate[entry.state] += 1
        #bystate[entry.state].append(entry)

    db.close()

    if request.args.get('json') is not None:
        return jsonify({k:v for k,v in bystate.items()})
    else:
        return render_template('task_stats.html', bystate=bystate)
    #return jsonify({k:len(v) for k,v in bystate.items()})

@app.route('/stats')
def stats():
    try:
        db.connect()
    except peewee.OperationalError as e:
        pass

    decode = bool(request.args.get('raw'))

    print("searching for entries")
    date_N_days_ago = datetime.datetime.now() - datetime.timedelta(days=float(request.args.get('since',1)))

    entries=[entry for entry in TaskEntry.select().where(TaskEntry.modified >= date_N_days_ago).order_by(TaskEntry.modified.desc()).execute()]

    bystate = defaultdict(int)
    #bystate = defaultdict(list)

    for entry in entries:
        print("found state", entry.state)
        bystate[entry.state] += 1
        #bystate[entry.state].append(entry)

    db.close()

    if request.args.get('json') is not None:
        return jsonify({k:v for k,v in bystate.items()})
    else:
        return render_template('task_stats.html', bystate=bystate)
    #return jsonify({k:len(v) for k,v in bystate.items()})

@app.route('/list')
def list():
    try:
        db.connect()
    except peewee.OperationalError as e:
        pass


    pick_state = request.args.get('state', 'any')

    json_filter = request.args.get('json_filter')

    decode = bool(request.args.get('raw'))

    print("searching for entries")
    date_N_days_ago = datetime.datetime.now() - datetime.timedelta(days=float(request.args.get('since',1)))

    if pick_state != "any":
        if json_filter:
            entries=[model_to_dict(entry) for entry in TaskEntry.select().where((TaskEntry.state == pick_state) & (TaskEntry.modified >= date_N_days_ago) & (TaskEntry.entry.contains(json_filter))).order_by(TaskEntry.modified.desc()).execute()]
        else:
            entries=[model_to_dict(entry) for entry in TaskEntry.select().where((TaskEntry.state == pick_state) & (TaskEntry.modified >= date_N_days_ago)).order_by(TaskEntry.modified.desc()).execute()]
    else:
        if json_filter:
            entries=[model_to_dict(entry) for entry in TaskEntry.select().where((TaskEntry.modified >= date_N_days_ago) & (TaskEntry.entry.contains(json_filter))).order_by(TaskEntry.modified.desc()).execute()]
        else:
            entries=[model_to_dict(entry) for entry in TaskEntry.select().where(TaskEntry.modified >= date_N_days_ago).order_by(TaskEntry.modified.desc()).execute()]


    print(("found entries",len(entries)))
    for entry in entries:
        print(("decoding",len(entry['entry'])))
        if entry['entry'] in decoded_entries:
            entry_data=decoded_entries[entry['entry']]
        else:
            try:
                entry_data=yaml.load(io.StringIO(entry['entry']))
                entry_data['submission_info']['callback_parameters']={}
                for callback in entry_data['submission_info']['callbacks']:
                    if callback is not None:
                        entry_data['submission_info']['callback_parameters'].update(urlparse.parse_qs(callback.split("?",1)[1]))
                    else:
                        entry_data['submission_info']['callback_parameters'].update(dict(job_id="unset",session_id="unset"))
            except Exception as e:
                raise
                print("problem decoding", repr(e))
                entry_data={'task_data':
                                {'object_identity':
                                    {'factory_name':'??'}},
                            'submission_info':
                                {'callback_parameters':
                                    {'job_id':['??'],
                                     'session_id':['??']}}
                            }


            decoded_entries[entry['entry']]=entry_data
        entry['entry']=entry_data

    db.close()
    return render_template('task_list.html', entries=entries)

@app.route('/task/info/<string:key>')
def task_info(key):
    entry=[model_to_dict(entry) for entry in TaskEntry.select().where(TaskEntry.key==key).execute()]
    if len(entry)==0:
        return make_response("no such entry found")

    entry=entry[0]

    print(("decoding",len(entry['entry'])))

    try:
        entry_data=yaml.load(io.StringIO(entry['entry']))
        entry['entry']=entry_data
            
        from ansi2html import ansi2html

        if entry['entry']['execution_info'] is not None:
            entry['exception']=entry['entry']['execution_info']['exception']['exception_message']
            formatted_exception=ansi2html(entry['entry']['execution_info']['exception']['formatted_exception']).split("\n")
        else:
            entry['exception']="no exception"
            formatted_exception=["no exception"]
        
        history=[model_to_dict(en) for en in TaskHistory.select().where(TaskHistory.key==key).order_by(TaskHistory.id.desc()).execute()]
        #history=[model_to_dict(en) for en in TaskHistory.select().where(TaskHistory.key==key).order_by(TaskHistory.timestamp.desc()).execute()]

        r = render_template('task_info.html', entry=entry,history=history,formatted_exception=formatted_exception)
    except:
        r = jsonify(entry['entry'])

    db.close()
    return r

@app.route('/purge')
def purge():
    nentries=TaskEntry.delete().execute()
    return make_response("deleted %i"%nentries)

@app.route('/resubmit/<string:scope>/<string:selector>')
def resubmit(scope,selector):
    if scope=="state":
        if selector=="all":
            nentries=TaskEntry.update({
                            TaskEntry.state:"waiting",
                            TaskEntry.modified:datetime.datetime.now(),
                        })\
                        .execute()
        else:
            nentries=TaskEntry.update({
                            TaskEntry.state:"waiting",
                            TaskEntry.modified:datetime.datetime.now(),
                        })\
                        .where(TaskEntry.state==selector)\
                        .execute()
    elif scope=="task":
        nentries=TaskEntry.update({
                        TaskEntry.state:"waiting",
                        TaskEntry.modified:datetime.datetime.now(),
                    })\
                    .where(TaskEntry.key==selector)\
                    .execute()

    return make_response("resubmitted %i"%nentries)


#         class MyApplication(Application):
#            def load(self):

#                  from openlibrary.coverstore import server, code
#                   server.load_config(configfile)
#                    return code.app.wsgifunc()

#from gunicorn.app.base import Application
#Application().run(app,port=5555,debug=True,host=args.host)

#       MyApplication().run()


def listen(args):
    app.run(port=5555,debug=True,host=args.host,threaded=True)
