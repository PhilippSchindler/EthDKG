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
# *     
RUN apt-get update \
  && apt-get install -y python3.7 python3.7-dev \
  && apt-get install -y python3-pip \
  #&& cd /usr/local/bin \
  #&& ln -s /usr/bin/python3.7 python \
  && python3.7 -m pip install --upgrade pip 
#	&& python3.7 -m pip install pipenv

# requirements for building underlying packages
# e.g., secp256k1 
RUN apt-get install -y build-essential pkg-config autoconf libtool libssl-dev libffi-dev libgmp-dev libsecp256k1-0 libsecp256k1-dev

RUN apt-get install -y python2.7 \
  && cd /usr/local/bin \
  && ln -s /usr/bin/python2.7 python
	
# install curl for the posibility to invoke rpc commands
RUN apt-get install -y curl

# requirements for ganache
# With custom node version:
# * install node version manager nvm
# * use nvm to install node version
# * use npm to install ganache-cli
RUN apt-get install -y git wget
RUN whoami
USER $UNAME
RUN whoami
RUN wget -qO- https://raw.githubusercontent.com/creationix/nvm/v0.33.11/install.sh | bash 
# NOTE: New bash instance needed since nvm is bunch of shell magic 
#RUN ["/bin/bash","-c","nvm install node"]
RUN /bin/bash -c "echo $HOME && source $HOME/.bashrc && source $HOME/.nvm/nvm.sh; nvm install node"
RUN /bin/bash -c "echo $HOME && source $HOME/.bashrc && source $HOME/.nvm/nvm.sh; npm install -g ganache-cli" 
USER root
RUN whoami

# get require solc version
# currently the latest 4. something version
RUN cd /usr/local/bin \
  && wget -qO solc https://github.com/ethereum/solidity/releases/download/v0.4.25/solc-static-linux \
  && chmod 755 solc 

# requirements for ganache
# System install, this does not always work!
#RUN apt-get isntall -y git npm 
#RUN npm install -g ganache-cli 

# basic system tools
RUN apt-get install -y vim 
  
# install requirements
RUN cd /ethdkg/ \
	&& python3.7 -m pip install -r requirements.txt

#port
EXPOSE 8545

#change final user
USER $UNAME

#CMD ["/bin/bash","ganache-cli","--networkId","1337","-h","0.0.0.0"]
CMD /bin/bash -c "source $HOME/.bashrc && source $HOME/.nvm/nvm.sh && ganache-cli --networkId 1337 -h 0.0.0.0"
