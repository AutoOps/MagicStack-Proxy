# -*- coding:utf-8 -*-
import logging
import datetime
from sqlalchemy.orm import sessionmaker
from conf.settings import engine
from dbcollections.account.models import User, UserGroup

logger = logging.getLogger()


def user_to_dict(user):
    """
    user object transfer to dict
    """
    res = {}
    try:
        group_list = []
        if user.group:
            for item in user.group:
                group_list.append(usergroup_to_dict(item))
        res = dict(id=user.id, username=user.username, password=user.password, email=user.email,
                   is_active=user.is_active, uuid=user.uuid, role=user.role, ssh_key_pwd=user.ssh_key_pwd,
                   group=group_list)
    except Exception as e:
        logger.error(e)
    return res


def usergroup_to_dict(group):
    res = dict(id=group.id, name=group.name, comment=group.comment)
    return res


def get_all_objects(obj_name):
    Session = sessionmaker()
    Session.configure(bind=engine)
    session = Session()
    res = []
    try:
        if obj_name == 'User':
            users = session.query(User).all()
            if users:
                for item in users:
                    res.append(user_to_dict(item))
        elif obj_name == 'UserGroup':
            groups = session.query(UserGroup).all()
            for item in groups:
                res.append(usergroup_to_dict(item))
    except Exception as e:
        logger.error(e)
    finally:
        session.close()
    return res


def get_one_object(obj_name,obj_id):
    Session = sessionmaker()
    Session.configure(bind=engine)
    session = Session()
    res = {}
    try:
        if obj_name == 'User':
            user = session.query(User).get(int(obj_id))
            res = user_to_dict(user)
        elif obj_name == 'UserGroup':
            group = session.query(UserGroup).get(int(obj_id))
            res = usergroup_to_dict(group)
    except Exception as e:
        logger.error(e)
    finally:
        session.close()
    return res


def save_user(session, param):
    now = datetime.datetime.now()
    try:
        group_ids = param['group_ids']
        group_list = [session.query(UserGroup).get(int(item)) for item in group_ids]
        user = User(username=param['username'], password=param['password'], email=param['email'],
                    is_active=param['is_active'], uuid=param['uuid'], role=param['role'], ssh_key_pwd=param['ssh_key_pwd'],
                    group=group_list, date_joined=now)
        session.add(user)
        session.commit()
    except Exception as e:
        logger.error(e)


def save_usergroup(session, param):
    try:
        group = UserGroup(name=param['name'], comment=param['comment'])
        for user_id in param['selected_ids']:
            user = session.query(User).get(user_id)
            user.group.add(group)
            session.add(user)
            session.commit()
    except Exception as e:
        logger.error(e)


def save_object(obj_name, param):
    msg = 'success'
    Session = sessionmaker()
    Session.configure(bind=engine)
    session = Session()
    try:
        if obj_name == 'User':
            save_user(session, param)
        elif obj_name == 'UserGroup':
            save_usergroup(session, param)
    except Exception as e:
        logger.error(e)
        msg = 'error'
    finally:
        session.close()
    return msg


def update_user(session, obj_id, param):
    try:
        group_ids = param['group_ids']
        group_list = [session.query(UserGroup).get(int(item)) for item in group_ids]
        user = session.query(User).get(int(obj_id))
        user.password = param['password']
        user.email = param['email']
        user.is_active = param['is_active']
        user.role = param['role']
        user.group = group_list
        session.commit()
    except Exception as e:
        logger.error(e)


def update_usergroup(session,obj_id, param):
    try:
        group = session.query(UserGroup).get(int(obj_id)).update(name=param.get('name'), comment=param.get('comment'))
        group.user.clean()
        for user_id in param['selected_ids']:
            user = session.query(User).get(int(user_id))
            user.group.add(group)
            session.commit()
        session.commit()
    except Exception as e:
        logger.error(e)


def update_object(obj_name, obj_id, param):
    msg = 'success'
    Session = sessionmaker()
    Session.configure(bind=engine)
    session = Session()
    try:
        if obj_name == 'User':
            update_user(session, obj_id, param)
        elif obj_name == 'UserGroup':
            update_usergroup(session, obj_id, param)
    except Exception as e:
        logger.error(e)
        msg = 'error'
    finally:
        session.close()
    return msg


def delete_object(obj_name, obj_id):
    msg = 'success'
    Session = sessionmaker()
    Session.configure(bind=engine)
    session = Session()
    del_obj = None
    try:
        if obj_name == 'User':
            del_obj = session.query(User).get(int(obj_id))
        elif obj_name == 'UserGroup':
            del_obj = session.query(UserGroup).get(int(obj_id))
        if del_obj is None:
            raise ValueError(u'对象不存在')
        session.delete(del_obj)
        session.commit()
    except Exception as e:
        logger.error(e)
        msg = 'error'
    finally:
        session.close()
    return msg
