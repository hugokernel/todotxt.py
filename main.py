# -*- coding: utf-8 -*-
import os
from bottle import get, route, request, run, template, static_file, jinja2_view, jinja2_template

from config.general import TODO_FILE, TODO_FILES, HOST, PORT

from lib.todo import Todo, TodoError, TodoHashError

t = Todo()

t.todo_file = TODO_FILES[0][0]
#print t.load()
#for l in t.load():
#    print l.text

#exit()

todo_selected = 0
todo_name = ''

def getRoot():
    return '/' + str(todo_selected)

class Helper:

    @staticmethod
    def loader(func):
        global t
        def wrapper(*args, **kwargs):
            global todo_selected, todo_name
            if 'todo' in kwargs:
                item = TODO_FILES[int(kwargs['todo'])]
                if type(item) == str:
                    t.todo_file = item
                    name = ''
                elif type(item) == tuple:
                    if len(item) == 2:
                        t.todo_file, name = item
                    elif len(item) == 3:
                        t.todo_file, name, configs = item
                        for attr, value in configs.iteritems():
                            setattr(t, attr, value)
                else:
                    raise Exception('TODO_FILES error !')
                todo_selected = int(kwargs['todo'])
                todo_name = name
            return func(**kwargs)
        return wrapper

    @staticmethod
    def list():
        out = list()
        for item in TODO_FILES:
            if type(item) == tuple:
                out.append(item)
            else:
                out.append((item, item))
        return out

@route('/static/js/<path:path>')
def javascripts(path):
    return static_file(path, root='static/js')

@route('/static/css/<path:path>')
def stylesheets(path):
    return static_file(path, root='static/css')

@route('/static/fonts/<path:path>')
def fonts(path):
    return static_file(path, root='static/fonts')

@route('/static/img/<path:path>')
def stylesheets(path):
    return static_file(path, root='static/img')

@route('/download/current')
@route('/<todo>/download/current')
@Helper.loader
def download(todo=None):
    print t.todo_file
    return static_file(t.todo_file, root='')

@route('/', name='home')
@route('/<todo>/')
@jinja2_view('main.html', template_lookup=['templates'], getRoot=getRoot)
@Helper.loader
def home(todo=None):
    todos, contexts, projects = t.get_data()

    todo_list = []
    for item in Helper.list():
        todo_list.append((item[0], item[1] if len(item) > 1 else item[0]))

    return {
        'todos':            todos,
        'contexts':         contexts, 
        'projects':         projects, 
        'todo_files':       todo_list, 
        'todo_filename':    os.path.basename(t.todo_file), 
        'todo_selected':    todo_selected, 
        'todo_name':        todo_name,
        'source':           ''.join(t.read()),
        'done':             ''.join(t.read(t.done_file)),
        'done_file':        t.action_when_done in (1, 2)
    }

@route('/list/get', name='listget')
@route('/<todo>/list/get')
@jinja2_view('list.html', template_lookup=['templates'], getRoot=getRoot)
@Helper.loader
def list_get(todo=None):
    return dict(zip(['todos', 'contexts', 'projects'], t.get_data()))

@route('/contexts/get', name='contextsget')
@route('/<todo>/contexts/get')
@jinja2_view('contexts.html', template_lookup=['templates'])
@Helper.loader
def contexts_get(todo=None):
    global t
    t.load()
    return { 'contexts': t.contexts }#, 'contexts_filtered': t.contexts_filtered }

@route('/projects/get', name='projectsget')
@route('/<todo>/projects/get')
@jinja2_view('projects.html', template_lookup=['templates'])
@Helper.loader
def projects_get(todo=None):
    global t
    t.load()
    return { 'projects': t.projects }#, 'projects_filtered': t.projects_filtered }

@route('/filter/<filters>', name='filter')
@route('/<todo>/filter/<filters>')
@jinja2_view('main.html', template_lookup=['templates'])
@Helper.loader
def filter(filters, todo=None):
    if filters[0] == '@':
        todos = t.load(contexts=[ filters[1:] ])
    elif filters[0] == '+':
        todos = t.load(projects=[ filter for filter in filters.split('+') if filter ])
    else:
        todos = t.load()

    todo_list = []
    for item in Helper.list():
        todo_list.append((item[0], item[1] if len(item) > 1 else item[0]))

    return {
        'todos':                todos,
        'contexts':             t.contexts,
        'projects':             t.projects,
        'filters':              filters,
        'todo_files':           todo_list,
        'todo_filename':        os.path.basename(t.todo_file),
        'todo_selected':        todo_selected,
        'todo_name':            todo_name,
        'projects_filtered':    t.projects_filtered,
        'contexts_filtered':    t.contexts_filtered,
        'source':               ''.join(t.read())
    }

def is_ajax():
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'

@route('/api/edit/<line:int>/<hash>', name='edit')
@route('/<todo>/api/edit/<line:int>/<hash>')
@jinja2_view('line.html', template_lookup=['templates'])
@Helper.loader
def edit(line, hash, todo=None):
    error_message = todo = ''
    try:
        todo = t.edit(line, request.query.get('data'), hash=hash)
    except TodoHashError:
        error_message = 'Line not found !'
    return { 'todo': todo, 'error_message': error_message }

@route('/mark_as_done/<line:int>/<hash>', name='mark_as_done')
@route('/<todo>/mark_as_done/<line:int>/<hash>')
@Helper.loader
def mark_as_done(line, hash, todo=None):
    error_message = ''
    try:
        t.mark_as_done(line, hash=hash)
    except TodoHashError:
        error_message = 'Line not found !'
    print 'err', error_message
    if is_ajax():
        return { 'status': 0 } if not error_message else { 'status': 1, 'error_message': error_message }
    else:
        return home()

@route('/delete/<line:int>/<hash>', name='delete')
@route('/<todo>/delete/<line:int>/<hash>')
@Helper.loader
def delete(line, hash, todo=None):

    error_message = ''
    try:
        t.delete(line, hash=hash)
    except TodoHashError:
        error_message = 'Line not found !'

    if is_ajax():
        return { 'status': 0 } if not error_message else { 'status': 1, 'error_message': error_message }
    else:
        return home()

@route('/api/new', name='new')#, method=['GET', 'POST'])
@route('/<todo>/api/new')
@jinja2_view('line.html', template_lookup=['templates'])
@Helper.loader
def new(todo=None):
    todo = t.new(request.query.get('data'))
    return { 'todo': todo }

@route('/api/raw/write', name='rawwrite', method='POST')
@route('/<todo>/api/raw/write')
@Helper.loader
def rawwrite(todo=None):
    data = request.forms.get('data').strip()
    t.write(data)
    return { 'data': data }

if False:
    from bottle.ext.websocket import GeventWebSocketServer
    from bottle.ext.websocket import websocket

    from watchdog.observers import Observer
    from watchdog.events import FileModifiedEvent

    class Toto:
        def dispatch(self, p):
            if type(p) == FileModifiedEvent and p.src_path == todofile:
                print 'event!', p.src_path, p
                wsrequest.send('update')

    toto = Toto()

    todofile = os.path.abspath(TODO_FILE)
    tododir = os.path.basename(todofile)

    observer = Observer()
    observer.schedule(toto, '/var/www/todo/src/todo/', recursive=False)
    observer.start()

    wsrequest = None
    @get('/websocket', apply=[websocket])
    def echo(ws):
        global wsrequest
        wsrequest = ws
        while True:
            msg = ws.receive()
            if msg is not None:
                ws.send(msg)
            #else:
            #    break

    run(host=HOST, port=PORT, server=GeventWebSocketServer)
else:
    run(host=HOST, port=PORT)

'''
@route('/websocket')
def handle_websocket():
    wsock = request.environ.get('wsgi.websocket')
    if not wsock:
        abort(400, 'Expected WebSocket request.')

    while True:
        try:
            message = wsock.receive()
            wsock.send("Your message was: %r" % message)
        except WebSocketError:
            break

from gevent.pywsgi import WSGIServer
from geventwebsocket import WebSocketHandler, WebSocketError
server = WSGIServer(("0.0.0.0", 8080), app,
                    handler_class=WebSocketHandler)
server.serve_forever()
'''

