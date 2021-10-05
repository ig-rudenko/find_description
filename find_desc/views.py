from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from find_desc.finder import find_description, get_stat, find_vlan
from configparser import ConfigParser
from pyvis.network import Network
import sys


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
        result=result
    )

    # if request.is_ajax():
    #     return JsonResponse(TREE)

    sevnet = Network(height="100%", width="100%", bgcolor="#ffffff", font_color="black")

    # set the physics layout of the network
    sevnet.repulsion()

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

        # По умолчанию зеленый цвет, форма точки
        src_gr = 3
        dst_gr = 3
        src_shape = 'dot'
        dst_shape = 'dot'
        if "ASW" in str(src):
            src_gr = 1
        if "ASW" in str(dst):
            dst_gr = 1
        if "SSW" in str(src):
            src_gr = 0
        if "SSW" in str(dst):
            dst_gr = 0
        if "DSL" in str(src):
            src_gr = 6
            src_shape = 'square'
        if "DSL" in str(dst):
            dst_gr = 6
            dst_shape = 'square'
        if "core" in str(src).lower() or "-cr" in str(dst).lower():
            src_gr = 4
            src_shape = 'diamond'
        if "core" in str(dst).lower() or "-cr" in str(dst).lower():
            dst_gr = 4
            dst_shape = 'diamond'
        if "honet" in str(src).lower():
            src_gr = 5
            src_shape = 'triangle'
        if "honet" in str(dst).lower():
            dst_gr = 5
            dst_shape = 'triangle'

        sevnet.add_node(src, src, title=src, group=src_gr, shape=src_shape)
        sevnet.add_node(dst, dst, title=dst, group=dst_gr, shape=dst_shape)
        sevnet.add_edge(src, dst, value=w, title=desc)

    neighbor_map = sevnet.get_adj_list()
    print('Всего узлов создано:', len(sevnet.nodes))
    # add neighbor data to node hover data

    for node in sevnet.nodes:
        node["value"] = len(neighbor_map[node["id"]]) * 2
        if "core" in node["title"].lower():
            node["value"] = 70
        if "-cr" in node["title"].lower():
            node["value"] = 100
        node["title"] += " Соединено:<br>" + "<br>".join(neighbor_map[node["id"]])

    # sevnet.show_buttons(filter_=['physics'])
    # sevnet.set_options("""
    # var options = {
    #   "edges": {
    #     "color": {
    #       "inherit": true
    #     },
    #     "smooth": false
    #   },
    #   "physics": {
    #     "forceAtlas2Based": {
    #       "springLength": 100
    #     },
    #     "minVelocity": 0.75,
    #     "solver": "forceAtlas2Based"
    #   }
    # }
    # """)
    sevnet.save_graph(f"{sys.path[0]}/templates/vlan{request.GET['vlan']}.html")
    print('save')

    return render(request, f"vlan{request.GET['vlan']}.html")
