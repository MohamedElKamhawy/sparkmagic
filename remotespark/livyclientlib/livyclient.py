# Copyright (c) 2015  aggftw@gmail.com
# Distributed under the terms of the Modified BSD License.

import remotespark.utils.configuration as conf
from remotespark.utils.log import Log


class LivyClient(object):
    """Spark client for Livy session"""

    def __init__(self, session):
        self.logger = Log("LivyClient")
        self._session = session
        self._execute_timeout_seconds = conf.execute_timeout_seconds()

    def __str__(self):
        return str(self._session)

    def start(self):
        self._session.create_sql_context()

    def serialize(self):
        return self._session.get_state().to_dict()

    def get_logs(self):
        try:
            return True, self._session.logs
        except ValueError as err:
            return False, "{}".format(err)

    def execute(self, commands):
        self._session.wait_for_idle(self._execute_timeout_seconds)
        return self._session.execute(commands)

    def execute_sql(self, command):
        return self.execute('sqlContext.sql("{}").collect()'.format(command))

    def execute_hive(self, command):
        return self.execute('hiveContext.sql("{}").collect()'.format(command))

    def close_session(self):
        self._session.delete()

    @property
    def kind(self):
        return self._session.kind

    @property
    def session_id(self):
        return self._session.id
