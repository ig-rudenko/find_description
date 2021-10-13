import os

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
    # print({'data': result, 'status': 'next' if result else 'end'})
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
def get_vlan(request):
    if not request.GET.get('vlan'):
        return JsonResponse({
            'data': {}
        })

    TREE = {}
    passed = set()

    result = []

    find_vlan(
        device='SVSL-99-GP15-SSW1',
        vlan_to_find=int(request.GET['vlan']),
        dict_enter=TREE,
        passed_devices=passed,
        result=result,
        empty_ports=request.GET.get('ep'),
        only_admin_up=request.GET.get('ad')
    )

    if request.GET.get('json'):
        return JsonResponse(TREE)

    sevnet = Network(height="100%", width="100%", bgcolor="#ffffff", font_color="black")

    # Создаем невидимые элементы, для инициализации групп 0-9
    # 0 - голубой;  1 - желтый;  2 - красный;  3 - зеленый;  4 - розовый;
    # 5 - пурпурный;  6 - оранжевый;  7 - синий;  8 - светло-красный;  9 - светло-зеленый
    for i in range(10):
        sevnet.add_node(i, i, title='', group=i, hidden=True)

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
        if "ASW" in str(src):
            src_gr = 1
        if "ASW" in str(dst):
            dst_gr = 1
        if "SSW" in str(src):
            src_gr = 0
        if "SSW" in str(dst):
            dst_gr = 0
        if "SVSL-99-GP15-SSW" in src or "SVSL-99-GP15-SSW" in dst:
            src_gr = 4
            src_shape = 'diamond'
        if "-->" in str(src).lower():
            src_gr = 3
            src_shape = 'triangle'
            src_label = src.split('-->')[1]
        if "-->" in str(dst).lower():
            dst_gr = 3
            dst_shape = 'triangle'
            dst_label = src.split('-->')[1]
        if "DSL" in str(src):
            src_gr = 6
            src_shape = 'square'
        if "DSL" in str(dst):
            dst_gr = 6
            dst_shape = 'square'
        if "core" in str(src).lower() or "-cr" in str(dst).lower():
            src_gr = 4
            src_shape = 'diamond'
        if "core" in str(dst).lower() or "-cr" in str(src).lower():
            dst_gr = 4
            dst_shape = 'diamond'
        # Пустой порт
        if "p:(" in str(src).lower():
            src_gr = 9
            src_shape = 'triangle'
            src_label = src.split('p:(')[1][:-1]
        if "p:(" in str(dst).lower():
            dst_gr = 9
            dst_shape = 'triangle'
            dst_label = dst.split('p:(')[1][:-1]

        # Если стиль отображения admin down status
        if request.GET.get('ad') == 'true' and admin_status == 'down':
            w = 0.5
        print(src, admin_status)

        all_nodes = sevnet.get_nodes()
        # Создаем узел, если его не было
        if src not in all_nodes:
            sevnet.add_node(src, src_label, title=src_label, group=src_gr, shape=src_shape)

        if dst not in all_nodes:
            sevnet.add_node(dst, dst_label, title=src_label, group=dst_gr, shape=dst_shape)

        sevnet.add_edge(src, dst, value=w, title=desc)

    neighbor_map = sevnet.get_adj_list()
    nodes_count = len(sevnet.nodes)

    print('Всего узлов создано:', nodes_count)
    # add neighbor data to node hover data

    # set the physics layout of the network
    sevnet.repulsion(
        node_distance=nodes_count if nodes_count > 130 else 130,
        damping=0.89
    )

    for node in sevnet.nodes:
        node["value"] = len(neighbor_map[node["id"]]) * 3
        if "core" in node["title"].lower():
            node["value"] = 70
        if "-cr" in node["title"].lower():
            node["value"] = 100
        # Пустой порт
        if "p:(" in node["title"]:
            node["value"] = 1
        node["title"] += " Соединено:<br>" + "<br>".join(neighbor_map[node["id"]])
    # sevnet.show_buttons(filter_=True)
    sevnet.set_edge_smooth('dynamic')

    if not os.path.exists(f"{sys.path[0]}/templates/vlans"):
        os.makedirs(f"{sys.path[0]}/templates/vlans")
    sevnet.save_graph(f"{sys.path[0]}/templates/vlans/vlan{request.GET['vlan']}.html")
    print('save')
    return render(request, f"vlans/vlan{request.GET['vlan']}.html")
