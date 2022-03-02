import os
import yaml
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from find_desc.finder import find_description, get_stat, find_vlan
from configparser import ConfigParser
from pyvis.network import Network
import sys
from re import findall


@login_required(login_url='accounts/login/')
def home(request):
    cfg = ConfigParser()
    zabbix_url = ''
    try:
        cfg.read(f'{sys.path[0]}/config')
        zabbix_url = cfg.get('data', 'zabbixurl')
    except Exception:
        pass

    devs_count, intf_count = get_stat('interfaces')
    return render(
        request,
        'find_descr.html',
        {
            "devs_count": devs_count,
            'intf_count': intf_count or 'None',
            'zabbix_url': zabbix_url
        }
    )


@login_required(login_url='accounts/login/')
def find_as_str(request):
    print(request.GET.dict())
    if not request.GET.get('string'):
        return JsonResponse({
            'data': []
        })
    result = find_description(
        finding_string=request.GET.get('string') if request.GET.get('type') == 'string' else '',
        re_string=request.GET.get('string') if request.GET.get('type') == 'regex' else '',
        stop_on=request.GET.get('stop_on')
    )
    print(len(result))

    return JsonResponse({
        'data': result,
        'status': 'next' if result else 'end'
    })


@login_required(login_url='accounts/login/')
def vlan_traceroute(request):
    cfg = ConfigParser()
    zabbix_url = ''
    try:
        cfg.read(f'{sys.path[0]}/config')
        zabbix_url = cfg.get('data', 'zabbixurl')
    except Exception:
        pass

    devs_count, intf_count = get_stat('vlans')
    return render(
        request,
        'vlan_traceroute.html',
        {
            "devs_count": devs_count,
            'intf_count': intf_count or 'None',
            'zabbix_url': zabbix_url
        }
    )


@login_required(login_url='accounts/login/')
def get_vlan_desc(request):
    print(request.GET)
    try:
        vlan = int(request.GET.get('vlan'))
    except ValueError:
        vlan = None

    if vlan and os.path.exists(f'{sys.path[0]}/vlan_traceroute/vlans.yaml'):
        with open(f'{sys.path[0]}/vlan_traceroute/vlans.yaml') as f:
            file = yaml.safe_load(f)
            return JsonResponse({'vlan_desc': file.get(vlan) or ''})

    return JsonResponse({})


@login_required(login_url='accounts/login/')
def get_vlan(request):
    if not request.GET.get('vlan'):
        return JsonResponse({
            'data': {}
        })
    print(request.GET)

    cfg = ConfigParser()
    cfg.read(f'{sys.path[0]}/config')

    # Определяем список устройств откуда будет начинаться трассировка vlan
    vlan_start = cfg.get('data', 'vlan_start').split(', ')

    # Определяем паттерн для поиска интерфейсов
    # Не используем configparser, так как он использует символ % как служебный, открываем просто как файл
    with open(f'{sys.path[0]}/config') as cf:
        find_device_pattern = findall('find_device_pattern=(.*)', cf.read())
    if not find_device_pattern:
        # Если не нашли, то обнуляем список начальных устройств для поиска, чтобы не запускать трассировку vlan
        vlan_start = []

    for start_dev in vlan_start:
        TREE = {}  # Древовидный вывод
        passed = set()  # Имена уже проверненных устройств
        result = []  # Список узлов сети, соседей и линий связи для визуализации

        try:
            vlan = int(request.GET['vlan'])
        except ValueError:
            break

        # трассировка vlan
        find_vlan(
            device=start_dev,
            vlan_to_find=vlan,
            dict_enter=TREE,
            passed_devices=passed,
            result=result,
            empty_ports=request.GET.get('ep'),
            only_admin_up=request.GET.get('ad'),
            find_device_pattern=find_device_pattern[0]
        )
        print(result)
        if result:  # Если поиск дал результат, то прекращаем
            break

    else:  # Если поиск не дал результатов
        TREE = {}
        result = []

    if request.GET.get('json'):  # Если необходимо отдать данные в json формате
        return JsonResponse(TREE)

    net = Network(height="100%", width="100%", bgcolor="#222222", font_color="white")

    # Создаем невидимые элементы, для инициализации групп 0-9
    # 0 - голубой;  1 - желтый;  2 - красный;  3 - зеленый;  4 - розовый;
    # 5 - пурпурный;  6 - оранжевый;  7 - синий;  8 - светло-красный;  9 - светло-зеленый
    for i in range(10):
        net.add_node(i, i, title='', group=i, hidden=True)

    # Создаем элементы и связи между ними
    for e in result:
        src = e[0]
        dst = e[1]
        w = e[2]
        desc = e[3]
        admin_status = e[4]

        # По умолчанию зеленый цвет, форма точки
        src_gr = 3
        dst_gr = 3
        src_shape = 'dot'
        dst_shape = 'dot'
        src_label = src
        dst_label = dst

        # ASW: желтый
        if "ASW" in str(src):
            src_gr = 1
        if "ASW" in str(dst):
            dst_gr = 1

        # SSW: голубой
        if "SSW" in str(src):
            src_gr = 0
        if "SSW" in str(dst):
            dst_gr = 0

        # Порт: зеленый, форма треугольника - △
        if "-->" in str(src).lower():
            src_gr = 3
            src_shape = 'triangle'
            src_label = src.split('-->')[1]
        if "-->" in str(dst).lower():
            dst_gr = 3
            dst_shape = 'triangle'
            dst_label = src.split('-->')[1]

        # DSL: оранжевый, форма квадрата - ☐
        if "DSL" in str(src):
            src_gr = 6
            src_shape = 'square'
        if "DSL" in str(dst):
            dst_gr = 6
            dst_shape = 'square'

        # CORE: розовый, форма ромба - ◊
        if "SVSL-99-GP15-SSW" in src or "SVSL-99-GP15-SSW" in dst:
            src_gr = 4
            src_shape = 'diamond'
        if "core" in str(src).lower() or "-cr" in str(dst).lower():
            src_gr = 4
            src_shape = 'diamond'
        if "core" in str(dst).lower() or "-cr" in str(src).lower():
            dst_gr = 4
            dst_shape = 'diamond'

        # Пустой порт: светло-зеленый, форма треугольника - △
        if "p:(" in str(src).lower():
            src_gr = 9
            src_shape = 'triangle'
            src_label = src.split('p:(')[1][:-1]
        if "p:(" in str(dst).lower():
            dst_gr = 9
            dst_shape = 'triangle'
            dst_label = dst.split('p:(')[1][:-1]

        # Только описание: зеленый
        if "d:(" in str(src).lower():
            src_gr = 3
            src_label = src.split('d:(')[1][:-1]
        if "d:(" in str(dst).lower():
            dst_gr = 3
            dst_label = dst.split('d:(')[1][:-1]

        # Если стиль отображения admin down status
        if request.GET.get('ad') == 'true' and admin_status == 'down':
            w = 0.5  # ширина линии связи
        print(src, admin_status)

        all_nodes = net.get_nodes()
        # Создаем узлы, если их не было
        if src not in all_nodes:
            net.add_node(src, src_label, title=src_label, group=src_gr, shape=src_shape)

        if dst not in all_nodes:
            net.add_node(dst, dst_label, title=src_label, group=dst_gr, shape=dst_shape)

        net.add_edge(src, dst, value=w, title=desc)

    neighbor_map = net.get_adj_list()
    nodes_count = len(net.nodes)

    print('Всего узлов создано:', nodes_count)
    # add neighbor data to node hover data

    # set the physics layout of the network
    net.repulsion(
        node_distance=nodes_count if nodes_count > 130 else 130,
        damping=0.89
    )

    for node in net.nodes:
        node["value"] = len(neighbor_map[node["id"]]) * 3
        if "core" in node["title"].lower():
            node["value"] = 70
        if "-cr" in node["title"].lower():
            node["value"] = 100
        # Пустой порт
        if "p:(" in node["title"]:
            node["value"] = 1
        node["title"] += " Соединено:<br>" + "<br>".join(neighbor_map[node["id"]])
    # net.show_buttons(filter_=True)
    net.set_edge_smooth('dynamic')

    if not os.path.exists(f"{sys.path[0]}/templates/vlans"):
        os.makedirs(f"{sys.path[0]}/templates/vlans")
    net.save_graph(f"{sys.path[0]}/templates/vlans/vlan{request.GET['vlan']}.html")
    print('save')
    return render(request, f"vlans/vlan{request.GET['vlan']}.html")
