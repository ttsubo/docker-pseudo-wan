import os.path
from fabric.api import local
from netaddr.ip import IPNetwork, IPAddress
from optparse import OptionParser
import sys
import os

serial_number = 0

def install_docker_and_tools():
    print "start install packages of test environment."
    local("apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys "
          "36A1D7869245C8950F966E92D8576A8BA88D21E9", capture=True)
    local('sh -c "echo deb https://get.docker.io/ubuntu docker main > /etc/apt/sources.list.d/docker.list"',
          capture=True)
    local("apt-get update", capture=True)
    local("apt-get install -y --force-yes lxc-docker-1.7.0 bridge-utils tcpdump", capture=True)
    local("ln -sf /usr/bin/docker.io /usr/local/bin/docker", capture=True)
    local("wget https://raw.github.com/jpetazzo/pipework/master/pipework -O /usr/local/bin/pipework",
          capture=True)
    local("chmod 755 /usr/local/bin/pipework", capture=True)
    local("docker pull ubuntu:14.04.2", capture=True)
    local("docker pull ttsubo/ryubgp-w-ovs2_3_1:latest", capture=True)
    local("mkdir -p /var/run/netns", capture=True)


class Router(object):
    def __init__(self, name):
        self.name = name
        self.image = 'ttsubo/ryubgp-w-ovs2_3_1:latest'

        if self.name in get_containers():
            print ("### Delete connertainer {0} ###".format(self.name))
            self.stop()

    def run(self):
        current_dir = os.getcwd()
        c = CmdBuffer(' ')
        c << "docker run --privileged=true"
        c << "-v {0}/{1}:/tmp".format(current_dir, self.name)
        c << "--name {0} -h {1} -itd {1}".format(self.name, self.image)
        c << "bash"

        print ("### Create connertainer {0} ###".format(self.name))
        self.id = local(str(c), capture=True)
        self.start_openvswitch(self.name)
        self.start_simpleRouter(self.name)
        self.is_running = True
        return 0

    def start_openvswitch(self, host):
        local("docker exec {0} /tmp/start_ovs.sh".format(host), capture=True)
        local("docker exec {0} ovs-vsctl add-br br0".format(host), capture=True)
        local("docker exec {0} ovs-vsctl set-controller br0 tcp:127.0.0.1:6633".format(host), capture=True)
        local("docker exec {0} ovs-vsctl set bridge br0 other-config:datapath-id=0000000000000001".format(host), capture=True)
        local("docker exec {0} ovs-vsctl set bridge br0 protocols=OpenFlow13".format(host), capture=True)
        local("docker exec {0} ovs-vsctl set-fail-mode br0 secure".format(host), capture=True)
        local("docker exec {0} ovs-vsctl set bridge br0 datapath_type=netdev".format(host), capture=True)


    def start_simpleRouter(self, host):
        local("docker exec {0} cp /tmp/OpenFlow.ini /root/simpleRouter/rest-client".format(host), capture=True)
        local("docker exec -d {0} ryu-manager /root/simpleRouter/ryu-app/openflowRouter.py --log-config-file /root/simpleRouter/ryu-app/logging.conf".format(host), capture=True)

    def create_wan_port(self, ifname, peer_addr, mac_addr):
        ifname_internal = "bgpPort_" + str(ifname)
        self.pipework('br_openflow', ifname, self.name)
        local("docker exec {0} ovs-vsctl add-port br0 {1}".format(self.name, ifname), capture=True)
        local("docker exec {0} ovs-vsctl add-port br0 {1} -- set Interface {1} type=internal".format(self.name, ifname_internal), capture=True)
        local("docker exec {0} ip addr add {1} dev {2}".format(self.name, peer_addr, ifname_internal), capture=True)
        local("docker exec {0} ip link set {1} address {2}".format(self.name, ifname_internal, mac_addr), capture=True)
        local("docker exec {0} ip link set {1} up".format(self.name, ifname_internal), capture=True)

    def create_lan_port(self, ifname, br_name, tenant_ip):
        self.pipework(br_name, ifname, self.name)
        local("docker exec {0} ovs-vsctl add-port br0 {1}".format(self.name, ifname), capture=True)
        ## Task: needs for registration of tenant_ip through rest-api

    def stop(self):
        local("docker rm -f " + self.name, capture=False)
        self.is_running = False

    def pipework(self, bridge, ifname, host):
        if not self.is_running:
            print ('*** call run() before pipeworking')
            return
        c = CmdBuffer(' ')
        c << "pipework {0}".format(bridge)

        if ifname != "":
            c << "-i {0} {1} 0.0.0.0/0".format(ifname, host)
            print ("### add_link_for_tenant {0} ###".format(ifname))
            return local(str(c), capture=True)


class Host(object):
    def __init__(self, name, serial, conn_ip, tenant_ip, tenant_num):
        self.name = name
        self.image = 'ubuntu:14.04.2'
        self.serial = serial
        self.conn_ip = conn_ip
        self.tenant_ip = tenant_ip
        self.tenant_num = tenant_num

        if self.name in get_containers():
            print ("### Delete connertainer {0} ###".format(self.name))
            self.stop()

    def run(self):
        c = CmdBuffer(' ')
        c << "docker run --privileged=true --net=none"
        c << "--name {0} -h {1} -itd {1}".format(self.name, self.image)
        c << "bash"

        print ("### Create connertainer {0} ###".format(self.name))
        self.id = local(str(c), capture=True)
        self.is_running = True
        self.add_link_for_wan(self.name, self.serial, self.conn_ip)
        self.add_link_for_lan(self.name, self.serial, self.tenant_ip, self.tenant_num)
        self.add_gw(self.conn_ip)
        return 0

    def add_link_for_wan(self, host, serial, hostip):
        subnet = IPNetwork(hostip)
        ipaddr = subnet.ip + 2
        mask = subnet.netmask
        prefix = IPNetwork(str(ipaddr) + '/' + str(mask))

        br_name = "br%03d"%serial + '-0'
        ifname = 'eth0'
        self.pipework(br_name, ifname, host, prefix)

    def add_link_for_lan(self, host, serial, hostip, num):
        for i in range(num):
            subnet = IPNetwork(hostip)
            ipaddr = subnet.ip + (256 * i) + 1
            mask = subnet.netmask
            prefix = IPNetwork(str(ipaddr) + '/' + str(mask))

            br_name = "br%03d"%serial + '-' + str(i+1)
            ifname = 'eth'+str(i+1)
            self.pipework(br_name, ifname, host, prefix)

    def add_gw(self, conn_ip):
        subnet = IPNetwork(conn_ip)
        ipaddr = subnet.ip + 1
        gateway = str(ipaddr)

        c = CmdBuffer(' ')
        c << "docker exec {0}".format(self.name)
        c << "route add -net 0.0.0.0/0 gw {0}".format(gateway)
        print ("### Add gateway {0} ###".format(self.name))
        return local(str(c), capture=True)

    def stop(self):
        local("docker rm -f " + self.name, capture=False)
        self.is_running = False

    def pipework(self, bridge, ifname, host, ip_addr):
        if not self.is_running:
            print ('*** call run() before pipeworking')
            return
        c = CmdBuffer(' ')
        c << "pipework {0}".format(bridge)

        if ifname != "":
            c << "-i {0}".format(ifname)
            c << "{0} {1}".format(host, ip_addr)
            print ("### add_link_for_tenant {0} ###".format(ifname))
            return local(str(c), capture=True)


class CmdBuffer(list):
    def __init__(self, delim='\n'):
        super(CmdBuffer, self).__init__()
        self.delim = delim

    def __lshift__(self, value):
        self.append(value)

    def __str__(self):
        return self.delim.join(self)


def get_bridges():
    return local("brctl show | awk '$3==\"no\"{print $1}'| grep -v 'docker0'",
                 capture=True).split('\n')

def get_containers():
    output = local("docker ps -a | awk 'NR > 1 {print $NF}'", capture=True)
    if output == '':
        return []
    return output.split('\n')

def create_host_tenant(wan_prefix_init, lan_prefix_init, num):
    global serial_number
    hosts = []

    for current in range(1, num+1):
        serial_number += 1
        if current == 1:
            wan_prefix = wan_prefix_init
            lan_prefix = lan_prefix_init
        else:
            wan_subnet = IPNetwork(wan_prefix)
            wan_ipaddr = wan_subnet.ip + 256 * 256
            wan_mask = wan_subnet.netmask
            wan_prefix = IPNetwork(str(wan_ipaddr) + '/' + str(wan_mask))

            lan_subnet = IPNetwork(lan_prefix)
            lan_ipaddr = lan_subnet.ip + 256 * 256
            lan_mask = lan_subnet.netmask
            lan_prefix = IPNetwork(str(lan_ipaddr) + '/' + str(lan_mask))

        host = "host_%03d"%serial_number
        hostname = Host(host, serial_number, wan_prefix, lan_prefix, 5)
        hosts.append(hostname)

    [host.run() for host in hosts]

def create_bgp_tenant(wan_prefix_init, num):
    pass

def deploy_host():
    create_host_tenant('130.1.0.0/24', '140.1.1.0/24', 2)


def deploy_simpleRouter():
    routername = Router('BGP')
    routername.run()
    routername.create_wan_port('eth1', '192.168.0.1/30', '00:00:00:00:01:01')
    routername.create_lan_port('eth2', 'br001-0', '130.1.0.1/24')
    routername.create_lan_port('eth3', 'br002-0', '130.2.0.1/24')
    local("brctl addif br_openflow eth1", capture=True)

if __name__ == '__main__':
    parser = OptionParser(usage="usage: %prog [install|start|stop|")
    options, args = parser.parse_args()

    if len(args) == 0:
        sys.exit(1)
    elif args[0] == 'install':
        install_docker_and_tools()
    elif args[0] == 'start':
        deploy_simpleRouter()
        deploy_host()
    elif args[0] == 'stop':
        for ctn in get_containers():
            local("docker rm -f {0}".format(ctn), capture=True)

        for bridge in get_bridges():
            local("ip link set down dev {0}".format(bridge), capture=True)
            local("ip link delete {0} type bridge".format(bridge), capture=True)
