﻿from mock import MagicMock, PropertyMock

from remotespark.livyclientlib.livyclient import LivyClient
from remotespark.livyclientlib.livysessionstate import LivySessionState
from remotespark.utils.utils import get_connection_string
from remotespark.utils.constants import Constants


def test_doesnt_create_sql_context_automatically():
    mock_spark_session = MagicMock()
    LivyClient(mock_spark_session)
    assert not mock_spark_session.create_sql_context.called


def test_start_creates_sql_context():
    mock_spark_session = MagicMock()
    client = LivyClient(mock_spark_session)
    client.start()
    mock_spark_session.create_sql_context.assert_called_with()


def test_execute_code():
    mock_spark_session = MagicMock()
    client = LivyClient(mock_spark_session)
    client.start()
    command = "command"

    client.execute(command)

    mock_spark_session.create_sql_context.assert_called_with()
    mock_spark_session.wait_for_idle.assert_called_with(3600)
    mock_spark_session.execute.assert_called_with(command)


def test_execute_sql():
    mock_spark_session = MagicMock()
    client = LivyClient(mock_spark_session)
    client.start()
    command = "command"

    client.execute_sql(command)

    mock_spark_session.create_sql_context.assert_called_with()
    mock_spark_session.wait_for_idle.assert_called_with(3600)
    mock_spark_session.execute.assert_called_with("sqlContext.sql(\"{}\").collect()".format(command))


def test_execute_hive():
    mock_spark_session = MagicMock()
    client = LivyClient(mock_spark_session)
    client.start()
    command = "command"

    client.execute_hive(command)

    mock_spark_session.create_sql_context.assert_called_with()
    mock_spark_session.wait_for_idle.assert_called_with(3600)
    mock_spark_session.execute.assert_called_with("hiveContext.sql(\"{}\").collect()".format(command))


def test_serialize():
    url = "url"
    username = "username"
    password = "password"
    connection_string = get_connection_string(url, username, password)
    http_client = MagicMock()
    http_client.connection_string = connection_string
    kind = Constants.session_kind_spark
    session_id = "-1"
    sql_created = False
    session = MagicMock()
    session.get_state.return_value = LivySessionState(session_id, connection_string, kind, sql_created)

    client = LivyClient(session)
    client.start()

    serialized = client.serialize()

    assert serialized["connectionstring"] == connection_string
    assert serialized["id"] == "-1"
    assert serialized["kind"] == kind
    assert serialized["sqlcontext"] == sql_created
    assert serialized["version"] == "0.0.0"
    assert len(serialized.keys()) == 5


def test_close_session():
    mock_spark_session = MagicMock()
    client = LivyClient(mock_spark_session)
    client.start()

    client.close_session()

    mock_spark_session.delete.assert_called_once_with()


def test_kind():
    kind = "pyspark"
    mock_spark_session = MagicMock()
    language_mock = PropertyMock(return_value=kind)
    type(mock_spark_session).kind = language_mock
    client = LivyClient(mock_spark_session)
    client.start()

    l = client.kind

    assert l == kind


def test_session_id():
    session_id = "0"
    mock_spark_session = MagicMock()
    session_id_mock = PropertyMock(return_value=session_id)
    type(mock_spark_session).id = session_id_mock
    client = LivyClient(mock_spark_session)
    client.start()

    i = client.session_id

    assert i == session_id


def test_get_logs_returns_session_logs():
    logs = "hi"
    mock_spark_session = MagicMock()
    mock_spark_session.logs = logs
    client = LivyClient(mock_spark_session)

    res, logs_r = client.get_logs()

    assert res
    assert logs_r == logs


def test_get_logs_returns_false_with_value_error():
    err = "err"
    mock_spark_session = MagicMock()
    type(mock_spark_session).logs = PropertyMock(side_effect=ValueError(err))
    client = LivyClient(mock_spark_session)

    res, logs_r = client.get_logs()

    assert not res
    assert logs_r == err
