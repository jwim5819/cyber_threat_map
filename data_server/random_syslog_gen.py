import random, syslog
from const import PORTMAP
from sys import exit
from time import sleep

def main():

    port_list = []
    type_attack_list = []

    for port in PORTMAP:
        port_list.append(port)
        type_attack_list.append(PORTMAP[port])

    while True:
        port = random.choice(port_list)
        type_attack = random.choice(type_attack_list)
        cve_attack = 'CVE:{}:{}'.format(
                                random.randrange(1,2000),
                                random.randrange(100,1000)
                                )

        rand_data = '{}.{}.{}.{},{}.{}.{}.{},{},{},{},{}'.format(
                                                            random.randrange(1, 256),
                                                            random.randrange(1, 256),
                                                            random.randrange(1, 256),
                                                            random.randrange(1, 256),
                                                            random.randrange(1, 256),
                                                            random.randrange(1, 256),
                                                            random.randrange(1, 256),
                                                            random.randrange(1, 256),
                                                            port,
                                                            port,
                                                            type_attack,
                                                            cve_attack
                                                            )

        syslog.syslog(rand_data)
        with open('/var/log/syslog', 'a') as syslog_file:
            syslog_file.write(rand_data + '\n')
            
        # 0.1초에서 3초 사이의 랜덤한 시간 간격으로 대기
        random_interval = random.uniform(0.5,1)
        sleep(random_interval)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        exit()