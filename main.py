import gzhu
import os
import configparser
import time
import concurrent.futures
from datetime import datetime


class Config(object):
    def __init__(self):
        self.config_ini = configparser.ConfigParser()
        self.file_path = os.path.join(os.path.abspath('.'), '配置信息.ini')
        self.config_ini.read(self.file_path, encoding='utf-8')
        base_info = dict(self.config_ini.items('baseinfo'))
        # self.mode1time = base_info['mode1time']
        self.username = base_info['username']
        self.password = base_info['password']
        self.startTime = base_info['starttime']

        # 将三个字典的值str->list
        self.mode1 = self.re_flash('mode1')
        self.mode2 = self.re_flash('mode2')
        self.mode3 = self.re_flash('mode3')

    def re_flash(self, section: str) -> dict:
        """
        :rtype: dict
        """
        data = dict(self.config_ini.items(section))
        for k in data:
            data[k] = data[k].split(',')
        return data

    def set_config(self):
        un = input('输入登录融合门户的学号 > ')
        pw = input('输入登录融合门户的密码 > ')
        self.config_ini.set('baseinfo', 'username', un)
        self.config_ini.set('baseinfo', 'password', pw)

        while True:
            md = input(' 1 - 自动抢课\n 2 - 捡漏模式\n 3 - 替换模式\n 输入你使用的模式前面的数字代号 > ')
            if md in '123':
                md = 'mode' + md
                break
            else:
                print('模式输入错误')

        i = 1   # 计数器

        # mode3 替换模式使用特殊格式
        if md == 'mode3':
            while True:
                print('目前正在设置第{}个替换设置'.format(i))
                jxb_old = input('输入你已选的教学班号(要退的) > ').strip()
                jxb_new = input('输入你想换成的教学班号 > ').strip()
                bl = input('输入该教学班对应的板块:主修/体育/通识  (输入中文文字) > ').strip()
                self.config_ini.set(md, str(i), '{},{},{}'.format(jxb_old, jxb_new, bl))

                end_mark = input('输入0结束录入, 输入其他继续录入 > ')
                if end_mark == '0':
                    self.config_ini.write(open(self.file_path, 'w', encoding='utf-8'))
                    break
                i += 1
        else:
            while True:
                print('目前正在设置第{}个教学班设置'.format(i))
                jxb = input('输入你要选的教学班号 > ').strip()  # 去掉前后空格
                bl = input('输入该教学班对应的板块:主修/体育/通识  (输入中文文字) > ').strip()
                yxj = input('输入优先级(数字越小优先级越高, 回车默认为1) > ').strip()
                if yxj == '':
                    yxj = '1'
                self.config_ini.set(md, str(i), '{},{},{}'.format(jxb, bl, yxj))

                end_mark = input('输入0结束录入, 输入其他继续录入 > ')
                if end_mark == '0':
                    self.config_ini.write(open(self.file_path, 'w', encoding='utf-8'))
                    break
                i += 1


def print_data(data: list):
    for detail in data:
        print('课程名称:{course_name}  学分:{xf}分  教师:{jsxx}  容量:{total_result}/{jxbrl}  选课状态:{success}'
              '  课程号:{kch}  备注:{msg}'.format(course_name=detail['course_name'], xf=detail['xf'],
                                             jsxx=detail['jsxx'], total_result=detail['totalResult'],
                                             jxbrl=detail['jxbrl'], success=detail['success'],
                                             kch=detail['kch_id'], msg=detail['msg']))


def get_daixuan_info(xuanke_data: dict) -> list:
    # 待选信息
    daixuan_info = []
    for key in xuanke_data:
        jxbh = xuanke_data[key][0]  # 教学班号
        block = xuanke_data[key][1]  # 板块
        priority = int(xuanke_data[key][2]) if len(xuanke_data[key]) > 2 else 1  # 优先级

        search_data = g.search_kch(jxbh, block)
        if len(search_data) != 0:
            # 不同教学班共用一个课程号，所以取第一个即可
            query_data = g.query_task(jxbh, search_data[0]['kch_id'], block)

            """
            如果正常,search_data应该有这些key
            'course_name': data['kcmc'],        # 课程名称：大学体育4
            'kch_id': data['kch_id'],           # 课程号ID：00121704
            'jxbmc': data['jxbmc'],             # 教学班名称：(2021-2022-2)-00121704-27
            'xf': data['xf']                    # 学分： 1.0
            'do_jxb_id': data['do_jxb_id'],     # 选课教学班id，64位哈希值
            'jsxx': data['jsxx'],               # 教师信息：103526/纪彦屹/讲师（高校）
            'totalResult': data['totalResult'], # 推测是已选人数：0
            'jxbrl': data['jxbrl']              # 教学班容量：31
            'found': True,                      # 作为已查找到的标记
            'block': '通识',                     # 板块区分
            """
            # 这里发生了转换,sd的类型从list转为dict
            all_data = {}
            all_data.update(search_data[0])
            all_data.update(query_data[0])
            all_data.update({'block': block, 'priority': priority})
            daixuan_info.append(all_data)
        else:
            search_data = {
                'course_name': '',
                'kch_id': jxbh,
                'jxbmc': '',
                'xf': '',
                'do_jxb_id': '',
                'jsxx': '',
                'totalResult': '',
                'jxbrl': '',
                # 'found': False
                'success': False,  # 选课成功标记
                'kklxdm': '',
                'xkkzid': '',
                'bklx_id': '',
                'rwlx': '',
                'xkly': '',
                'msg': '',  # 存放后面选课返回的信息作为备注
                'priority': priority,
            }
            daixuan_info.append(search_data)
    # [{'cousrse_name':"...",...},{...},...]
    return daixuan_info


def xuanke1(xuanke_data: dict):
    print('正在执行xuanke1'.center(20, '*'))
    if g.xuan_ke():
        daixuan_info = get_daixuan_info(xuanke_data=xuanke_data)

        # 按优先级分组（数字越小优先级越高）
        priority_groups = {}
        for item in daixuan_info:
            p = item.get('priority', 1)
            if p not in priority_groups:
                priority_groups[p] = []
            priority_groups[p].append(item)

        try_time = 1
        for priority in sorted(priority_groups.keys()):
            group = priority_groups[priority]

            while True:
                # 当前优先级中仍需处理的条目（排除已成功和已标记满员待降级的）
                pending = [
                    item for item in group
                    if item['success'] is not True
                    and item.get('msg', '') != '已满，等待降级到低优先级'
                ]

                if not pending:
                    break

                print(''.center(30, '='))
                print('{time}  优先级{pri} 第{tt}次轮询'.format(
                    time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    pri=priority, tt=try_time))

                def submit_one(item):
                    if item['course_name'] == '':
                        item['msg'] = '教学班号:{}查找无结果'.format(item['kch_id'])
                        return item, False
                    if item['success'] is True:
                        return item, True
                    if (item['totalResult'] < item['jxbrl']) or ('通识' in item['block']):
                        status, msg = g.post_do_jxb(item)
                        item['success'] = status
                        item['msg'] = msg
                        return item, status
                    else:
                        item['success'] = True
                        item['msg'] = '已满，等待降级到低优先级'
                        return item, False

                with concurrent.futures.ThreadPoolExecutor(max_workers=len(pending)) as executor:
                    futures = [executor.submit(submit_one, item) for item in pending]
                    for future in concurrent.futures.as_completed(futures):
                        item, status = future.result()
                        if item['success'] is True and item.get('msg') != '已满，等待降级到低优先级':
                            print('{time}  {cn}选课成功'.format(
                                time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                cn=item['course_name']))
                        elif item.get('msg') == '已满，等待降级到低优先级':
                            print('{cn}已满，等待降级到低优先级'.format(cn=item['course_name']))
                        else:
                            if item.get('msg') == '一门课程只能选一个教学班，不可再选！':
                                item['success'] = True
                            print('{time}  {cn}选课失败  原因：{msg}'.format(
                                time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                cn=item['course_name'], msg=item.get('msg', '')))

                time.sleep(10)
                try_time += 1

        print('全部选课完成'.center(30, '='))
        print_data(daixuan_info)
        return
    else:
        print('选课系统暂未开放，5s后继续重复调用')
        time.sleep(5)
        xuanke1(xuanke_data=xuanke_data)


def xuanke2(xuanke_data: dict):
    try_time = 1
    while True:
        daixuan_info = get_daixuan_info(xuanke_data=xuanke_data)
        print(''.center(15, '-'))
        print('{time}  正在进行第{tt}次轮询'.format(time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'), tt=try_time))
        for daixuan in daixuan_info:
            if daixuan['course_name'] == '':
                print('教学班号:{}查找无结果'.format(daixuan['kch_id']))
                continue
            if daixuan['success'] is not True:
                status, msg = g.post_do_jxb(daixuan)
                daixuan['success'] = status
                daixuan['msg'] = msg
                if status:
                    print('{time}  {cn}选课成功'.format(time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                                    cn=daixuan['course_name']))
                else:
                    if msg == '一门课程只能选一个教学班，不可再选！':  # 没有必要再选下去，因此直接化成True即可
                        daixuan['success'] = True
                    print('{time}  {cn}选课失败  原因：{msg}'.format(time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                                              cn=daixuan['course_name'], msg=daixuan['msg']))
        # 判断是否全部选完
        success_mark = []
        for daixuan in daixuan_info:
            success_mark.append(daixuan['success'])
        if try_time % 10 == 0:
            print('\n\n')
            print(''.center(30, '='))
            print_data(daixuan_info)
        if False not in success_mark:
            print('\n\n')
            print('全部选课完成'.center(30, '='))
            print_data(daixuan_info)
            break
        time.sleep(0.1)
        try_time += 1


def xuanke3(xuanke_data: dict):
    """替换模式：监控目标教学班空位 → 退旧教学班 → 选新教学班"""
    print('正在执行xuanke3(替换模式)'.center(20, '*'))
    if not g.xuan_ke():
        print('选课系统暂未开放，10s后重试...')
        time.sleep(10)
        xuanke3(xuanke_data=xuanke_data)
        return

    # 构建替换任务列表: [(旧教学班号, 新教学班号, 板块), ...]
    tasks = []
    for key in xuanke_data:
        raw = xuanke_data[key]
        if len(raw) < 3:
            continue
        tasks.append({
            'jxb_old': raw[0],  # 已选的（要退的）
            'jxb_new': raw[1],  # 想换的
            'block': raw[2],
        })

    # 先查询所有课程信息
    for task in tasks:
        # 查旧课信息
        tmp_old = {'1': [task['jxb_old'], task['block']]}
        old_info = get_daixuan_info(xuanke_data=tmp_old)
        task['old_data'] = old_info[0] if old_info else None

        # 查新课信息
        tmp_new = {'1': [task['jxb_new'], task['block']]}
        new_info = get_daixuan_info(xuanke_data=tmp_new)
        task['new_data'] = new_info[0] if new_info else None

    try_time = 1
    while True:
        print(''.center(30, '='))
        print('{time}  正在进行第{tt}次轮询'.format(
            time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'), tt=try_time))

        for task in tasks:
            new_data = task['new_data']
            old_data = task['old_data']

            if new_data is None or new_data.get('course_name') == '':
                print('目标教学班号:{}查找无结果'.format(task['jxb_new']))
                continue
            if old_data is None or old_data.get('course_name') == '':
                print('旧教学班号:{}查找无结果（可能已退课）'.format(task['jxb_old']))
                continue

            # 如果新课已经标记为成功（已换课成功），跳过
            if new_data.get('success') is True:
                continue

            # 刷新新课容量信息
            tmp_new_refresh = {'1': [task['jxb_new'], task['block']]}
            refreshed_new = get_daixuan_info(xuanke_data=tmp_new_refresh)
            if refreshed_new:
                new_data = refreshed_new[0]

            total = new_data.get('totalResult', 0)
            jxbrl = new_data.get('jxbrl', 0)

            # 检查新课是否有空位
            if (total < jxbrl) or ('通识' in task['block']):
                print('目标教学班{}有空位({}/{})，开始替换...'.format(
                    new_data.get('course_name', ''), total, jxbrl))

                # 保留旧课的退课关键信息
                tmp_old_refresh = {'1': [task['jxb_old'], task['block']]}
                refreshed_old = get_daixuan_info(xuanke_data=tmp_old_refresh)
                if refreshed_old:
                    old_data = refreshed_old[0]

                if old_data.get('course_name') == '':
                    # 旧课可能已经不在可选列表中了，直接尝试选新课
                    print('旧教学班不在可选列表，直接选新课...')

                # 先退旧课
                if old_data.get('do_jxb_id'):
                    tk_status, tk_msg = g.tuike(old_data)
                    print('退课 {} : {}'.format(old_data.get('course_name', ''), tk_msg))
                else:
                    tk_status = True
                    tk_msg = '无旧课信息，跳过退课'

                if tk_status or '不可再选' in str(tk_msg):
                    # 再选新课
                    status, msg = g.post_do_jxb(new_data)
                    new_data['success'] = status
                    new_data['msg'] = msg
                    if status:
                        print('{time}  替换成功: {old_cn} → {new_cn}'.format(
                            time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            old_cn=old_data.get('course_name', '?'),
                            new_cn=new_data.get('course_name', '?')))
                        task['old_data'] = old_data
                        task['new_data'] = new_data
                    else:
                        print('{time}  选新课失败  原因：{msg}'.format(
                            time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            msg=msg))
                else:
                    print('退课失败: {}'.format(tk_msg))
            else:
                print('目标教学班{}已满({}/{}), 等待空位...'.format(
                    new_data.get('course_name', task['jxb_new']), total, jxbrl))

        # 判断是否全部替换完成
        all_done = True
        for task in tasks:
            nd = task.get('new_data')
            if nd is None or nd.get('success') is not True:
                all_done = False
                break
        if all_done:
            print('\n全部替换完成'.center(30, '='))
            for task in tasks:
                new_data = task.get('new_data', {})
                old_data = task.get('old_data', {})
                print('{old_cn} → {new_cn}  状态:{msg}'.format(
                    old_cn=old_data.get('course_name', '?'),
                    new_cn=new_data.get('course_name', '?'),
                    msg=new_data.get('msg', '')))
            break

        time.sleep(10)
        try_time += 1


if __name__ == '__main__':
    menustr = """
    0:配置信息助手
    1:登录教务系统
    9:退出
"""
    while True:
        os.system('cls')
        print(menustr)
        choice_menu = input('\n输入操作前面的数字标号，按回车确定 > ')

        if choice_menu == '0':
            config = Config()
            config.set_config()
        elif choice_menu == '1':
            config = Config()
            print('正在登录教务系统中...')
            g = gzhu.GZHU(config.username, config.password)
            if g.login():
                # g.xuan_ke() 执行各种初始化操作，但这需要选课系统的开放。
                print('\n登录成功!当前用户为{un}'.format(un=config.username))
                while True:
                    print('1：自动抢课\n2：捡漏模式（推荐）\n3：替换模式\n99：返回主界面')
                    choice_xuanke = input('请输入选课模式,按回车确定 > ')
                    if choice_xuanke == '1':
                        import schedule
                        schedule.every().day.at(config.startTime).do(xuanke1, xuanke_data=config.mode1)
                        print('已设定于{}开始抢课'.format(config.startTime))
                        while True:
                            schedule.run_pending()
                            time.sleep(5)

                    elif choice_xuanke == '2':
                        if g.xuan_ke():
                            xuanke2(config.mode2)
                        else:
                            print('选课系统未开放！')
                            os.system('pause')
                            continue

                    elif choice_xuanke == '3':
                        if g.xuan_ke():
                            xuanke3(config.mode3)
                        else:
                            print('选课系统未开放！')
                            os.system('pause')
                            continue

                    elif choice_xuanke == '99':
                        break

                    else:
                        print('输入有误!')
                        os.system('pause')
                        continue
                    os.system('pause')
            else:
                print('登录失败!请检查用户名和密码是否正确!高峰时期可多试几次！')
                os.system('pause')
        else:
            os._exit(0)

