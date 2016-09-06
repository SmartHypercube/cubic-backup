# encoding=utf-8


import os
from os.path import join as pathjoin, relpath, getmtime, getatime, exists, splitext, split as splitpath
import quopri
import hashlib
import time


def qp_encode(s: str) -> str:
    return quopri.encodestring(s.encode()).decode()

def qp_decode(s: str) -> str:
    return quopri.decodestring(s.encode()).decode()

def f_hash(path: str, algo=hashlib.sha1) -> str:
    obj = algo()
    n = True
    with open(path, 'rb') as f:
        while n:
            s = f.read(65536)
            n = len(s)
            obj.update(s)
    return obj.hexdigest()

def localtime(t=None) -> str:
    return '%d-%02d-%02d_%02d-%02d-%02d' % time.localtime(t)[:6]

def copy(src, dst):
    n = True
    with open(src, 'rb') as fi:
        with open(dst, 'wb') as fo:
            while n:
                s = fi.read(65536)
                n = len(s)
                fo.write(s)

def log(s):
    try:
        print(s)
    except:
        pass


def ver1(cache, repository):
    log('upgrade to version 1: %s' % repository)
    pool = pathjoin(repository, '.cubicpool')
    verfile = pathjoin(pool, 'version')
    for f in os.listdir(pool):
        if f == 'version':
            continue
        n = pathjoin(f[:2], f[2:])
        os.makedirs(pathjoin(pool, splitpath(n)[0]), exist_ok=True)
        os.rename(pathjoin(pool, f), pathjoin(pool, n))
    with open(verfile, 'w') as f:
        f.write('1')
    log('upgrade done')

upgrades = [ver1]


def commit(cache, repository):
    """将一个缓存文件夹的改动提交到库"""
    log('commit %s to %s ...' % (cache, repository))
    pool = pathjoin(repository, '.cubicpool')
    verfile = pathjoin(pool, 'version')
    if not exists(pool):
        os.mkdir(pool)
        with open(verfile, 'w') as f:
            f.write(repr(len(upgrades)))

    # 版本检查
    if not exists(verfile):
        version = 0
    else:
        with open(verfile) as f:
            version = int(f.read())
    for f in upgrades[version:]:
        f(cache, repository)

    for dirpath, dirnames, filenames in os.walk(cache):
        for filename in filenames:
            # 对于每个文件
            cachepath = pathjoin(dirpath, filename)
            repopath = pathjoin(repository, relpath(pathjoin(dirpath, filename), cache))
            if exists(repopath):
                # 若库中同名版本修改时间相同则跳过
                if getmtime(cachepath) == getmtime(repopath):
                    continue
                # 若库中同名版本哈希相同则修正修改时间并跳过
                if f_hash(cachepath) == f_hash(repopath):
                    log('reset mtime: %s' % cachepath)
                    os.utime(cachepath, (getatime(cachepath), getmtime(repopath)))
                    continue
                # 这个文件被修改了
                log('file changed: %s' % cachepath)
                t = time.time()
                l, r = splitext(repopath)
                while exists(l + '.' + localtime(t) + r):
                    t += 1
                os.rename(repopath, l + '.' + localtime(t) + r)
                # fall through
            # 这是一个新文件
            log('commit new file: %s' % cachepath)
            h = f_hash(cachepath)
            hpath = pathjoin(pool, h[:2], h[2:])
            if not exists(hpath):
                os.makedirs(splitpath(hpath)[0], exist_ok=True)
                copy(cachepath, hpath)
                os.utime(cachepath, (getatime(cachepath), getmtime(hpath)))
            os.makedirs(splitpath(repopath)[0], exist_ok=True)
            os.link(hpath, repopath)
    log('commit %s to %s Done' % (cache, repository))


def main():
    from config import mappings
    for cache, repository in mappings.items():
        commit(cache, repository)

if __name__ == '__main__':
    main()
