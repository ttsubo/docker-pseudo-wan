What's docker-pseudo-wan
==========
Dockerコンテナを活用して、WANネットワークの疑似環境を構築するものです. 


Environment
==========
Ubuntu Server版を推奨とします.

	$ cat /etc/lsb-release 
	DISTRIB_ID=Ubuntu
	DISTRIB_RELEASE=14.04
	DISTRIB_CODENAME=trusty
	DISTRIB_DESCRIPTION="Ubuntu 14.04.3 LTS"

Dockerコンテナで構成されるWANネットワークと外部環境と通信するために、eth1のインタフェースを前提とします.

	$ ip link
        ...
	3: eth1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP mode DEFAULT group default qlen 1000
	    link/ether 00:0c:29:fc:4f:25 brd ff:ff:ff:ff:ff:ff


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
	REPOSITORY                 TAG                 IMAGE ID            CREATED             VIRTUAL SIZE
	ttsubo/ryubgp-w-ovs2_3_1   latest              acc83513331e        4 hours ago         640.9 MB
	ubuntu                     14.04.2             63e3c10217b8        4 weeks ago         188.4 MB


Quick Start
===========
### Dockerコンテナ起動
WANネットワークの疑似環境を構築します.

	$ sudo python pseudo-wan.py start

	(...snip)


Dockerコンテナ実行状況を確認します.

	$ docker ps
	CONTAINER ID        IMAGE                             COMMAND             CREATED             STATUS              PORTS               NAMES

	(...snip)
	53c8ecb408a2        ubuntu:14.04.2                    "bash"              20 seconds ago      Up 19 seconds                           host_002            
	d75712aa7402        ubuntu:14.04.2                    "bash"              21 seconds ago      Up 20 seconds                           host_001            
	2e7daa9472ab        ttsubo/ryubgp-w-ovs2_3_1:latest   "bash"              22 seconds ago      Up 21 seconds                           BGP 


Linuxブリッジ動作状況を確認します.

	$ brctl show

	(...snip)
	br001-0		8000.26d81e0f1150	no		veth0pl15223
								veth2pl14469
	br001-1		8000.de5df3684915	no		veth1pl15223
	br001-2		8000.26ff6e6d48f4	no		veth2pl15223
	br001-3		8000.c253624e0316	no		veth3pl15223
	br001-4		8000.5e7349365cad	no		veth4pl15223
	br001-5		8000.166bc3d3012f	no		veth5pl15223
	br002-0		8000.065a7b8e9d06	no		veth0pl15969
								veth3pl14469
	br002-1		8000.163fb46b5c34	no		veth1pl15969
	br002-2		8000.72ee38fb374f	no		veth2pl15969
	br002-3		8000.3637a58a2a3e	no		veth3pl15969
	br002-4		8000.da626c03f655	no		veth4pl15969
	br002-5		8000.46f6b58c3304	no		veth5pl15969
	br_openflow		8000.000c29fc4f25	no		eth1
								veth1pl14469


### Dockerコンテナへアクセス
例えば、dockerコンテナ"host_001_2001"にアクセスして、ネットワーク情報を確認してみます.

	$ docker exec -it host_001_2001 bash
	# ip route
	default via 130.1.0.1 dev vnic1.2001 
	130.1.0.0/24 dev vnic1.2001  proto kernel  scope link  src 130.1.0.4 
	130.1.0.0/24 dev vnic2.2001  proto kernel  scope link  src 130.1.0.5 
	140.1.1.0/24 dev eth0  proto kernel  scope link  src 140.1.1.1 
	140.1.2.0/24 dev eth1  proto kernel  scope link  src 140.1.2.1 
	140.1.3.0/24 dev eth2  proto kernel  scope link  src 140.1.3.1 
	140.1.4.0/24 dev eth3  proto kernel  scope link  src 140.1.4.1 
	140.1.5.0/24 dev eth4  proto kernel  scope link  src 140.1.5.1 
	# exit




### Dockerコンテナ停止
Dockerコンテナを停止します.

	$ sudo python pseudo-dc.py stop

	(...snip)


Dockerコンテナが起動していないことを確認します.

	$ docker ps
	CONTAINER ID        IMAGE               COMMAND             CREATED             STATUS              PORTS

