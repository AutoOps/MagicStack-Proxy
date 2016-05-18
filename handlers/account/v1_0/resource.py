# -*- coding:utf-8 -*-
import logging
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
    try:
        group_id = param['group_id']
        group_list = [session.query(UserGroup).get(int(item)) for item in group_id]
        user = User(username=param['username'], password=param['password'], email=param['email'],
                    is_active=param['is_active'], uuid=param['uuid'], role=param['role'], ssh_key_pwd=param['ssh_key_pwd'],
                    group=group_list)
        session.add(user)
        session.commit()
    except Exception as e:
        logger.error(e)


def save_usergroup(session, param):
    try:
        group = UserGroup(param)
        session.add(group)
        session.commit()
    except Exception as e:
        logger.error(e)


def save_object(obj_name, param):
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
    finally:
        session.close()


def update_user(session, obj_id, param):
    try:
        group_id = param['group_id']
        group_list = [session.query(UserGroup).get(int(item)) for item in group_id]
        user = session.query(User).get(int(obj_id))
        user.username = param['username']
        user.password = param['password']
        user.email = param['email']
        user.is_active = param['is_active']
        user.uuid = param['uuid']
        user.role = param['role']
        user.ssh_key_pwd = param['ssh_key_pwd']
        user.group = group_list
        session.commit()
    except Exception as e:
        logger.error(e)


def update_usergroup(session,obj_id, param):
    try:
        session.query(UserGroup).filter_by(int(obj_id)).update(param)
        session.commit()
    except Exception as e:
        logger.error(e)


def update_object(obj_name, obj_id, param):
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
    finally:
        session.close()


def delete_object(obj_name, obj_id):
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
    finally:
        session.close()