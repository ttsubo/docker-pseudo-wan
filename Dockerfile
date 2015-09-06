FROM ubuntu:15.04

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update -y

### Install OpenvSwitch
RUN apt-get install -y openvswitch-switch

### Install Ryu controller
RUN apt-get install -y python-dev python-pip python-lxml python-paramiko
RUN apt-get install -y libxml2-dev
RUN apt-get install -y git
RUN pip install --upgrade six
WORKDIR /root
RUN git clone https://github.com/osrg/ryu.git
WORKDIR /root/ryu/tools
RUN pip install -r pip-requires
WORKDIR /root/ryu
RUN python ./setup.py install

### Install simpleRouter
WORKDIR /root
RUN git clone https://github.com/ttsubo/simpleRouter.git
WORKDIR /root/simpleRouter
RUN git checkout master

### Install utility-tool
RUN apt-get install -y iputils-ping net-tools vim
WORKDIR /root
