from sanic.response import json, file, redirect
from .proxy import escape_kubernet
from naas.types import t_notebook, t_scheduler, t_error, t_health
import papermill as pm
import traceback
import asyncio
import time
import os

class Notebooks():
    __logger = None
    __port = None
    __notif = None
    __loop = None
    __api_internal = None
    
    def __init__(self, logger, loop, notif):
        self.__port = int(os.environ.get('NAAS_RUNNER_PORT', 5000))
        self.__user = os.environ.get('JUPYTERHUB_USER', 'joyvan@naas.com')
        self.__single_user_api_path = os.environ.get('SINGLEUSER_PATH', '.jupyter-single-user.dev.svc.cluster.local')
        self.__api_internal = f"http://jupyter-{escape_kubernet(self.__user)}{self.__single_user_api_path}:{self.__port}/"
        self.__loop = loop
        self.__logger = logger
        self.__notif = notif
        
    def response(self, uid, res, duration, params):
        next_url = params.get('next_url', None)
        if next_url is not None:
            if "http" not in next_url:
                next_url = f'{self.__api_internal}{next_url}'
            self.__logger.info(
                {'id': uid, 'type': t_notebook, 'status': 'next_url', 'url': next_url})
            return redirect(next_url, code=302)
        else:
            res_data = self.__get_res(res)
            if res_data and res_data.get('type') == 'application/json':
                return json(res_data.get('data'))
            elif res_data:
                return file(res_data.get('data'), mimetype=res_data.get('type'))
        return json({'id': uid, "status": "Done", "time": duration})

    def __get_res(self, res):
        cells = res.get('cells')
        result = None
        result_type = None
        for cell in cells:
            outputs = cell.get('outputs', [])
            for output in outputs:
                metadata = output.get('metadata', [])
                data = output.get('data', dict())
                for meta in metadata:
                    if metadata[meta].get('naas_api'):
                        if (data.get('application/json')):
                            result_type = 'application/json'
                            result = data.get('application/json')
                        elif (data.get('text/html')):
                            result_type = 'text/html'
                            result = data.get('text/html')
                        elif (data.get('image/jpeg')):
                            result_type = 'image/jpeg'
                            result = data.get('image/jpeg')
                        elif (data.get('image/png')):
                            result_type = 'image/png'
                            result = data.get('image/png')
                        elif (data.get('image/svg+xml')):
                            result_type = 'image/svg+xml'
                            result = data.get('image/svg+xml')
                        if result_type is not None:
                            result = data.get(result_type)
        if result is None or result_type is None:
            return None
        return {'type': result_type, 'data': result}


    async def exec(self, uid, job):
        value = job.get('value', None)
        current_type = job.get('type', None)
        file_filepath = job.get('path')
        if not os.path.exists(file_filepath):
            err = 'file not found'
            self.__logger.error({'id': uid, 'type': 'filepath', "status": t_error,
                                    'filepath': file_filepath, 'error': err})
            return {"error": err}
        file_dirpath = os.path.dirname(file_filepath)
        file_filename = os.path.basename(file_filepath)
        file_filepath_out = os.path.join(file_dirpath, f'out_{file_filename}')
        params = job.get('params', dict())
        notif_down = params.get('notif_down', None)
        notif_up = params.get('notif_up', None)
        params['run_uid'] = uid
        start_time = time.time()
        res = None
        try:
            res = pm.execute_notebook(
                input_path=file_filepath,
                output_path=file_filepath_out,
                progress_bar=False,
                cwd=file_dirpath,
                parameters=params
            )
        except pm.PapermillExecutionError as err:
            self.__logger.error({'id': uid, 'type': 'PapermillExecutionError', "status": t_error,
                                    'filepath': file_filepath, 'output_filepath': file_filepath_out, 'error': str(err)})
            res = {"error": str(err)}
        except:
            tb = traceback.format_exc()
            res = {'error': str(tb)}
            self.__logger.error({'id': uid, 'type': 'Exception', "status": t_error,
                                    'filepath': file_filepath, 'output_filepath': file_filepath_out, 'error': str(tb)})
        if (not res):
            res = {'error': 'Unknow error'}
            self.__logger.error({'id': uid, 'type': 'Exception', "status": t_error,
                                    'filepath': file_filepath, 'output_filepath': file_filepath_out, 'error': res['error']})
        else:
            self.__logger.error({'id': uid, 'type': 'Exception', "status": t_health,
                                    'filepath': file_filepath, 'output_filepath': file_filepath_out})
        res['duration'] = (time.time() - start_time)
        if(res.get('error')):
            self.__notif.send_error(uid, str(res.get('error')), file_filepath)
            if (notif_down and current_type == t_scheduler):
                self.__notif.send_scheduler(uid, 'down', notif_down, file_filepath, value)
            elif (notif_down):
                self.__notif.send(uid, 'down', notif_down, file_filepath, current_type)
        elif (notif_up and current_type == t_scheduler):
            self.__notif.send_scheduler(uid, 'up', notif_down, file_filepath, value)
        elif (notif_up):
            self.__notif.send(uid, 'up', notif_up, file_filepath, current_type)
        return res
