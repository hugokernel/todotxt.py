# -*- coding: utf-8 -*-

import re
import os
import hashlib
import datetime
import codecs

from dateutil.relativedelta import relativedelta

from lib.atomicfile import AtomicFile

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

    contexts = {}
    projects = {}

    content = ''

    '''
    Context order :
    - 0: Name
    - 1: Count
    '''
    context_order = 0
    project_order = 0

    '''
    When mark done :
    - 0: Mark as done (x prefixed) in todo.txt
    - 1: Save in done.txt
    - 2: Both
    '''
    action_when_done = 1

    def getFile(self, file=None):
        return os.path.expanduser(file if file else self.todo_file)

    def read(self, file=None):
        with codecs.open(self.getFile(file), "r", "utf-8") as f:
            content = f.readlines()
        return content

    def write(self, data, file=None):
        with AtomicFile(self.getFile(file if file else self.todo_file), "w") as f:
            f.write(data)
        return True

    @staticmethod
    def get_hash(text):
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def generate(self, text, index=0):

        line = TodoLine(index)
        line.text = text.strip()

        _contexts = re.findall(r'@(\w+)', line.text)
        _projects = re.findall(r'\+(\w+)', line.text)
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
        self.contexts = self.projects = {}

        content = self.read()

        self.contexts = {}
        self.projects = {}

        count = 0
        _contexts = _projects = []
        for text in content:

            # Skip done
            if text[0] == 'x':
                count += 1
                continue

            line = self.generate(text, count)

            # Get all contexts and all projects
            for context in line.contexts:
                self.contexts[context] = 1 if context not in self.contexts else self.contexts[context] + 1
            for project in line.projects:
                self.projects[project] = 1 if project not in self.projects else self.projects[project] + 1

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

            if statusx and statusy and dx == dy:
                statusx, dx = date(x.text)
                statusy, dy = date(y.text)
                return 1 if dx < dy else -1
            else:
                return 1 if dx > dy else -1

        out = sorted(out, compare)

        self.contexts_filtered = []
        self.projects_filtered = []
        for line in out:
            for context in line.contexts:
                if context not in self.contexts_filtered:
                    self.contexts_filtered.append(context)
            for project in line.projects:
                if project not in self.projects_filtered:
                    self.projects_filtered.append(project)

        if self.context_order == 0:
            self.contexts = sorted(self.contexts.items(), key=lambda x: x[0])
        elif self.context_order == 1:
            self.contexts = sorted(self.contexts.items(), key=lambda x: x[1], reverse=True)

        if self.project_order == 0:
            self.projects = sorted(self.projects.items(), key=lambda x: x[0])
        elif self.project_order == 1:
            self.projects = sorted(self.projects.items(), key=lambda x: x[1], reverse=True)

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

        if self.action_when_done in (1, 2):
            # Save in done.txt
            deleted_line = content[line]
            if self.action_when_done == 1:
                del content[line]

        if self.action_when_done in (0, 2):
            # Mark as done
            content[line] = 'x ' + content[line]

        '''
        - 0: Mark as done
        - 1: Save in done.txt
        - 2: Both
        '''
        if self.action_when_done in (1, 2):
            done = self.read(self.done_file)
            done.append(str(datetime.date.today()) + ' ' + deleted_line)

            # First, save done file
            with AtomicFile(self.getFile(self.done_file), "w") as f:
                f.write(''.join(done).encode('utf-8'))

        # Save todo file !
        with AtomicFile(self.getFile(), "w") as f:
            f.write(''.join(content).encode('utf-8'))

    @verif_hash
    def edit(self, line, data):
        content = self.read()

        content[line] = data.decode('utf-8').strip() + '\n'

        # Save todo file !
        with AtomicFile(self.getFile(self.todo_file), "w") as f:
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

        with AtomicFile(self.getFile(), "a") as f:
            f.write(''.join(content).encode('utf-8'))

        return self.generate(data)

    @verif_hash
    def delete(self, line):
        content = self.read()

        del(content[line])

        # Save todo file !
        with AtomicFile(self.getFile(), "w") as f:
            f.write(''.join(content).encode('utf-8'))

        return True

