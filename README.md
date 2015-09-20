What's docker-pseudo-wan
==========
Dockerコンテナを活用して、MPLS-VPNネットワークの疑似環境を構築するものです.
なお、RyuBGPとBGPピア接続する対向BGPルータは、mp-BGPを動作させる必要があります.

	                       (static) +-----------+     mp-BGP    +----------+	
	host_001_xxx container -------+ |  RyuBGP   | +-----------+ |   BGP    | +---- ...
	host_002_xxx container -------+ | container | (eth1)        |  Router  |
	     :                          +-----------+               +----------+
	                     < AS65030 >   192.168.103.1         192.168.103.2  < AS9598 >

           <------- docker-pseudo-wanのスコープ ------>            <---- スコープ外 ---->


Environment
==========
Ubuntu Server版を推奨とします.

	$ cat /etc/lsb-release
	DISTRIB_ID=Ubuntu
	DISTRIB_RELEASE=14.04
	DISTRIB_CODENAME=trusty
	DISTRIB_DESCRIPTION="Ubuntu 14.04.3 LTS"


Dockerコンテナで構成されるWANネットワークと外部環境と通信するために、eth1のインタフェースを前提とします.
すなわち、RyuBGPと対向BGPルータのあいだでBGPピアを確立するためには、事前にeth1のインターフェースと結線しておく必要があります.

	$ ip link
	...
	3: eth1: <BROADCAST,MULTICAST,PROMISC,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP mode DEFAULT group default qlen 1000
	    link/ether 52:54:00:1a:b0:d5 brd ff:ff:ff:ff:ff:ff



Installation
==========
### 事前準備
OpenvSwitchをインストールして、"openvswitch"カーネルモジュールを組み込みます.
OpenvSwitch自体は起動する必要がないため、停止しておきます.

	$ sudo apt-get install openvswitch-switch
	$ sudo service openvswitch-switch stop
	openvswitch-switch stop/waiting

"openvswitch"カーネルモジュールが組み込まれたことを確認します.

	$ lsmod|grep open
	openvswitch            65844  0
	gre                    13796  1 openvswitch
	vxlan                  37629  1 openvswitch
	libcrc32c              12644  1 openvswitch

### リポジトリ情報
Githubよりリポジトリ情報を取得します.

	$ git clone https://github.com/ttsubo/docker-pseudo-wan.git

### インストール開始
ルート権限でdockerパッケージ類をインストールします.

	$ cd docker-pseudo-wan
	$ sudo apt-get install python-dev
	$ sudo apt-get install python-paramiko
	$ sudo apt-get install python-pip
	$ sudo pip install -r requirements.txt
	$ sudo python ./pseudo-wan.py install
	$ sudo gpasswd -a `whoami` docker


### インストール結果確認
グループ"docker"への反映を有効にするため、再ログインします.

	$ docker version
	Client version: 1.7.0
	Client API version: 1.19
	Go version (client): go1.4.2
	Git commit (client): 0baf609
	OS/Arch (client): linux/amd64
	Server version: 1.7.0
	Server API version: 1.19
	Go version (server): go1.4.2
	Git commit (server): 0baf609
	OS/Arch (server): linux/amd64


Dockerイメージを確認します.

	$ docker images
	REPOSITORY               TAG                 IMAGE ID            CREATED             VIRTUAL SIZE
	ttsubo/ryubgp-for-apgw   latest              7a23b20fcf52        4 days ago          644.5 MB
	ubuntu                   14.04.3             91e54dfb1179        4 weeks ago         188.4 MB


Quick Start
===========
### BGPピア接続用の設定ファイルの編集
RyuBGPと対向BGPルータ間でBGPピアを確立するための設定を行います.

	$ vi OpenFlow.ini 
	------------------------------
	[Bgp]
	as_number = "65030"
	router_id = "10.10.10.1"
	label_range_start = "1000"
	label_range_end = "1999"

	[Port]
	port = "1"
	macaddress = "00:00:00:01:01:01"
	ipaddress = "192.168.103.1"
	netmask = "255.255.255.252"
	opposite_ipaddress = "192.168.103.2"
	opposite_asnumber = "9598"
	port_offload_bgp = "2"
	bgp_med = "100"
	bgp_local_pref = ""
	bgp_filter_asnumber = ""
	vrf_routeDist = ""


ちなみに、BGPピアを確立するためのIPアドレス値は、Linuxネットワーク設定情報を使用しません.
実際にBGPピア接続で使用するIPアドレス値は、OpenFlow.iniで指定したipaddress"192.168.103.1"が使用されます.macaddressも同様です.

	$ ip addr
	...
	3: eth1: <BROADCAST,MULTICAST,PROMISC,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP group default qlen 1000
	    link/ether 52:54:00:1a:b0:d5 brd ff:ff:ff:ff:ff:ff
	    inet6 fe80::5054:ff:fe1a:b0d5/64 scope link 
	       valid_lft forever preferred_lft forever


"eth1"ネットワーク設定では、プロミスキャストを有効にしておきます.

	$ sudo vi /etc/network/interfaces
	...
	auto eth1
	iface eth1 inet manual
	up ifconfig $IFACE 0.0.0.0 up
	up ip link set $IFACE promisc on
	down ip link set $IFACE promisc off
	down ifconfig $IFACE down


### Dockerコンテナ起動
WANネットワークの疑似環境を構築します.

	$ sudo python pseudo-wan.py

	(...snip)


Dockerコンテナ実行状況を確認します.

	$ docker ps

	(...snip)

	CONTAINER ID        IMAGE                              COMMAND             CREATED             STATUS              PORTS                    NAMES
	c1429a74bbed        ubuntu:14.04.3                  "bash"              9 seconds ago        Up 9 seconds                                 host_010_1006110010   
	5fc162e06664        ubuntu:14.04.3                  "bash"              31 seconds ago       Up 30 seconds                                host_009_1006110009   
	1c5e2731c570        ubuntu:14.04.3                  "bash"              53 seconds ago       Up 53 seconds                                host_008_1006110008   
	25595efffbf7        ubuntu:14.04.3                  "bash"              About a minute ago   Up About a minute                            host_007_1006110007   
	6826e1893c33        ubuntu:14.04.3                  "bash"              About a minute ago   Up About a minute                            host_006_1006110006   
	a181caeb0704        ubuntu:14.04.3                  "bash"              About a minute ago   Up About a minute                            host_005_1006110005   
	dcbc5ac8d601        ubuntu:14.04.3                  "bash"              2 minutes ago        Up 2 minutes                                 host_004_1006110004   
	31a8efc5652f        ubuntu:14.04.3                  "bash"              2 minutes ago        Up 2 minutes                                 host_003_1006110003   
	a7bdef9965e2        ubuntu:14.04.3                  "bash"              3 minutes ago        Up 3 minutes                                 host_002_1006110002   
	ecfe4bf33260        ubuntu:14.04.3                  "bash"              3 minutes ago        Up 3 minutes                                 host_001_1006110001   
	f37e2b0a8175        ttsubo/ryubgp-for-apgw:latest   "bash"              4 minutes ago        Up 4 minutes        0.0.0.0:8080->8080/tcp   RyuBGP


### RyuBGPでの経路情報を確認
dockerコンテナ"RyuBGP"が開設しているBGPピア状態を確認してみます.
なお、コマンド操作は、Linux上で行います.

	$ cd show
	$ ./get_peer_status.sh
	======================================================================
	get_peer_status
	======================================================================
	/openflow/0000000000000001/status/peer
	----------
	reply: 'HTTP/1.1 200 OK\r\n'
	header: Content-Type: application/json; charset=UTF-8
	header: Content-Length: 197
	header: Date: Thu, 24 Sep 2015 01:17:12 GMT
	+++++++++++++++++++++++++++++++
	2015/09/24 01:17:12 : Peer Status
	+++++++++++++++++++++++++++++++
	occurTime            status    myPeer             remotePeer         asNumber
	-------------------- --------- ------------------ ------------------ --------
	2015/09/24 01:10:41  Peer Up   10.10.10.1         10.0.0.10          9598


つぎに、RyuBGPのインターフェース情報を確認してみます.
各インタフェースでのvrf収容構成については、RD値により識別することができます.

	$ ./get_interface.sh 
	======================================================================
	get_interface
	======================================================================
	/openflow/0000000000000001/interface
	----------
	reply: 'HTTP/1.1 200 OK\r\n'
	header: Content-Type: application/json; charset=UTF-8
	header: Content-Length: 2424
	header: Date: Thu, 24 Sep 2015 01:18:42 GMT
	+++++++++++++++++++++++++++++++
	2015/09/24 01:18:42 : PortTable
	+++++++++++++++++++++++++++++++
	portNo   IpAddress       MacAddress        RouteDist
	-------- --------------- ----------------- ---------
	       1 192.168.103.1   00:00:00:01:01:01 
	       3 10.1.0.1        00-00-00-00-00-01 9598:1006110001
	       4 10.2.0.1        00-00-00-00-00-02 9598:1006110002
	       5 10.3.0.1        00-00-00-00-00-03 9598:1006110003
	       6 10.4.0.1        00-00-00-00-00-04 9598:1006110004
	       7 10.5.0.1        00-00-00-00-00-05 9598:1006110005
	       8 10.6.0.1        00-00-00-00-00-06 9598:1006110006
	       9 10.7.0.1        00-00-00-00-00-07 9598:1006110007
	       a 10.8.0.1        00-00-00-00-00-08 9598:1006110008
	       b 10.9.0.1        00-00-00-00-00-09 9598:1006110009
	       c 10.10.0.1       00-00-00-00-00-0A 9598:1006110010

	(...snip)


RyuBGPが保持しているARPテーブルを確認することも可能です.
もし、対向BGPルータとの間でピア接続がうまく確立できない場合には、対向BGPルータのmacaddressが正しく学習できているかを確認します.

	$ ./get_arp.sh 
	======================================================================
	get_arp
	======================================================================
	/openflow/0000000000000001/arp
	----------
	reply: 'HTTP/1.1 200 OK\r\n'
	header: Content-Type: application/json; charset=UTF-8
	header: Content-Length: 2543
	header: Date: Thu, 24 Sep 2015 01:22:09 GMT
	+++++++++++++++++++++++++++++++
	2015/09/24 01:22:09 : ArpTable 
	+++++++++++++++++++++++++++++++
	portNo   MacAddress        IpAddress
	-------- ----------------- ------------
	       1 ca:07:1b:92:00:1d 192.168.103.2
	       3 1e:81:69:c3:04:b2 10.1.0.2
	       4 c6:4d:b0:db:72:80 10.2.0.2
	       5 a6:54:72:75:0f:d1 10.3.0.2
	       6 66:9f:cd:7e:6e:34 10.4.0.2
	       7 16:82:5b:24:d2:76 10.5.0.2
	       8 72:94:3e:3f:f3:2e 10.6.0.2
	       9 6e:f8:59:86:14:7b 10.7.0.2
	       a de:2f:a4:be:97:7f 10.8.0.2
	       b ca:b2:7d:4f:0f:3a 10.9.0.2
	       c 26:13:b3:1b:a5:e6 10.10.0.2

	(...snip)


さらに、dockerコンテナ"RyuBGP"で保持しているBGP経路情報を確認してみます.

	$ ./get_vrf.sh
	======================================================================
	get_vrf
	======================================================================
	/openflow/0000000000000001/vrf
	----------
	reply: 'HTTP/1.1 200 OK\r\n'
	header: Content-Type: application/json; charset=UTF-8
	header: Content-Length: 252656
	header: Date: Thu, 24 Sep 2015 01:24:13 GMT
	+++++++++++++++++++++++++++++++
	2015/09/24 01:24:12 : Show vrf 
	+++++++++++++++++++++++++++++++
	Status codes: * valid, > best
	Origin codes: i - IGP, e - EGP, ? - incomplete
	     Network                          Labels   Next Hop             Reason          Metric LocPrf Path

	(...snip)

	VPN: ('9598:1006110001', 'ipv4')
	 *>  110.1.9.0/24                     None     10.1.0.2             Only Path                     ?
	 *>  140.1.2.0/24                     None     192.168.103.2        AS Path                       9598 ?
	 *                                    None     192.168.103.2                                      9598 65000 ?
	 *>  110.1.0.0/24                     None     10.1.0.2             Only Path                     ?
	 *>  140.2.2.0/24                     None     192.168.103.2        AS Path                       9598 ?
	 *                                    None     192.168.103.2                                      9598 65000 ?
	 *>  110.1.6.0/24                     None     10.1.0.2             Only Path                     ?
	 *>  130.2.0.0/24                     None     192.168.103.2        AS Path                       9598 ?
	 *                                    None     192.168.103.2                                      9598 65000 ?
	 *>  110.1.17.0/24                    None     10.1.0.2             Only Path                     ?
	 *>  110.1.10.0/24                    None     10.1.0.2             Only Path                     ?
	 *>  110.1.11.0/24                    None     10.1.0.2             Only Path                     ?
	 *>  130.1.0.0/24                     None     192.168.103.2        AS Path                       9598 ?
	 *                                    None     192.168.103.2                                      9598 65000 ?
	 *>  140.2.5.0/24                     None     192.168.103.2        AS Path                       9598 ?
	 *                                    None     192.168.103.2                                      9598 65000 ?
	 *>  140.3.1.0/24                     None     192.168.103.2        AS Path                       9598 ?
	 *                                    None     192.168.103.2                                      9598 65000 ?
	 *>  110.1.18.0/24                    None     10.1.0.2             Only Path                     ?
	 *>  110.1.24.0/24                    None     10.1.0.2             Only Path                     ?
	 *>  110.1.12.0/24                    None     10.1.0.2             Only Path                     ?
	 *>  110.1.5.0/24                     None     10.1.0.2             Only Path                     ?
	 *>  110.1.2.0/24                     None     10.1.0.2             Only Path                     ?
	 *>  110.1.15.0/24                    None     10.1.0.2             Only Path                     ?
	 *>  10.79.5.0/24                     None     192.168.103.2        Only Path                     9598 ?
	 *>  10.1.1.1/32                      None     192.168.103.2        Only Path                     9598 ?
	 *>  110.1.27.0/24                    None     10.1.0.2             Only Path                     ?
	 *>  110.1.19.0/24                    None     10.1.0.2             Only Path                     ?
	 *>  10.1.0.2/32                      None     0.0.0.0              Only Path                     ?
	 *>  140.3.4.0/24                     None     192.168.103.2        AS Path                       9598 ?
	 *                                    None     192.168.103.2                                      9598 65000 ?
	 *>  140.3.3.0/24                     None     192.168.103.2        AS Path                       9598 ?
	 *                                    None     192.168.103.2                                      9598 65000 ?
	 *>  110.1.16.0/24                    None     10.1.0.2             Only Path                     ?
	 *>  110.1.29.0/24                    None     10.1.0.2             Only Path                     ?
	 *>  110.1.26.0/24                    None     10.1.0.2             Only Path                     ?
	 *>  110.1.23.0/24                    None     10.1.0.2             Only Path                     ?
	 *>  110.1.21.0/24                    None     10.1.0.2             Only Path                     ?
	 *>  110.1.25.0/24                    None     10.1.0.2             Only Path                     ?
	 *>  140.1.3.0/24                     None     192.168.103.2        AS Path                       9598 ?
	 *                                    None     192.168.103.2                                      9598 65000 ?
	 *>  140.1.4.0/24                     None     192.168.103.2        AS Path                       9598 ?
	 *                                    None     192.168.103.2                                      9598 65000 ?
	 *>  130.3.0.0/24                     None     192.168.103.2        AS Path                       9598 ?
	 *                                    None     192.168.103.2                                      9598 65000 ?
	 *>  110.1.3.0/24                     None     10.1.0.2             Only Path                     ?
	 *>  110.1.8.0/24                     None     10.1.0.2             Only Path                     ?
	 *>  110.1.28.0/24                    None     10.1.0.2             Only Path                     ?
	 *>  110.1.22.0/24                    None     10.1.0.2             Only Path                     ?
	 *>  110.1.20.0/24                    None     10.1.0.2             Only Path                     ?
	 *>  140.3.2.0/24                     None     192.168.103.2        AS Path                       9598 ?
	 *                                    None     192.168.103.2                                      9598 65000 ?
	 *>  140.2.1.0/24                     None     192.168.103.2        AS Path                       9598 ?
	 *                                    None     192.168.103.2                                      9598 65000 ?
	 *>  140.2.4.0/24                     None     192.168.103.2        AS Path                       9598 ?
	 *                                    None     192.168.103.2                                      9598 65000 ?
	 *>  140.2.3.0/24                     None     192.168.103.2        AS Path                       9598 ?
	 *                                    None     192.168.103.2                                      9598 65000 ?
	 *>  110.1.13.0/24                    None     10.1.0.2             Only Path                     ?
	 *>  110.1.7.0/24                     None     10.1.0.2             Only Path                     ?
	 *>  140.1.5.0/24                     None     192.168.103.2        AS Path                       9598 ?
	 *                                    None     192.168.103.2                                      9598 65000 ?
	 *>  110.1.1.0/24                     None     10.1.0.2             Only Path                     ?
	 *>  110.1.14.0/24                    None     10.1.0.2             Only Path                     ?
	 *>  140.1.1.0/24                     None     192.168.103.2        AS Path                       9598 ?
	 *                                    None     192.168.103.2                                      9598 65000 ?
	 *>  110.1.4.0/24                     None     10.1.0.2             Only Path                     ?
	 *>  140.3.5.0/24                     None     192.168.103.2        AS Path                       9598 ?
	 *                                    None     192.168.103.2                                      9598 65000 ?

	(...snip)


BGP経路情報に加えて、MPLSラベル情報も確認してみます.

	$ ./get_mpls.sh 
	======================================================================
	get_mpls
	======================================================================
	/openflow/0000000000000001/mpls
	----------
	reply: 'HTTP/1.1 200 OK\r\n'
	header: Content-Type: application/json; charset=UTF-8
	header: Content-Length: 453570
	header: Date: Thu, 24 Sep 2015 01:32:31 GMT
	+++++++++++++++++++++++++++++++
	2015/09/24 01:32:30 : MplsTable 
	+++++++++++++++++++++++++++++++
	routeDist  prefix             nexthop          label
	---------- ------------------ ---------------- -----
	9598:1006110001  10.1.0.2/32        0.0.0.0          1000 
	9598:1006110001  110.1.0.0/24       10.1.0.2         1001 
	9598:1006110001  110.1.1.0/24       10.1.0.2         1001 
	9598:1006110001  110.1.10.0/24      10.1.0.2         1001 
	9598:1006110001  110.1.11.0/24      10.1.0.2         1001 
	9598:1006110001  110.1.12.0/24      10.1.0.2         1001 
	9598:1006110001  110.1.13.0/24      10.1.0.2         1001 
	9598:1006110001  110.1.14.0/24      10.1.0.2         1001 
	9598:1006110001  110.1.15.0/24      10.1.0.2         1001 
	9598:1006110001  110.1.16.0/24      10.1.0.2         1001 
	9598:1006110001  110.1.17.0/24      10.1.0.2         1001 
	9598:1006110001  110.1.18.0/24      10.1.0.2         1001 
	9598:1006110001  110.1.19.0/24      10.1.0.2         1001 
	9598:1006110001  110.1.2.0/24       10.1.0.2         1001 
	9598:1006110001  110.1.20.0/24      10.1.0.2         1001 
	9598:1006110001  110.1.21.0/24      10.1.0.2         1001 
	9598:1006110001  110.1.22.0/24      10.1.0.2         1001 
	9598:1006110001  110.1.23.0/24      10.1.0.2         1001 
	9598:1006110001  110.1.24.0/24      10.1.0.2         1001 
	9598:1006110001  110.1.25.0/24      10.1.0.2         1001 
	9598:1006110001  110.1.26.0/24      10.1.0.2         1001 
	9598:1006110001  110.1.27.0/24      10.1.0.2         1001 
	9598:1006110001  110.1.28.0/24      10.1.0.2         1001 
	9598:1006110001  110.1.29.0/24      10.1.0.2         1001 
	9598:1006110001  110.1.3.0/24       10.1.0.2         1001 
	9598:1006110001  110.1.4.0/24       10.1.0.2         1001 
	9598:1006110001  110.1.5.0/24       10.1.0.2         1001 
	9598:1006110001  110.1.6.0/24       10.1.0.2         1001 
	9598:1006110001  110.1.7.0/24       10.1.0.2         1001 
	9598:1006110001  110.1.8.0/24       10.1.0.2         1001 
	9598:1006110001  110.1.9.0/24       10.1.0.2         1001 
	9598:1006110001  130.1.0.0/24       192.168.103.2    10589
	9598:1006110001  130.2.0.0/24       192.168.103.2    10000
	9598:1006110001  130.3.0.0/24       192.168.103.2    9948 
	9598:1006110001  140.1.1.0/24       192.168.103.2    10388
	9598:1006110001  140.1.2.0/24       192.168.103.2    10088
	9598:1006110001  140.1.3.0/24       192.168.103.2    10559
	9598:1006110001  140.1.4.0/24       192.168.103.2    10560
	9598:1006110001  140.1.5.0/24       192.168.103.2    10591
	9598:1006110001  140.2.1.0/24       192.168.103.2    10308
	9598:1006110001  140.2.2.0/24       192.168.103.2    10134
	9598:1006110001  140.2.3.0/24       192.168.103.2    10561
	9598:1006110001  140.2.4.0/24       192.168.103.2    10172
	9598:1006110001  140.2.5.0/24       192.168.103.2    10265
	9598:1006110001  140.3.1.0/24       192.168.103.2    10468
	9598:1006110001  140.3.2.0/24       192.168.103.2    10266
	9598:1006110001  140.3.3.0/24       192.168.103.2    10015
	9598:1006110001  140.3.4.0/24       192.168.103.2    8883 
	9598:1006110001  140.3.5.0/24       192.168.103.2    10505

	(...snip)


### Dockerコンテナへアクセス
dockerコンテナ"host_001_1006110001"にアクセスして、ネットワーク情報を確認してみます.
hostテナント側では、110.1.0.0/24 - 110.1.29.0/24までの30経路のIFを有効にすべきです.
本ツールでは、３０経路のうち、最初のIF（たとえば、"110.1.0.0/24"）しか作成しておりません.

	$ docker exec -it host_001_1006110001 bash
	# route -n
	Kernel IP routing table
	Destination     Gateway         Genmask         Flags Metric Ref    Use Iface
	0.0.0.0         10.1.0.1        0.0.0.0         UG    0      0        0 eth0
	10.1.0.0        0.0.0.0         255.255.255.0   U     0      0        0 eth0
	110.1.0.0       0.0.0.0         255.255.255.0   U     0      0        0 eth1


さらに、DC側vfwのインタフェース(130.1.0.4)に対して、疎通性を確認してみます.

	# ping 130.1.0.4
	PING 130.1.0.4 (130.1.0.4) 56(84) bytes of data.
	64 bytes from 130.1.0.4: icmp_seq=1 ttl=63 time=60.9 ms
	64 bytes from 130.1.0.4: icmp_seq=2 ttl=63 time=55.7 ms
	64 bytes from 130.1.0.4: icmp_seq=3 ttl=63 time=69.3 ms
	64 bytes from 130.1.0.4: icmp_seq=4 ttl=63 time=74.6 ms
	64 bytes from 130.1.0.4: icmp_seq=5 ttl=63 time=73.8 ms
	^C
	--- 130.1.0.4 ping statistics ---
	5 packets transmitted, 5 received, 0% packet loss, time 4006ms
	rtt min/avg/max/mdev = 55.711/66.908/74.673/7.417 ms

	# exit


### RyuBGPでの通過パケット流量を確認
RyuBGPが転送したパケット流量を、port単位で確認することも可能です.

	$ ./get_port_stats.sh 
	======================================================================
	get_portstats
	======================================================================
	/openflow/0000000000000001/stats/port
	----------
	reply: 'HTTP/1.1 200 OK\r\n'
	header: Content-Type: application/json; charset=UTF-8
	header: Content-Length: 12949
	header: Date: Thu, 24 Sep 2015 01:54:44 GMT
	+++++++++++++++++++++++++++++++
	2015/09/24 01:54:44 : PortStats
	+++++++++++++++++++++++++++++++
	portNo   rxPackets rxBytes  rxErrors txPackets txBytes  txErrors
	-------- --------- -------- -------- --------- -------- --------
	       1     24921 35660207        0     24021  1735423        0
	       2     23973  1609177        0     21386 21766653        0
	       3       107     7662        0       101     7242        0
	       4        52     2496        0        52     2496        0
	       5        51     2454        0        51     2454        0
	       6        51     2454        0        51     2454        0
	       7        51     2454        0        51     2454        0
	       8        50     2412        0        50     2412        0
	       9        50     2412        0        50     2412        0
	       a        50     2412        0        50     2412        0
	       b        49     2370        0        49     2370        0
	       c        49     2370        0        49     2370        0

	(...snip)


### Dockerコンテナ停止
Dockerコンテナを停止します.

	$ sudo python pseudo-wan.py stop

	(...snip)


Dockerコンテナが起動していないことを確認します.

	$ docker ps
	CONTAINER ID        IMAGE               COMMAND             CREATED             STATUS              PORTS
