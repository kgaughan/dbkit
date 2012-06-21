import web
import psycopg2
import pystache
from dbkit import Pool, transactional, query, query_value, execute, dict_set


urls = (
    '/(.*)', 'hello'
)
app = web.application(urls, globals())
pool = Pool(psycopg2, 2, "dbname=namecounter user=keith")


TEMPLATE = """<!DOCTYPE html>
<html>
    <head>
        <title>Hello!</title>
    </head>
    <body>
        <p>Hello, {{name}}!</p>
        <p>Previously, I've said hello to:</p>
        <ul>
        {{#hellos}}
            <li>{{name}}, {{n}} times</li>
        {{/hellos}}
        </ul>
    </body>
</html>"""


@transactional
def save_name(name):
    if query_value("SELECT n FROM greeted WHERE name = %s", (name,), 0) == 0:
        execute("INSERT INTO greeted (name, n) VALUES (%s, 1)", (name,))
    else:
        execute("UPDATE greeted SET n = n + 1 WHERE name = %s", (name,))


def get_names():
    return query("SELECT name, n FROM greeted ORDER BY n", factory=dict_set)


class hello(object):
    def GET(self, name):
        ctx = pool.connect()
        if not name:
            name = 'World'
        with ctx:
            hellos = list(get_names())
            save_name(name)
        return pystache.render(TEMPLATE, {'name': name, 'hellos': hellos})


if __name__ == '__main__':
    try:
        app.run()
    finally:
        pool.finalise()
