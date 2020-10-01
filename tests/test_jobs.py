from naas.types import t_notebook, t_add, t_delete, t_update
from naas.runner.jobs import Jobs
from naas.runner.logger import Logger
import pytest  # noqa: F401
import uuid
import os

clean = True
init_data = []

user_folder_name = "test_user_folder"


async def test_init(tmp_path):
    path_srv_root = os.path.join(str(tmp_path), user_folder_name)
    os.environ["JUPYTER_SERVER_ROOT"] = str(path_srv_root)
    logger = Logger()
    uid = str(uuid.uuid4())
    jobs = Jobs(logger, clean, init_data)
    list_job = await jobs.list(uid)
    assert len(list_job) == 0


async def test_add(tmp_path):
    path_srv_root = os.path.join(str(tmp_path), user_folder_name)
    os.environ["JUPYTER_SERVER_ROOT"] = path_srv_root
    logger = Logger()
    uid = str(uuid.uuid4())
    jobs = Jobs(logger, clean, init_data)
    path = os.path.join(os.getcwd(), "test_add.py")
    target_type = t_notebook
    value = user_folder_name
    params = {}
    run_time = 0
    await jobs.update(uid, path, target_type, value, params, t_add, run_time)
    list_job = await jobs.list(uid)
    assert len(list_job) == 1
    data = await jobs.find_by_path(uid, path, target_type)
    assert data.get("value") == value
    assert data["params"] == params
    assert data["lastRun"] == run_time


async def test_clean_data(tmp_path):
    path_srv_root = os.path.join(str(tmp_path), user_folder_name)
    os.environ["JUPYTER_SERVER_ROOT"] = path_srv_root
    logger = Logger()
    uid = str(uuid.uuid4())
    jobs = Jobs(logger, clean, init_data)
    path = os.path.join(os.getcwd(), "test_add.py")
    target_type = t_notebook
    value = user_folder_name
    params = {}
    run_time = 0
    await jobs.update(uid, path, target_type, value, params, t_add, run_time)
    list_job = await jobs.list(uid)
    assert len(list_job) == 1
    jobs = None
    jobs = Jobs(logger, clean, init_data)
    list_job = await jobs.list(uid)
    assert len(list_job) == 0


async def test_delete(tmp_path):
    path_srv_root = os.path.join(str(tmp_path), user_folder_name)
    os.environ["JUPYTER_SERVER_ROOT"] = path_srv_root
    logger = Logger()
    uid = str(uuid.uuid4())
    jobs = Jobs(logger, clean, init_data)
    path = os.path.join(os.getcwd(), "test_delete.py")
    target_type = t_notebook
    value = user_folder_name
    params = {}
    run_time = 0
    await jobs.update(uid, path, target_type, value, params, t_add, run_time)
    list_job = await jobs.list(uid)
    assert len(list_job) == 1
    await jobs.update(uid, path, target_type, value, params, t_delete, run_time)
    list_job = await jobs.list(uid)
    assert len(list_job) == 0


async def test_update(tmp_path):
    path_srv_root = os.path.join(str(tmp_path), user_folder_name)
    os.environ["JUPYTER_SERVER_ROOT"] = path_srv_root
    logger = Logger()
    uid = str(uuid.uuid4())
    jobs = Jobs(logger, clean, init_data)
    path = os.path.join(os.getcwd(), "test_update.py")
    target_type = t_notebook
    value = user_folder_name
    new_value = "value_changed"
    params = {}
    run_time = 0
    await jobs.update(uid, path, target_type, value, params, t_add, run_time)
    list_job = await jobs.list(uid)
    assert len(list_job) == 1
    await jobs.update(uid, path, target_type, new_value, params, t_update, run_time)
    list_job = await jobs.list(uid)
    assert len(list_job) == 1
    data = await jobs.find_by_path(uid, path, target_type)
    assert data["value"] == new_value
    await jobs.update(uid, path, target_type, value, params, t_delete, run_time)
    list_job = await jobs.list(uid)
    assert len(list_job) == 0
