import os
import sys
import yaml
from re import findall, sub
from configparser import ConfigParser
from .models import DevicesInfo
import json


def get_stat(st: str):
    devs_count = 0
    intf_count = 0
    try:
        devs_count = DevicesInfo.objects.count()
        if st == 'interfaces':
            intf_count = DevicesInfo.objects.filter(interfaces__isnull=False).count()
        elif st == 'vlans':
            intf_count = DevicesInfo.objects.filter(vlans__isnull=False).count()
    except Exception:
        pass
    return devs_count, intf_count


def find_description(finding_string: str, re_string: str):

    result = []

    all_devices = DevicesInfo.objects.all()

    # Производим поочередный поиск
    for device in all_devices:
        try:
            interfaces = json.loads(device.interfaces)
            if not interfaces:
                continue
            for line in interfaces:
                if (finding_string and finding_string.lower() in line.get('Description').lower()) or \
                        (re_string and findall(re_string, line.get('Description'))):
                    # Если нашли совпадение в строке

                    result.append({
                        'Device': device.device_name or 'Dev' + ' ' + device.ip,
                        'Interface': line['Interface'],
                        'Description': line['Description'],
                        'SavedTime': device.interfaces_date.strftime('%d.%m.%Y %H:%M:%S'),
                        'percent': '100%'
                    })
            # if result:
            #     return result  # Если на данном оборудовании были найдены совпадения, то
            #     # возвращаем их и прерываем дальнейший поиск

        except Exception as e:
            print(e)
            pass

    print(result)
    return result


def reformatting(name: str):
    with open(f'{sys.path[0]}/vlan_traceroute/name_format.yaml') as file:
        name_format = yaml.safe_load(file)

    for n in name_format:
        if n == name:  # Если имя совпадает с правильным, то отправляем его
            return name
        for pattern in name_format[n]:
            if pattern in name:  # Если паттерн содержится в исходном имени
                return sub(pattern, n, name)  # Заменяем совпадение "pattern" в названии "name" на правильное "n"
    return name


def vlan_range(vlans_ranges: list) -> set:
    """
    Преобразовывает сокращенные диапазоны VLAN'ов в развернутый список

    14, 100-103, 142 -> 14, 100, 101, 102, 103, 142

    :param vlans_ranges: Список диапазонов
    :return: развернутое множество VLAN'ов
    """
    vlans = []
    for v_range in vlans_ranges:
        if len(v_range.split()) > 1:
            vlans += list(vlan_range(v_range.split()))
        try:
            if '-' in v_range:
                parts = v_range.split('-')
                vlans += range(int(parts[0]), int(parts[1]) + 1)
            else:
                vlans.append(int(v_range))
        except ValueError:
            pass

    return set(vlans)


cfg = ConfigParser()
cfg.read(f'{sys.path[0]}/config')
data_dir = cfg.get('data', 'path')


def find_vlan(device: str, vlan_to_find: int, passed_devices: set, dict_enter: dict, result: list,
              empty_ports: str, only_admin_up: str, find_device_pattern: str):
    """
        Осуществляет поиск VLAN'ов по портам оборудования, которое расположено в папке /root_dir/data/device/
        И имеет файл vlans.yaml
        :param device: Имя устройства, на котором осуществляется поиск
        :param vlan_to_find: VLAN, который ищем
        :param passed_devices:  Уже пройденные устройства
        :param dict_enter:  Вхождение
        """

    dict_enter[device] = {}
    admin_status = ''  # Состояние порта

    passed_devices.add(device)  # Добавляем узел в список уже пройденных устройств
    if not os.path.exists(os.path.join(data_dir, device, 'vlans.yaml')):
        return
    with open(os.path.join(data_dir, device, 'vlans.yaml')) as file_yaml:
        vlans_yaml = yaml.safe_load(file_yaml)

    interfaces = vlans_yaml['data']
    if not interfaces:
        return

    intf_found_count = 0  # Кол-во найденных интерфейсов на этом устройстве

    for line in interfaces:
        vlans_list = []  # Список VLAN'ов на порту
        if 'all' in line["VLAN's"] or line["VLAN's"].strip() == 'trunk':
            # Если разрешено пропускать все вланы
            vlans_list = list(range(1, 4097))  # 1-4096
        else:
            if 'to' in line["VLAN's"]:
                # Если имеется формат "711 800 to 804 1959 1961 1994 2005"
                # Определяем диапазон 800 to 804
                vv = [list(range(int(v[0]), int(v[1]) + 1)) for v in
                      [range_ for range_ in findall(r'(\d+)\s*to\s*(\d+)', line["VLAN's"])]]
                for v in vv:
                    vlans_list += v
                # Добавляем единичные 711 800 to 801 1959 1961 1994 2005
                print(line["VLAN's"].split())

                vlans_list += line["VLAN's"].split()
            else:
                # Формат представления стандартный "trunk,123,33,10-100"
                vlans_list = vlan_range([v for v in line["VLAN's"].split(',') if
                                         v != 'trunk' and v != 'access' and v != 'hybrid' and v != 'dot1q-tunnel'])
                # Если искомый vlan находится в списке vlan'ов на данном интерфейсе

        # Если нашли влан в списке вланов
        if vlan_to_find in vlans_list or str(vlan_to_find) in vlans_list:

            intf_found_count += 1

            # Словарь для json ответа
            dict_enter[device][line["Interface"] + ' --- ' + line["Description"]] = {}

            next_device = findall(find_device_pattern, line["Description"])  # Ищем в описании порта следующий узел сети
            # Приводим к единому формату имя узла сети
            next_device = reformatting(next_device[0]) if next_device else ''

            # Пропускаем порты admin down, если включена опция only admin up
            if only_admin_up == 'true':
                admin_status = 'down' if \
                    'down' in str(line.get('Admin Status')).lower() or 'dis' in str(line.get('Admin Status')).lower() \
                    or 'admin down' in str(line.get('Status')).lower() or 'dis' in str(line.get('Status')).lower() \
                    else 'up'

            # Создаем данные для visual map
            if next_device:
                # Следующий узел сети
                result.append(
                    (
                        device,  # Устройство (название узла)
                        next_device,  # Сосед (название узла)
                        10,  # Толщина линии соединения
                        f'{device} ({line["Interface"]}) --- {line["Description"]}',  # Описание линии соединения
                        admin_status
                    )
                )
            # Порт с описанием
            elif line["Description"]:
                result.append(
                    (
                        device,  # Устройство (название узла)
                        f'{device} d:({line["Description"]})',  # Порт (название узла)
                        10,  # Толщина линии соединения
                        line["Interface"],  # Описание линии соединения
                        admin_status
                    )
                )
            # Пустые порты
            elif empty_ports == 'true':
                result.append(
                    (
                        device,  # Устройство (название узла)
                        f'{device} p:({line["Interface"]})',  # Порт (название узла)
                        5,  # Толщина линии соединения
                        line["Interface"],  # Описание линии соединения
                        admin_status
                    )
                )

            if next_device and next_device not in list(passed_devices):
                find_vlan(
                    next_device,
                    vlan_to_find,
                    passed_devices,
                    dict_enter=dict_enter[device][line["Interface"] + ' --- ' + line["Description"]],
                    result=result,
                    empty_ports=empty_ports,
                    only_admin_up=only_admin_up,
                    find_device_pattern=find_device_pattern
                )
