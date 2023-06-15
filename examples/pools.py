from bottle import route, run, template
import psycopg2

from dbkit import dict_set, execute, Pool, query, query_value, transactional

TEMPLATE = """<!DOCTYPE html>
<html>
    <head>
        <title>Hello!</title>
    </head>
    <body>
        <p>Hello, {{name}}!</p>
        <p>Previously, I've said hello to:</p>
        <ul>
        % for item in hellos
            <li>{{item.name}}, {{item.n}} times</li>
        % end
        </ul>
    </body>
</html>"""


pool = Pool(psycopg2, 2, "dbname=namecounter user=keith")


@transactional
def save_name(name):
    if query_value("SELECT n FROM greeted WHERE name = %s", (name,), 0) == 0:
        execute("INSERT INTO greeted (name, n) VALUES (%s, 1)", (name,))
    else:
        execute("UPDATE greeted SET n = n + 1 WHERE name = %s", (name,))


def get_names():
    return query("SELECT name, n FROM greeted ORDER BY n", factory=dict_set)


@route("/<name>")
def index(name):
    ctx = pool.connect()
    if not name:
        name = "World"
    with ctx:
        hellos = list(get_names())
        save_name(name)
    return template(TEMPLATE, name=name, hellos=hellos)


if __name__ == "__main__":
    try:
        run(host="localhost", port=8080)
    finally:
        pool.finalise()
