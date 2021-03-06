# Copyright (c) 2015  aggftw@gmail.com
# Distributed under the terms of the Modified BSD License.

from .pandaslivyclientbase import PandasLivyClientBase


class PandasScalaLivyClient(PandasLivyClientBase):
    """Spark client for Livy session in Scala"""

    def make_context_columns(self, context_name, command):
        return '{}.sql("""{}""").columns.foreach(println)'.format(context_name, command)

    def get_records(self, context_name, command, max_take_rows):
        command = '{}.sql("""{}""").toJSON.take({}).foreach(println)'.format(context_name, command, max_take_rows)
        return self.execute(command)
