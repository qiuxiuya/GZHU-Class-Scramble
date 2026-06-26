"""
测试脚本：读取 配置信息.ini 中所有课程，并查询课程具体信息。

用途：
- 复用 main.py 里的配置格式
- 依次查询 mode1 / mode2 / mode3 中配置的教学班
- 输出课程名称、课程号、教学班、教师、容量等信息，方便联调测试
"""

import os
import configparser
from datetime import datetime

import gzhu
from login_cache import login_with_cache


# 本次运行内的课程详情缓存，key=(教学班号, 板块)
COURSE_DETAIL_CACHE = {}


CONFIG_FILE = '配置信息.ini'


def read_config(path: str = CONFIG_FILE):
    cfg = configparser.ConfigParser()
    cfg.read(path, encoding='utf-8')

    if 'baseinfo' not in cfg:
        raise KeyError('配置文件缺少 [baseinfo] 节')

    base_info = dict(cfg.items('baseinfo'))

    def read_section(section: str) -> dict:
        if section not in cfg:
            return {}
        data = dict(cfg.items(section))
        for k in data:
            data[k] = [x.strip() for x in data[k].split(',')]
        return data

    return {
        'username': base_info.get('username', '').strip(),
        'password': base_info.get('password', '').strip(),
        'starttime': base_info.get('starttime', '').strip(),
        'skipcapacity': [x.strip() for x in base_info.get('skipcapacity', '通识').split(',') if x.strip()],
        'requestinterval': base_info.get('requestinterval', '0.5').strip(),
        'mode1': read_section('mode1'),
        'mode2': read_section('mode2'),
        'mode3': read_section('mode3'),
    }


def parse_mode_entries(mode_data: dict, mode_name: str):
    entries = []
    for key in sorted(mode_data.keys(), key=lambda x: int(x)):
        raw = [x.strip() for x in mode_data[key] if x.strip()]
        if not raw:
            continue

        if mode_name == 'mode3':
            if len(raw) < 3:
                continue
            entries.append({
                'index': key,
                'jxb_old': raw[0],
                'jxb_new': raw[1],
                'block': raw[2],
            })
        else:
            entries.append({
                'index': key,
                'jxb': raw[0],
                'block': raw[1] if len(raw) > 1 else '',
                'priority': int(raw[2]) if len(raw) > 2 and raw[2].isdigit() else 1,
            })
    return entries


def query_detail(g: gzhu.GZHU, jxb: str, block: str):
    """根据教学班号和板块查询课程具体信息；同一教学班只查一次并复用 hash。"""
    if not jxb or not block:
        return {
            'found': False,
            'msg': '教学班号或板块为空',
            'jxb': jxb,
            'block': block,
        }

    cache_key = (jxb, block)
    cached = COURSE_DETAIL_CACHE.get(cache_key)
    if cached is not None:
        result = dict(cached)
        result['msg'] = '缓存命中'
        return result

    search_data = g.search_kch(jxb, block)
    if not search_data:
        return {
            'found': False,
            'msg': f'搜索无结果 (jxb={jxb}, block={block})',
            'jxb': jxb,
            'block': block,
        }

    # 教学班对应的课程 hash(kch_id)是固定的，首次拿到后后续直接复用。
    first = search_data[0]
    kch_id = first.get('kch_id', '')
    query_data = g.query_task(jxb, kch_id, block)

    result = {
        'found': True,
        'course_name': first.get('course_name', '?'),
        'kch_id': kch_id,
        'jxbmc': first.get('jxbmc', '?'),
        'xf': first.get('xf', '?'),
        'totalResult': first.get('totalResult', '?'),
        'block': block,
        'msg': '查询成功',
    }

    if query_data:
        detail = query_data[0]
        result.update({
            'do_jxb_id': detail.get('do_jxb_id', '?'),
            'jsxx': detail.get('jsxx', '?'),
            'jxbrl': detail.get('jxbrl', '?'),
            'kklxdm': detail.get('kklxdm', '?'),
            'xkkzid': detail.get('xkkzid', '?'),
        })
    else:
        result.update({
            'do_jxb_id': '?',
            'jsxx': '?',
            'jxbrl': '?',
            'kklxdm': '?',
            'xkkzid': '?',
            'msg': 'query_task 无结果',
        })

    COURSE_DETAIL_CACHE[cache_key] = dict(result)
    return result


def print_course(title: str, info: dict):
    print(title)
    if not info.get('found'):
        print(f"  [失败] {info.get('msg', '未知错误')}")
        return

    print(f"  课程名称: {info.get('course_name', '?')}")
    print(f"  课程号:   {info.get('kch_id', '?')}")
    print(f"  教学班:   {info.get('jxbmc', '?')}")
    print(f"  教学班ID: {info.get('do_jxb_id', '?')}")
    print(f"  学分:     {info.get('xf', '?')}")
    print(f"  教师:     {info.get('jsxx', '?')}")
    print(f"  容量:     {info.get('totalResult', '?')}/{info.get('jxbrl', '?')}")
    print(f"  板块:     {info.get('block', '?')}")
    print(f"  备注:     {info.get('msg', '')}")


def print_header(title: str):
    print('\n' + '=' * 12 + f' {title} ' + '=' * 12)


def main():
    config_path = os.path.join(os.path.abspath('.'), CONFIG_FILE)
    if not os.path.exists(config_path):
        print(f'配置文件不存在: {config_path}')
        return

    cfg = read_config(config_path)
    username = cfg['username']
    password = cfg['password']

    if not username or not password:
        print('配置文件中用户名或密码为空，请先在 main.py 的配置助手中填写')
        return

    mode1_entries = parse_mode_entries(cfg['mode1'], 'mode1')
    mode2_entries = parse_mode_entries(cfg['mode2'], 'mode2')
    mode3_entries = parse_mode_entries(cfg['mode3'], 'mode3')

    total = len(mode1_entries) + len(mode2_entries) + len(mode3_entries)
    print(f'读取到 {total} 个课程配置：mode1={len(mode1_entries)}，mode2={len(mode2_entries)}，mode3={len(mode3_entries)}')

    if total == 0:
        print('配置文件中没有课程条目，请先在 main.py 里写入课程配置')
        return

    print('正在登录教务系统...')
    g = gzhu.GZHU(username, password)
    login_ok, login_source = login_with_cache(g)
    if not login_ok:
        print('登录失败，请检查账号密码')
        return

    print('登录成功，正在初始化选课系统...')
    if login_source == 'cache':
        print('已使用本地登录缓存')
    else:
        print('已完成登录并更新本地缓存')
    if not g.xuan_ke():
        print('选课系统未开放，无法获取课程具体信息')
        return

    print('初始化成功，可用板块如下：')
    for name, data in g.xkkz_dict.items():
        print(f'  - {name}: kklxdm={data[0]}, xkkz_id={data[1]}')
    print('说明：课程 hash / 详情在本次运行内会缓存，重复教学班不会再次请求。')

    if mode1_entries:
        print_header('mode1 自动抢课')
        for entry in mode1_entries:
            print(f"\n[{entry['index']}] 教学班号={entry['jxb']} 板块={entry['block']} 优先级={entry['priority']}")
            info = query_detail(g, entry['jxb'], entry['block'])
            print_course('  课程详情', info)

    if mode2_entries:
        print_header('mode2 捡漏模式')
        for entry in mode2_entries:
            print(f"\n[{entry['index']}] 教学班号={entry['jxb']} 板块={entry['block']} 优先级={entry['priority']}")
            info = query_detail(g, entry['jxb'], entry['block'])
            print_course('  课程详情', info)

    if mode3_entries:
        print_header('mode3 替换模式')
        for entry in mode3_entries:
            print(f"\n[{entry['index']}] 旧={entry['jxb_old']} -> 新={entry['jxb_new']} 板块={entry['block']}")
            old_info = query_detail(g, entry['jxb_old'], entry['block'])
            new_info = query_detail(g, entry['jxb_new'], entry['block'])
            print_course('  旧课程详情', old_info)
            print_course('  新课程详情', new_info)

    print_header('完成')
    print('查询时间:', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


if __name__ == '__main__':
    main()
