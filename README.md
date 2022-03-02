# Find Description - VLAN traceroute

---

Данное приложение является веб модулем для 
[Zabbix Devices Output](https://github.com/ig-rudenko/Zabbix-Devices-Output)

## Find Description

Позволяет найти строку, которая имеется в описании на порту узла сети
по строгому поиску, а также используя регулярное выражение.

После того как данные интерфейсов собраны с помощью [автоматического сбора ZDO](https://github.com/ig-rudenko/Zabbix-Devices-Output#автоматический-сбор-данных)
Find Description обеспечит поиск по описанию портов, которые хранятся в файлах:

`/<zabbix-devices-output-path>/data/<device_name>/interfaces.yaml`

![img.png](static/img/img1.png)


## VLAN traceroute

Отображает топологию конкретного VLAN в виде графа

После того как данные vlan'ов собраны с помощью [автоматического сбора ZDO](https://github.com/ig-rudenko/Zabbix-Devices-Output#автоматический-сбор-данных)
VLAN traceroute обеспечит поиск используя файлы:

`/<zabbix-devices-output-path>/data/<device_name>/vlan.yaml`


![img.png](static/img/img2.png)
![img.png](static/img/img3.png)


## Установка

Скачиваем репозиторий и переходим в него

    git clone https://github.com/ig-rudenko/find_description.git && cd find_description

В файле `config` указываем полный путь до папки `zabbix-devices-output/data`, 
а также URL zabbix.

    [data]
    path=/full/path/zabbix-devices-output/data/
    zabbixurl=https://localhost/zabbix

Создаем образ docker

    docker image build -t find_descr_vlan:0.7 .

Запускаем

    docker-compose up -d

---

Подключаемся к серверу используя порт 8000

По умолчанию логин/пароль суперпользователя: root/password
