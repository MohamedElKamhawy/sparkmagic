﻿# Copyright (c) 2015  aggftw@gmail.com
# Distributed under the terms of the Modified BSD License.

import textwrap
from time import sleep, time
import remotespark.utils.configuration as conf
from remotespark.utils.constants import Constants
from remotespark.utils.log import Log
from .livyclienttimeouterror import LivyClientTimeoutError
from .livyunexpectedstatuserror import LivyUnexpectedStatusError
from .livysessionstate import LivySessionState


class LivySession(object):
    """Session that is livy specific."""

    def __init__(self, ipython_display, http_client, session_id, sql_created, properties):
        assert "kind" in properties.keys()
        kind = properties["kind"]
        self.properties = properties
        self.ipython_display = ipython_display

        status_sleep_seconds = conf.status_sleep_seconds()
        statement_sleep_seconds = conf.statement_sleep_seconds()
        create_sql_context_timeout_seconds = conf.create_sql_context_timeout_seconds()

        assert status_sleep_seconds > 0
        assert statement_sleep_seconds > 0
        assert create_sql_context_timeout_seconds > 0
        if session_id == "-1" and sql_created is True:
            raise ValueError("Cannot indicate sql state without session id.")

        self.logger = Log("LivySession")

        kind = kind.lower()
        if kind not in Constants.session_kinds_supported:
            raise ValueError("Session of kind '{}' not supported. Session must be of kinds {}."
                             .format(kind, ", ".join(Constants.session_kinds_supported)))

        if session_id == "-1":
            self._status = Constants.not_started_session_status
            sql_created = False
        else:
            self._status = Constants.busy_session_status

        self._logs = ""
        self._http_client = http_client
        self._status_sleep_seconds = status_sleep_seconds
        self._statement_sleep_seconds = statement_sleep_seconds
        self._create_sql_context_timeout_seconds = create_sql_context_timeout_seconds

        self._state = LivySessionState(session_id, http_client.connection_string,
                                       kind, sql_created)

    def __str__(self):
        return "Session id: {}\tKind: {}\tState: {}".format(self.id, self.kind, self._status)

    def get_state(self):
        return self._state

    def start(self):
        """Start the session against actual livy server."""
        self.logger.debug("Starting '{}' session.".format(self.kind))

        r = self._http_client.post("/sessions", [201], self.properties)
        self._state.session_id = str(r.json()["id"])
        self._status = str(r.json()["state"])

        self.ipython_display.writeln("Creating SparkContext as 'sc'")
        self.logger.debug("Session '{}' started.".format(self.kind))

    def create_sql_context(self):
        """Create a sqlContext object on the session. Object will be accessible via variable 'sqlContext'."""
        if self.started_sql_context:
            return

        self.logger.debug("Starting '{}' sql and hive session.".format(self.kind))

        self.ipython_display.writeln("Creating SqlContext as 'sqlContext'")
        self._create_context(Constants.context_name_sql)

        self.ipython_display.writeln("Creating HiveContext as 'hiveContext'")
        self._create_context(Constants.context_name_hive)

        self._state.sql_context_created = True

    def _create_context(self, context_type):
        if context_type == Constants.context_name_sql:
            command = self._get_sql_context_creation_command()
        elif context_type == Constants.context_name_hive:
            command = self._get_hive_context_creation_command()
        else:
            raise ValueError("Cannot create context of type {}.".format(context_type))

        try:
            self.wait_for_idle(self._create_sql_context_timeout_seconds)
            self.execute(command)
            self.logger.debug("Started '{}' {} session.".format(self.kind, context_type))
        except LivyClientTimeoutError:
            raise LivyClientTimeoutError("Failed to create the {} context in time. Timed out after {} seconds."
                                         .format(context_type, self._create_sql_context_timeout_seconds))

    @property
    def id(self):
        return self._state.session_id

    @property
    def started_sql_context(self):
        return self._state.sql_context_created

    @property
    def kind(self):
        return self._state.kind

    @property
    def logs(self):
        self._refresh_logs()
        return self._logs

    @property
    def http_client(self):
        return self._http_client

    @staticmethod
    def is_final_status(status):
        return status in Constants.final_status
    
    def execute(self, commands):
        code = textwrap.dedent(commands)

        data = {"code": code}
        r = self._http_client.post(self._statements_url(), [201], data)
        statement_id = r.json()['id']
        
        return self._get_statement_output(statement_id)

    def delete(self):
        self.logger.debug("Deleting session '{}'".format(self.id))

        if self._status != Constants.not_started_session_status and self._status != Constants.dead_session_status:
            self._http_client.delete("/sessions/{}".format(self.id), [200, 404])
            self._status = Constants.dead_session_status
            self._state.session_id = "-1"
        else:
            raise ValueError("Cannot delete session {} that is in state '{}'."
                             .format(self.id, self._status))

    def wait_for_idle(self, seconds_to_wait):
        """Wait for session to go to idle status. Sleep meanwhile. Calls done every status_sleep_seconds as
        indicated by the constructor.

        Parameters:
            seconds_to_wait : number of seconds to wait before giving up.
        """
        self._refresh_status()
        current_status = self._status
        if current_status == Constants.idle_session_status:
            return

        if current_status in Constants.final_status:
            error = "Session {} unexpectedly reached final status {}. See logs:\n{}"\
                .format(self.id, current_status, self.logs)
            self.logger.error(error)
            raise LivyUnexpectedStatusError(error)

        if seconds_to_wait <= 0.0:
            error = "Session {} did not reach idle status in time. Current status is {}."\
                .format(self.id, current_status)
            self.logger.error(error)
            raise LivyClientTimeoutError(error)

        start_time = time()
        self.logger.debug("Session {} in state {}. Sleeping {} seconds."
                          .format(self.id, current_status, seconds_to_wait))
        sleep(self._status_sleep_seconds)
        elapsed = (time() - start_time)
        return self.wait_for_idle(seconds_to_wait - elapsed)

    def _statements_url(self):
        return "/sessions/{}/statements".format(self.id)

    def _refresh_status(self):
        status = self._get_latest_status()

        if status in Constants.possible_session_status:
            self._status = status
        else:
            raise ValueError("Status '{}' not supported by session.".format(status))

        return self._status

    def _refresh_logs(self):
        self._logs = self._get_latest_logs()

    def _get_latest_status(self):
        r = self._http_client.get("/sessions/{}".format(self.id), [200])
        session = r.json()
                    
        return session['state']

    def _get_latest_logs(self):
        r = self._http_client.get("/sessions/{}/log?from=0".format(self.id), [200])
        log_array = r.json()['log']
        logs = "\n".join(log_array)

        return logs
    
    def _get_statement_output(self, statement_id):
        statement_running = True
        out = ""
        while statement_running:
            r = self._http_client.get(self._statements_url(), [200])
            statement = [i for i in r.json()["statements"] if i["id"] == statement_id][0]
            status = statement["state"]

            self.logger.debug("Status of statement {} is {}.".format(statement_id, status))

            if status == "running":
                sleep(self._statement_sleep_seconds)
            else:
                statement_running = False
                
                statement_output = statement["output"]
                if statement_output["status"] == "ok":
                    out = (True, statement_output["data"]["text/plain"])
                elif statement_output["status"] == "error":
                    out = (False, statement_output["evalue"] + "\n" +
                           "".join(statement_output["traceback"]))
                else:
                    raise ValueError("Unknown output status: '{}'".format(statement_output["status"]))

        return out

    def _get_sql_context_creation_command(self):
        if self.kind == Constants.session_kind_spark:
            sql_context_command = "val sqlContext = new org.apache.spark.sql.SQLContext(sc)\n" \
                                  "import sqlContext.implicits._"
        elif self.kind == Constants.session_kind_pyspark:
            sql_context_command = "from pyspark.sql import SQLContext\nfrom pyspark.sql.types import *\n" \
                                  "sqlContext = SQLContext(sc)"
        elif self.kind == Constants.session_kind_sparkr:
            sql_context_command = "sqlContext <- sparkRSQL.init(sc)"
        else:
            raise ValueError("Do not know how to create sqlContext in session of kind {}.".format(self.kind))

        return sql_context_command

    def _get_hive_context_creation_command(self):
        if self.kind == Constants.session_kind_spark:
            hive_context_command = "val hiveContext = new org.apache.spark.sql.hive.HiveContext(sc)"
        elif self.kind == Constants.session_kind_pyspark:
            hive_context_command = "from pyspark.sql import HiveContext\nhiveContext = HiveContext(sc)"
        elif self.kind == Constants.session_kind_sparkr:
            hive_context_command = "hiveContext <- sparkRHive.init(sc)"
        else:
            raise ValueError("Do not know how to create hiveContext in session of kind {}.".format(self.kind))

        return hive_context_command
