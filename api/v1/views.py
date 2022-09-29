import datetime

from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from find_desc.models import DevicesInfo

from configparser import ConfigParser
import json
import yaml
import sys
import os


def auth_check(requests):
    """
    Проверяет API key
    """
    # Проверяем, передан ли в заголовку ключ API
    if not requests.META.get('HTTP_API_KEY'):
        return {'error': 'Unauthorized'}, 401  # Не авторизирован
    cfg = ConfigParser()
    cfg.read(f'{sys.path[0]}/config')
    api_key = cfg.get('api', 'key')
    if api_key != requests.META['HTTP_API_KEY']:
        return {'error': 'Invalid API key'}, 400
    return None, 200


class GetStatInfo(APIView):
    """
    Выдает общее кол-во устройств в базе и кол-во собранных интерфейсов и VLAN
    """
    def get(self, request):
        status, code = auth_check(request)     # Проверка авторизации пользователя
        if status:
            return Response(status, status=code)

        return Response(
            {
                "all_devices": DevicesInfo.objects.count(),
                "stats": {
                    "devs_interfaces": DevicesInfo.objects.filter(interfaces__isnull=False).count(),
                    "devs_vlans": DevicesInfo.objects.filter(vlans__isnull=False).count()
                }
            }
        )


class GetData(APIView):
    """
    Выдаем информацию о интерфейсах и VLAN
    """
    def get(self, request, type_: str):
        status, code = auth_check(request)     # Проверка авторизации пользователя
        if status:
            return Response(status, status=code)

        if not request.GET.get('dev'):  # В запросе должно быть указано имя устройства
            return Response({'error': 'No device name'}, status=400)  # Неверный запрос

        data = get_object_or_404(DevicesInfo, device_name=request.GET['dev'])

        if type_ == 'vlans':
            print(data.vlans)
            res = json.loads(data.vlans)
            for interface in res:
                if isinstance(interface["VLAN's"], str):  # Если VLAN's представлены строкой, то превращаем в список
                    interface["VLAN's"] = interface["VLAN's"].strip().replace('\n', '').replace('\r', '').split(',')
        else:
            res = json.loads(data.interfaces)

        if not request.GET.get('interface'):  # Если интерфейс/vlan не указан явно
            return Response(res)
        try:
            intf_num = int(request.GET['interface'])
            if intf_num > len(res) or intf_num < 1:  # Если переданный номер интерфейса выходит за пределы
                return Response(
                    {'error': f"Interface number out of range for this device (max: {len(res)})"},
                    status=400
                )

        except ValueError:
            return Response(
                {'error': "Interface parameter must be integer"},
                status=400
            )  # Неверно передан интерфейс

        return Response(res[intf_num - 1])

    def post(self, request, type_: str):
        status, code = auth_check(request)     # Проверка авторизации пользователя
        if status:
            return Response(status, status=code)

        device_name: str = request.POST.get('dev', '')
        device = get_object_or_404(DevicesInfo, device_name=device_name)

        try:
            interfaces = json.loads(request.POST.get('interfaces', ''))  # Преобразуем в словарь
            # Проверяем правильность принятых данных
            for interface in interfaces:  # Проходимся по каждому интерфейсу

                # Если элемент это словарь из 4х элементов (для vlans), длина статуса больше 1 и меньше 20
                # Длина описания порта меньше 100
                # Если в URL был указан тип vlans и они есть
                if len(interface) == 4 and isinstance(interface, dict) and \
                        len(interface["Interface"]) < 40 and \
                        1 < len(interface["Status"]) < 30 and \
                        len(interface['Description']) < 100 and \
                        type_ == 'vlans':

                    # Если VLAN's переданы в виде списка чисел или в виде списка строк, которые являются цифрами
                    if isinstance(interface["VLAN's"], list) and all(
                            [
                                isinstance(v, int) or (isinstance(v, str) and v.isdigit())
                                for v in interface["VLAN's"]
                            ]
                    ):

                        # VLAN должен быть в пределах от 1 до 4096
                        for vlan in map(int, interface["VLAN's"]):
                            if vlan > 4096 or vlan < 1:
                                interface['error'] = f'Vlan must be in range 1-4096 not {vlan}'
                                print('Vlan must be in range 1-4096')
                                return Response(interface, status=400)
                        # Переводим каждый VLAN в строку
                        interface["VLAN's"] = list(map(str, interface["VLAN's"]))

                    else:
                        interface['error'] = "Vlans must be numbers"
                        print('Vlans must be numbers')
                        return Response(interface, status=400)

                # Если элемент это словарь из 3х элементов (для interfaces), Интерфейс
                # длина статуса больше 1 и меньше 20
                # Длина описания порта меньше 100
                elif len(interface) == 3 and isinstance(interface, dict) and \
                        len(interface["Interface"]) < 40 and \
                        1 < len(interface["Status"]) < 20 and \
                        len(interface['Description']) < 100 and \
                        type_ == 'interfaces':
                    pass
                else:
                    interface['error'] = 'Invalid format'
                    return Response(interface, status=400)

            # Сохраняем данные
            if type_ == 'vlans':
                update_fields = ['vlans', 'vlans_date']
                device.vlans = json.dumps(interfaces)
                device.vlans_date = datetime.datetime.now()
            else:
                update_fields = ['interfaces', 'interfaces_date']
                device.interfaces = json.dumps(interfaces)
                device.interfaces_date = datetime.datetime.now()

            device.save(update_fields=update_fields)

            return Response(interfaces)

        except json.decoder.JSONDecodeError:
            pass
        except (KeyError, TypeError):
            pass

        return Response({'error': 'Invalid format'}, status=400)


class GetVlan(APIView):
    """
    Выводит VLAN и его описание
    """
    def get(self, request, vid: int):
        try:
            vid = int(vid)  # Пробуем перевести переданный VLAN в число
            if 0 > vid or vid > 4096:  # Если переданный номер VLAN выходит за пределы
                return Response({'error': f"VLAN ({vid}) out of range [1; 4096]"}, status=400)
        except ValueError:  # Если не удалось перевести VLAN в число
            return Response({'error': "VLAN must be integer"}, status=400)  # Неверно передан VLAN
        except Exception as e:
            return Response({'error': e}, status=500)  # Ошибка на сервере

        if os.path.exists(f"{sys.path[0]}/vlan_traceroute/vlans.yaml"):  # Проверяем, есть ли файл соответствия
            with open(f"{sys.path[0]}/vlan_traceroute/vlans.yaml") as vfile:
                vlans = yaml.safe_load(vfile)
            return Response({'vlan': vid, 'description': vlans.get(vid) or ""})  # Выводим VLAN и его описание

        return Response({'vlan': vid, 'description': ''})  # Если не существует файла соответствия VLAN и описания


class GetVlanByDesc(APIView):
    """
    Осуществляет поиск VLAN по части его описания
    """
    def get(self, request, desc):
        if os.path.exists(f"{sys.path[0]}/vlan_traceroute/vlans.yaml"):
            with open(f"{sys.path[0]}/vlan_traceroute/vlans.yaml") as vfile:
                vlans = yaml.safe_load(vfile)
            result = []
            for k in vlans:  # Проходимся по каждому влану
                if desc.lower() in vlans[k].lower():  # Ищем совпадения в описании
                    result.append({'vlan': k, "description": vlans[k]})  # Добавляем совпадение в список
            return Response(result)
        return Response({""})
