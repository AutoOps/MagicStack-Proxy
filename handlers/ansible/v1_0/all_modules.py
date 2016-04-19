#!/usr/bin/python
# -*- coding:utf-8 -*-
import os
import json

ANSIBLE_PATHS = {'core': '/usr/lib/python2.7/site-packages/ansible/modules/core', 'extra': '/usr/lib/python2.7/site-packages/ansible/modules/extras'}

def gen_classify_modules(ppath):
    ansi_classify_modules = {}
    for key, path in ppath.items():
        ansi_modules = {}
        ansi_classify_modules[key] = {}
        if os.path.exists(path):
            for item_dir in os.listdir(path):
                if os.path.isfile(os.path.join(path, item_dir)):
                        continue
                ansi_modules[item_dir] = []
                for root_path, dirs, files in os.walk(os.path.join(path, item_dir)):
                    module_cls = {}
                    classify_name = os.path.basename(root_path)
                    module_cls[classify_name] = []
                    if dirs:
                        continue
                    for item in files:
                            if item.startswith('__') or item.endswith('pyc'):
                                continue
                            module_name = item.split('.')[0]
                            module_cls[classify_name].append(module_name)
                    ansi_modules[item_dir].append(module_cls)
            ansi_classify_modules[key] = ansi_modules
        else:
            print "ansible 目录不存在"
    return ansi_classify_modules

if __name__ == '__main__':
  ansi_classify_modules = gen_classify_modules(ANSIBLE_PATHS)
  
  print "ansi_modules_core",ansi_classify_modules['core']

  print "-----------------------------------------------"

  print "ansi_modules_extra",ansi_classify_modules['extra']
          
 
  
    
   

