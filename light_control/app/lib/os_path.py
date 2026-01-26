"""A subset of the os.path functions from python that are laking in micropython"""

import os

def make_path(*args):
    """
    Attempt to create a path made up of the elements in args.
    if the last arg does not end in a slash an empty file will be
    created.
    
    The the first argument must always begin with a / and describe the
    full path to be created.
    
    """
    
    filespec = join(*args)
    filename = ''
    
    # for this simple version, alway start from root
    if not filespec or not filespec[0] == '/':
        raise AssertionError('filespec must begin with a slash')
        
    # save the current working dir
    save_dir = os.getcwd()
    out = True
    
    # split it into directories and create them if needed
    path_list = filespec.split("/")
    if path_list and path_list[0] == '':
        path_list[0] = '/'
        
    if path_list and not path_list[-1].endswith('/'):
        filename = path_list.pop() # save the file name element
        
    current_path= path_list[0]
    try:
        for d in path_list:
            os.chdir(current_path)
            if d != '/' and not d in os.listdir():
                os.mkdir(d)
                
            current_path = join(current_path,d)
    except Exception as e:
        print(f'Unable to create path: {current_path}',str(e))
        out = False
        
    if filename:
        f = open(join(current_path,filename),'a')
        f.close()
    
    os.chdir(save_dir) # restore the working dir
    return out


def join(*args):
    """Roughly replicate python os.path.join"""
    
    arg_list = [x.strip() for x in args]
    out = ''

    out = '/'.join(arg_list).replace('//','/')
        
    return out


def is_dir(node):
    """return true if node name is in the current working
direcory and it is a directory itself.

    node may be a path."""
    
    path = ''
    if '/' in node:
        path = node.rstrip('/')
        i = path.rfind('/')
        if i < 0:
            node = path
            path = ''
        else:
            node = path[i+1:]
            path = path[:i+1]

    d = os.ilistdir(path)
    for e in d:
        if node == e[0]:
            if e[1] == 0x4000:
                return True
            break
        
    return False


def exists(node):
    try:
        with open(node,'r') as f:
            return True
    except OSError:
        return False
    

def delete_all(path):
    """Delete all nodes in the last element of the path.
    if the last element in the path is a directory
    delete all down to and including that directory.

    If the last element in path is not a directory, delete only that node.
        
    path must orginate at the root directory '/'
    
    Return True if successful
    
    """
    
    out = True

    if not path or path[0] != '/': return False

    path_list = path.split('/')

    if not path_list: return False
    
    path_list.pop(0) # remove the root reference

    if not path_list: return out # dont delete the root dir

    try:
        current_path = '/' + '/'.join(path_list)
        if is_dir(current_path):
            file_list = os.listdir(current_path)
            for f in file_list:
                delete_all(join(current_path,f))
            os.rmdir(current_path)
            path_list.pop()
        else:
            os.remove(current_path)
    except Exception as e:
        out = False
       
    return out    
