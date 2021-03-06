# Copyright (c) 2015  aggftw@gmail.com
# Distributed under the terms of the Modified BSD License.


class Constants(object):
    config_json = "config.json"

    session_kind_spark = "spark"
    session_kind_pyspark = "pyspark"
    session_kind_sparkr = "sparkr"
    session_kinds_supported = [session_kind_spark, session_kind_pyspark, session_kind_sparkr]

    context_name_spark = "spark"
    context_name_sql = "sql"
    context_name_hive = "hive"

    lang_scala = "scala"
    lang_python = "python"
    lang_r = "r"
    lang_supported = [lang_scala, lang_python, lang_r]

    long_random_variable_name = "_yQeKOYBsFgLWWGWZJu3y"

    magics_logger_name = "magicsLogger"

    idle_session_status = "idle"
    error_session_status = "error"
    dead_session_status = "dead"
    not_started_session_status = "not_started"
    starting_session_status = "starting"
    busy_session_status = "busy"

    possible_session_status = [not_started_session_status, idle_session_status, starting_session_status,
                               busy_session_status, error_session_status, dead_session_status]
    final_status = [dead_session_status, error_session_status]

    delete_session_action = "delete"
    start_session_action = "start"
    do_nothing_action = "nothing"
