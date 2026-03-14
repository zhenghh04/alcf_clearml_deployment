#!/bin/bash
set -e # Stop script on error

echo "--- 1. Installing Docker CE ---"
# Update and install prerequisites
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# Add Docker’s official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up the repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Verify Docker
sudo docker run hello-world

echo "--- 2. Installing Docker Compose ---"
# Downloading specific version mentioned in the guide (1.24.1)
sudo curl -L "https://github.com/docker/compose/releases/download/1.24.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

echo "--- 3. System Configuration (Elasticsearch & THP) ---"
# Increase vm.max_map_count for Elasticsearch
echo "vm.max_map_count=524288" | sudo tee /tmp/99-allegro.conf
echo "vm.overcommit_memory=1" | sudo tee -a /tmp/99-allegro.conf
echo "fs.inotify.max_user_instances=256" | sudo tee -a /tmp/99-allegro.conf
sudo mv /tmp/99-allegro.conf /etc/sysctl.d/99-allegro.conf
sudo sysctl -w vm.max_map_count=524288
sudo service docker restart

# Disable Transparent Huge Pages (THP)
sudo bash -c 'cat > /etc/systemd/system/disable-thp.service <<EOF
[Unit]
Description=Disable Transparent Huge Pages (THP)

[Service]
Type=simple
ExecStart=/bin/sh -c "echo never > /sys/kernel/mm/transparent_hugepage/enabled && echo never > /sys/kernel/mm/transparent_hugepage/defrag"

[Install]
WantedBy=multi-user.target
EOF'

sudo systemctl daemon-reload
sudo systemctl enable disable-thp
sudo systemctl start disable-thp

echo "--- 4. Creating ClearML Directories ---"
# Clean up old installs if any
sudo rm -rf /opt/clearml/
sudo rm -rf /opt/allegro/

# Create directories
sudo mkdir -pv /opt/allegro/data/elastic7plus
sudo mkdir -pv /opt/allegro/data/mongo_4/configdb
sudo mkdir -pv /opt/allegro/data/mongo_4/db
sudo mkdir -pv /opt/allegro/data/redis
sudo mkdir -pv /opt/allegro/data/fileserver
sudo mkdir -pv /opt/allegro/data/fileserver/tmp
sudo mkdir -pv /opt/allegro/logs/apiserver
sudo mkdir -pv /opt/allegro/documentation
sudo mkdir -pv /opt/allegro/logs/fileserver
sudo mkdir -pv /opt/allegro/logs/fileserver-proxy
sudo mkdir -pv /opt/allegro/data/fluentd/buffer
sudo mkdir -pv /opt/allegro/config/webserver_external_files
sudo mkdir -pv /opt/allegro/config/onprem_poc

# Set ownership (User 1000 is standard for the containers)
sudo chown -R 1000:1000 /opt/allegro

echo "--- 5. Setup Complete ---"
echo "You must now copy your 'docker-compose.yml', 'docker-compose.override.yml', and 'constants.env' to /opt/allegro/"
sudo cp -v override/* /opt/allegro/
# If you prefer to use URLs that do not begin with app, api, or files, you must also add the following configuration for the web server in your docker-compose.override.yml file:
#webserver:
#    environment:
#      - WEBSERVER__displayedServerUrls={"apiServer":"$APISERVER_URL_FOR_EXTERNAL_WORKERS","filesServer":"$FILESERVER_URL_FOR_EXTERNAL_WORKERS"}