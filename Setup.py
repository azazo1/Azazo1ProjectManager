# coding=utf-8
import os
import sys

needs = ['pip']
logName = 'Logs.txt'
print('Start')
state = 1
for p in sys.path:
    for module in needs:
        print(f'Installing:{module}')
        os.chdir(p)
        state = (os.system(f'python -m '
                           f'pip install {module} --upgrade '
                           f'-i https://pypi.douban.com/simple '
                           f'>>{logName}')
                 and state)
    if state == 0:  # 成功安装
        break
with open(logName, 'rb') as r:
    print(r.read().decode())
print('Over')
os.system('pause')
