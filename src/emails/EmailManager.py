# coding=utf-8
import smtplib
import os
import traceback
import zipfile
from typing import List, Tuple, Union, Dict
import src.Constant as Const
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
import email
import email.header
import imaplib
from src.Tools import removeFileOrDir, makedir


class ProjectArchiveInfo:
    def __init__(self, fileName: str, projectName: str, version: str, data: bytes):
        self.filename = fileName
        self.projectName = projectName
        self.version = version
        self.data = data


def countTopFolderInZIP(z: zipfile.ZipFile):
    folders = set()
    for f in z.filelist:
        topFolder = f.filename.replace('\\', '/').split('/')[0]  # 获得最顶层的文件夹
        folders.add(topFolder)
    return len(folders)


def checkContainsArchive(msg: email.message.Message):
    """检查对应的信封是否是Azazo的传输文件"""
    try:
        if (msg.get(Const.PROJECT_NAME_HEADER) and
                msg.get(Const.PROJECT_VERSION_HEADER)):
            return True
    except Exception:
        traceback.print_exc()


def clearExtraPath(path: str, target: str = None) -> str:
    """
    example:
        path="D:/123/456", target="D:/123"
        I will return "123/456".
    """
    if not target:
        target = path
    root = os.path.split(target)[-1]
    if path.startswith(target):
        return root + path.split(target)[-1]
    else:
        raise ValueError('path and target are not Corresponding.')


def analysisArchive(msg: email.message.Message) -> ProjectArchiveInfo:
    """return ((filename, file-content), (ProjectName, ProjectVersion))"""
    for payload in msg.get_payload():  # type:email.message.Message
        if payload.get_content_type() == Const.ARCHIVE_TYPE:
            return ProjectArchiveInfo(
                fileName=payload.get_filename(),
                data=payload.get_payload(decode=True),
                projectName=get_by_msg(msg, Const.PROJECT_NAME_HEADER),
                version=get_by_msg(msg, Const.PROJECT_VERSION_HEADER),
            )


def get_by_msg(msg: email.message.Message, attr: str, decode=False) -> Union[bytes, str]:
    """get attribute from msg"""
    get = msg.get(attr)
    if decode:
        get, charset = email.header.decode_header(get)
        if charset:
            get = get.decode(charset)
    return get


class Uploader:
    def __init__(self, subject: str, version: str):
        self.subject, self.version = subject, version
        self._temp = []  # 临时文件夹与文件
        self._zip_name = subject + '.zip'
        self._zip_dir = Const.TEMP_FOLDER_PATH
        self._zip_path = os.path.join(self._zip_dir, self._zip_name)
        makedir(self._zip_dir)
        self._temp.append(self._zip_dir)
        self._temp.append(self._zip_path)

        self._smtpObj = smtplib.SMTP_SSL(host=Const.SMTP_HOST)
        self._message = MIMEMultipart()
        self._alive = False
        self._message.add_header('From', Const.EMAIL_ADDRESS)
        self._message.add_header('To', Const.EMAIL_ADDRESS)
        self._message.add_header('Subject', subject)
        self._message.add_header(Const.PROJECT_NAME_HEADER, subject)
        self._message.add_header(Const.PROJECT_VERSION_HEADER, version)
        self._message.attach(MIMEText(Const.SIGN, 'plain'))

    def _check(self, sit=True):
        """如果不是该状况则报错"""
        if not (self._alive == sit):
            raise RuntimeError('This Uploader is not available now.')
        return True

    def _bindToZip(self, ):
        self._check()
        with open(self._zip_path, 'rb') as r:
            data = r.read()
        attachment = MIMEApplication(data)
        attachment.add_header('Content-Disposition', 'attachment',
                              filename=self._zip_name)
        self._message.attach(attachment)

    def attachFiles(self, filePath: List[str]):
        self._check()
        for file in filePath:
            self.attachFile(file)

    def attachFile(self, filePath: str):
        """
        I will clear the path before the folder:
            D:/abc/def.ghi => def.ghi
        """
        self._check()
        with open(filePath, 'rb') as r:
            data = r.read()
        z = zipfile.ZipFile(self._zip_path, 'a')
        z.writestr(os.path.split(filePath)[-1], data)
        z.close()

    def attachFolder(self, folderPath: str):
        """
        I will clear the path before the folder:
            D:/abc/def => def
        """
        self._check()
        if not os.path.exists(folderPath):
            raise FileNotFoundError('Can not find {}'.format(folderPath))
        z = zipfile.ZipFile(self._zip_path, 'a')
        for p, childrenDir, files in os.walk(folderPath):
            for f in files:
                insidePath = os.path.join(clearExtraPath(p, folderPath), f)
                realPath = os.path.join(p, f)
                with open(realPath, 'rb') as r:
                    z.writestr(insidePath, r.read())
        z.close()

    def login(self):
        self._smtpObj.connect(host=Const.SMTP_HOST, port=Const.SMTP_PORT)
        self._smtpObj.login(Const.EMAIL_ADDRESS, Const.PASSWORD)
        self._alive = True

    def send(self):
        self._check()
        self._bindToZip()
        self._smtpObj.sendmail(Const.EMAIL_ADDRESS, Const.EMAIL_ADDRESS, self._message.as_bytes())
        self.close()

    def clearTemp(self):
        for f in self._temp:
            removeFileOrDir(f)
        self._temp.clear()

    def close(self):
        if self._alive:
            self.clearTemp()
            self._smtpObj.close()
            self._alive = False

    def __del__(self):
        self.close()


class Downloader:
    def __init__(self, save_path: str = Const.SAVE_PATH):
        self.imapObj = imaplib.IMAP4_SSL(host=Const.IMAP_HOST, port=Const.IMAP_PORT)
        self._alive = False
        self.got_files = []
        self.temp = []
        self.save_path = save_path

    def _check(self, sit=True):
        """如果不是该状况则报错"""
        if not (self._alive == sit):
            raise RuntimeError('This Downloader is not available now.')
        return True

    def login(self):
        self.imapObj.login(Const.EMAIL_ADDRESS, Const.PASSWORD)
        self._alive = True
        self.imapObj.select('INBOX')

    def getAllUid(self) -> Tuple[str]:
        self._check()
        typ, data = self.imapObj.search(None, 'ALL')
        if typ == 'OK':
            return tuple(data[0].split()[::-1])  # 倒序输出,为了让最近的在前面

    def getSubjectByUID(self, UID: Union[int, str]):
        typ, data = self.imapObj.fetch(f'{UID}', '(BODY.PEEK[HEADER])')
        if not typ == 'OK':
            raise ValueError('Invalid Email.')
        msg = email.message_from_bytes(data[0][1])
        subject = get_by_msg(msg, 'subject', True)
        return subject

    def searchFromAvailableEmails(self, projectName: str, version: str):
        """
        Find the correct project of correct version in the mailbox.
        """
        available = self.getAllAvailableEmails()
        for i, header_msg in available.items():
            try:
                msg_projectName = get_by_msg(header_msg, Const.PROJECT_NAME_HEADER)
                msg_version = get_by_msg(header_msg, Const.PROJECT_VERSION_HEADER)
                if projectName == msg_projectName and version == msg_version:  # 判断
                    return i
            except (TypeError, AttributeError):
                pass

    def getAllAvailableEmails(self) -> Dict[str, email.message.Message]:
        """
        find the emails which belongs to AzazoFilesTransportation
        return the dict contains UID and the Header Message of it.
        """
        get = {}
        for i in self.getAllUid():
            typ, data = self.imapObj.fetch(i, f'(BODY.PEEK[HEADER])')
            if not typ == 'OK':
                continue
            try:
                msg = email.message_from_bytes(data[0][1])
                if checkContainsArchive(msg):
                    get[i] = msg
            except (TypeError, AttributeError):
                pass
        return get

    def fetch(self, projectName: str, version: str):
        if not projectName:
            raise ValueError('Keyword can not be empty!')
        self._check()
        target_UID = self.searchFromAvailableEmails(projectName, version)
        if target_UID:
            typ, data = self.imapObj.fetch(target_UID, '(BODY[])')
            if not typ:
                raise Exception(f'Wrong email, whose data is {data}.')
            msg = email.message_from_bytes(data[0][1])
            get = analysisArchive(msg)
            self.got_files.append(get)
        else:
            raise FileNotFoundError(f'Can not find the email whose name is {projectName}.')

    def save(self, report=lambda msg: None, overWrite=True):
        """return the download path."""
        zip_dir = Const.TEMP_FOLDER_PATH
        to_path = self.save_path
        for projectFile in self.got_files:  # type:ProjectArchiveInfo
            folder_name = f'{projectFile.projectName}{Const.SHOW_SEPARATE}{projectFile.version}'
            if os.path.exists(os.path.join(to_path, folder_name)):  # 检查是否存在原项目
                if overWrite:
                    report(f'"{folder_name}" exists, uninstalling it... \n')
                    removeFileOrDir(os.path.join(to_path, folder_name))
                    report(f'Uninstalling "{folder_name}" successfully. \n')
                else:
                    report(f'Failed to install "{folder_name}".\n')
                    raise FileExistsError(f'"{folder_name}" has already exists. Consider to turn overWrite on.')
            report(f'Installing "{folder_name}"...\n')
            zip_path = os.path.join(zip_dir, projectFile.filename)
            makedir(zip_dir)  # 创建临时文件夹
            z = UnZIPer(zip_path, projectFile.data)
            z.extractAll(to_path, folder_name)
            self.temp.append(zip_path)
            self.temp.append(zip_dir)
            report(f'Installing "{folder_name} successfully!"\n')
        self.got_files.clear()
        return to_path

    def clearTempFile(self):
        for f in self.temp:
            removeFileOrDir(f)
        self.temp.clear()

    def close(self):
        if self._alive:
            self._alive = False
            self.clearTempFile()
            self.imapObj.close()
            self.imapObj.logout()

    def __del__(self):
        self.close()


class UnZIPer:
    def __init__(
            self,
            zipFile: str,
            content: bytes = None,
    ):
        self.zip_path = zipFile
        if content:
            with open(self.zip_path, 'wb') as w:
                w.write(content)
        self.content = self.readArchive()

    def readArchive(self):
        if not os.path.exists(self.zip_path):
            raise FileNotFoundError(f'Can not find "{self.zip_path}".')
        with open(self.zip_path, 'rb') as r:
            return r.read()

    def extractAll(self, to_path: str, dirName: str = None):
        z = zipfile.ZipFile(self.zip_path, 'r')
        # extract to one folder
        if countTopFolderInZIP(z) > 1 or dirName:
            zipName = dirName if dirName else os.path.splitext(os.path.split(self.zip_path)[-1])[0]
            to_path = os.path.join(to_path, zipName)
        makedir(to_path)
        z.extractall(to_path)
        z.close()


def testUpload():
    Const.PASSWORD = ''
    u = Uploader('', '')
    try:
        u.login()
        u.attachFolder(r'')
        u.send()
    finally:
        u.close()


def testDownload():
    d = Downloader()
    try:
        d.login()
        d.fetch('Escape_Rect', '0.47')
        d.save()
    finally:
        d.close()

if __name__ == '__main__':
    testUpload()
