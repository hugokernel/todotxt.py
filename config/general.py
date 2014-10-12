
TODO_FILE = './todo/todo.txt'
#TODO_FILE = '~/todo.txt'
'''
TODO_FILES = (
    ( './todo/todo.txt' ),
    ( '~/todo.txt'),
    ( './todo/pouf.txt' ),
)
'''
TODO_FILES = (
    ( './todo/todo.txt', 'Todo app', { 'action_when_done': 1 } ),
    ( '~/todo.txt',      'Mine'),
    ( './todo/pouf.txt', 'Test' ),
)

HOST = '0.0.0.0'
PORT = 8080

