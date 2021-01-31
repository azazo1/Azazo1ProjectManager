# coding=utf-8
import os
import threading
import time
import tkinter as tk
import tkinter.messagebox as tkmsg
from typing import List
from src.emails.EmailManager import Downloader, get_by_msg
from src.Tools import decode, showException, checkProjectRunnable, runProject, deleteProject, checkProjectExists
import src.Constant as Const
import json


def destroy(widget):
    try:
        if isinstance(widget, tk.Tk):
            widget.destroy()
        else:
            widget.forget()
    except (tk.TclError, AttributeError):
        pass


def hasUserMsg():
    return os.path.exists(Const.USER_MSG_PATH)


def getPasswordFromCache():
    with open(Const.USER_MSG_PATH) as r:
        msg = json.load(r)
    return msg[Const.PASSWORD_JSON_KEY]


def savePassword(pwd: str):
    with open(Const.USER_MSG_PATH, 'w') as w:
        json.dump(
            {Const.PASSWORD_JSON_KEY: pwd},
            w
        )
    tkmsg.showinfo('保存成功', f'你的密码已保存至"{Const.USER_MSG_PATH}".')


class UserFacer:
    def __init__(self):
        self.alive = True
        self.emails = {}  # 邮箱上对应的应用列表
        self.selected = {}
        self.downloadTargets: List[str] = []
        self.root = tk.Tk()
        self.root.title('Azazo软件管理')
        self.topFrame = None
        self.downloader = Downloader()
        if not self.checkPassword():
            self.alive = False

    def applyPassword(self, pwd: str):
        Const.PASSWORD = decode(pwd)  # 解密得到邮箱密码
        self.initDownloader()
        self.packAvailablePackage()

    def askForPassword(self):
        """
        :return: (得到的输入:str, 是否取消了输入:bool, 是否要将输入信息保存:bool)
        """
        self.changeNewTopFrame()

        def toggleShowing():
            if show.get():
                e['show'] = ''
            else:
                e['show'] = '*'

        def over(confirm=True):
            """
            confirm: 是否确认输入
            """
            self.root.protocol('WM_DELETE_WINDOW', lambda *a, r=self.root: r.destroy())
            if not confirm:
                pwd.set('')
                cancel[0] = True
            alive[0] = False

        alive = [True]
        cancel = [False]
        self.root.title('Azazo软件管理')
        self.root.protocol('WM_DELETE_WINDOW', lambda *a: over(False))
        pwd = tk.StringVar()
        show = tk.BooleanVar()
        save = tk.BooleanVar()

        tk.Label(self.topFrame, text='输入密码').pack(expand=True)

        frame = tk.Frame(self.topFrame)
        frame.pack(expand=True, fill=tk.X)

        e = tk.Entry(frame, textvariable=pwd, width=60, show='*')
        e.focus()
        e.bind('<Return>', over)
        e.pack(side=tk.LEFT, expand=True, fill=tk.X)
        b = tk.Button(frame, text='确认', command=over)
        b.pack(side=tk.LEFT, expand=True, fill=tk.X)
        frame = tk.Frame(self.topFrame)
        frame.pack(expand=True)
        tk.Checkbutton(frame, text='保存密码', variable=save).pack(side=tk.LEFT)
        tk.Checkbutton(frame, text='显示密码', command=toggleShowing, variable=show).pack(side=tk.LEFT)

        while alive[0]:
            self.root.update()
        return pwd.get(), cancel[0], save.get()

    def checkPassword(self):
        """如果玩家正确输入密码则返回True"""
        if hasUserMsg():
            p = getPasswordFromCache()
            try:
                self.applyPassword(p)
                return True
            except Exception:
                showException('密码失效', f'"{p}"无效，请联系Azazo1获取新的密码')

        while True:
            self.changeNewTopFrame()
            p, cancel, save = self.askForPassword()
            if cancel:
                return False
            if not p:
                showException('密码为空', '请重新输入密码')
                continue
            try:
                self.applyPassword(p)
                if save:  # 此时cancel只能为False
                    savePassword(p)
                return True
            except Exception:
                showException('密码错误', attach=f'"{p}"无效，请检查密码是否正确，或联系Azazo1获取密码。')

    def check(self, raises=True):
        if not self.alive and raises:
            raise Exception('This UserFacer isn\'t available now.')
        elif self.alive:
            return True

    def initDownloader(self):
        self.check()
        if self.downloader.imapObj.state != 'SELECTED':
            self.downloader.login()
        self.getAvailablePackages()

    def refresh(self):
        # 刷新项目
        self.getAvailablePackages()
        self.packAvailablePackage()

    def changeNewTopFrame(self):
        self.check()
        destroy(self.topFrame)
        self.topFrame = tk.Frame(self.root)
        self.topFrame.pack(expand=True, fill=tk.BOTH)
        return self.topFrame

    def getAvailablePackages(self):
        self.emails = self.downloader.getAllAvailableEmails()

    def packAvailablePackage(self):
        self.check()
        self.changeNewTopFrame()
        tk.Label(self.topFrame,
                 text='选择你要下载的项目',
                 width=60,
                 ).pack(expand=True, fill=tk.X)
        for UID, header_msg in self.emails.items():
            projectName = get_by_msg(header_msg, Const.PROJECT_NAME_HEADER)
            version = get_by_msg(header_msg, Const.PROJECT_VERSION_HEADER)
            showName = f'{projectName}{Const.SHOW_SEPARATE}{version}'
            totalName = f'{projectName}{Const.CODE_SEPARATE}{version}'
            frame = tk.Frame(self.topFrame)
            select = tk.BooleanVar()
            selectButton = tk.Checkbutton(frame, text=showName, variable=select)
            selectButton.pack(expand=True, fill=tk.BOTH, side=tk.LEFT)
            self.selected[totalName] = select  # 加入项目选择列表
            frame.pack(expand=True, fill=tk.BOTH)
            if checkProjectRunnable(projectName, version):  # 摆放可运行按钮
                runButton = tk.Button(frame,
                                      text='运行',
                                      command=lambda p=projectName, v=version: runProject(p, v))
                runButton.pack(side=tk.LEFT)
            if checkProjectExists(projectName, version):
                openButton = tk.Button(frame,
                                       text='打开目录',
                                       command=lambda p=projectName, v=version: os.system(
                                           f'start explorer '
                                           f'{os.path.realpath(os.path.join(Const.SAVE_PATH, p + Const.SHOW_SEPARATE + v))}'))
                openButton.pack(side=tk.LEFT)
                deleteButton = tk.Button(frame,
                                         text='删除',
                                         command=lambda p=projectName, v=version: deleteProject(p, v) or self.refresh())
                deleteButton.pack(side=tk.LEFT)
            self.root.update()
        if not self.emails:
            frame = tk.Frame(self.topFrame)
            tk.Button(frame,
                      text=f'没有项目，请稍后再试或咨询Azazo1',
                      bg='red',
                      command=lambda: self.close()
                      ).pack(expand=True, fill=tk.BOTH)
            frame.pack(expand=True, fill=tk.BOTH)
        else:
            frame = tk.Frame(self.topFrame)
            download = tk.Button(frame,
                                 text='下载',
                                 command=self.newWindowRetrieve
                                 )
            download.bind('<space>', lambda *a: download['command']())
            download.pack(side=tk.LEFT)
            refresh = tk.Button(frame,
                                text='刷新',
                                command=self.refresh
                                )
            refresh.pack(side=tk.LEFT)
            frame.pack(expand=True)

    def checkEmptySelect(self):
        for i, b in self.selected.items():
            if b.get():
                return False
        else:
            return True

    def newWindowRetrieve(self):
        """第二线程新窗口下载"""
        self.check()

        if self.checkEmptySelect():
            showException('选择错误', '请选择你要下载的项目！')
            self.refresh()
            return
        alive = [True]
        output = []

        def close():
            log = text.get(0.0, tk.END)
            log = time.asctime(time.localtime(time.time())) + '\n' + log + '-----\n'
            with open(Const.LOG_PATH, 'ab') as w:
                w.write(log.encode())
            destroy(window)
            alive[0] = False

        def rep(msg: str):
            output.append(msg)

        def checkOutput():
            if not output:
                return
            msg = output.pop(0)
            if Const.FINISH_DOWNLOAD in msg:
                close()
                p = msg.split(Const.CODE_SEPARATE)[-1]
                if tkmsg.askokcancel('下载成功', f'是否前往"{p}"查看项目。'):
                    os.system(f'start explorer "{p}"')
                return
            text.insert(tk.END, msg)

        window = tk.Tk()
        window.title('下载进度')
        window.protocol('WM_DELETE_WINDOW', lambda *args: None)
        text = tk.Text(window)
        text.pack(expand=True, fill=tk.BOTH)
        threading.Thread(target=self.retrieve, args=(rep,), daemon=True).start()
        while alive[0]:
            window.update()
            checkOutput()
        self.refresh()

    def retrieve(self, report: lambda msg: None):
        """下载选中项目"""
        self.check()
        for name, button in self.selected.items():  # type: str, tk.BooleanVar
            if not button.get():
                continue
            report(f'下载{name.split(Const.CODE_SEPARATE)}中...\n')
            projectName, version = name.split(Const.CODE_SEPARATE)
            self.downloader.fetch(projectName, version)
        else:
            report(f'下载完毕, 正在安装...\n')
            p = os.path.realpath(self.downloader.save(report=report))
            self.downloader.clearTempFile()
            report(Const.FINISH_DOWNLOAD + Const.CODE_SEPARATE + p)  # 报告：下载完成加保存路径

    def close(self):
        if self.alive:
            self.alive = False
            destroy(self.root)
            self.downloader.close()

    def __del__(self):
        self.close()

    def mainloop(self):
        if self.check(False):
            self.root.mainloop()
        else:
            destroy(self.root)


if __name__ == '__main__':
    UserFacer().mainloop()
