# -*- coding: utf-8 -*-

import re
import os
import hashlib
import datetime
from dateutil.relativedelta import relativedelta
import codecs

from bottle import get, route, request, run, template, static_file, jinja2_view, jinja2_template

from lib.atomicfile import AtomicFile

from config import TODO_FILE, TODO_FILES

class TodoLine:
    text = None
    html = None
    projects = set()
    contexts = set()
    priority = None
    line = -1
    hash = None

    def __init__(self, line):
        self.line = line

    def __unicode__(self):
        return self.text

    def __repr__(self):
        return self.text

class TodoError:
    pass

class TodoHashError:
    pass

class Todo:

    todo_file = None
    done_file = './todo/done.txt'
    #path = '/Users/hugo/Documents/Dropbox/Todo'

    contexts = []
    projects = []

    content = ''

    '''
    When mark done :
    - 0: Mark as done (x prefixed) in todo.txt
    - 1: Save in done.txt
    - 2: Both
    '''
    ACTION_WHEN_DONE = 1

    def read(self, file=None):
        with codecs.open(os.path.expanduser(file if file else self.todo_file), "r", "utf-8") as f:
            content = f.readlines()
        return content

    @staticmethod
    def get_hash(text):
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def generate(self, text, index=0):

        line = TodoLine(index)
        line.text = text.strip()

        _contexts = re.findall(r'@(\w+)', line.text)
        self.contexts = set(_contexts + list(self.contexts))

        _projects = re.findall(r'\+(\w+)', line.text)
        self.projects = set(_projects + list(self.projects))

        line.contexts = list(set([ context for context in _contexts ])) if len(_contexts) else []
        line.projects = list(set([ project for project in _projects ])) if len(_projects) else []

        #print a, type(a)
        line.html = re.sub(r'(@\w*)', r'<span class="context" data-type="context" data-value="\1">\1</span>', line.text)
        line.html = re.sub(r'(\+\w*)', r'<span class="project" data-type="project" data-value="\1">\1</span>', line.html)

        # Date handler
        dates = {
            datetime.date.today() + relativedelta(days=-2): "Avant-hier",
            datetime.date.today() + relativedelta(days=-1): "Hier",
            datetime.date.today(): "Aujourd'hui",
            datetime.date.today() + relativedelta(days=1): "Demain",
            datetime.date.today() + relativedelta(days=2): "Après-demain"
        }
        for date, string in dates.iteritems():
            line.html = re.sub(r'(' + str(date) + ')', r'<span class="date">' + string + '</span>', line.html)

        # Urls
        line.html = re.sub(r'(?P<url>https?://[^\s]+)', r'<a href="\1">\1</a>', line.html)
        #print re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', line.text)
        #print re.findall("(?P<url>https?://[^\s]+)", line.text)

        line.html = re.sub(r'([0-9]{4}-[0-9]{2}-[0-9]{2})', r'<span class="date">\1</span>', line.html)
        line.html = re.sub(r'^\(([A-Z]{1})\)', r'<span class="priority priority-\1">(\1)</span>', line.html)

        m = re.match(r'^\(([A-Z]{1})\)', line.text)
        if m:
            line.priority = m.groups(0)[0]

        line.hash = self.get_hash(line.text)

        #print ' > ', text, '|', line.text, '|', line.html, '|', line.contexts

        return line

    def load(self, contexts=[], projects=[]):
        out = []
        self.contexts = self.projects = []

        content = self.read()

        #with open(self.path + '/todo.txt', 'r') as f:
        #    content = f.readlines()

        #content = [line.strip() for line in open(self.path + '/todo.txt')]
        #print content

        count = 0
        _contexts = _projects = []
        for text in content:

            # Skip done
            if text[0] == 'x':
                count += 1
                continue

            line = self.generate(text, count)

            if contexts:
                found = True
                for context in contexts:
                    if context not in line.contexts:
                        found = False
                        break

                if not found:
                    continue

            if projects:
                found = True
                for project in projects:
                    if project not in line.projects:
                        found = False
                        break

                if not found:
                    continue

            out.append(line)
            count += 1

        def compare(x, y):
            def priority(text):
                m = re.search(r'^\(([A-Z]{1})\)', text)
                return bool(m), m.group(1) if m else 'Z' * 10

            def date(text):
                m = re.search(r'^([0-9]{4}-[0-9]{2}-[0-9]{2})', text)
                return bool(m), m.group(1) if m else '9999-99-99'

            statusx, dx = priority(x.text)
            statusy, dy = priority(y.text)

            #if statusx and statusy:
            #print statusx, statusy, date(x.text)

            if statusx and statusy and dx == dy:
                statusx, dx = date(x.text)
                statusy, dy = date(y.text)
                return 1 if dx < dy else -1
            else:
                return 1 if dx > dy else -1

        out = sorted(out, compare)

        return out

    def get_data(*args, **kwargs):
        return (args[0].load(*args[1:], **kwargs), args[0].contexts, args[0].projects)

    def verif_hash(func):
        def wrapper(*args, **kwargs):
            self, line = args[0], args[1]

            content = self.read()

            try:
                hash = kwargs['hash']
                if hash and hash != self.get_hash(content[line].strip()):
                    raise TodoHashError()
            except IndexError:
                raise TodoHashError()

            return func(*args)

        return wrapper

    @verif_hash
    def mark_as_done(self, line):
        content = self.read()

        content[line] = content[line].strip() + '\n'

        if self.ACTION_WHEN_DONE in (1, 2):
            # Save in done.txt
            deleted_line = content[line]
            if self.ACTION_WHEN_DONE == 1:
                del content[line]

        if self.ACTION_WHEN_DONE in (0, 2):
            # Mark as done
            content[line] = 'x ' + content[line]

        '''
        - 0: Mark as done
        - 1: Save in done.txt
        - 2: Both
        '''
        if self.ACTION_WHEN_DONE in (1, 2):
            done = self.read(self.done_file)
            done.append(str(datetime.date.today()) + ' ' + deleted_line)

            # First, save done file
            with AtomicFile(self.done_file, "w") as f:
                f.write(''.join(done).encode('utf-8'))

        # Save todo file !
        with AtomicFile(self.todo_file, "w") as f:
            f.write(''.join(content).encode('utf-8'))

    @verif_hash
    def edit(self, line, data):
        content = self.read()

        content[line] = data.decode('utf-8').strip() + '\n'

        # Save todo file !
        with AtomicFile(self.todo_file, "w") as f:
            f.write(''.join(content).encode('utf-8'))

        return self.generate(content[line], line)

    def new(self, data):
        content = self.read()

        data = data.decode('utf-8').strip()

        # Handle priority
        priority = ''
        m = re.match(r'^\(([A-Z]{1})\)', data)
        if m:
            priority = '(' + m.groups(0)[0] + ') '
            data = data[4:]

        # + str(datetime.date.today())
        content.append(priority + ' ' + data + '\n')

        with AtomicFile(self.todo_file, "a") as f:
            f.write(''.join(content).encode('utf-8'))

        return self.generate(data)

    @verif_hash
    def delete(self, line):
        content = self.read()

        del(content[line])

        # Save todo file !
        with AtomicFile(self.todo_file, "w") as f:
            f.write(''.join(content).encode('utf-8'))

        return True

t = Todo()
#print t.load()
#for l in t.load():
#    print l.text

#exit()

todo_selected = 0

def getRoot():
    return '/' + str(todo_selected)

class Helper:

    @staticmethod
    def loader(func):
        global t
        def wrapper(*args, **kwargs):
            global todo_selected
            if 'todo' in kwargs:
                item = TODO_FILES[int(kwargs['todo'])]
                if type(item) == str:
                    t.todo_file = item
                else:
                    _, t.todo_file = item
                todo_selected = int(kwargs['todo'])
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
def stylesheets(path):
    return static_file(path, root='static/fonts')

@route('/static/img/<path:path>')
def stylesheets(path):
    return static_file(path, root='static/img')

@route('/', name='home')
@route('/<todo>/')
@jinja2_view('main.html', template_lookup=['templates'], getRoot=getRoot)
@Helper.loader
def home(todo=None):
    #return dict(zip(['todos', 'contexts', 'projects'], t.get_data())).update({ 'todo_files': ('paf', 'pif') })
    todos, contexts, projects = t.get_data()
    return { 'todos': todos, 'contexts': contexts, 'projects': projects, 'todo_files': Helper.list(), 'todo_selected': todo_selected }

@route('/list/get', name='listget')
@route('/<todo>/list/get')
@jinja2_view('list.html', template_lookup=['templates'], getRoot=getRoot)
@Helper.loader
def list_get(todo=None):
    #return { 'todos': [ line.__dict__ for line in t.load() ]}#, 'contexts': t.contexts, 'projects': t.projects }
    return dict(zip(['todos', 'contexts', 'projects'], t.get_data()))
    #return { 'todos': t.load(), 'contexts': t.contexts, 'projects': t.projects }

@route('/contexts/get', name='contextsget')
@route('/<todo>/contexts/get')
@jinja2_view('contexts.html', template_lookup=['templates'])
@Helper.loader
def contexts_get(todo=None):
    global t
    t.load()
    return { 'contexts': t.contexts }

@route('/projects/get', name='projectsget')
@route('/<todo>/projects/get')
@jinja2_view('projects.html', template_lookup=['templates'])
@Helper.loader
def projects_get(todo=None):
    global t
    t.load()
    return { 'projects': t.projects }

#@route('/all', name='home')
#def reload():
#    return { 'todos': template('list.html', todos=t.load(), contexts=t.contexts, projects=t.projects, template_lookup=['templates']) }
    #return { 'todos': t.load(), 'contexts': t.contexts, 'projects': t.projects }

@route('/filter/<filters>', name='filter')
@route('/<todo>/filter/<filters>')
@jinja2_view('main.html', template_lookup=['templates'])
@Helper.loader
def filter(filters, todo=None):
    if filters[0] == '@':
        data = t.load(contexts=[ filters[1:] ])
    elif filters[0] == '+':
        data = t.load(projects=[ filters[1:] ])
    else:
        data = t.load()
    return { 'todos': data, 'contexts': t.contexts, 'projects': t.projects, 'filters': filters }

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

    run(host='localhost', port=8080, server=GeventWebSocketServer)
else:
    run(host='localhost', port=8080)

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

