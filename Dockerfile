# Use freesurfer as the base image
FROM freesurfer/freesurfer:7.4.1

RUN sed -i -e "s|mirrorlist=|#mirrorlist=|g" /etc/yum.repos.d/CentOS-*
RUN sed -i -e "s|#baseurl=http://mirror.centos.org|baseurl=http://vault.centos.org|g" /etc/yum.repos.d/CentOS-*

# Install python & python packages
RUN yum install -y python3-pip
RUN pip3 install pymeshlab==2021.10 nibabel==3.2.2

# Set work dir
WORKDIR /app

# Copy scripts to working directory
COPY main.py .

# Specify the command to run the Python script
ENTRYPOINT ["python3", "main.py"]