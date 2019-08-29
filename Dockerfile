# Docker file for python in ubuntu
FROM ubuntu:devel

WORKDIR /ethdkg

COPY . /ethdkg

# Add a user given as build argument
ARG UNAME=user
ARG UID=1000
ARG GID=1000
RUN groupadd -g $GID -o $UNAME
RUN useradd -m -u $UID -g $GID -o -s /bin/bash $UNAME

# basic python setup
# Notes:
# * python3-pip because dedicated python3.7-pip was not yet available
#		but you can install modules for 3.7 by invoking it like this
#   python3.7 -m pip --version
#
RUN apt-get update \
  && apt-get install -y python3.7 python3.7-dev \
  && apt-get install -y python3-pip \
  && python3.7 -m pip install --upgrade pip 

# requirements for building underlying packages
# e.g., secp256k1 
RUN apt-get install -y build-essential pkg-config autoconf libtool libssl-dev libffi-dev libgmp-dev libsecp256k1-0 libsecp256k1-dev

# install some tools for debugging 
RUN apt-get install -y git wget vim iputils-ping netcat iproute2  

# install requirements
RUN cd /ethdkg/ \
	&& python3.7 -m pip install -r requirements.txt

# install ethdkg python package
RUN pip install -e /ethdkg

#change final user
USER $UNAME

CMD ["/bin/bash"]
