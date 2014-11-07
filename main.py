# -*- coding: utf-8 -*-
import os
from bottle import get, route, request, run, template, static_file, jinja2_view, jinja2_template

from config.general import TODO_FILE, HOST, PORT, BASE_PATH

from lib.todo import Todo, TodoError, TodoHashError

t = Todo()

if type(TODO_FILE) == str:
    TODO_FILE = ( ( TODO_FILE, ), )

t.todo_file = TODO_FILE[0][0]

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
                item = TODO_FILE[int(kwargs['todo'])]
                name = ''
                if type(item) == str:
                    t.todo_file = item
                elif type(item) == tuple:
                    if len(item) == 2:
                        t.todo_file, name = item
                    elif len(item) == 3:
                        t.todo_file, name, configs = item
                        for attr, value in configs.iteritems():
                            setattr(t, attr, value)

                    if t.action_when_done in (1, 2):
                        t.done_file = os.path.join(os.path.dirname(t.todo_file), 'done.txt')
                else:
                    raise Exception('TODO_FILE error !')
                todo_selected = int(kwargs['todo'])
                todo_name = name
            return func(**kwargs)
        return wrapper

    @staticmethod
    def list():
        out = list()
        for item in TODO_FILE:
            if type(item) == tuple:
                out.append(item)
            else:
                out.append((item, item))
        return out

@route(BASE_PATH + 'static/js/<path:path>')
def javascripts(path):
    return static_file(path, root='static/js')

@route(BASE_PATH + 'static/css/<path:path>')
def stylesheets(path):
    return static_file(path, root='static/css')

@route(BASE_PATH + 'static/fonts/<path:path>')
def fonts(path):
    return static_file(path, root='static/fonts')

@route(BASE_PATH + 'static/img/<path:path>')
def stylesheets(path):
    return static_file(path, root='static/img')

@route(BASE_PATH + 'download/current')
@route(BASE_PATH + '<todo>/download/current')
@Helper.loader
def download(todo=None):
    return static_file(t.todo_file, root='')

@route(BASE_PATH + 'filter/')
@route(BASE_PATH + '<todo>/filter/')
@route(BASE_PATH + '', name='home')
@route(BASE_PATH + '<todo>/')
@jinja2_view('main.html', template_lookup=['templates'], getRoot=getRoot)
@Helper.loader
def home(todo=None):
    todos, contexts, projects = t.get_data()

    todo_list = []
    for item in Helper.list():
        todo_list.append((item[0], item[1] if len(item) > 1 else item[0]))

    return {
        'HOST':             HOST,
        'PORT':             PORT,
        'BASE_PATH':         BASE_PATH,
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

@route(BASE_PATH + 'list/get', name='listget')
@route(BASE_PATH + '<todo>/list/get')
@jinja2_view('list.html', template_lookup=['templates'], getRoot=getRoot)
@Helper.loader
def list_get(todo=None):
    return dict(zip(['todos', 'contexts', 'projects'], t.get_data()))

@route(BASE_PATH + 'contexts/get', name='contextsget')
@route(BASE_PATH + '<todo>/contexts/get')
@jinja2_view('contexts.html', template_lookup=['templates'])
@Helper.loader
def contexts_get(todo=None):
    global t
    t.load()
    return { 'contexts': t.contexts, 'BASE_PATH': BASE_PATH }

@route(BASE_PATH + 'projects/get', name='projectsget')
@route(BASE_PATH + '<todo>/projects/get')
@jinja2_view('projects.html', template_lookup=['templates'])
@Helper.loader
def projects_get(todo=None):
    global t
    t.load()
    return { 'projects': t.projects, 'BASE_PATH': BASE_PATH }

@route(BASE_PATH + 'filter/<filters>', name='filter')
@route(BASE_PATH + '<todo>/filter/<filters>')
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
        'BASE_PATH':             BASE_PATH,
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

@route(BASE_PATH + 'api/edit/<line:int>/<hash>', name='edit')
@route(BASE_PATH + '<todo>/api/edit/<line:int>/<hash>')
@jinja2_view('line.html', template_lookup=['templates'])
@Helper.loader
def edit(line, hash, todo=None):
    error_message = todo = ''
    try:
        todo = t.edit(line, request.query.get('data'), hash=hash)
    except TodoHashError:
        error_message = 'Line not found !'
    return { 'todo': todo, 'error_message': error_message }

@route(BASE_PATH + 'mark_as_done/<line:int>/<hash>', name='mark_as_done')
@route(BASE_PATH + '<todo>/mark_as_done/<line:int>/<hash>')
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

@route(BASE_PATH + 'delete/<line:int>/<hash>', name='delete')
@route(BASE_PATH + '<todo>/delete/<line:int>/<hash>')
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

@route(BASE_PATH + 'api/new', name='new')#, method=['GET', 'POST'])
@route(BASE_PATH + '<todo>/api/new')
@jinja2_view('line.html', template_lookup=['templates'])
@Helper.loader
def new(todo=None):
    todo = t.new(request.query.get('data'))
    return { 'todo': todo }

@route(BASE_PATH + 'api/raw/write', name='rawwrite', method='POST')
@route(BASE_PATH + '<todo>/api/raw/write')
@Helper.loader
def rawwrite(todo=None):
    data = request.forms.get('data').strip()
    t.write(data)
    return { 'data': data }

@route(BASE_PATH + 'api/raw/write/done', name='rawwrite', method='POST')
@route(BASE_PATH + '<todo>/api/raw/write/done')
@Helper.loader
def rawwritedone(todo=None):
    if t.action_when_done in (1, 2):
        data = request.forms.get('data').strip()
        t.write(data, t.done_file)
    return { 'data': data }

@route(BASE_PATH + '<todo>/api/raw/read')
@Helper.loader
def rawread(todo=None):
    data = { 'todo': t.read() }
    if t.action_when_done in (1, 2):
        data['done'] = t.read(t.done_file)
    return data

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
@route(BASE_PATH + 'websocket')
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

