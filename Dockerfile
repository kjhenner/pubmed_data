FROM debian:latest
MAINTAINER Kevin Henner <kjhenner@gmail.com>

RUN apt-get -qq update && apt-get -qq -y install python python-pip python-dev build-essential gfortran libatlas-base-dev libxml2-dev libxslt-dev lib32z1-dev curl
RUN pip install --upgrade pip
RUN pip install python-sql numpy scipy matplotlib scikit-learn nltk neo4j-driver lxml
