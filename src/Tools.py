# coding=utf-8
import os
import sys
import time
import tkinter.messagebox as tkmsg
import tkinter as tk
import traceback as tb
import src.Constant as Const
import base64
import subprocess


def makedir(path):
    """连续创建文件夹"""
    try:
        os.makedirs(path)
    except FileExistsError:
        return


def removeFileOrDir(path: str):
    try:
        if os.path.isdir(path):
            p, son, files = next(os.walk(path))
            files += son
            for f in files:
                removeFileOrDir(os.path.join(p, f))  # 递归清空子目录与文件
            os.rmdir(path)
        else:
            os.remove(path)
    except FileNotFoundError:
        pass


def checkProjectRunnable(projectName: str, version: str):
    try:
        target = projectName + Const.SHOW_SEPARATE + version
        p, son, files = next(os.walk(Const.SAVE_PATH))
        if target in son:
            for p2, son2, files2 in os.walk(os.path.join(p, target)):
                if Const.RUN_FILE in files2:
                    return True
    except (FileNotFoundError, StopIteration):
        return False


def checkProjectExists(projectName: str, version: str):
    try:
        target = projectName + Const.SHOW_SEPARATE + version
        p, son, files = next(os.walk(Const.SAVE_PATH))
        if target in son:
            return True
    except (FileNotFoundError, StopIteration):
        return False


def runProject(projectName: str, version: str) -> subprocess.Popen:
    target = projectName + Const.SHOW_SEPARATE + version
    dirs = os.listdir(Const.SAVE_PATH)
    if target in dirs:
        for p2, son2, files2 in os.walk(os.path.join(Const.SAVE_PATH, target)):
            if Const.RUN_FILE in files2:
                # 在对应目录启动文件
                nowPath = os.popen('cd').read().strip()
                os.chdir(p2)
                runPath = os.path.realpath(Const.RUN_FILE)
                get = subprocess.Popen(['python', f'{runPath}'], creationflags=subprocess.CREATE_NEW_CONSOLE)
                os.chdir(nowPath)
                return get
        else:
            raise FileNotFoundError(f'Can not find the correct project "{target}"\'s RunFile.')
    else:
        raise FileNotFoundError(f'Can not find the correct project "{target}"\'s RunFile.')


def deleteProject(projectName: str, version: str, ask=True):
    target = projectName + Const.SHOW_SEPARATE + version
    dirs = os.listdir(Const.SAVE_PATH)
    if target in dirs:
        deleteTarget = os.path.join(Const.SAVE_PATH, target)
        if ask:
            if tkmsg.askokcancel('要删除吗？', f'是否真的要删除"{target}"？删除操作无法撤销！请做好信息备份！'):
                removeFileOrDir(deleteTarget)
        else:
            removeFileOrDir(deleteTarget)
            print(f'Delete "{deleteTarget}" successfully.')


def askForAnswer(title: str, message: str, root: tk.Tk = None, topFrame: tk.Frame = None, destroy=True):
    """cancel: 是否取消了回答"""

    def delete(save=True):
        """
        save: 是否返回输入
        """
        root.protocol('WM_DELETE_WINDOW', lambda *a, r=root: r.destroy())
        if not save:
            s.set('')
            cancel[0] = True
        if destroy:
            root.destroy()
        alive[0] = False

    alive = [True]
    cancel = [False]
    if not root:
        root = tk.Tk()
    if not topFrame:
        topFrame = tk.Frame(root)
        topFrame.pack()
    root.title(title)
    root.protocol('WM_DELETE_WINDOW', lambda *a: delete(False))
    s = tk.StringVar()

    tk.Label(topFrame, text=message).pack(expand=True)

    frame = tk.Frame(topFrame)
    frame.pack(expand=True, fill=tk.X)

    tk.Entry(frame, textvariable=s, width=60).pack(side=tk.LEFT, expand=True, fill=tk.X)
    tk.Button(frame, text='确认', command=delete).pack(side=tk.LEFT, expand=True, fill=tk.X)

    while alive[0]:
        try:
            root.update()
        except tk.TclError:
            break
    topFrame.forget()
    return s.get(), cancel[0]


def changeEnDecode(code: str, pwd: str):
    changed = ''
    for c in code:
        c = ord(c)
        for i, p in enumerate(pwd):
            c ^= (ord(p) + i)
        changed += chr(c)
    return changed


def getLife(code: str):
    pwdLife = base64.decodebytes(code.encode()).decode().split(Const.CODE_SEPARATE)[1]
    return pwdLife


def decode(code: str, pwd=Const.ENCODING_SIGN):
    decoded, pwdLife = base64.decodebytes(code.encode()).decode().split(Const.CODE_SEPARATE)
    pwdLife = int(pwdLife)
    timeStamp = f'{time.time() // pwdLife}'
    return changeEnDecode(decoded, pwd + timeStamp)  # 用对应时间解析密码


def encode(origin: str, pwd: str = Const.ENCODING_SIGN, life=Const.PASSWORD_AVAILABLE_SECONDS):
    timeStamp = f'{time.time() // life}'  # 设置密码有效期
    encoded = changeEnDecode(origin, pwd + timeStamp) + Const.CODE_SEPARATE + f'{life}'
    return base64.encodebytes(encoded.encode()).decode().strip()


def showException(title: str = '', message='', attach=''):
    def delete():
        alive[0] = False
        root.destroy()

    alive = [True]
    root = tk.Tk()
    root.title('错误' + (':' + title) if title else '')
    root.attributes('-topmost', True)
    root.bind('<Escape>', lambda *a: delete())
    root.protocol('WM_DELETE_WINDOW', lambda *a: delete())
    exception = message if message else tb.format_exc()
    width = max(len(max(exception.splitlines(), key=len)) * 10, 300)
    height = len(exception.splitlines()) * 10 + 100
    root.geometry(f'{width}x{height}')
    b = tk.Button(root, text='确定', command=delete)
    b.focus()
    b.bind('<Return>', lambda *a: delete())
    b.pack(fill=tk.X)
    t = tk.Text(root)
    t.insert(tk.END, exception + '\n' + attach) if exception else None
    t.pack(expand=True, fill=tk.BOTH)
    print('\a' + exception, file=sys.stderr)
    root.focus_force()
    while alive[0]:
        root.update()


if __name__ == '__main__':
    print(getLife(''))
