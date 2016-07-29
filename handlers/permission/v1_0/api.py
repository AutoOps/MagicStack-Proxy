# -*- coding:utf-8 -*-
import logging
import traceback
try:
    import simplejson as json
except ImportError:
    import json

from tornado.web import asynchronous, HTTPError
from common.base import RequestHandler
from sqlalchemy.orm import sessionmaker
from utils.auth import auth
from resource import get_all_objects, get_one_object, save_object, update_object, delete_object
from conf.settings import engine
from dbcollections.task.models import Task

logger = logging.getLogger('permission')

class PermObjectsHandler(RequestHandler):

    @auth
    def get(self, *args, **kwargs):
        """
        获取数据
        """
        try:
            obj_name = kwargs.get('obj_name')
            obj_uuid = kwargs.get('obj_uuid')
            logger.info('obj_uuid_id:%s'%obj_uuid)
            if obj_uuid == 'all':
                perm_objs = get_all_objects(obj_name)
            else:
                perm_objs = get_one_object(obj_name, obj_uuid)
            self.set_status(200, 'success')
            self.finish({'messege': perm_objs})
        except ValueError:
            logger.error(traceback.format_exc())
            self.set_status(400, 'value error')
            self.finish({'messege':'value error'})
        except HTTPError as http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege':http_error.log_message})
        except:
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege':'failed'})

    @auth
    def post(self, *args, **kwargs):
        """
        保存数据
        """
        try:
            obj_name = kwargs.get('obj_name')
            params = json.loads(self.request.body)
            msg = save_object(obj_name, params)
            self.set_status(200, 'success')
            self.finish({'messege': msg})
        except ValueError:
            logger.error(traceback.format_exc())
            self.set_status(400, 'value error')
            self.finish({'messege':'value error'})
        except HTTPError as http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege':http_error.log_message})
        except:
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege':'failed'})

    @auth
    def put(self, *args, **kwargs):
        """
        更新数据
        """
        try:
            obj_name = kwargs.get('obj_name')
            obj_uuid = kwargs.get('obj_uuid')
            params = json.loads(self.request.body)
            msg = update_object(obj_name, obj_uuid, params)
            self.set_status(200, 'success')
            self.finish({'messege': msg})
        except ValueError:
            logger.error(traceback.format_exc())
            self.set_status(400, 'value error')
            self.finish({'messege':'value error'})
        except HTTPError as http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege':http_error.log_message})
        except:
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege':'failed'})

    @auth
    def delete(self, *args, **kwargs):
        """
        删除数据
        """
        try:
            obj_name = kwargs.get('obj_name')
            obj_uuid = kwargs.get('obj_uuid')
            msg = delete_object(obj_name, obj_uuid)
            self.set_status(200, 'success')
            self.finish({'messege': msg})
        except ValueError:
            logger.error(traceback.format_exc())
            self.set_status(400, 'value error')
            self.finish({'messege':'value error'})
        except HTTPError as http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege':http_error.log_message})
        except:
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege':'failed'})


class PushEventHandler(RequestHandler):
    """
        查询用户推送结果
    """
    @auth
    def post(self, *agrs, **kwargs):
        Session = sessionmaker()
        Session.configure(bind=engine)
        session = Session()
        try:
            param = json.loads(self.request.body)
            tk_name = param['task_name']
            web_username = param['username']
            event = session.query(Task).filter_by(task_name=tk_name, username=web_username).first()
            result = event.result
            self.set_status(200, 'success')
            self.finish({'messege': result})
        except ValueError:
            logger.error(traceback.format_exc())
            self.set_status(400, 'value error')
            self.finish({'messege':'value error'})
        except HTTPError, http_error:
            logger.error(traceback.format_exc())
            self.set_status(http_error.status_code, http_error.log_message)
            self.finish({'messege':http_error.log_message})
        except:
            logger.error(traceback.format_exc())
            self.set_status(500, 'failed')
            self.finish({'messege':'failed'})
        finally:
            session.close()



