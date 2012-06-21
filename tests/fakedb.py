"""
A fake DB-API 2 driver.
"""

# DB names used to trigger certain behaviours.
INVALID_DB = 'invalid-db'
INVALID_CURSOR = 'invalid-cursor'

apilevel = '2.0'
threadsafety = 2
paramstyle = 'qmark'


def connect(database):
    return Connection(database)


class Connection(object):
    """
    A fake connection.
    """

    __slots__ = ['database', 'session', 'valid', 'cursors', 'executed']

    def __init__(self, database):
        super(Connection, self).__init__()
        self.database = database
        self.session = []
        self.cursors = 0
        self.executed = 0
        if database == INVALID_DB:
            self.valid = False
            raise OperationalError()
        self.valid = True

    def close(self):
        self.session.append('close')
        if self.database == INVALID_DB:
            raise OperationalError()

    def commit(self):
        self.session.append('commit')

    def rollback(self):
        self.session.append('rollback')

    def cursor(self):
        self.session.append('cursor')
        if not self.valid:
            raise InterfaceError()
        return Cursor(self)


class Cursor(object):
    """
    A fake cursor.
    """

    __slots__ = ['connection', 'valid', 'result']

    def __init__(self, connection):
        self.connection = connection
        self.result = None
        if connection.database == INVALID_CURSOR:
            self.valid = False
            raise OperationalError()
        connection.cursors += 1
        self.valid = True

    def close(self):
        self.connection.session.append('cursor-close')
        if not self.valid:
            raise InterfaceError()
        self.connection.cursors -= 1
        self.valid = False

    def execute(self, stmt, args=()):
        if not self.valid or not self.connection.valid:
            raise InterfaceError()
        stmt_type, = stmt.lstrip().lower().split(' ', 1)
        if stmt_type in ('select', 'update', 'insert', 'delete'):
            self.result = None if args is () else args
            self.connection.session.append(stmt_type)
            self.connection.executed += 1
        else:
            self.result = None
            raise ProgrammingError()

    def callproc(self, procname, args=()):
        if not self.valid or not self.connection.valid:
            raise InterfaceError()
        self.result = None if args is () else args
        self.connection.session.append('proc:' + procname)
        self.connection.executed += 1

    def fetchone(self):
        if not self.valid:
            raise InterfaceError()
        result = self.result
        self.result = None
        return result


class Warning(StandardError):
    pass


class Error(StandardError):
    pass


class InterfaceError(Error):
    pass


class DatabaseError(Error):
    pass


class DataError(DatabaseError):
    pass


class OperationalError(DatabaseError):
    pass


class IntegrityError(DatabaseError):
    pass


class InternalError(DatabaseError):
    pass


class ProgrammingError(DatabaseError):
    pass


class NotSupportedError(DatabaseError):
    pass
